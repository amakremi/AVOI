"""STAGE 3 / WP2 - CERT external evidence-model development and adequacy.

Development: r4.2, r5.2 (previously examined; cross-release validation train r4.2->test r5.2 and reverse).
New (untouched) releases: r4.1, r5.1, r6.1, r6.2, pooled and split label-blind by 'release:user' into
calibration (20%) / adequacy_validation (40%) / confirmation (40%) - see config/stage3.yaml wp2.cert.

  python experiments/stage3/run_wp2_cert.py devcheck
  python experiments/stage3/run_wp2_cert.py adequacy
  python experiments/stage3/run_wp2_cert.py confirm
"""
from __future__ import annotations

import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "stage3"))

from avoi import adequacy as AQ  # noqa: E402
from avoi.costs import CostModel  # noqa: E402
from avoi.datasets.cert import CLAIM, load_cert  # noqa: E402
from avoi.datasets.common import Discretizer  # noqa: E402
from avoi.evaluation import engine as E  # noqa: E402
from avoi.evaluation import stage2 as S  # noqa: E402
from avoi.evaluation import stage3 as S3M  # noqa: E402
from avoi.evaluation import stage3_wp2 as W2  # noqa: E402
from avoi.evaluation.labels import load_labels  # noqa: E402
from avoi.evaluation.stage3 import S3  # noqa: E402

DEV_RELEASES = {"r4.2": "data/processed/cert", "r5.2": "data/processed/cert_stage2"}
# r6.1/r6.2 dropped before any Stage-3 label was read - see config/stage3.yaml wp2.cert.new_releases and
# docs/STAGE3_EXTERNAL_MODELS.md Section 2b (single-threaded bz2 decompression time budget, not a data-driven choice).
NEW_RELEASES = {"r4.1": "data/processed/cert_stage3_r4_1", "r5.1": "data/processed/cert_stage3_r5_1"}


def require_new_releases():
    missing = [r for r, d in NEW_RELEASES.items() if not (ROOT / d / "evidence_store.json").exists()]
    if missing:
        raise FileNotFoundError(f"CERT Stage-3 releases not yet built: {missing} (run experiments/stage3/build_cert_stage3.py)")


def load_release(name: str, out_dir: str):
    data = load_cert(out_dir)[CLAIM]
    label_domain = "cert" if out_dir == "data/processed/cert" else ("cert_stage2" if out_dir == "data/processed/cert_stage2" else out_dir.split("/")[-1])
    y = load_labels(label_domain, data.episode_ids)
    return data, y


def develop_cert(C: dict):
    dev_data = {}
    for name, out_dir in DEV_RELEASES.items():
        dev_data[name] = load_release(name, out_dir)
    K = [len(a.outcomes) for a in dev_data["r4.2"][0].actions]
    disc = Discretizer().fit(np.concatenate([d.values for d, _ in dev_data.values()]))
    codes_by_release = {name: (disc.transform(d.values), y) for name, (d, y) in dev_data.items()}
    cands = W2.lodo_candidates(codes_by_release, K, None, C)
    chosen = W2.select_candidate(cands)
    all_data = S3M.concat([d for d, _ in dev_data.values()], list(dev_data), "cert_s3")
    all_y = np.concatenate([y for _, y in dev_data.values()])
    codes_all = disc.transform(all_data.values)
    base = W2.fit_final(chosen["kind"], chosen.get("alpha"), K, codes_all, all_y, C)
    cost = CostModel.fit(all_data.records, all_data.bytes_, all_data.seconds, all_data.n_categories(), "B")
    stability = W2.feature_stability(codes_by_release, [a.action_id for a in all_data.actions])
    return {"all_data": all_data, "all_y": all_y, "disc": disc, "base": base, "cost": cost, "candidates": cands,
            "chosen": chosen, "stability": stability, "K": K}


def load_new_pool(disc):
    require_new_releases()
    datas, ys, releases = [], [], []
    for name, out_dir in NEW_RELEASES.items():
        d, y = load_release(name, out_dir)
        datas.append(d); ys.append(y); releases.append(name)
    pool = S3M.concat(datas, releases, "cert_s3_new")
    y = np.concatenate(ys)
    return pool, y


def new_split(pool, C: dict):
    c = C["s3"]["cert"]
    users = pool.groups   # already "release:user" via S3M.concat (never collide across releases)
    frac = np.array([S3M.hash_fraction(c["user_split"]["seed"], u) for u in users])
    cal = frac < 20
    val = (frac >= 20) & (frac < 60)
    conf = frac >= 60
    return cal, val, conf, users


