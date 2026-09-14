"""Keycloak testbed access layer: admin REST client, PostgreSQL access, scripted browser-flow login.

Credentials below are testbed-only values defined in docker-compose.yml (bound to 127.0.0.1).
"""
from __future__ import annotations

import base64
import html
import json
import re
import subprocess
import time
import urllib.parse as up
from dataclasses import dataclass, field

import pg8000.native
import pyotp
import requests

KC_BASE = "http://127.0.0.1:58080"
REPO_BASE = "http://127.0.0.1:58081"
DB = dict(user="keycloak", host="127.0.0.1", port=55432, password="keycloak-testbed-only", database="keycloak")
REDIRECT = "http://localhost/cb"


# Sensitive-category detection on the payloads ACTUALLY accessed by an acquisition (keys / CSV headers / source type).
KEY_CATEGORY = {
    "username": "user_identifier", "firstName": "user_identifier", "lastName": "user_identifier", "userId": "user_identifier",
    "full_name": "user_identifier", "subject": "user_identifier", "employee_id": "user_identifier", "scope": "user_identifier",
    "email": "email_address",
    "ipAddress": "ip_address",
    "termination_date": "hr_employment_record",
    "last_login": "authentication_event", "login_time": "authentication_event",
    "decisions": "role_group_membership", "approved_date": "role_group_membership",
}


def detect_categories(obj=None, source: str = "", header: list[str] | None = None) -> set[str]:
    cats: set[str] = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in KEY_CATEGORY and v not in (None, "", [], {}):
                    cats.add(KEY_CATEGORY[k])
                if k == "type" and v == "emergency":
                    cats.add("security_incident_information")
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    for h in header or []:
        if h in KEY_CATEGORY:
            cats.add(KEY_CATEGORY[h])
    nonempty = obj not in (None, [], {}, "") or bool(header)
    if nonempty:
        if "/admin-events" in source:
            cats.add("role_group_membership")
        elif "/events" in source:
            cats.add("authentication_event")
        if "role-mappings" in source or "/members" in source or ("/roles/" in source and source.endswith("/users")) \
                or source.endswith("/groups"):
            cats.add("role_group_membership")
        if source.startswith("hr/") or "/hr/" in source:
            cats.add("hr_employment_record")
        if "siem/" in source:
            cats.add("authentication_event")
    return cats


@dataclass
class IOStats:
    """Accumulates bytes, records and sensitive categories touched by an acquisition."""
    bytes_read: int = 0
    records: int = 0
    calls: int = 0
    categories: set = field(default_factory=set)

    def add(self, nbytes: int, nrecords: int = 0, categories: set | None = None):
        self.bytes_read += int(nbytes)
        self.records += int(nrecords)
        self.calls += 1
        if categories:
            self.categories |= categories


class KeycloakAdmin:
    def __init__(self):
        self._token, self._exp = None, 0.0
        self.http = requests.Session()

    def token(self) -> str:
        if time.time() > self._exp - 20:
            r = requests.post(f"{KC_BASE}/realms/master/protocol/openid-connect/token",
                              data={"grant_type": "password", "client_id": "admin-cli", "username": "admin",
                                    "password": "admin-testbed-only"}, timeout=30)
            r.raise_for_status()
            j = r.json()
            self._token, self._exp = j["access_token"], time.time() + j.get("expires_in", 60)
        return self._token

    def req(self, method: str, path: str, stats: IOStats | None = None, **kw):
        url = path if path.startswith("http") else f"{KC_BASE}/admin/realms{path}"
        for attempt in range(4):
            r = self.http.request(method, url, headers={"Authorization": f"Bearer {self.token()}"}, timeout=60, **kw)
            if r.status_code in (502, 503) and attempt < 3:
                time.sleep(2)
                continue
            break
        if r.status_code >= 400 and not (method == "DELETE" and r.status_code == 404):
            raise RuntimeError(f"{method} {url} -> {r.status_code} {r.text[:300]}")
        body = r.json() if r.content and "json" in r.headers.get("Content-Type", "") else None
        if stats is not None:
            stats.add(len(r.content), len(body) if isinstance(body, list) else (1 if body else 0),
                      detect_categories(body, url.split("?")[0]))
        return body, r

    def get(self, path, stats=None, **params):
        return self.req("GET", path, stats, params=params)[0]

    def post(self, path, json_body=None):
        return self.req("POST", path, json=json_body)[1]

    def put(self, path, json_body=None):
        return self.req("PUT", path, json=json_body)[1]

    def delete(self, path):
        return self.req("DELETE", path)[1]


def db() -> pg8000.native.Connection:
    return pg8000.native.Connection(**DB)


