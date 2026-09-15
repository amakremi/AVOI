"""Stage-2 figures (results/stage2/figures), generated only from saved Stage-2 raw outputs.

Same encoding as the Stage-1 figures (fixed categorical slot + marker + line style per method; AVOI emphasised).
Raw (ungated acquisition-policy) and adequacy-enforced views are always labelled explicitly.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import precision_recall_curve, roc_curve  # noqa: E402

from avoi import adequacy as AQ  # noqa: E402
from avoi.bayes_risk import HUMAN_REVIEW, LossMatrix  # noqa: E402
from avoi.evaluation import figures as F1  # noqa: E402
from avoi.evaluation import stage2_tables as T  # noqa: E402

S2 = T.S2
FIG = S2 / "figures"
INK, INK2, MUTED = F1.INK, F1.INK2, F1.MUTED
DOMS = T.DOMAINS
DT = {"iam": "Controlled IAM (new scenarios)", "ait": "AIT-LDS v2.0 (harrison, wardbeck)", "cert": "CERT r5.2 (confirmation users)"}
DTV = {"iam": "Controlled IAM (validation families)", "ait": "AIT-LDS v2.0 (fox)", "cert": "CERT r5.2 (validation users)"}
CURVE_METHODS = ["AVOI", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
                 "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI", "B0-AllEvidence", "B2-Random"]
STATUS_COL = {AQ.VALIDATED: "#1baf7a", AQ.RESTRICTED: "#eda100", AQ.UNSUPPORTED: "#e34948"}
st = F1.st


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=300)
    plt.close(fig)
    return [f"results/stage2/figures/{name}.pdf", f"results/stage2/figures/{name}.png"]


def lw(m):
    return 2.2 if m == "AVOI" else 1.2


def val_predictions(dom):
    out = []
    for f in sorted((S2 / "adequacy").glob(f"val_predictions_{dom}_*.csv.gz")):
        out.append(pd.read_csv(f).assign(objective=f.name[len(f"val_predictions_{dom}_"):-7]))
    return pd.concat(out) if out else pd.DataFrame()


def pooled_curve(dom, method, mode="raw", experiment="primary"):
    c = T.aux("curves", mode)
    c = c[(c["domain"] == dom) & (c["experiment"] == experiment)]
    c = c[c["method"].str.replace(r"\[s\d+\]", "", regex=True) == method]
    if c.empty:
        return c
    p = c.groupby("tau", dropna=False)[["n", "n_viol", "n_hr", "n_unsafe", "loss_sum", "cost_sum", "privacy_sum", "nacq_sum"]].sum().reset_index()
    p["coverage"] = 1 - p["n_hr"] / p["n"]
    p["UAR"] = p["n_unsafe"] / p["n_viol"]
    p["expected_loss"] = p["loss_sum"] / p["n"]
    p["cost"] = p["cost_sum"] / p["n"]
    return p


def statuses(dom):
    return {o.split("|")[1]: v["status"] for o, v in T.decisions().items() if o.startswith(dom + "|")}


# ------------------------------------------------------------------------------------------------ 1
def fig_model_adequacy_diagnostics():
    ma, _ = T.table_model_adequacy()
    recs = T.adequacy_records()
    panels = [("AUROC", 0.5, "AUROC (violation)"), ("PR_skill", 0.0, "PR skill"), ("BSS", 0.0, "Brier skill score"),
              ("ECE", 0.10, "ECE (10 bins)"), ("calibration_slope", None, "Calibration slope")]
    keys = sorted(recs, key=lambda k: (DOMS.index(recs[k]["domain"]), recs[k]["objective"]))
    fig, axes = plt.subplots(1, len(panels), figsize=(11, 0.33 * len(keys) + 1.4), sharey=True)
    ylab = [f"{recs[k]['domain'].upper()} {recs[k]['objective']}" for k in keys]
    for ax, (mt, thr, lab) in zip(axes, panels):
        for i, k in enumerate(keys):
            r = recs[k]
            v = r["validation_primary"]["metrics"][mt]
            lo, hi = r["validation_primary"]["bootstrap"]["ci"][mt]
            col = STATUS_COL[r["decision"]["status"]]
            ax.errorbar(v, i, xerr=[[max(v - lo, 0)], [max(hi - v, 0)]], fmt="o", color=col, ms=4, capsize=1.5, lw=1)
        if thr is not None:
            ax.axvline(thr, color=INK2, lw=0.8, ls="--")
        if mt == "calibration_slope":
            ax.axvspan(0.5, 1.5, color="#e1e0d9", alpha=0.5, lw=0)
        ax.set_title(lab)
    axes[0].set_yticks(range(len(keys)), ylab, fontsize=6)
    axes[0].invert_yaxis()
    handles = [plt.Line2D([], [], color=c, marker="o", ls="none", label=s) for s, c in STATUS_COL.items()]
    fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Evidence-model adequacy on the adequacy-validation partition (point, 95% group-bootstrap CI; dashed = primary policy threshold)",
                 y=1.02, color=INK)
    fig.tight_layout()
    return save(fig, "model_adequacy_diagnostics")


# ------------------------------------------------------------------------------------------------ 2
def reliability(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    rows = []
    for k in range(bins):
        m = idx == k
        if m.any():
            rows.append((p[m].mean(), y[m].mean(), int(m.sum())))
    return np.array(rows)


def fig_calibration():
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.3))
    for ax, dom in zip(axes, DOMS):
        vp = val_predictions(dom)
        ax.plot([0, 1], [0, 1], color=MUTED, lw=0.8, ls="--")
        if vp.empty:
            continue
        ref = np.mean([r["prevalence_satisfied_dev"] for r in T.adequacy_records().values() if r["domain"] == dom])
        for col_p, lab, col, mk in (("p_uncalibrated", "before calibration", "#b5b3ab", "s"), ("p_calibrated", "after (dev-selected calibrator)", "#2a78d6", "o")):
            y, p = vp["y"].to_numpy(int), vp[col_p].to_numpy(float)
            m = AQ.point_metrics(y, p, ref)
            R = reliability(y, p)
            ax.plot(R[:, 0], R[:, 1], color=col, marker=mk, lw=1.4,
                    label=f"{lab}: BSS {m['BSS']:.2f}, ECE {m['ECE']:.3f}, slope {m['calibration_slope']:.2f}, int. {m['calibration_intercept']:.2f}")
            if col_p == "p_calibrated":
                for x_, y_, n_ in R:
                    ax.annotate(f"{n_}", (x_, y_), textcoords="offset points", xytext=(2, -8), fontsize=5, color=INK2)
        ax.set_title(DTV[dom], fontsize=8)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xlabel("Predicted P(Y=1 | E) (pooled objectives)")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=5.5)
    axes[0].set_ylabel("Observed frequency of Y=1")
    fig.suptitle("Reliability of the evidence models on adequacy-validation data (10 bins; numbers = bin counts)", y=1.03, color=INK)
    return save(fig, "calibration_curve")


# ------------------------------------------------------------------------------------------------ 3
def fig_roc_pr():
    fig, axes = plt.subplots(2, 3, figsize=(9.2, 5.6))
    for j, dom in enumerate(DOMS):
        vp = val_predictions(dom)
        sts = statuses(dom)
        if vp.empty:
            continue
        for o, g in vp.groupby("objective"):
            yv, s = (g["y"] == 0).astype(int), 1 - g["p_calibrated"]
            if yv.nunique() < 2:
                continue
            col = STATUS_COL[sts.get(o, AQ.RESTRICTED)]
            fpr, tpr, _ = roc_curve(yv, s)
            pr, rc, _ = precision_recall_curve(yv, s)
            axes[0][j].plot(fpr, tpr, color=col, lw=1.1, label=f"{o} ({sts.get(o)})")
            axes[1][j].plot(rc, pr, color=col, lw=1.1, label=o)
            axes[1][j].axhline(yv.mean(), color=col, lw=0.6, ls=":")
        axes[0][j].plot([0, 1], [0, 1], color=MUTED, lw=0.7, ls=":")
        axes[0][j].set_title(DTV[dom], fontsize=8)
        axes[0][j].legend(fontsize=5, loc="lower right")
        axes[0][j].set_xlabel("False-positive rate"); axes[1][j].set_xlabel("Recall (violation)")
    axes[0][0].set_ylabel("True-positive rate (violation)"); axes[1][0].set_ylabel("Precision (dotted = prevalence)")
    fig.suptitle("ROC and precision-recall of the calibrated evidence models (adequacy validation; colour = adequacy status)", y=1.01, color=INK)
    fig.tight_layout()
    return save(fig, "roc_pr_curves")


# ------------------------------------------------------------------------------------------------ 4/5
def _risk_cov(mode, name, title):
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.1))
    for ax, dom in zip(axes, DOMS):
        for m in CURVE_METHODS:
            c = pooled_curve(dom, m, mode)
            if c.empty:
                continue
            q = c.dropna(subset=["UAR"]).groupby("coverage", as_index=False)["UAR"].min().sort_values("coverage")
            col, mk, ls, lab = st(m)
            if len(q) > 1:
                ax.plot(q["coverage"], q["UAR"], color=col, ls=ls, marker=mk, markevery=max(1, len(q) // 8), label=lab, lw=lw(m), zorder=3 if m == "AVOI" else 2)
            else:
                ax.plot(q["coverage"], q["UAR"], color=col, marker=mk, ls="none", ms=7, label=lab, markeredgecolor="#fcfcfb")
        sts = statuses(dom)
        ax.set_title(DT[dom] + "\n" + ", ".join(f"{k}:{v[0]}" for k, v in sorted(sts.items())), fontsize=7)
        ax.set_xlim(-0.02, 1.02)
        ax.set_xlabel("Autonomous coverage")
    axes[0].set_ylabel("UAR = #(Assured ∧ Y=0) / #(Y=0)")
    F1.shared_legend(fig, axes[None, :])
    fig.suptitle(title, y=1.08, color=INK)
    fig.text(0.5, -0.16, "Status letters: V = VALIDATED, R = RESTRICTED, U = UNSUPPORTED. The UAR denominator (all Y=0 episodes) is constant along each curve; "
             "curves reaching coverage = 1 are thresholds at which no episode escalates.", ha="center", fontsize=6.5, color=INK2, wrap=True)
    return save(fig, name)


def fig_risk_coverage_raw():
    return _risk_cov("raw", "risk_coverage_raw", "Risk-coverage, RAW acquisition policies (no adequacy gate), confirmation data")


def fig_risk_coverage_enforced():
    return _risk_cov("enforced", "risk_coverage_adequacy_enforced",
                     "Risk-coverage, ADEQUACY-ENFORCED (gate applied to every method; gated models contribute coverage 0)")


# ------------------------------------------------------------------------------------------------ 6
def fig_frontier():
    fig, axes = plt.subplots(2, 3, figsize=(9.2, 5.6))
    pdist = T.pareto_distance(T.episodes("raw"))
    for j, dom in enumerate(DOMS):
        allpts = []
        for m in CURVE_METHODS:
            c = pooled_curve(dom, m)
            if c.empty:
                continue
            col, mk, ls, lab = st(m)
            d = pdist[(pdist["domain"] == dom) & (pdist["method"] == T.DISPLAY.get(m, m))]
            dl = f" (d={d['min_normalized_distance_to_frontier'].iloc[0]:.3f})" if len(d) else ""
            for i, ycol in enumerate(("expected_loss", "UAR")):
                axes[i][j].scatter(c["cost"], c[ycol], s=16 if m == "AVOI" else 9, color=col, marker=mk, label=lab + (dl if i == 0 else ""),
                                   linewidths=0, zorder=3 if m == "AVOI" else 2)
            allpts.append(c)
        if not allpts:
            continue
        pts = pd.concat(allpts)
        for i, ycol in enumerate(("expected_loss", "UAR")):
            p = pts.dropna(subset=[ycol])
            fr = p[F1.pareto_mask(p["cost"].to_numpy(), p[ycol].to_numpy())].sort_values("cost")
            axes[i][j].step(fr["cost"], fr[ycol], where="post", color=INK, lw=0.9, zorder=4)
        axes[0][j].set_title(DT[dom], fontsize=8)
        axes[0][j].legend(fontsize=4.8, loc="upper right")
        axes[1][j].set_xlabel("Mean normalised acquisition cost")
    axes[0][0].set_ylabel("Expected decision loss"); axes[1][0].set_ylabel("UAR")
    fig.suptitle("Cost-safety frontier (raw policies; points = threshold configurations; black = global Pareto frontier; "
                 "d = min. normalised distance to frontier)", y=1.01, color=INK)
    fig.tight_layout()
    return save(fig, "cost_safety_frontier")


# ------------------------------------------------------------------------------------------------ 7
def fig_budget():
    b = T.aux("budget")
    b["mf"] = b["method"].str.replace(r"\[s\d+\]", "", regex=True)
    fig, axes = plt.subplots(3, 3, figsize=(9.2, 7.4), sharex="col")
    for j, dom in enumerate(DOMS):
        d = b[b["domain"] == dom]
        for m in [x for x in CURVE_METHODS if x != "B0-AllEvidence"]:
            s = d[d["mf"] == m]
            if s.empty:
                continue
            col, mk, ls, lab = st(m)
            agg = []
            for k, g in s.groupby("budget"):
                r = T.SA.rates(g)
                agg.append((k, g["loss"].mean(), r["UAR"], r["coverage"]))
            A = np.array(agg)
            for i in range(3):
                axes[i][j].plot(A[:, 0], A[:, i + 1], color=col, marker=mk, ls=ls, label=lab, lw=lw(m))
        axes[0][j].set_title(DT[dom], fontsize=8)
        axes[2][j].set_xlabel("Hard budget k (at most k acquisitions)")
    for i, lab in enumerate(("Expected decision loss", "UAR", "Autonomous coverage")):
        axes[i][0].set_ylabel(lab)
    F1.shared_legend(fig, axes)
    fig.suptitle("Budget performance (validation-tuned thresholds; the policy may stop before k)", y=1.03, color=INK)
    return save(fig, "budget_performance_curve")


# ------------------------------------------------------------------------------------------------ traces helpers
def load_traces(dom, method):
    out = []
    for f in sorted((S2 / "traces" / dom / method).glob("*.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            out += [json.loads(l) for l in fh]
    return out


def fig_trajectory():
    loss = LossMatrix()
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.1))
    for ax, dom in zip(axes, DOMS):
        for m in ("AVOI", "B1-FixedChecklist", "B4-InformationGain", "B6-ConfidenceThreshold"):
            trs = load_traces(dom, m)
            if not trs:
                continue
            y, M = F1.trajectory_matrix(trs, loss)
            col, mk, ls, lab = st(m)
            for cls, lsty, nm in ((1, "-", "Y=1"), (0, "--", "Y=0")):
                sub = M[y == cls]
                if not len(sub):
                    continue
                I = np.random.default_rng(0).integers(0, len(sub), (1000, len(sub)))
                bs = sub[I].mean(1)
                t = np.arange(sub.shape[1])
                ax.plot(t, sub.mean(0), color=col, ls=lsty, marker=mk, markevery=2, label=f"{lab} {nm}", lw=lw(m))
                ax.fill_between(t, np.quantile(bs, .025, 0), np.quantile(bs, .975, 0), color=col, alpha=0.1, lw=0)
        ax.set_title(DT[dom], fontsize=8); ax.set_xlabel("Evidence-acquisition step")
    axes[0].set_ylabel("Mean Bayes decision risk (95% CI)")
    F1.shared_legend(fig, axes[None, :])
    fig.suptitle("Assurance-risk trajectory (raw policies, confirmation): solid Y=1, dashed Y=0", y=1.08, color=INK)
    fig.text(0.5, -0.2, "For episodes terminating before step t, terminal risk is carried forward to avoid survivor conditioning.", ha="center", fontsize=6.5, color=INK2)
    return save(fig, "acquisition_risk_trajectory")


def fig_ecdf():
    raw = T.cold(T.episodes("raw"))
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.0))
    for ax, dom in zip(axes, DOMS):
        d = raw[raw["domain"] == dom]
        for m in CURVE_METHODS:
            x = T.per_method(d, m)
            if x.empty:
                continue
            col, mk, ls, lab = st(m)
            v = np.sort(x["n_acq"].to_numpy(float))
            ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", color=col, ls=ls, label=lab, lw=lw(m))
        ax.set_title(DT[dom], fontsize=8); ax.set_xlabel("Acquisitions before decision"); ax.set_ylim(0, 1.02)
    axes[0].set_ylabel("Cumulative share of episodes")
    F1.shared_legend(fig, axes[None, :])
    fig.suptitle("ECDF of evidence requests (raw policies, validation-tuned thresholds, confirmation)", y=1.08, color=INK)
    return save(fig, "evidence_request_ecdf")


# ------------------------------------------------------------------------------------------------ missingness
def _miss_frame(mode):
    mt = T.missingness_table(T.episodes("raw"), T.episodes("enforced"))
    return mt[mt["adequacy_mode"] == mode]


def fig_missingness():
    mt = _miss_frame("raw")
    methods = ["AVOI", "Checklist", "Cheapest First", "Information Gain", "Generic VOI", "Confidence Threshold", "Myopic Cost-Sensitive VOI", "All Evidence"]
    rev = {v: k for k, v in T.DISPLAY.items()}
    fig, axes = plt.subplots(3, 3, figsize=(9.2, 7.2), sharex=True)
    for i, dom in enumerate(DOMS):
        for j, mode in enumerate(("mcar", "block", "adversarial")):
            ax = axes[i][j]
            for m in methods:
                s = mt[(mt["domain"] == dom) & (mt["method"] == m) & (mt["missing_mode"] == mode)].sort_values("initially_unacquired_pct")
                if s.empty:
                    continue
                col, mk, ls, lab = st(rev[m])
                ax.plot(s["initially_unacquired_pct"], s["expected_loss"], color=col, marker=mk, ls=ls, label=lab, lw=lw(rev[m]))
            if i == 0:
                ax.set_title({"mcar": "MCAR", "block": "Source-block", "adversarial": "Adversarially inconvenient"}[mode])
            if j == 0:
                ax.set_ylabel(f"{dom.upper()}\nExpected decision loss")
            if i == 2:
                ax.set_xlabel("Initially unacquired (%); 100 = cold start")
    F1.shared_legend(fig, axes)
    fig.suptitle("Missing-evidence robustness: expected loss (raw policies, confirmation)", y=1.03, color=INK)
    return save(fig, "missingness_robustness")


def fig_missingness_uar_cov():
    mt = _miss_frame("raw")
    rev = {v: k for k, v in T.DISPLAY.items()}
    methods = ["AVOI", "Checklist", "Information Gain", "Generic VOI", "Confidence Threshold", "All Evidence"]
    fig, axes = plt.subplots(2, 3, figsize=(9.2, 5.4), sharex=True)
    for j, dom in enumerate(DOMS):
        for m in methods:
            s = mt[(mt["domain"] == dom) & (mt["method"] == m)].groupby("initially_unacquired_pct", as_index=False)[["UAR", "coverage"]].mean()
            if s.empty:
                continue
            col, mk, ls, lab = st(rev[m])
            axes[0][j].plot(s["initially_unacquired_pct"], s["UAR"], color=col, marker=mk, ls=ls, label=lab, lw=lw(rev[m]))
            axes[1][j].plot(s["initially_unacquired_pct"], s["coverage"], color=col, marker=mk, ls=ls, label=lab, lw=lw(rev[m]))
        axes[0][j].set_title(DT[dom], fontsize=8)
        axes[1][j].set_xlabel("Initially unacquired (%), mean over MCAR/block/adversarial")
    axes[0][0].set_ylabel("UAR"); axes[1][0].set_ylabel("Autonomous coverage")
    F1.shared_legend(fig, axes)
    fig.suptitle("Missingness: UAR and coverage reported jointly (a lower UAR with lower coverage is abstention, not improvement)", y=1.03, color=INK)
    return save(fig, "missingness_uar_coverage")


# ------------------------------------------------------------------------------------------------ privacy
def fig_privacy():
    pt = T.privacy_table(T.episodes("raw"))
    raw = T.cold(T.episodes("raw"))
    fig, axes = plt.subplots(2, 3, figsize=(9.2, 5.4))
    for j, dom in enumerate(DOMS):
        s = pt[pt["domain"] == dom].sort_values("mu")
        for i, met in enumerate(("expected_loss", "UAR")):
            ax = axes[i][j]
            ax.plot(s["privacy_exposure"], s[met], color=st("AVOI")[0], marker="o", lw=1.8, label="AVOI (μ varied)")
            for _, r in s.iterrows():
                ax.annotate(f"μ={r['mu']:g}", (r["privacy_exposure"], r[met]), textcoords="offset points", xytext=(3, 3), fontsize=5.5, color=INK2)
            d = raw[raw["domain"] == dom]
            for m in ("B1-FixedChecklist", "B4-InformationGain", "B5-GenericVOI", "B6-ConfidenceThreshold", "B0-AllEvidence"):
                x = d[d["method"] == m]
                if x.empty:
                    continue
                col, mk, ls, lab = st(m)
                v = x["loss"].mean() if met == "expected_loss" else T.SA.rates(x)["UAR"]
                ax.plot(x["privacy"].mean(), v, color=col, marker=mk, ls="none", ms=6, label=lab)
        axes[0][j].set_title(DT[dom], fontsize=8)
        axes[1][j].set_xlabel("Mean privacy exposure (proxy)")
    axes[0][0].set_ylabel("Expected decision loss"); axes[1][0].set_ylabel("UAR")
    F1.shared_legend(fig, axes)
    fig.suptitle("Privacy-safety trade-off (actual μ values; thresholds re-tuned on validation per μ)", y=1.03, color=INK)
    return save(fig, "privacy_safety_tradeoff")


# ------------------------------------------------------------------------------------------------ action heatmap
def fig_action_frequency():
    trs = load_traces("iam", "AVOI")
    if not trs:
        return []
    freq = T.SA.action_frequency(trs)
    single = T.SA.single_action_objectives(trs)
    objs = sorted({k[0] for k in freq})
    fig, axes = plt.subplots(2, 3, figsize=(14, 6.5), gridspec_kw={"wspace": 1.1, "hspace": 0.5})
    im = None
    for ax, obj in zip(np.ravel(axes), objs):
        steps = sorted(t for o, t in freq if o == obj)
        acts = sorted({a for (o, t), v in freq.items() if o == obj for a in v["freq"]})
        M = np.array([[freq[(obj, t)]["freq"].get(a, 0.0) for t in steps] for a in acts])
        im = ax.imshow(M, aspect="auto", cmap="Blues", vmin=0, vmax=1)
        ax.set_yticks(range(len(acts)), acts, fontsize=5.5)
        ax.set_xticks(range(len(steps)), [f"{t}\nn={freq[(obj, t)]['n_t']}" for t in steps], fontsize=6)
        ax.set_title(obj + ("  [single-action objective]" if obj in single else ""), fontsize=7)
        ax.set_xlabel("Step t (n_t = episodes reaching t)"); ax.grid(False)
    if im is not None:
        fig.colorbar(im, ax=axes, fraction=0.02, label="P(A_t = a | N_acq ≥ t)")
    fig.suptitle("AVOI action selection frequency, conditional on reaching step t (IAM confirmation, raw policy)", color=INK)
    return save(fig, "action_frequency_heatmap")


# ------------------------------------------------------------------------------------------------ asymmetric ablation
def fig_asymmetric():
    raw = T.episodes("raw")
    fig, axes = plt.subplots(1, 4, figsize=(10, 2.8))
    mets = [("UAR", "UAR"), ("FAA", "False assurance among assurances"), ("expected_loss", "Expected loss (10:2:1 scale)"), ("mean_acquisitions", "Mean acquisitions")]
    for k, (mt, lab) in enumerate(mets):
        ax = axes[k]
        for j, dom in enumerate(DOMS):
            d = T.cold(raw[raw["domain"] == dom], "ablation")
            for off, (m, col, name) in enumerate((("AVOI", "#2a78d6", "Asymmetric 10:2:1"), ("A1-NoAsymmetricLoss", "#b5b3ab", "Symmetric 2:2:1"))):
                x = d[d["method"] == m]
                if x.empty:
                    continue
                s = T.boot_summary(x, 2000)
                v, (lo, hi) = s["point"][mt], s["ci"][mt]
                ax.bar(j + (off - 0.5) * 0.38, v, width=0.36, color=col, edgecolor="#fcfcfb", label=name if j == 0 else None)
                if not np.isnan(v):
                    ax.errorbar(j + (off - 0.5) * 0.38, v, yerr=[[max(v - lo, 0)], [max(hi - v, 0)]], color=INK2, lw=0.8, capsize=1.5)
        ax.set_xticks(range(3), [d.upper() for d in DOMS]); ax.set_title(lab, fontsize=8)
    axes[0].legend(fontsize=6)
    fig.suptitle("Asymmetric-loss ablation (confirmation, raw policies, 95% group-bootstrap CI)", y=1.04, color=INK)
    fig.tight_layout()
    return save(fig, "asymmetric_loss_ablation")


# ------------------------------------------------------------------------------------------------ adequacy sensitivity
def fig_adequacy_sensitivity():
    s = T.adequacy_sensitivity(T.episodes("raw"))
    s = s[s["domain"] == "all"]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), gridspec_kw={"width_ratios": [1.2, 1]})
    y = np.arange(len(s))
    left = np.zeros(len(s))
    for colname, st_, c in (("models_validated", AQ.VALIDATED, STATUS_COL[AQ.VALIDATED]), ("models_restricted", AQ.RESTRICTED, STATUS_COL[AQ.RESTRICTED]),
                            ("models_unsupported", AQ.UNSUPPORTED, STATUS_COL[AQ.UNSUPPORTED])):
        axes[0].barh(y, s[colname], left=left, color=c, label=st_, edgecolor="#fcfcfb")
        left += s[colname].to_numpy()
    axes[0].set_yticks(y, [("► " if p else "") + v for v, p in zip(s["policy_variant"], s["is_primary_policy"])], fontsize=6.5)
    axes[0].invert_yaxis(); axes[0].set_xlabel("Number of evidence models"); axes[0].legend(fontsize=6, loc="lower right")
    axes[1].scatter(s["autonomous_coverage"], s["UAR"], color="#2a78d6", s=18)
    for _, r in s.iterrows():
        axes[1].annotate(r["policy_variant"], (r["autonomous_coverage"], r["UAR"]), fontsize=5, xytext=(2, 2), textcoords="offset points", color=INK2)
    axes[1].set_xlabel("Enforced AVOI autonomous coverage (all domains)"); axes[1].set_ylabel("Enforced AVOI UAR")
    fig.suptitle("Adequacy-policy sensitivity (► = frozen primary policy; alternatives are reported, not used)", y=1.02, color=INK)
    fig.tight_layout()
    return save(fig, "adequacy_sensitivity")


def fig_cost_violin():
    raw = T.cold(T.episodes("raw"))
    methods = ["AVOI", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI", "B6-ConfidenceThreshold",
               "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI", "B0-AllEvidence"]
    fig, axes = plt.subplots(3, 1, figsize=(7.5, 6.3))
    for ax, dom in zip(axes, DOMS):
        d = raw[raw["domain"] == dom]
        data = [d[d["method"] == m]["cost"].to_numpy(float) for m in methods]
        keep = [i for i, v in enumerate(data) if len(v)]
        if not keep:
            continue
        parts = ax.violinplot([data[i] for i in keep], showmedians=True, widths=0.8)
        for pc, i in zip(parts["bodies"], keep):
            pc.set_facecolor(st(methods[i])[0]); pc.set_alpha(0.55); pc.set_edgecolor("#fcfcfb")
        for key in ("cmedians", "cmins", "cmaxes", "cbars"):
            parts[key].set_color(INK2); parts[key].set_linewidth(0.8)
        ax.set_xticks(range(1, len(keep) + 1), [st(methods[i])[3] for i in keep], rotation=20, ha="right")
        ax.set_ylabel(f"{dom.upper()}\ncost / episode")
    fig.suptitle("Per-episode normalised acquisition cost (raw policies, confirmation)", color=INK)
    fig.tight_layout()
    return save(fig, "cost_violin")


def fig_decision_flow():
    raw, enf = T.cold(T.episodes("raw")), T.cold(T.episodes("enforced"))
    colors = {"Assured": "#2a78d6", "NotAssured": "#eb6834", "HumanReview (evidence uncertainty)": "#898781",
              "HumanReview (model adequacy)": "#e34948"}
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.0))
    for ax, dom in zip(axes, DOMS):
        rows = []
        for mode, df in (("raw", raw), ("enforced", enf)):
            x = df[(df["domain"] == dom) & (df["method"] == "AVOI")]
            if x.empty:
                continue
            gate = x["reason"].astype(str).str.startswith("MODEL_ADEQUACY")
            rows.append({"mode": mode, "Assured": (x["decision"] == "Assured").mean(), "NotAssured": (x["decision"] == "NotAssured").mean(),
                         "HumanReview (evidence uncertainty)": ((x["decision"] == HUMAN_REVIEW) & ~gate).mean(),
                         "HumanReview (model adequacy)": ((x["decision"] == HUMAN_REVIEW) & gate).mean()})
        R = pd.DataFrame(rows)
        if R.empty:
            continue
        left = np.zeros(len(R))
        for k, c in colors.items():
            ax.barh(R["mode"], R[k], left=left, color=c, edgecolor="#fcfcfb", label=k)
            left += R[k].to_numpy()
        ax.set_title(DT[dom], fontsize=8); ax.set_xlim(0, 1); ax.set_xlabel("Share of AVOI episodes")
    F1.shared_legend(fig, axes[None, :])
    fig.suptitle("AVOI terminal decisions: raw vs adequacy-enforced (escalation type separated)", y=1.06, color=INK)
    return save(fig, "decision_flow")


FIGURES = [("model_adequacy_diagnostics", fig_model_adequacy_diagnostics), ("calibration_curve", fig_calibration), ("roc_pr_curves", fig_roc_pr),
           ("risk_coverage_raw", fig_risk_coverage_raw), ("risk_coverage_adequacy_enforced", fig_risk_coverage_enforced),
           ("cost_safety_frontier", fig_frontier), ("budget_performance_curve", fig_budget), ("acquisition_risk_trajectory", fig_trajectory),
           ("evidence_request_ecdf", fig_ecdf), ("missingness_robustness", fig_missingness), ("missingness_uar_coverage", fig_missingness_uar_cov),
           ("privacy_safety_tradeoff", fig_privacy), ("action_frequency_heatmap", fig_action_frequency), ("asymmetric_loss_ablation", fig_asymmetric),
           ("adequacy_sensitivity", fig_adequacy_sensitivity), ("cost_violin", fig_cost_violin), ("decision_flow", fig_decision_flow)]


def all_figures() -> dict:
    F1.setup()
    out = {}
    for name, fn in FIGURES:
        try:
            out[name] = fn()
        except Exception as exc:  # recorded in the report, never hidden
            import traceback
            traceback.print_exc()
            out[name] = [f"FAILED: {exc!r}"]
    return out