def devcheck():
    C = S.cfg(); C["s3"] = S3M.cfg3()["wp2"]
    dev = develop_cert(C)
    print("candidates (worst-fold AUROC):", [(c["kind"], c.get("alpha"), round(c["worst_fold_AUROC"], 3), round(c["median_PR_skill"], 3)) for c in dev["candidates"]])
    print("selected:", dev["chosen"]["kind"], dev["chosen"].get("alpha"), "passed_pr_skill_filter", dev["chosen"]["passed_pr_skill_filter"])
    flips = dev["stability"][dev["stability"]["direction_reverses"]]["action_id"].tolist()
    print("unstable features:", flips)
    S3M.save_json({"chosen": {k: v for k, v in dev["chosen"].items() if k != "fold_metrics"}, "candidates": [{k: v for k, v in c.items() if k != "fold_metrics"} for c in dev["candidates"]]},
                 S3 / "development" / "wp2_cert_devcheck.json")
    dev["stability"].to_csv(S3 / "development" / "wp2_cert_feature_stability.csv", index=False)
    require_new_releases()
    print("new releases available; devcheck complete")


def variants(dev, C):
    pool, y = load_new_pool(dev["disc"])
    cal, val, conf, users = new_split(pool, C)
    codes = dev["disc"].transform(pool.values)
    kind, alpha = dev["chosen"]["kind"], dev["chosen"].get("alpha")
    model_id_zs = f"cert_s3:{CLAIM}:{kind}(alpha={alpha})+zero_shot"
    zero_shot = AQ.CalibratedEvidenceModel(dev["base"], AQ.Calibrator("none").fit(np.array([0.5]), np.array([1])), model_id_zs)
    p_cal = np.array([dev["base"].posterior(tuple((j, int(codes[i, j])) for j in range(codes.shape[1]))) for i in range(len(y)) if cal[i]])
    y_cal, u_cal = y[cal], users[cal]
    name, scores, calr, rejected = S3M.monotone_calibrator(p_cal, y_cal, u_cal, C["adequacy"]["calibration_candidates"], C["adequacy"]["bootstrap"]["seed"])
    model_id_tc = f"cert_s3:{CLAIM}:{kind}(alpha={alpha})+target_{name}"
    target_cal = AQ.CalibratedEvidenceModel(dev["base"], calr, model_id_tc)
    return {"pool": pool, "y": y, "codes": codes, "cal": cal, "val": val, "conf": conf, "users": users,
            "zero_shot": zero_shot, "target_calibrated": target_cal, "calibrator_name": name, "calibrator_scores": scores,
            "rejected_calibrators": rejected}


def validate_model(model, codes, y, groups, ref_prev, C):
    p = np.array([model.posterior(tuple((j, int(codes[i, j])) for j in range(codes.shape[1]))) for i in range(len(y))])
    pol = C["adequacy"]
    m = AQ.point_metrics(y, p, ref_prev, pol["ece_bins"])
    boot = AQ.group_bootstrap(y, p, groups, ref_prev, pol["bootstrap"]["n_resamples"], pol["bootstrap"]["seed"], pol["bootstrap"]["confidence"], pol["ece_bins"])
    return m, boot, p


def adequacy_phase() -> dict:
    C = S.cfg(); C["s3"] = S3M.cfg3()["wp2"]
    dev = develop_cert(C)
    var = variants(dev, C)
    val_idx = var["val"]
    ref_prev = float(np.mean(dev["all_y"]))
    m_zs, boot_zs, p_zs = validate_model(var["zero_shot"], var["codes"][val_idx], var["y"][val_idx], var["users"][val_idx], ref_prev, C)
    m_tc, boot_tc, p_tc = validate_model(var["target_calibrated"], var["codes"][val_idx], var["y"][val_idx], var["users"][val_idx], ref_prev, C)
    gwv = int(len(set(var["users"][val_idx][var["y"][val_idx] == 0])))
    dec = AQ.decide(var["target_calibrated"].model_id, m_tc, boot_tc, C["adequacy"], var["calibrator_name"], groups_with_violation=gwv)
    rec = {"work_package": "WP2", "domain": "cert", "objective": CLAIM, "model_id": dec.model_id, "decision": asdict(dec),
           "development_releases": list(DEV_RELEASES), "new_releases": list(NEW_RELEASES),
           "selection": {"chosen_model": {k: v for k, v in dev["chosen"].items() if k != "fold_metrics"}, "calibrator": var["calibrator_name"],
                        "calibrator_cv_log_loss": var["calibrator_scores"], "rejected_non_monotone_calibrators": var["rejected_calibrators"]},
           "target_calibrated": {"metrics": m_tc, "bootstrap": boot_tc}, "zero_shot": {"metrics": m_zs, "bootstrap": boot_zs},
           "groups_with_violation": gwv, "prevalence_satisfied_dev": ref_prev}
    S3M.save_json(rec, S3 / "validation" / "wp2_cert.json")
    print(CLAIM, dec.status, dec.reason, "target-calibrated AUROC", round(m_tc["AUROC"], 3), "zero-shot AUROC", round(m_zs["AUROC"], 3), flush=True)
    return rec