def repo_get(path: str, stats: IOStats | None = None):
    """Fetch an artifact from the documentary evidence repository. Returns (content or None, kind)."""
    r = requests.get(f"{REPO_BASE}/{path}", timeout=30)
    if r.status_code == 404:
        if stats is not None:
            stats.add(len(r.content), 0)
        return None
    r.raise_for_status()
    if path.endswith(".json"):
        body = r.json()
        if stats is not None:
            n = len(body) if isinstance(body, list) else len(body.get("rows", body.get("decisions", []))) or 1
            stats.add(len(r.content), n, detect_categories(body, path))
        return body
    text = r.text
    if stats is not None:
        rows = text.splitlines()
        stats.add(len(r.content), max(0, len(rows) - 1), detect_categories(None, path, rows[0].split(",") if len(rows) > 1 else None))
    return text


def docker_exec(container: str, cmd: str, stats: IOStats | None = None) -> str:
    out = subprocess.run(["docker", "exec", container, "sh", "-c", cmd], capture_output=True, text=True, timeout=60)
    if stats is not None:
        # host inspection always reveals the host identifier; account entries reveal user identifiers
        cats = {"host_device_identifier"} | ({"user_identifier"} if out.stdout.strip() else set())
        stats.add(len(out.stdout.encode()), out.stdout.count("\n"), cats)
    return out.stdout


@dataclass
class LoginResult:
    outcome: str          # authenticated | otp_challenged | otp_enrolment_required | failed
    detail: str = ""
    bytes: int = 0
    otp_secret: str | None = None


def browser_login(realm: str, client_id: str, username: str, password: str, otp_secret: str | None = None,
                  complete_otp: bool = False) -> LoginResult:
    """Scripted browser (authorization-code) flow. Keycloak sets Secure cookies; they are forwarded explicitly
    because the testbed is served over plain HTTP on localhost.

    complete_otp=False  -> stop at the first OTP challenge (TEST mode, used by collectors/oracle)
    complete_otp=True   -> answer OTP / perform TOTP enrolment (history simulation only)
    """
    jar: dict[str, str] = {}
    nbytes = 0

    def store(resp):
        for c in resp.cookies:
            jar[c.name] = c.value

    def cookie_header():
        return "; ".join(f"{k}={v}" for k, v in jar.items())

    s = requests.Session()
    r = s.get(f"{KC_BASE}/realms/{realm}/protocol/openid-connect/auth",
              params={"client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT, "scope": "openid"},
              allow_redirects=False, timeout=30)
    store(r)
    nbytes += len(r.content)
    m = re.search(r'action="([^"]+)"', r.text)
    if not m:
        return LoginResult("failed", f"no login form ({r.status_code})", nbytes)
    r = requests.post(html.unescape(m.group(1)), data={"username": username, "password": password, "credentialId": ""},
                      headers={"Cookie": cookie_header()}, allow_redirects=False, timeout=30)
    store(r)
    nbytes += len(r.content)
    secret = otp_secret
    for _ in range(15):
        loc = r.headers.get("Location", "")
        if r.status_code in (302, 303) and loc.startswith(REDIRECT):
            return LoginResult("authenticated", "", nbytes, secret)
        if r.status_code in (302, 303):
            r = requests.get(loc if loc.startswith("http") else KC_BASE + loc, headers={"Cookie": cookie_header()},
                             allow_redirects=False, timeout=30)
            store(r)
            nbytes += len(r.content)
            continue
        body = r.text
        if 'id="kc-totp-settings-form"' in body or "totpSecret" in body:
            if not complete_otp:
                return LoginResult("otp_enrolment_required", "", nbytes)
            sec = re.search(r'name="totpSecret"[^>]*value="([^"]+)"', body) or re.search(r'value="([^"]+)"[^>]*name="totpSecret"', body)
            act = re.search(r'id="kc-totp-settings-form"[^>]*action="([^"]+)"', body) or re.search(r'action="([^"]+)"', body)
            raw_secret = html.unescape(sec.group(1))
            secret = base64.b32encode(raw_secret.encode()).decode()  # Keycloak uses the raw secret bytes as HMAC key
            code = pyotp.TOTP(secret).now()
            r = requests.post(html.unescape(act.group(1)), data={"totp": code, "totpSecret": raw_secret, "userLabel": "testbed",
                                                                 "mode": "manual"},
                              headers={"Cookie": cookie_header()}, allow_redirects=False, timeout=30)
            store(r)
            nbytes += len(r.content)
            continue
        if 'id="kc-otp-login-form"' in body or 'name="otp"' in body:
            if not complete_otp:
                return LoginResult("otp_challenged", "", nbytes)
            if not secret:
                return LoginResult("failed", "otp requested but no secret", nbytes)
            act = re.search(r'id="kc-otp-login-form"[^>]*action="([^"]+)"', body) or re.search(r'action="([^"]+)"', body)
            r = requests.post(html.unescape(act.group(1)), data={"otp": pyotp.TOTP(secret).now()},
                              headers={"Cookie": cookie_header()}, allow_redirects=False, timeout=30)
            store(r)
            nbytes += len(r.content)
            continue
        return LoginResult("failed", re.sub(r"\s+", " ", body)[:200], nbytes)
    return LoginResult("failed", "too many steps", nbytes)


