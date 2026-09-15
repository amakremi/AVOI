"""STAGE 3 / WP2 - AIT-LDS v2.0 external evidence-model development and adequacy.

  python experiments/stage3/run_wp2_ait.py devcheck   development-only LODO diagnostics (no target/confirmation data)
  python experiments/stage3/run_wp2_ait.py adequacy   fit on development, adequacy on target-A validation split
  python experiments/stage3/run_wp2_ait.py confirm    requires the Stage-3 freeze + ADEQUACY_DECISIONS_STAGE3.json
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "stage3"))

from common import ROOT as _ROOT  # noqa: E402

from avoi import adequacy as AQ  # noqa: E402
from avoi.costs import CostModel  # noqa: E402
from avoi.datasets.ait_episodes import load_ait  # noqa: E402
from avoi.datasets.common import Discretizer, codes_for  # noqa: E402
from avoi.evaluation import engine as E  # noqa: E402
from avoi.evaluation import stage2 as S  # noqa: E402
from avoi.evaluation import stage3 as S3M  # noqa: E402
from avoi.evaluation import stage3_wp2 as W2  # noqa: E402
from avoi.evaluation.labels import load_labels  # noqa: E402
from avoi.evaluation.stage3 import S3  # noqa: E402

CLAIMS = ("AIT-EXFIL", "AIT-INTRUSION")
DEV_TESTBEDS = ["russellmitchell", "santos", "fox", "harrison", "wardbeck"]
TARGET_A = "shaw"
CONFIRM_TESTBEDS = ["wheeler", "wilson"]


def load_claim(claim: str):
    """Loads (dev-by-source, target-A, confirmation) ObjectiveData for one claim, reusing avoi.datasets.ait_episodes."""
    dev1 = load_ait()[claim]                                   # russellmitchell, santos (from data/processed/ait)
    dev2 = load_ait("data/processed/ait_stage2", "ait_stage2")[claim]   # fox, harrison, wardbeck (Stage 2)
    tgt = load_ait("data/processed/ait_stage3", "ait_stage3")[claim]    # shaw, wheeler, wilson (Stage 3, untouched)
    y1 = load_labels("ait", dev1.episode_ids)
    y2 = load_labels("ait_stage2", dev2.episode_ids)
    yt = load_labels("ait_stage3", tgt.episode_ids)
    return dev1, y1, dev2, y2, tgt, yt


def per_source(data, y, testbeds: list[str]) -> dict:
    return {tb: (data.values[data.groups == tb], y[data.groups == tb]) for tb in testbeds if (data.groups == tb).any()}


def develop_ait(claim: str, C: dict) -> dict:
    dev1, y1, dev2, y2, tgt, yt = load_claim(claim)
    dev_all = S3M.concat([dev1, dev2], ["stage1", "stage2"], "ait_s3")
    y_all = np.concatenate([y1, y2])
    disc = Discretizer().fit(dev_all.values)
    codes_by_tb = {}
    for tb in DEV_TESTBEDS:
        m = dev_all.strata["testbed"] == tb
        codes_by_tb[tb] = (disc.transform(dev_all.values[m]), y_all[m])
    K = [len(a.outcomes) for a in dev_all.actions]
    cands = W2.lodo_candidates(codes_by_tb, K, [list(a.polarity) for a in dev_all.actions], C)
    chosen = W2.select_candidate(cands)
    codes_all = disc.transform(dev_all.values)
    base = W2.fit_final(chosen["kind"], chosen.get("alpha"), K, codes_all, y_all, C)
    cost = CostModel.fit(dev_all.records, dev_all.bytes_, dev_all.seconds, dev_all.n_categories(), "B")
    stability = W2.feature_stability(codes_by_tb, [a.action_id for a in dev_all.actions])
    return {"dev_all": dev_all, "y_all": y_all, "disc": disc, "base": base, "cost": cost, "candidates": cands,
            "chosen": chosen, "stability": stability, "codes_by_tb": codes_by_tb, "K": K, "target_raw": (tgt, yt)}


def target_a_only(tgt, yt):
    """Restrict to testbed A (shaw) - confirmation testbeds (wheeler, wilson) must never enter the target
    calibration/adequacy-validation split."""
    m = tgt.strata["testbed"] == TARGET_A
    return tgt.subset(np.flatnonzero(m)), yt[m]


def target_split(tgt_a, C: dict):
    c = C["s3"]["ait"]["target_split"]
    assert set(tgt_a.strata["testbed"]) <= {TARGET_A}, "target_split must receive testbed-A-only data"
    blocks = np.array([f"{tb}:{int(w) // 3600}" for tb, w in zip(tgt_a.strata["testbed"], tgt_a.strata["w0"])])
    cal_pct = int(c["rule"].split("< ")[1].split(" ")[0])
    is_cal = W2.build_target_split(tgt_a.episode_ids, blocks, c["seed"], cal_pct)
    return is_cal, blocks


def variants(dev: dict, claim: str, C: dict):
    tgt_full, yt_full = dev["target_raw"]
    tgt, yt = target_a_only(tgt_full, yt_full)   # testbed-A (shaw) only; confirmation testbeds excluded here
    is_cal, blocks = target_split(tgt, C)
    codes_t = dev["disc"].transform(tgt.values)
    model_id_zs = f"ait_s3:{claim}:{dev['chosen']['kind']}(alpha={dev['chosen'].get('alpha')})+zero_shot"
    zero_shot = AQ.CalibratedEvidenceModel(dev["base"], AQ.Calibrator("none").fit(np.array([0.5]), np.array([1])), model_id_zs)
    cal_codes, cal_y = codes_t[is_cal], yt[is_cal]
    p_cal = np.array([dev["base"].posterior(tuple((j, int(cal_codes[i, j])) for j in range(cal_codes.shape[1]))) for i in range(len(cal_y))])
    name, scores, cal, rejected = S3M.monotone_calibrator(p_cal, cal_y, blocks[is_cal], C["adequacy"]["calibration_candidates"], C["adequacy"]["bootstrap"]["seed"])
    model_id_tc = f"ait_s3:{claim}:{dev['chosen']['kind']}(alpha={dev['chosen'].get('alpha')})+target_{name}"
    target_cal = AQ.CalibratedEvidenceModel(dev["base"], cal, model_id_tc)
    return {"zero_shot": zero_shot, "target_calibrated": target_cal, "calibrator_name": name, "calibrator_scores": scores,
            "rejected_calibrators": rejected, "is_calibration": is_cal, "blocks": blocks, "codes_t": codes_t,
            "tgt_a": tgt, "yt_a": yt}


def validate_variant(model, y_val, p_val_codes, groups_val, ref_prev, C):
    p = np.array([model.posterior(tuple((j, int(p_val_codes[i, j])) for j in range(p_val_codes.shape[1]))) for i in range(len(y_val))])
    pol = C["adequacy"]
    m = AQ.point_metrics(y_val, p, ref_prev, pol["ece_bins"])
    boot = AQ.group_bootstrap(y_val, p, groups_val, ref_prev, pol["bootstrap"]["n_resamples"], pol["bootstrap"]["seed"], pol["bootstrap"]["confidence"], pol["ece_bins"])
    return m, boot, p


def devcheck():
    C = S.cfg(); C["s3"] = S3M.cfg3()["wp2"]
    for claim in CLAIMS:
        dev = develop_ait(claim, C)
        print(claim, "candidates (worst-fold AUROC):", [(c["kind"], c.get("alpha"), round(c["worst_fold_AUROC"], 3), round(c["median_PR_skill"], 3)) for c in dev["candidates"]], flush=True)
        print(claim, "selected:", dev["chosen"]["kind"], dev["chosen"].get("alpha"), "passed_pr_skill_filter", dev["chosen"]["passed_pr_skill_filter"], flush=True)
        flips = dev["stability"][dev["stability"]["direction_reverses"]]["action_id"].tolist()
        print(claim, "unstable (direction-reversing) features:", flips, flush=True)
        S3M.save_json({"candidates": [{k: v for k, v in c.items() if k != "fold_metrics"} for c in dev["candidates"]] + [{"fold_metrics_note": "see per-candidate fold_metrics in full record"}],
                      "candidates_full": dev["candidates"], "chosen": {k: v for k, v in dev["chosen"].items() if k != "fold_metrics"}},
                     S3 / "development" / f"wp2_ait_{claim}_devcheck.json")
        dev["stability"].to_csv(S3 / "development" / f"wp2_ait_{claim}_feature_stability.csv", index=False)


def adequacy_phase():
    C = S.cfg(); C["s3"] = S3M.cfg3()["wp2"]
    recs = {}
    for claim in CLAIMS:
        dev = develop_ait(claim, C)
        var = variants(dev, claim, C)
        tgt, yt = var["tgt_a"], var["yt_a"]     # testbed-A (shaw) only
        is_cal = var["is_calibration"]
        val_codes, val_y, val_blocks = var["codes_t"][~is_cal], yt[~is_cal], var["blocks"][~is_cal]
        ref_prev = float(np.mean(dev["y_all"]))
        m_zs, boot_zs, p_zs = validate_variant(var["zero_shot"], val_y, val_codes, val_blocks, ref_prev, C)
        m_tc, boot_tc, p_tc = validate_variant(var["target_calibrated"], val_y, val_codes, val_blocks, ref_prev, C)
        gwv = int(len(set(val_blocks[val_y == 0])))
        dec = AQ.decide(var["target_calibrated"].model_id, m_tc, boot_tc, C["adequacy"], var["calibrator_name"], groups_with_violation=gwv)
        rec = {"work_package": "WP2", "domain": "ait", "objective": claim, "model_id": dec.model_id, "decision": asdict(dec),
               "development_sources": DEV_TESTBEDS, "target_testbed": TARGET_A, "confirmation_testbeds": CONFIRM_TESTBEDS,
               "selection": {"chosen_model": {k: v for k, v in dev["chosen"].items() if k != "fold_metrics"}, "calibrator": var["calibrator_name"],
                            "calibrator_cv_log_loss": var["calibrator_scores"], "rejected_non_monotone_calibrators": var["rejected_calibrators"]},
               "target_calibrated": {"metrics": m_tc, "bootstrap": boot_tc}, "zero_shot": {"metrics": m_zs, "bootstrap": boot_zs},
               "groups_with_violation": gwv, "prevalence_satisfied_dev": ref_prev}
        S3M.save_json(rec, S3 / "validation" / f"wp2_ait_{claim}.json")
        pd.DataFrame({"episode_id": tgt.episode_ids[~is_cal], "block": val_blocks, "y": val_y, "p_zero_shot": p_zs, "p_target_calibrated": p_tc}).to_csv(
            S3 / "validation" / f"wp2_ait_{claim}_val_predictions.csv.gz", index=False, compression="gzip")
        recs[claim] = rec
        print(claim, dec.status, dec.reason, "target-calibrated AUROC", round(m_tc["AUROC"], 3), "zero-shot AUROC", round(m_zs["AUROC"], 3), flush=True)
    return recs


def confirm():
    from run_stage3 import verify_freeze, load_decisions
    verify_freeze()
    decisions = load_decisions()
    C = S.cfg(); C["s3"] = S3M.cfg3()["wp2"]
    lcfg = C["loss"]
    from avoi.bayes_risk import LossMatrix
    loss = LossMatrix(lcfg["primary"]["false_assurance"], lcfg["primary"]["false_non_assurance"], lcfg["primary"]["human_review"])
    w = lcfg["preference_weights"]
    S.CONFLICT["flags"] = None   # AIT has no IAM-style evidence-polarity conflict flag; clear any stale global from WP1
    rows_raw, rows_enf, curve_rows = [], [], []
    for claim in CLAIMS:
        dev = develop_ait(claim, C)
        var = variants(dev, claim, C)
        fd = decisions[f"ait|{claim}"]
        model_map = {"zero_shot": var["zero_shot"], "target_calibrated": var["target_calibrated"]}
        primary_variant = C["s3"]["primary_variant"]
        chosen_model = model_map[primary_variant]
        if fd["model_id"] != chosen_model.model_id:
            raise RuntimeError(f"model id changed after freeze for {claim}: {fd['model_id']} vs {chosen_model.model_id}")
        decision = AQ.AdequacyDecision(**{k: fd[k] for k in ("model_id", "status", "reason", "discrimination_pass", "calibration_pass",
                                                             "support_pass", "failed_conditions", "metrics", "ci", "calibrator", "policy_version")})
        tgt, yt = dev["target_raw"]
        conf_mask = np.isin(tgt.strata["testbed"], CONFIRM_TESTBEDS)
        cdata = tgt.subset(np.flatnonzero(conf_mask))
        cy = yt[conf_mask]
        cblocks = np.array([f"{tb}:{int(w0) // 3600}" for tb, w0 in zip(cdata.strata["testbed"], cdata.strata["w0"])])
        ccodes = dev["disc"].transform(cdata.values)
        K = dev["K"]
        models = {"primary": chosen_model, "zero_shot": var["zero_shot"], "target_calibrated": var["target_calibrated"]}
        ctx = E.FoldContext(cdata, ccodes, K, dev["cost"], models, {}, np.arange(0), list(range(len(K))))
        cidx = np.arange(cdata.n)
        specs = S.suite(C, loss, w["lambda_cost"], w["mu_privacy"], w["nu_delay"], "main", 0)
        specs = [s for s in specs if not s.name.startswith("B2-Random")] + [s for s in specs if s.name == "B2-Random[s0]"]
        # thresholds tuned on the target-A (shaw) adequacy-validation split only, never on confirmation
        vcodes = var["codes_t"][~var["is_calibration"]]
        vy_ = var["yt_a"][~var["is_calibration"]]
        vblocks_ = var["blocks"][~var["is_calibration"]]
        vdata_full = var["tgt_a"].subset(np.flatnonzero(~var["is_calibration"]))
        vctx = E.FoldContext(vdata_full, vcodes, K, dev["cost"], models, {}, np.arange(0), list(range(len(K))))
        chosen, targets, tab = S.tune(vctx, specs, vy_, vblocks_, loss, w["lambda_cost"], w["mu_privacy"], w["nu_delay"], C)
        for s in specs:
            s2 = replace(s, model_kind="primary")
            trs = S.trajectories(ctx, s2, cidx, decision, record=False)
            r = S.rows_at(trs, s2, cidx, cy, cblocks, loss, [chosen[s.name]], extra={"objective": claim, "experiment": "primary"})
            rows_raw += r
            rows_enf += S.gate_rows(r, decision, loss)
            curve_rows.append(S.curve_counts(S.rows_at(trs, s2, cidx, cy, cblocks, loss, E.tau_grid(s2, C["hp"]["policy_thresholds"]))).assign(objective=claim))
        print(claim, decision.status, "confirmation episodes", cdata.n, flush=True)
    raw = S3 / "raw" / "wp2_ait"
    S.write(pd.DataFrame(rows_raw).assign(domain="ait"), raw / "episodes_raw.csv.gz")
    S.write(pd.DataFrame(rows_enf).assign(domain="ait"), raw / "episodes_enforced.csv.gz")
    S.write(pd.concat(curve_rows).assign(domain="ait"), raw / "curves.csv.gz")


if __name__ == "__main__":
    {"devcheck": devcheck, "adequacy": adequacy_phase, "confirm": confirm}[sys.argv[1]]()
