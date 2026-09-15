"""Stage-3 figures. Reuses Stage-1/2 plotting infrastructure (style, fonts, method colours/markers, save helper)."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from avoi.evaluation import figures as F1  # noqa: E402
from avoi.evaluation import stage3_tables as T3  # noqa: E402

S3 = T3.S3
FIG = S3 / "figures"
INK, INK2, MUTED = F1.INK, F1.INK2, F1.MUTED
st = F1.st


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=300)
    plt.close(fig)
    return [f"results/stage3/figures/{name}.pdf", f"results/stage3/figures/{name}.png"]


# ------------------------------------------------------------------------------------------------ 1: adaptive selection
def fig_adaptive_selection(adapt_summary: dict, rank_trace_path: Path, wp1_objectives: list[str]):
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 8.2))
    # Panel A: example objective, action selected at step 2 grouped by step-1 outcome
    example_oid = next((o for o in wp1_objectives if adapt_summary[o]["permutation"]["p"] < 0.05), wp1_objectives[0])
    rank = pd.read_parquet(rank_trace_path, engine="fastparquet") if rank_trace_path.exists() else pd.DataFrame()
    axA = axes[0][0]
    if not rank.empty:
        r2 = rank[(rank["objective"] == example_oid) & (rank["policy"] == "AVOI") & (rank["step"] == 2)].copy()
        r2["h1"] = r2["observed_history"].apply(lambda s: json.loads(s)[0][1] if json.loads(s) else "none")
        ct = pd.crosstab(r2["h1"], r2["selected_action"], normalize="index")
        im = axA.imshow(ct.to_numpy(), aspect="auto", cmap="Blues", vmin=0, vmax=1)
        axA.set_yticks(range(len(ct.index)), ct.index, fontsize=6.5)
        axA.set_xticks(range(len(ct.columns)), ct.columns, fontsize=6.5, rotation=30, ha="right")
        axA.set_ylabel("Step-1 observed outcome"); axA.set_xlabel("Step-2 selected action")
        fig.colorbar(im, ax=axA, fraction=0.046, label="P(action | history)")
    axA.set_title(f"A. {example_oid}: same objective, same action set,\ndifferent next action given different history", fontsize=8)

    # Panel B: AVOI value ranking before/after one observation (example episode)
    axB = axes[0][1]
    if not rank.empty:
        ex = rank[(rank["objective"] == example_oid) & (rank["policy"] == "AVOI") & (rank["step"].isin([1, 2]))]
        eids = ex[ex["step"] == 2]["episode_id"].unique()
        if len(eids):
            eid = eids[0]
            for step, ls, lab in ((1, "--", "before evidence (t=1 ranking)"), (2, "-", "after 1 observation (t=2 ranking)")):
                row = ex[(ex["episode_id"] == eid) & (ex["step"] == step)]
                if row.empty:
                    continue
                vals = json.loads(row.iloc[0]["avoi_values"])
                items = sorted(vals.items(), key=lambda kv: -kv[1])
                axB.plot([v for _, v in items], range(len(items)), marker="o", ls=ls, color=INK if step == 2 else MUTED, label=lab)
                if step == 2:
                    axB.set_yticks(range(len(items)), [k for k, _ in items], fontsize=6.5)
        axB.legend(fontsize=6.5, loc="lower right")
        axB.set_xlabel("AVOI value"); axB.invert_yaxis()
    axB.set_title(f"B. {example_oid}: one example episode's\nAVOI ranking recomputed after evidence", fontsize=8)

    # Panel C: rank-reversal rate by objective
    axC = axes[1][0]
    rr = [adapt_summary[o]["adaptive"]["rank_reversal_rate"] for o in wp1_objectives]
    axC.bar(range(len(wp1_objectives)), rr, color=st("AVOI")[0])
    axC.set_xticks(range(len(wp1_objectives)), wp1_objectives, rotation=20, ha="right", fontsize=7)
    axC.set_ylabel("Rank-reversal rate\n(adaptive next != frozen-order next)")
    axC.set_title("C. Rank-reversal rate by objective", fontsize=8)

    # Panel D: adaptive vs frozen-order loss at k=2,3
    axD = axes[1][1]
    fh = T3.pd.read_csv(S3 / "tables" / "table_fixed_horizon_stage3.csv") if (S3 / "tables" / "table_fixed_horizon_stage3.csv").exists() else None
    if fh is not None:
        width = 0.35
        for i, oid in enumerate(wp1_objectives):
            d = fh[fh["objective"] == oid]
            for j, k in enumerate(sorted(d["horizon_k"].unique())):
                r = d[d["horizon_k"] == k].iloc[0]
                x = i * 3 + j
                axD.bar(x - width / 2, r["adaptive_loss"], width, color=st("AVOI")[0], label="Adaptive AVOI" if x == 0 else None)
                axD.bar(x + width / 2, r["frozen_loss"], width, color=MUTED, label="Frozen-Order AVOI" if x == 0 else None)
        axD.legend(fontsize=6.5)
    axD.set_ylabel("Expected decision loss"); axD.set_xlabel("objective x horizon k")
    axD.set_title("D. Adaptive vs Frozen-Order loss, fixed horizons k=2,3", fontsize=8)
    fig.suptitle("Same objective + same available actions + different observations = different next action", fontsize=10, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return save(fig, "adaptive_next_evidence_selection")


# ------------------------------------------------------------------------------------------------ 2: external adequacy
def fig_external_adequacy(ait_records: dict, cert_record: dict | None):
    from avoi import adequacy as AQ
    recs = [("AIT", k, v) for k, v in ait_records.items()]
    if cert_record is not None:
        recs.append(("CERT", cert_record["objective"], cert_record))
    status_col = {"VALIDATED": "#1baf7a", "RESTRICTED": "#eda100", "UNSUPPORTED": "#e34948"}
    panels = [("AUROC", 0.5, "AUROC (violation)"), ("PR_skill", 0.0, "PR skill"), ("BSS", 0.0, "BSS"), ("ECE", 0.10, "ECE"), ("calibration_slope", None, "Slope")]
    fig, axes = plt.subplots(1, len(panels), figsize=(11, 0.5 * len(recs) + 2.4), sharey=True)
    for ax, (mt, thr, lab) in zip(axes, panels):
        for i, (dom, claim, r) in enumerate(recs):
            for variant, marker, alpha in (("zero_shot", "s", 0.5), ("target_calibrated", "o", 1.0)):
                m = r[variant]["metrics"]; ci = r[variant]["bootstrap"]["ci"]
                v, lo, hi = m[mt], ci[mt][0], ci[mt][1]
                col = status_col[r["decision"]["status"]] if variant == "target_calibrated" else "#b5b3ab"
                if mt == "calibration_slope":
                    v, lo, hi = np.clip([v, lo, hi], -8, 6)
                ax.errorbar(v, i, xerr=[[max(v - lo, 0)], [max(hi - v, 0)]], fmt=marker, color=col, ms=4, capsize=1.5, alpha=alpha)
        if thr is not None:
            ax.axvline(thr, color=INK2, lw=0.8, ls="--")
        ax.set_title(lab, fontsize=8)
    axes[0].set_yticks(range(len(recs)), [f"{d} {c}" for d, c, _ in recs], fontsize=7)
    axes[0].invert_yaxis()
    handles = ([plt.Line2D([], [], color=c, marker="o", ls="none", label=s) for s, c in status_col.items()] +
              [plt.Line2D([], [], color=INK2, marker="s", ls="none", alpha=0.5, label="zero-shot"),
               plt.Line2D([], [], color=INK2, marker="o", ls="none", label="target-calibrated")])
    fig.tight_layout(rect=[0, 0.14, 1, 0.90])
    fig.legend(handles=handles, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0), fontsize=7)
    fig.suptitle("Stage-3 external-domain adequacy (unchanged Stage-2 policy thresholds; squares=zero-shot, circles=target-calibrated)", fontsize=9, color=INK)
    return save(fig, "external_model_adequacy_stage3")


# ------------------------------------------------------------------------------------------------ 3: transfer
def fig_external_transfer(ait_dev_records: dict, cert_dev_record: dict | None, ait_records: dict, cert_record: dict | None):
    metrics = ["AUROC", "ECE", "BSS"]
    claims = list(ait_records) + (["CERT-INSIDER"] if cert_record else [])
    fig, axes = plt.subplots(1, len(metrics), figsize=(10.5, 3.2))
    for ax, mt in zip(axes, metrics):
        for claim in claims:
            dev_rec = ait_dev_records.get(claim) if claim != "CERT-INSIDER" else cert_dev_record
            rec = ait_records.get(claim) if claim != "CERT-INSIDER" else cert_record
            if rec is None:
                continue
            fold_metrics = []
            if dev_rec:
                chosen_kind, chosen_alpha = dev_rec["chosen"]["kind"], dev_rec["chosen"].get("alpha")
                match = next((c for c in dev_rec["candidates_full"] if c["kind"] == chosen_kind and c.get("alpha") == chosen_alpha), None)
                fold_metrics = match["fold_metrics"] if match else []
            dev_vals = [fm[mt] for fm in fold_metrics if np.isfinite(fm.get(mt, np.nan))]
            m_val = rec["target_calibrated"]["metrics"][mt]
            xs = [0] * len(dev_vals) + [1]
            ys = dev_vals + [m_val]
            ax.plot(xs, ys, marker="o", ls="-", ms=4, alpha=0.7, label=claim if ax is axes[0] else None)
        ax.set_title(mt, fontsize=8)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["dev (LODO/cross-release\nheld-out folds)", "target\nadequacy-validation"], fontsize=6)
    axes[0].legend(fontsize=6.5, loc="best")
    fig.suptitle("External evidence-model quality: development (LODO/cross-release) -> target adequacy validation", fontsize=9, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return save(fig, "external_model_transfer_stage3")


# ------------------------------------------------------------------------------------------------ 4: cross-stage summary
def fig_cross_stage_summary():
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.axis("off")
    stages = [
        ("Stage 1", "Efficient evidence acquisition demonstrated;\nAVOI cut acquisitions sharply on 3 datasets.\nAIT cross-testbed model-transfer\nfailure discovered.", "#2a78d6"),
        ("Stage 2", "Evidence-model adequacy safety condition.\n4/9 evidence models VALIDATED (all IAM).\nNo AIT/CERT model passed.\nGate withholds autonomy where adequacy fails.", "#eb6834"),
        ("Stage 3", "WP1: adaptive next-evidence selection tested\nvs a Frozen-Order AVOI ablation.\nWP2: external-domain adequacy re-attempted\nwith multi-source development + LODO selection.", "#1baf7a"),
    ]
    for i, (title, body, col) in enumerate(stages):
        x = 0.05 + i * 0.32
        ax.add_patch(plt.Rectangle((x, 0.15), 0.28, 0.7, facecolor=col, alpha=0.12, edgecolor=col, linewidth=1.5))
        ax.text(x + 0.14, 0.78, title, ha="center", fontsize=11, weight="bold", color=col)
        ax.text(x + 0.14, 0.45, body, ha="center", va="center", fontsize=7.5, color=INK)
        if i < 2:
            ax.annotate("", xy=(x + 0.30, 0.5), xytext=(x + 0.28, 0.5), arrowprops={"arrowstyle": "->", "color": INK2, "lw": 1.5})
    fig.suptitle("Cross-stage scientific progression", fontsize=11, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return save(fig, "cross_stage_summary")