def confirm():
    from run_stage3 import verify_freeze, load_decisions
    verify_freeze()
    decisions = load_decisions()
    C = S.cfg(); C["s3"] = S3M.cfg3()["wp2"]
    from avoi.bayes_risk import LossMatrix
    lcfg = C["loss"]; w = lcfg["preference_weights"]
    loss = LossMatrix(lcfg["primary"]["false_assurance"], lcfg["primary"]["false_non_assurance"], lcfg["primary"]["human_review"])
    S.CONFLICT["flags"] = None   # CERT has no IAM-style evidence-polarity conflict flag; clear any stale global from WP1/WP2-AIT
    dev = develop_cert(C)
    var = variants(dev, C)
    fd = decisions[f"cert|{CLAIM}"]
    primary_variant = C["s3"]["primary_variant"]
    chosen_model = {"zero_shot": var["zero_shot"], "target_calibrated": var["target_calibrated"]}[primary_variant]
    if fd["model_id"] != chosen_model.model_id:
        raise RuntimeError(f"model id changed after freeze: {fd['model_id']} vs {chosen_model.model_id}")
    decision = AQ.AdequacyDecision(**{k: fd[k] for k in ("model_id", "status", "reason", "discrimination_pass", "calibration_pass",
                                                         "support_pass", "failed_conditions", "metrics", "ci", "calibrator", "policy_version")})
    conf_idx = np.flatnonzero(var["conf"])
    cdata = var["pool"].subset(conf_idx)
    cy = var["y"][conf_idx]
    cgroups = var["users"][conf_idx]
    ccodes = var["codes"][conf_idx]
    K = dev["K"]
    models = {"primary": chosen_model, "zero_shot": var["zero_shot"], "target_calibrated": var["target_calibrated"]}
    ctx = E.FoldContext(cdata, ccodes, K, dev["cost"], models, {}, np.arange(0), list(range(len(K))))
    cidx = np.arange(cdata.n)
    val_idx = np.flatnonzero(var["val"])
    vdata = var["pool"].subset(val_idx)
    vctx = E.FoldContext(vdata, var["codes"][val_idx], K, dev["cost"], models, {}, np.arange(0), list(range(len(K))))
    specs = S.suite(C, loss, w["lambda_cost"], w["mu_privacy"], w["nu_delay"], "main", 0)
    specs = [s for s in specs if not s.name.startswith("B2-Random")] + [s for s in specs if s.name == "B2-Random[s0]"]
    chosen, targets, tab = S.tune(vctx, specs, var["y"][val_idx], var["users"][val_idx], loss, w["lambda_cost"], w["mu_privacy"], w["nu_delay"], C)
    rows_raw, rows_enf, curve_rows = [], [], []
    for s in specs:
        s2 = replace(s, model_kind="primary")
        trs = S.trajectories(ctx, s2, cidx, decision, record=False)
        r = S.rows_at(trs, s2, cidx, cy, cgroups, loss, [chosen[s.name]], extra={"objective": CLAIM, "experiment": "primary"})
        rows_raw += r
        rows_enf += S.gate_rows(r, decision, loss)
        curve_rows.append(S.curve_counts(S.rows_at(trs, s2, cidx, cy, cgroups, loss, E.tau_grid(s2, C["hp"]["policy_thresholds"]))).assign(objective=CLAIM))
    raw = S3 / "raw" / "wp2_cert"
    S.write(pd.DataFrame(rows_raw).assign(domain="cert"), raw / "episodes_raw.csv.gz")
    S.write(pd.DataFrame(rows_enf).assign(domain="cert"), raw / "episodes_enforced.csv.gz")
    S.write(pd.concat(curve_rows).assign(domain="cert"), raw / "curves.csv.gz")
    print(CLAIM, decision.status, "confirmation episodes", cdata.n, flush=True)


if __name__ == "__main__":
    {"devcheck": devcheck, "adequacy": adequacy_phase, "confirm": confirm}[sys.argv[1]]()
