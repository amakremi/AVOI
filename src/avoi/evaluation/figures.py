"""Publication figures generated exclusively from saved raw experiment results (results/raw, results/traces).

Encoding: fixed categorical slot per method (validated palette; never cycled), plus marker and line-style as a
colour-independent secondary encoding; reference methods (all-evidence, random) in neutral grey. Every figure is saved
as vector PDF and 300-DPI PNG.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import precision_recall_curve, roc_curve  # noqa: E402

from avoi.bayes_risk import LossMatrix  # noqa: E402
from avoi.evaluation import analysis_data as AD  # noqa: E402
from avoi.evaluation import metrics as MT  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "results" / "figures"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
STYLE = {  # method -> (color, marker, linestyle, short label)
    "AVOI-GRC": ("#2a78d6", "o", "-", "AVOI-GRC"),
    "B1-FixedChecklist": ("#eb6834", "s", "--", "B1 Checklist"),
    "B4-InformationGain": ("#1baf7a", "^", "-.", "B4 Info-gain"),
    "B5-GenericVOI": ("#eda100", "D", ":", "B5 Generic VOI"),
    "B6-ConfidenceThreshold": ("#e87ba4", "v", "--", "B6 Confidence"),
    "B7-MyopicCostSensitiveVOI": ("#008300", "P", "-.", "B7 Myopic CS-VOI"),
    "B7b-Lookahead2VOI": ("#4a3aa7", "X", ":", "B7b Lookahead-2"),
    "B3-CheapestFirst": ("#e34948", "*", "-", "B3 Cheapest-first"),
    "B0-AllEvidence": ("#898781", "h", "-", "B0 All evidence"),
    "B2-Random": ("#b5b3ab", "x", ":", "B2 Random (20 seeds)"),
}
CURVE_METHODS = ["AVOI-GRC", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
                 "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI", "B0-AllEvidence", "B2-Random"]
DOM_TITLE = {"iam": "Controlled IAM testbed", "ait": "AIT-LDS v2.0 replay", "cert": "CERT r4.2 replay"}


def setup():
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
                         "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "axes.spines.top": False,
                         "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 7, "lines.linewidth": 1.6,
                         "lines.markersize": 4.5, "savefig.bbox": "tight", "pdf.fonttype": 42})


def save(fig, name: str) -> list[str]:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=300)
    plt.close(fig)
    return [f"results/figures/{name}.pdf", f"results/figures/{name}.png"]


def st(m):
    return STYLE.get(m, ("#52514e", "o", "-", m))


def domains_present(experiment="primary"):
    return [d for d in AD.DOMAINS if not AD.episodes(experiment, d).empty]


def shared_legend(fig, axes):
    handles, labels = {}, {}
    for ax in np.ravel(axes):
        for h, l in zip(*ax.get_legend_handles_labels()):
            key = l.split(" (AURC")[0]
            if key not in handles:
                handles[key], labels[key] = h, key
    fig.legend(list(handles.values()), list(labels.values()), loc="upper center", ncol=min(5, len(handles)),
               bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout()


# ------------------------------------------------------------------------------------------------ Figure 1
def fig_risk_coverage() -> list[str]:
    doms = domains_present()
    fig, axes = plt.subplots(1, len(doms), figsize=(2.6 * len(doms) + 0.6, 2.8), squeeze=False)
    for ax, dom in zip(axes[0], doms):
        cur = AD.curves("primary", dom)
        for m in CURVE_METHODS:
            c = AD.pooled_curve(cur, m)
            if c.empty:
                continue
            col, mk, ls, lab = st(m)
            c = c.sort_values("coverage")
            if len(c) > 1:
                ax.plot(c["coverage"], c["UAR"], color=col, ls=ls, marker=mk, markevery=max(1, len(c) // 8),
                        label=f"{lab} (AURC {AD.aurc(c):.3f})", zorder=3 if m == "AVOI-GRC" else 2,
                        lw=2.2 if m == "AVOI-GRC" else 1.4)
            else:
                ax.plot(c["coverage"], c["UAR"], color=col, marker=mk, ls="none", ms=7, label=lab,
                        markeredgecolor="#fcfcfb", markeredgewidth=0.8)
        ax.set_title(DOM_TITLE[dom])
        ax.set_xlabel("Autonomous coverage")
        ax.set_xlim(-0.02, 1.02)
    axes[0][0].set_ylabel("Unsafe assurance rate (UAR)")
    shared_legend(fig, axes)
    fig.suptitle("Risk–coverage (held-out, thresholds varied)", y=1.06, color=INK)
    return save(fig, "risk_coverage_curve")


# ------------------------------------------------------------------------------------------------ Figure 2
def pareto_mask(x, y):
    pts = np.column_stack([x, y])
    keep = np.ones(len(pts), bool)
    for i, p in enumerate(pts):
        if np.any(np.all(pts <= p, axis=1) & np.any(pts < p, axis=1)):
            keep[i] = False
    return keep


def fig_cost_safety_frontier() -> list[str]:
    doms = domains_present()
    fig, axes = plt.subplots(2, len(doms), figsize=(2.6 * len(doms) + 0.6, 5.0), squeeze=False)
    for j, dom in enumerate(doms):
        cur = AD.curves("primary", dom)
        allpts = []
        for m in CURVE_METHODS:
            c = AD.pooled_curve(cur, m)
            if c.empty:
                continue
            col, mk, ls, lab = st(m)
            for i, ycol in enumerate(("expected_loss", "UAR")):
                axes[i][j].scatter(c["cost"], c[ycol], s=10 if m != "AVOI-GRC" else 16, color=col, marker=mk, label=lab,
                                   alpha=0.9, linewidths=0, zorder=3 if m == "AVOI-GRC" else 2)
            allpts.append(c.assign(method=m))
        pts = pd.concat(allpts)
        for i, ycol in enumerate(("expected_loss", "UAR")):
            p = pts.dropna(subset=[ycol])
            mask = pareto_mask(p["cost"].to_numpy(), p[ycol].to_numpy())
            fr = p[mask].sort_values("cost")
            axes[i][j].step(fr["cost"], fr[ycol], where="post", color=INK, lw=0.9, zorder=4, label="Pareto frontier (all methods)")
            share = (fr["method"] == "AVOI-GRC").mean()
            axes[i][j].text(0.98, 0.95, f"AVOI share of frontier: {share:.0%}", transform=axes[i][j].transAxes, ha="right",
                            va="top", fontsize=6.5, color=INK2)
        axes[0][j].set_title(DOM_TITLE[dom])
        axes[1][j].set_xlabel("Mean normalised acquisition cost")
    axes[0][0].set_ylabel("Expected decision loss")
    axes[1][0].set_ylabel("Unsafe assurance rate")
    shared_legend(fig, axes)
    fig.suptitle("Cost–safety frontier (each point = one threshold configuration, held-out)", y=1.06, color=INK)
    return save(fig, "cost_safety_frontier")


# ------------------------------------------------------------------------------------------------ Figure 3
def fig_budget() -> list[str]:
    doms = domains_present()
    fig, axes = plt.subplots(2, len(doms), figsize=(2.6 * len(doms) + 0.6, 5.0), squeeze=False)
    for j, dom in enumerate(doms):
        from avoi.evaluation.posthoc import budget_filled
        bud = budget_filled(dom)
        bud["method_family"] = bud["method"].str.replace(r"\[s\d+\]", "", regex=True)
        for m in ["AVOI-GRC", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
                  "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI", "B2-Random"]:
            s = bud[bud["method_family"] == m]
            if s.empty:
                continue
            col, mk, ls, lab = st(m)
            ks, loss, lo, hi, bacc = [], [], [], [], []
            for k, g in s.groupby("budget"):
                if m == "B2-Random":
                    g = g.groupby(["objective", "fold", "episode_index", "y"], as_index=False)[["loss", "belief"]].mean()
                y = g["y"].to_numpy()
                I = MT.stratified_indices(y, 2000, 1)
                lv = g["loss"].to_numpy(float)[I].mean(1)
                ks.append(k); loss.append(g["loss"].mean()); lo.append(np.quantile(lv, .025)); hi.append(np.quantile(lv, .975))
                b = g["belief"].to_numpy(float)
                rec_v = ((b < 0.5) & (y == 0)).sum() / max(1, (y == 0).sum())
                spec = ((b >= 0.5) & (y == 1)).sum() / max(1, (y == 1).sum())
                bacc.append((rec_v + spec) / 2)
            axes[0][j].plot(ks, loss, color=col, marker=mk, ls=ls, label=lab, lw=2.2 if m == "AVOI-GRC" else 1.3)
            axes[0][j].fill_between(ks, lo, hi, color=col, alpha=0.12, lw=0)
            axes[1][j].plot(ks, bacc, color=col, marker=mk, ls=ls, label=lab, lw=2.2 if m == "AVOI-GRC" else 1.3)
        axes[0][j].set_title(DOM_TITLE[dom])
        axes[1][j].set_xlabel("Budget (max. acquisitions)")
    axes[0][0].set_ylabel("Expected decision loss (95% CI)")
    axes[1][0].set_ylabel("Balanced accuracy of posterior")
    shared_legend(fig, axes)
    fig.suptitle("Evidence-budget performance (tuned thresholds, hard budget)", y=1.06, color=INK)
    return save(fig, "budget_performance_curve")


# ------------------------------------------------------------------------------------------------ Figure 4
def fig_calibration() -> list[str]:
    doms = domains_present()
    fig, axes = plt.subplots(1, len(doms), figsize=(2.6 * len(doms) + 0.6, 2.9), squeeze=False)
    for ax, dom in zip(axes[0], doms):
        ax.plot([0, 1], [0, 1], color=MUTED, lw=0.8, ls="--", label="Perfect calibration")
        for exp, method, label, col, mk in (("primary", "B0-AllEvidence", "TAN, all evidence", "#2a78d6", "o"),
                                            ("primary", "masked_random", "TAN, random evidence subsets", "#1baf7a", "s"),
                                            ("model_lr", "B0-AllEvidence", "Calibrated LR, all evidence", "#eb6834", "^")):
            c = AD.table(exp, dom, "calib")
            if c.empty:
                continue
            s = c[c["method"] == method]
            if s.empty:
                continue
            rt = MT.reliability_table(s["y"], s["belief_full"])
            cm = MT.calibration_metrics(s["y"].to_numpy(), s["belief_full"].to_numpy())
            ax.errorbar(rt["mean_predicted"], rt["observed"], yerr=[rt["observed"] - rt["ci_low"], rt["ci_high"] - rt["observed"]],
                        color=col, marker=mk, lw=1.2, capsize=1.5, label=f"{label} (Brier {cm['Brier']:.3f}, ECE {cm['ECE']:.3f})")
        ax.set_title(DOM_TITLE[dom])
        ax.set_xlabel("Predicted P(Y=1 | E)")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=5.8)
    axes[0][0].set_ylabel("Observed frequency of Y=1")
    fig.suptitle("Calibration / reliability of the evidence models (held-out, 10 bins, 95% CI)", y=1.06, color=INK)
    return save(fig, "calibration_curve")


# ------------------------------------------------------------------------------------------------ Figure 5
def trajectory_matrix(traces, loss: LossMatrix):
    rows = []
    for tr in traces:
        op = tr["operating_point"]
        stop = op["n_acquisitions"]
        risks = [loss.risk(s["belief"]) for s in tr["states"][: stop + 1]]
        rows.append((tr["y"], risks))
    T = max(len(r) for _, r in rows)
    M = np.array([r + [r[-1]] * (T - len(r)) for _, r in rows])
    return np.array([y for y, _ in rows]), M


def fig_trajectory() -> list[str]:
    doms = domains_present()
    loss = LossMatrix()
    fig, axes = plt.subplots(1, len(doms), figsize=(2.6 * len(doms) + 0.6, 2.9), squeeze=False)
    for ax, dom in zip(axes[0], doms):
        for m in ("AVOI-GRC", "B1-FixedChecklist", "B4-InformationGain", "B6-ConfidenceThreshold"):
            traces = AD.load_traces(dom, m)
            if not traces:
                continue
            y, M = trajectory_matrix(traces, loss)
            col, mk, ls, lab = st(m)
            for cls, lsty, name in ((1, "-", "satisfied"), (0, "--", "violated")):
                sub = M[y == cls]
                if len(sub) == 0:
                    continue
                t = np.arange(sub.shape[1])
                I = np.random.default_rng(0).integers(0, len(sub), (2000, len(sub)))
                bs = sub[I].mean(1)
                ax.plot(t, sub.mean(0), color=col, ls=lsty, marker=mk, markevery=2, label=f"{lab} – Y {name}",
                        lw=2.0 if m == "AVOI-GRC" else 1.2)
                ax.fill_between(t, np.quantile(bs, .025, axis=0), np.quantile(bs, .975, axis=0), color=col, alpha=0.10, lw=0)
        ax.set_title(DOM_TITLE[dom])
        ax.set_xlabel("Evidence-acquisition step")
    axes[0][0].set_ylabel("Mean posterior Bayes risk (95% CI)")
    shared_legend(fig, axes)
    fig.suptitle("Sequential assurance-risk trajectory (carried forward after stopping)", y=1.06, color=INK)
    return save(fig, "acquisition_risk_trajectory")


# ------------------------------------------------------------------------------------------------ Figure 6
def fig_ecdf() -> list[str]:
    doms = domains_present()
    fig, axes = plt.subplots(1, len(doms), figsize=(2.6 * len(doms) + 0.6, 2.8), squeeze=False)
    for ax, dom in zip(axes[0], doms):
        df = AD.tuned("primary", dom)
        for m in CURVE_METHODS:
            x = AD.per_method(df, m)
            if x.empty:
                continue
            col, mk, ls, lab = st(m)
            v = np.sort(x["n_acq"].to_numpy(float))
            ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", color=col, ls=ls, label=lab,
                    lw=2.2 if m == "AVOI-GRC" else 1.2)
        ax.set_title(DOM_TITLE[dom])
        ax.set_xlabel("Acquisitions before decision")
        ax.set_ylim(0, 1.02)
    axes[0][0].set_ylabel("Cumulative proportion of episodes")
    shared_legend(fig, axes)
    fig.suptitle("ECDF of evidence requests (tuned operating points, held-out)", y=1.06, color=INK)
    return save(fig, "evidence_request_ecdf")


# ------------------------------------------------------------------------------------------------ Figure 7
def fig_privacy_tradeoff() -> list[str]:
    doms = [d for d in AD.DOMAINS if not AD.episodes("weight_sensitivity", d).empty]
    fig, axes = plt.subplots(2, len(doms), figsize=(2.6 * len(doms) + 0.6, 5.0), squeeze=False)
    for j, dom in enumerate(doms):
        ws = AD.episodes("weight_sensitivity", dom)
        ws = ws[(ws["start"] == "cold") & (ws["shift"] == "none") & ws["condition"].str.contains(r"lam=1\.0\|mu=")]
        pts = []
        for cond, g in ws.groupby("condition"):
            mu = float(cond.split("mu=")[1].split("|")[0])
            s = MT.decision_metrics(g)
            pts.append((mu, s["privacy_exposure"], s["expected_loss"], s["UAR"]))
        prim = AD.tuned("primary", dom)
        s = MT.decision_metrics(AD.per_method(prim, "AVOI-GRC"))
        pts.append((1.0, s["privacy_exposure"], s["expected_loss"], s["UAR"]))
        pts = sorted(set(pts))
        for i, idx in enumerate((2, 3)):
            ax = axes[i][j]
            ax.plot([p[1] for p in pts], [p[idx] for p in pts], color=st("AVOI-GRC")[0], marker="o", lw=1.8, label="AVOI-GRC (μ varied)")
            for p in (pts[0], pts[-1]):
                ax.annotate(f"μ×{p[0]:g}", (p[1], p[idx]), textcoords="offset points", xytext=(3, 3), fontsize=6, color=INK2)
            for m in ("B1-FixedChecklist", "B4-InformationGain", "B5-GenericVOI", "B6-ConfidenceThreshold", "B0-AllEvidence"):
                x = AD.per_method(prim, m)
                if x.empty:
                    continue
                sm = MT.decision_metrics(x)
                col, mk, ls, lab = st(m)
                ax.plot(sm["privacy_exposure"], sm[["expected_loss", "UAR"][i]], color=col, marker=mk, ls="none", ms=6, label=lab)
        axes[0][j].set_title(DOM_TITLE[dom])
        axes[1][j].set_xlabel("Mean normalised privacy exposure")
    axes[0][0].set_ylabel("Expected decision loss")
    axes[1][0].set_ylabel("Unsafe assurance rate")
    shared_legend(fig, axes)
    fig.suptitle("Privacy–safety trade-off (privacy weight μ varied; thresholds re-tuned per μ)", y=1.06, color=INK)
    return save(fig, "privacy_safety_tradeoff")


# ------------------------------------------------------------------------------------------------ Figure 8
def missingness_frame(dom):
    df = AD.episodes("primary", dom)
    df = df[(df["condition"] == AD.PRIMARY_COND) & (df["shift"] == "none")]
    rows = []
    for (m, mode, level), g in df.groupby(["method", "missing_mode", "missing_level"]):
        if m.startswith("B2-Random"):
            continue
        s = MT.decision_metrics(g)
        rows.append({"method": m, "mode": mode, "level": level, "expected_loss": s["expected_loss"], "UAR": s["UAR"],
                     "acquisitions": s["mean_acquisitions"], "n": s["n"]})
    out = pd.DataFrame(rows)
    cold = out[out["mode"] == "none"]
    full = []
    for mode in ("mcar", "block", "adversarial"):
        full.append(pd.concat([out[out["mode"] == mode], cold.assign(mode=mode)]))
    return pd.concat(full) if full else out


def fig_missingness() -> list[str]:
    doms = domains_present()
    paths = []
    for metric, name, ylab in (("expected_loss", "missingness_robustness_curve", "Expected decision loss"),
                               ("UAR", "missingness_uar_curve", "Unsafe assurance rate")):
        fig, axes = plt.subplots(len(doms), 3, figsize=(8.2, 2.3 * len(doms) + 0.6), squeeze=False, sharex=True)
        for i, dom in enumerate(doms):
            mf = missingness_frame(dom)
            for j, mode in enumerate(("mcar", "block", "adversarial")):
                ax = axes[i][j]
                for m in ("AVOI-GRC", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
                          "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI"):
                    s = mf[(mf["method"] == m) & (mf["mode"] == mode)].sort_values("level")
                    if s.empty:
                        continue
                    col, mk, ls, lab = st(m)
                    ax.plot(100 * s["level"], s[metric], color=col, marker=mk, ls=ls, label=lab, lw=2.2 if m == "AVOI-GRC" else 1.2)
                if i == 0:
                    ax.set_title({"mcar": "MCAR initial availability", "block": "Source-block missingness",
                                  "adversarial": "Adversarially inconvenient"}[mode])
                if j == 0:
                    ax.set_ylabel(f"{DOM_TITLE[dom]}\n{ylab}")
                if i == len(doms) - 1:
                    ax.set_xlabel("Initially unacquired (%); 100 = cold start")
        shared_legend(fig, axes)
        fig.suptitle("Missing-evidence robustness (held-out; thresholds tuned at cold start)", y=1.06, color=INK)
        paths += save(fig, name)
    return paths


# ------------------------------------------------------------------------------------------------ additional figures
def fig_roc_pr() -> list[str]:
    doms = domains_present()
    fig, axes = plt.subplots(2, len(doms), figsize=(2.6 * len(doms) + 0.6, 5.0), squeeze=False)
    for j, dom in enumerate(doms):
        for exp, lab, col, ls in (("primary", "TAN", "#2a78d6", "-"), ("model_lr", "Calibrated LR", "#eb6834", "--")):
            c = AD.table(exp, dom, "calib")
            if c.empty:
                continue
            s = c[c["method"] == "B0-AllEvidence"]
            yv = (s["y"] == 0).astype(int)
            score = 1 - s["belief_full"]
            fpr, tpr, _ = roc_curve(yv, score)
            pr, rc, _ = precision_recall_curve(yv, score)
            axes[0][j].plot(fpr, tpr, color=col, ls=ls, label=lab)
            axes[1][j].plot(rc, pr, color=col, ls=ls, label=lab)
        axes[0][j].plot([0, 1], [0, 1], color=MUTED, lw=0.7, ls=":")
        axes[0][j].set_title(DOM_TITLE[dom]); axes[0][j].set_xlabel("False-positive rate (violation)")
        axes[1][j].set_xlabel("Recall (violation)")
    axes[0][0].set_ylabel("True-positive rate"); axes[1][0].set_ylabel("Precision (violation)")
    shared_legend(fig, axes)
    fig.suptitle("Violation detection with all evidence (held-out posterior)", y=1.06, color=INK)
    return save(fig, "roc_pr_curves")


def fig_sensitivity_heatmap() -> list[str]:
    doms = [d for d in AD.DOMAINS if not AD.curves("loss_sensitivity", d).empty]
    if not doms:
        return []
    fig, axes = plt.subplots(1, len(doms), figsize=(3.6 * len(doms) + 0.8, 3.0), squeeze=False, gridspec_kw={"wspace": 0.45})
    for ax, dom in zip(axes[0], doms):
        cur = AD.curves("loss_sensitivity", dom)
        grid = []
        fas = sorted({float(c.split("fa=")[1].split("|")[0]) for c in cur["condition"].unique()})
        for fa in fas:
            cond = f"fa={fa}|lam=1.0|mu=1.0|nu=1.0"
            c = AD.pooled_curve(cur, "AVOI-GRC", cond)
            L = LossMatrix(fa, 2.0, 1.0)
            # realised loss under that FA penalty is stored per condition
            grid.append(c.set_index("tau")["expected_loss"])
        G = pd.DataFrame(grid, index=fas)
        cols = [t for t in G.columns if np.isclose((t * 20) % 1, 0) or np.isclose((t * 20) % 1, 1)]
        G = G[cols]
        im = ax.imshow(G.to_numpy(), aspect="auto", cmap="Blues", origin="lower")
        ax.set_yticks(range(len(fas)), [f"{f:g}" for f in fas])
        step = max(1, len(cols) // 6)
        ax.set_xticks(range(0, len(cols), step), [f"{c:.2f}" for c in cols[::step]])
        ax.set_xlabel("Risk threshold τ"); ax.set_title(DOM_TITLE[dom]); ax.grid(False)
        fig.colorbar(im, ax=ax, fraction=0.046, label="Expected loss (AVOI)")
    axes[0][0].set_ylabel("False-assurance penalty")
    fig.suptitle("Sensitivity: risk threshold × false-assurance penalty (held-out)", y=1.06, color=INK)
    return save(fig, "sensitivity_heatmap_tau_fa")


def fig_action_frequency() -> list[str]:
    traces = AD.load_traces("iam", "AVOI-GRC")
    if not traces:
        return []
    rows = []
    for tr in traces:
        k = tr["operating_point"]["n_acquisitions"]
        for s in tr["steps"][:k]:
            rows.append((tr["objective_id"], s["selected_action"], s["t"]))
    df = pd.DataFrame(rows, columns=["objective", "action", "t"])
    n_ep = pd.Series([tr["objective_id"] for tr in traces]).value_counts()
    fig, axes = plt.subplots(2, 3, figsize=(14, 6.5), gridspec_kw={"wspace": 1.1, "hspace": 0.45})
    for ax, (obj, g) in zip(np.ravel(axes), df.groupby("objective")):
        freq = g.pivot_table(index="action", columns="t", aggfunc="size", fill_value=0) / n_ep[obj]
        im = ax.imshow(freq.to_numpy(), aspect="auto", cmap="Blues", vmin=0, vmax=1)
        ax.set_yticks(range(len(freq.index)), freq.index, fontsize=5.5)
        ax.set_xticks(range(len(freq.columns)), freq.columns)
        ax.set_title(obj, fontsize=7); ax.set_xlabel("Step"); ax.grid(False)
    fig.colorbar(im, ax=axes, fraction=0.02, label="Fraction of episodes selecting action at step")
    fig.suptitle("AVOI-GRC action selection frequency by objective (IAM, held-out)", color=INK)
    return save(fig, "action_frequency_heatmap")


def fig_cost_violin() -> list[str]:
    doms = domains_present()
    methods = ["AVOI-GRC", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
               "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI", "B0-AllEvidence"]
    fig, axes = plt.subplots(len(doms), 1, figsize=(7.5, 2.1 * len(doms)), squeeze=False)
    for ax, dom in zip(axes[:, 0], doms):
        df = AD.tuned("primary", dom)
        data = [AD.per_method(df, m)["cost"].to_numpy(float) for m in methods]
        parts = ax.violinplot(data, showmedians=True, widths=0.8)
        for pc, m in zip(parts["bodies"], methods):
            pc.set_facecolor(st(m)[0]); pc.set_alpha(0.55); pc.set_edgecolor("#fcfcfb")
        for key in ("cmedians", "cmins", "cmaxes", "cbars"):
            parts[key].set_color(INK2); parts[key].set_linewidth(0.8)
        ax.set_xticks(range(1, len(methods) + 1), [st(m)[3] for m in methods], rotation=20, ha="right")
        ax.set_ylabel(f"{DOM_TITLE[dom]}\ncost per episode")
    fig.suptitle("Per-episode normalised acquisition cost (tuned operating points)", color=INK)
    return save(fig, "cost_violin")


def fig_decision_flow() -> list[str]:
    doms = domains_present()
    fig, axes = plt.subplots(1, len(doms), figsize=(2.6 * len(doms) + 0.6, 2.8), squeeze=False)
    colors = {"Assured": "#2a78d6", "NotAssured": "#eb6834", "HumanReview": "#898781"}
    for ax, dom in zip(axes[0], doms):
        x = AD.per_method(AD.tuned("primary", dom), "AVOI-GRC")
        tab = x.pivot_table(index="n_acq", columns="decision", aggfunc="size", fill_value=0) / len(x)
        bottom = np.zeros(len(tab))
        for d in ("Assured", "NotAssured", "HumanReview"):
            if d in tab:
                ax.bar(tab.index, tab[d], bottom=bottom, color=colors[d], label=d, edgecolor="#fcfcfb", linewidth=1)
                bottom += tab[d].to_numpy()
        ax.set_title(DOM_TITLE[dom]); ax.set_xlabel("Acquisitions before stopping")
    axes[0][0].set_ylabel("Share of episodes")
    shared_legend(fig, axes)
    fig.suptitle("AVOI-GRC state transitions: Unknown → acquire × k → terminal decision", y=1.06, color=INK)
    return save(fig, "decision_flow")


def all_figures() -> dict[str, list[str]]:
    setup()
    out = {}
    for name, fn in [("Figure 1 risk-coverage", fig_risk_coverage), ("Figure 2 cost-safety frontier", fig_cost_safety_frontier),
                     ("Figure 3 budget performance", fig_budget), ("Figure 4 calibration", fig_calibration),
                     ("Figure 5 risk trajectory", fig_trajectory), ("Figure 6 ECDF", fig_ecdf),
                     ("Figure 7 privacy-safety", fig_privacy_tradeoff), ("Figure 8 missingness", fig_missingness),
                     ("ROC/PR", fig_roc_pr), ("Sensitivity heatmap", fig_sensitivity_heatmap),
                     ("Action frequency heatmap", fig_action_frequency), ("Cost violin", fig_cost_violin),
                     ("Decision flow", fig_decision_flow)]:
        try:
            out[name] = fn()
        except Exception as exc:  # recorded in the report, never silently hidden
            import traceback
            out[name] = [f"FAILED: {exc!r}"]
            traceback.print_exc()
    return out
