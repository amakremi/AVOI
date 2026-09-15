"""Append Stage-2 confirmation sources to data/manifests/dataset_sources.json (selection rules fixed a priori)."""
import json
from pathlib import Path

p = Path(__file__).resolve().parent / "manifests" / "dataset_sources.json"
reg = json.loads(p.read_text(encoding="utf-8"))
ids = {s["id"] for s in reg["sources"]}
new = [
    {"id": "ait_lds_v2_fox", "testbed": "fox", "size": 15837626707, "md5": "b6cd133398fbed6f3e7434dafbc45756",
     "role": "Stage-2 adequacy-validation testbed (smallest unused AIT-LDS v2.0 archive)"},
    {"id": "ait_lds_v2_harrison", "testbed": "harrison", "size": 16773705987, "md5": "4fbe3dd17a194776b2851116f8b51380",
     "role": "Stage-2 confirmation testbed (2nd smallest unused archive)"},
    {"id": "ait_lds_v2_wardbeck", "testbed": "wardbeck", "size": 17163231368, "md5": "ff524634e64c7779def2eb804e8c52ac",
     "role": "Stage-2 confirmation testbed (3rd smallest unused archive)"},
]
for n in new:
    if n["id"] in ids:
        continue
    reg["sources"].append({
        "id": n["id"], "dataset": f"AIT Log Data Set V2.0 - testbed {n['testbed']}", "version": "v2_0",
        "organization": "AIT Austrian Institute of Technology", "source_page": "https://zenodo.org/records/5789064",
        "url": f"https://zenodo.org/records/5789064/files/{n['testbed']}.zip?download=1", "filename": f"ait/{n['testbed']}.zip",
        "doi": "10.5281/zenodo.5789064", "license": "CC BY-NC-SA 4.0", "published_checksum": f"md5:{n['md5']}",
        "role": n["role"], "stage": 2})
if "cert_r5_2" not in ids:
    reg["sources"].append({
        "id": "cert_r5_2", "dataset": "CERT Insider Threat Test Dataset release r5.2", "version": "r5.2",
        "organization": "Carnegie Mellon University Software Engineering Institute (CERT Division) / ExactData",
        "source_page": "https://kilthub.cmu.edu/articles/dataset/Insider_Threat_Test_Dataset/12841247",
        "url": "https://ndownloader.figshare.com/files/24849938", "filename": "cert/r5.2.tar.bz2", "doi": "10.1184/R1/12841247.v1",
        "license": "CC BY 4.0", "published_checksum": "md5:e24c10807f4923b731276c3421a13c9f",
        "role": "Stage-2 external confirmation release (only other 'dense needle' release with many instances per scenario)",
        "stage": 2})
reg["stage2_selection_rationale"] = {
    "ait": "Fixed before any Stage-2 evaluation: the three smallest AIT-LDS v2.0 archives not used in Stage 1 (fox, harrison, "
           "wardbeck), ordered by archive size only. Role rule: smallest -> adequacy validation; the other two -> confirmation.",
    "cert": "r5.2 is the only other release whose answer key contains per-scenario instance directories (many insiders per "
            "scenario); r4.1, r5.1, r6.1 and r6.2 contain one instance per scenario, giving too few refuted user-weeks. "
            "r5.2 users are split by a seeded user-level partition into adequacy-validation (40%) and confirmation (60%).",
}
p.write_text(json.dumps(reg, indent=2), encoding="utf-8")
print(len(reg["sources"]))
