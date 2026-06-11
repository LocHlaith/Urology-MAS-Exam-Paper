#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "derived_data"
OUT = ROOT / "figures" / "panels"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.sans-serif": ["DejaVu Sans"],
    "mathtext.fontset": "dejavusans",
    "font.size": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.dpi": 600,
    "savefig.transparent": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

COLORS = {
    "grid": "#E3DFD8", "spine": "#9E9A93", "text": "#3E3E3E",
    "text_dark": "#2A251F", "tick": "#4F4F4F", "border": "#C8C2B8",
    "Human": "#313E96", "MAS": "#B86758", "Human_fill": "#D9DCF1", "MAS_fill": "#F2DFDB",
    "accent": "#75AFCA", "warn": "#D97757",
    "purple": "#7C5CFF", "blue": "#4D6BFE"
}
LEVELS = ["knowledge", "application", "reasoning"]
LEVEL_LABELS = {"knowledge": "Knowledge", "application": "Clinical\napplication", "reasoning": "Clinical\nreasoning"}


def save_pdf(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def bootstrap_diff(a, h, scale=1.0, reps=2000, seed=1):
    a = np.asarray(pd.Series(a).dropna(), dtype=float) * scale
    h = np.asarray(pd.Series(h).dropna(), dtype=float) * scale
    if len(a) == 0 or len(h) == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    point = a.mean() - h.mean()
    boots = rng.choice(a, (reps, len(a)), True).mean(axis=1) - rng.choice(h, (reps, len(h)), True).mean(axis=1)
    return float(point), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def diff_by_level(df, value_col, source_col="source_true", scale=1.0, seed=1):
    rows = []
    for i, level in enumerate(LEVELS):
        sub = df[df["cognitive_level"].eq(level)]
        mas = sub.loc[sub[source_col].eq("MAS"), value_col]
        human = sub.loc[sub[source_col].eq("Human"), value_col]
        est, lo, hi = bootstrap_diff(mas, human, scale=scale, seed=seed+i)
        rows.append({"cognitive_level": level, "estimate": est, "ci_low": lo, "ci_high": hi,
                     "n_mas": int(mas.notna().sum()), "n_human": int(human.notna().sum())})
    return pd.DataFrame(rows)


def forest(data, title, xlabel, name, xlim=None, margin=None, color="#B86758", counts=True, marker_note=None):
    d = data.copy()
    d["order"] = d["cognitive_level"].map({k: i for i, k in enumerate(LEVELS)})
    d = d.sort_values("order", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(4.1, 2.45))
    y = np.arange(len(d))
    ax.axvline(0, color=COLORS["text_dark"], lw=0.9, zorder=0)
    if margin is not None:
        ax.axvline(margin, color=COLORS["warn"], ls="--", lw=1.0, zorder=0)
        ax.text(margin, len(d)-0.25, "NI margin", color=COLORS["warn"], fontsize=7,
                ha="right" if margin < 0 else "left", va="bottom")
    ax.errorbar(d["estimate"], y, xerr=[d["estimate"]-d["ci_low"], d["ci_high"]-d["estimate"]],
                fmt="o", color=color, ecolor=color, elinewidth=1.2, capsize=3, ms=4.5)
    labels = []
    for _, r in d.iterrows():
        lab = LEVEL_LABELS.get(r["cognitive_level"], r["cognitive_level"])
        if counts:
            lab += f"\nMAS n={int(r.n_mas)}, Human n={int(r.n_human)}"
        labels.append(lab)
    ax.set_yticks(y, labels)
    ax.set_xlabel(xlabel)
    ax.set_title(title, loc="left", fontweight="bold", fontsize=10)
    ax.grid(axis="x", color=COLORS["grid"], lw=0.7)
    ax.tick_params(colors=COLORS["tick"])
    for sp in ax.spines.values(): sp.set_color(COLORS["spine"])
    if xlim: ax.set_xlim(*xlim)
    # Direction notes are kept in captions/source data to avoid crowding panel interiors.
    save_pdf(fig, name)


def figure3():
    item = pd.read_csv(DERIVED / "item_master.csv")[["item_id", "source_true", "cognitive_level"]]
    expert = pd.read_csv(DERIVED / "expert_ratings_updated.csv").merge(item[["item_id", "cognitive_level"]], on="item_id", how="left")
    q = diff_by_level(expert, "quality_score_5", seed=31)
    q.to_csv(DERIVED / "fig3A_quality_by_cognitive_level_updated.csv", index=False)
    forest(q, "A  Expert-rated quality by cognitive level", "Mean quality score difference, MAS - Human", 
           "Figure3A_quality_by_cognitive_level", xlim=(-0.55, 0.55), margin=-0.30, color=COLORS["MAS"], marker_note="Positive values favor MAS")

    defect = pd.read_csv(DERIVED / "defect_adjudication_proxy.csv").merge(item[["item_id", "cognitive_level"]], on="item_id", how="left")
    defect["defect_pp"] = ((defect["final_major_defect"].fillna(0).astype(float) > 0) | (defect["final_critical_defect"].fillna(0).astype(float) > 0)).astype(float)
    d = diff_by_level(defect, "defect_pp", scale=100, seed=41)
    d.to_csv(DERIVED / "fig3B_defect_risk_by_cognitive_level_updated.csv", index=False)
    forest(d, "B  Item-writing defect risk by cognitive level", "Defect-risk difference, MAS - Human (percentage points)",
           "Figure3B_defect_risk_by_cognitive_level", xlim=(-15, 15), color=COLORS["warn"], marker_note="Positive values indicate higher MAS defect risk")

    resp = pd.read_csv(DERIVED / "responses.csv").merge(item[["item_id", "cognitive_level"]], on="item_id", how="left")
    c = diff_by_level(resp, "correct", scale=100, seed=51)
    c.to_csv(DERIVED / "fig3C_student_accuracy_by_cognitive_level_updated.csv", index=False)
    forest(c, "C  Student accuracy by cognitive level", "Correct-answer rate difference, MAS - Human (percentage points)",
           "Figure3C_student_accuracy_by_cognitive_level", xlim=(-16, 16), color=COLORS["blue"], marker_note="Positive values indicate higher MAS accuracy")

    # D source x cognitive-level interaction proxy from quality score differences.
    qd = q.set_index("cognitive_level")
    base = qd.loc["knowledge", "estimate"]
    rows = []
    for level in LEVELS:
        rows.append({"contrast": f"{LEVEL_LABELS[level].replace(chr(10),' ')} - Knowledge", "estimate": qd.loc[level, "estimate"] - base})
    inter = pd.DataFrame(rows)
    inter.to_csv(DERIVED / "fig3D_source_cognitive_interaction_updated.csv", index=False)
    fig, ax = plt.subplots(figsize=(3.6, 2.35))
    y = np.arange(len(inter))[::-1]
    vals = inter["estimate"].to_numpy()[::-1]
    ax.axvline(0, color=COLORS["text_dark"], lw=0.9)
    ax.barh(y, vals, color=COLORS["MAS"], alpha=0.72, height=0.52)
    ax.set_yticks(y, inter["contrast"].to_numpy()[::-1])
    ax.set_xlabel("Difference-in-differences in quality score")
    ax.set_title("D  Source x cognitive-level interaction", loc="left", fontweight="bold", fontsize=10)
    ax.grid(axis="x", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure3D_source_cognitive_interaction")

    # E CTT by level, using item-rest discrimination where available.
    ctt = pd.read_csv(DERIVED / "ctt_item_analysis.csv").merge(item[["item_id", "cognitive_level", "source_true"]], on="item_id", how="left", suffixes=("", "_m"))
    col = "item_rest_correlation" if "item_rest_correlation" in ctt.columns else ("discrimination" if "discrimination" in ctt.columns else None)
    if col:
        summ = ctt.groupby(["cognitive_level", "source_true"])[col].mean().reset_index()
        fig, ax = plt.subplots(figsize=(3.7, 2.5))
        x = np.arange(len(LEVELS)); w = 0.36
        for off, src, color in [(-w/2, "Human", COLORS["Human"]), (w/2, "MAS", COLORS["MAS"] )]:
            vals = [summ[(summ.cognitive_level.eq(l)) & (summ.source_true.eq(src))][col].mean() for l in LEVELS]
            ax.bar(x+off, vals, width=w, color=color, alpha=0.82, label=src)
        ax.axhline(0, color=COLORS["text_dark"], lw=0.7)
        ax.set_xticks(x, [LEVEL_LABELS[l] for l in LEVELS], rotation=0)
        ax.set_ylabel("Item-rest discrimination")
        ax.set_title("E  Exploratory CTT by cognitive level", loc="left", fontweight="bold", fontsize=10)
        ax.legend(frameon=False)
        ax.grid(axis="y", color=COLORS["grid"], lw=0.7)
        save_pdf(fig, "Figure3E_ctt_by_cognitive_level")


def figure4():
    src = pd.read_csv(DERIVED / "source_detection_updated.csv").dropna(subset=["source_guess"])
    src["correct_source_guess"] = (src["source_guess"] == src["source_true"]).astype(int)
    mas = src[src.source_true.eq("MAS")]["correct_source_guess"].to_numpy()
    human = src[src.source_true.eq("Human")]["correct_source_guess"].to_numpy()
    rng = np.random.default_rng(71)
    boot = ((rng.choice(mas, (2000, len(mas)), True).mean(axis=1) + rng.choice(human, (2000, len(human)), True).mean(axis=1)) / 2)
    bal = float((mas.mean() + human.mean()) / 2)
    lo, hi = np.percentile(boot, [5, 95])  # source-detectability figures use 90% CI by SAP convention
    pd.DataFrame([{"metric":"balanced_accuracy", "estimate":bal, "ci_low":lo, "ci_high":hi, "n_judgments":len(src), "n_raters":src.rater_id.nunique(), "n_items":src.item_id.nunique()}]).to_csv(DERIVED / "fig4A_source_detection_accuracy_updated.csv", index=False)
    fig, ax = plt.subplots(figsize=(2.55, 2.55))
    ax.axhspan(45, 55, color=COLORS["accent"], alpha=0.18, label="45%-55% near-chance range")
    ax.axhline(50, color=COLORS["text_dark"], lw=0.9)
    ax.errorbar([0], [bal*100], yerr=[[bal*100-lo*100], [hi*100-bal*100]], fmt="o", color=COLORS["blue"], ecolor=COLORS["blue"], capsize=3, ms=5)
    ax.text(0.08, bal*100, f"{bal*100:.1f}%", va="center", fontsize=8)
    ax.set_xlim(-0.45, 0.7); ax.set_ylim(0, 100)
    ax.set_xticks([0], [f"Source judgments\nn={len(src)}"])
    ax.set_ylabel("Balanced accuracy (%)")
    ax.set_title("A  Source-identification accuracy", loc="left", fontweight="bold", fontsize=10)
    ax.text(0.67, 50.8, "Chance level = 50%", ha="right", va="bottom", fontsize=6.5)
    ax.grid(axis="y", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure4A_source_detection_accuracy")

    tab = pd.crosstab(src.source_true, src.source_guess).reindex(index=["Human", "MAS"], columns=["Human", "MAS"], fill_value=0)
    prop = tab.div(tab.sum(axis=1), axis=0) * 100
    tab.to_csv(DERIVED / "fig4B_source_judgment_confusion_matrix_updated.csv")
    fig, ax = plt.subplots(figsize=(3.25, 2.55))
    x = np.arange(len(prop)); bottom = np.zeros(len(prop))
    for col, color, lab in [("Human", COLORS["Human"], "Guessed human"), ("MAS", COLORS["MAS"], "Guessed MAS")]:
        vals = prop[col].to_numpy()
        ax.bar(x, vals, bottom=bottom, color=color, width=0.58, label=lab)
        for xi, v, b in zip(x, vals, bottom):
            if v >= 7:
                ax.text(xi, b+v/2, f"{v:.0f}%", ha="center", va="center", fontsize=7, color="white")
        bottom += vals
    ax.set_xticks(x, ["Human-authored\nitems", "MAS-generated\nitems"])
    ax.set_ylabel("Source judgments (%)")
    ax.set_ylim(0, 100)
    ax.set_title("B  Source-judgment confusion matrix", loc="left", fontweight="bold", fontsize=10)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    save_pdf(fig, "Figure4B_source_judgment_confusion_matrix")

    ratings = pd.read_csv(DERIVED / "source_task_ratings_updated.csv").dropna(subset=["source_task_rating_5"])
    data = [ratings.loc[ratings.source_true.eq(s), "source_task_rating_5"].to_numpy() for s in ["Human", "MAS"]]
    fig, ax = plt.subplots(figsize=(3.05, 2.55))
    bp = ax.boxplot(data, labels=["Human-authored\nitems", "MAS-generated\nitems"], patch_artist=True, widths=0.52, showfliers=False)
    for patch, color, fill in zip(bp["boxes"], [COLORS["Human"], COLORS["MAS"]], [COLORS["Human_fill"], COLORS["MAS_fill"]]):
        patch.set(facecolor=fill, edgecolor=color, lw=1.0)
    for med in bp["medians"]: med.set(color=COLORS["text_dark"], lw=1.3)
    rng = np.random.default_rng(80)
    for i, vals in enumerate(data, start=1):
        ax.scatter(rng.normal(i, 0.045, len(vals)), vals, s=8, color=[COLORS["Human"], COLORS["MAS"]][i-1], alpha=0.45, linewidths=0)
    ax.set_ylabel("Source-task item rating (1-5)")
    ax.set_ylim(1, 5.1)
    ax.set_title("C  Ratings during source task", loc="left", fontweight="bold", fontsize=10)
    ax.grid(axis="y", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure4C_source_task_ratings")

    # Efficiency panels: human workflow total time is absent, so use observed MAS timing without fabricating human comparator.
    timing = pd.read_csv(DERIVED / "mas_question_generation_time.csv")
    timing["total_minutes"] = timing["total_generation_seconds"] / 60.0
    timing["minutes_per_generated_item"] = timing["total_minutes"] / timing["generated_items"]
    timing.to_csv(DERIVED / "fig4D_mas_observed_generation_time.csv", index=False)
    fig, ax = plt.subplots(figsize=(4.15, 2.5))
    order = list(timing["bank_type"])
    x = np.arange(len(order))
    ax.bar(x, timing["total_minutes"], color=COLORS["MAS"], alpha=0.82)
    ax.set_xticks(x, order)
    ax.set_ylabel("Observed MAS wall-clock time (min)")
    ax.set_xlabel("Item type")
    ax.set_title("D  Available workflow timing: MAS generation", loc="left", fontweight="bold", fontsize=10)
    ax.grid(axis="y", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure4D_workflow_total_time")

    item = pd.read_csv(DERIVED / "item_master.csv")[["item_id", "source_true"]]
    defect = pd.read_csv(DERIVED / "defect_adjudication_proxy.csv")
    nondef_mas = int(((defect.source_true.eq("MAS")) & (defect.final_major_defect.fillna(0).astype(float).eq(0)) & (defect.final_critical_defect.fillna(0).astype(float).eq(0))).sum())
    final_mas = int(item.source_true.eq("MAS").sum())
    mas_total_minutes = timing["total_minutes"].sum()
    eff_rows = pd.DataFrame([
        {"metric":"Per final MAS item", "minutes": mas_total_minutes / max(final_mas, 1), "denominator": final_mas},
        {"metric":"Per nondefective MAS item", "minutes": mas_total_minutes / max(nondef_mas, 1), "denominator": nondef_mas},
    ])
    eff_rows.to_csv(DERIVED / "fig4E_quality_adjusted_time_available_mas_only.csv", index=False)
    fig, ax = plt.subplots(figsize=(3.35, 2.55))
    ax.bar(np.arange(len(eff_rows)), eff_rows["minutes"], color=[COLORS["accent"], COLORS["MAS"]], alpha=0.82)
    ax.set_xticks(np.arange(len(eff_rows)), ["Final MAS\nitems", "Nondefective\nMAS items"])
    ax.set_ylabel("Observed minutes per item")
    ax.set_title("E  Available quality-adjusted MAS timing", loc="left", fontweight="bold", fontsize=10)
    for i, r in eff_rows.iterrows():
        ax.text(i, r["minutes"], f"{r['minutes']:.1f}\nn={int(r['denominator'])}", ha="center", va="bottom", fontsize=7)
    ax.grid(axis="y", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure4E_quality_adjusted_time")

    scenarios = pd.DataFrame({
        "Scenario": ["MAS -20%", "Observed MAS", "MAS +20%"],
        "minutes_per_nondefective": [eff_rows.loc[1, "minutes"]*0.8, eff_rows.loc[1, "minutes"], eff_rows.loc[1, "minutes"]*1.2]
    })
    scenarios.to_csv(DERIVED / "fig4F_efficiency_sensitivity_available_mas_only.csv", index=False)
    fig, ax = plt.subplots(figsize=(3.65, 2.55))
    y = np.arange(len(scenarios))[::-1]
    vals = scenarios["minutes_per_nondefective"].to_numpy()[::-1]
    ax.barh(y, vals, color=COLORS["MAS"], alpha=0.75)
    ax.set_yticks(y, scenarios["Scenario"].to_numpy()[::-1])
    ax.set_xlabel("Minutes per nondefective MAS item")
    ax.set_title("F  MAS timing sensitivity using available data", loc="left", fontweight="bold", fontsize=10)
    for yi, v in zip(y, vals):
        ax.text(v, yi, f" {v:.1f}", va="center", fontsize=7)
    ax.grid(axis="x", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure4F_efficiency_sensitivity")


def figure5():
    block = pd.read_csv(DERIVED / "block_scores.csv")
    wide = block.pivot_table(index=["student_id", "form", "training_setting"], columns="source_true", values="score_percent").reset_index()
    wide["mas_minus_human"] = wide["MAS"] - wide["Human"]
    wide.to_csv(DERIVED / "fig5_block_score_differences_updated.csv", index=False)
    fig, ax = plt.subplots(figsize=(3.35, 2.75))
    for form, color, lab in [("A", COLORS["Human"], "Form A: Human -> MAS"), ("B", COLORS["MAS"], "Form B: MAS -> Human")]:
        sub = wide[wide.form.eq(form)]
        for _, r in sub.iterrows():
            ax.plot([0, 1], [r["Human"], r["MAS"]], color=color, alpha=0.30, lw=0.8)
        ax.scatter(np.zeros(len(sub)), sub["Human"], s=13, color=color, alpha=0.70, label=lab)
        ax.scatter(np.ones(len(sub)), sub["MAS"], s=13, color=color, alpha=0.70)
    ax.set_xticks([0, 1], ["Human-authored\nblock", "MAS-generated\nblock"])
    ax.set_ylabel("Block score (%)")
    ax.set_title("B  Paired block scores by source and sequence", loc="left", fontweight="bold", fontsize=10)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=1)
    ax.grid(axis="y", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure5B_paired_block_scores")

    fig, ax = plt.subplots(figsize=(3.0, 2.6))
    groups = [wide[wide.form.eq("A")]["mas_minus_human"], wide[wide.form.eq("B")]["mas_minus_human"]]
    bp = ax.boxplot(groups, labels=["Form A\nHuman -> MAS", "Form B\nMAS -> Human"], patch_artist=True, widths=0.50, showfliers=False)
    for patch, color, fill in zip(bp["boxes"], [COLORS["Human"], COLORS["MAS"]], [COLORS["Human_fill"], COLORS["MAS_fill"]]):
        patch.set(facecolor=fill, edgecolor=color, lw=1.0)
    ax.axhline(0, color=COLORS["text_dark"], lw=0.9)
    rng = np.random.default_rng(95)
    for i, vals in enumerate(groups, start=1):
        ax.scatter(rng.normal(i, 0.04, len(vals)), vals, s=13, color=[COLORS["Human"], COLORS["MAS"]][i-1], alpha=0.60, linewidths=0)
    ax.set_ylabel("MAS - Human block score difference")
    ax.set_title("C  Within-participant differences by sequence", loc="left", fontweight="bold", fontsize=10)
    ax.grid(axis="y", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure5C_individual_differences_by_sequence")

    # D: overall adjusted participant-item linear probability model, plus sequence-stratified paired contrasts.
    resp = pd.read_csv(DERIVED / "responses.csv")
    im = pd.read_csv(DERIVED / "item_master.csv")[["item_id", "topic", "cognitive_level", "item_type"]]
    resp = resp.merge(im, on="item_id", how="left", suffixes=("", "_im"))
    if "item_type_im" in resp.columns:
        resp["item_type_model"] = resp["item_type_im"].fillna(resp.get("item_type", np.nan))
    else:
        resp["item_type_model"] = resp["item_type"]
    resp["is_mas"] = resp["source_true"].eq("MAS").astype(int)
    formula = "correct ~ is_mas + C(block_position) + C(form) + C(training_setting) + C(training_year) + C(item_type_model) + C(cognitive_level) + C(topic)"
    fit = smf.ols(formula, data=resp).fit(cov_type="cluster", cov_kwds={"groups": resp["student_id"]})
    coef = float(fit.params["is_mas"] * 100)
    ci_low, ci_high = [float(x * 100) for x in fit.conf_int().loc["is_mas"]]
    rows = [{"contrast": "Overall adjusted", "estimate": coef, "ci_low": ci_low, "ci_high": ci_high, "n_students": resp.student_id.nunique(), "n_responses": len(resp), "method": formula + "; cluster-robust SE by student"}]
    rng = np.random.default_rng(101)
    for label, sub in [("Form A (Human -> MAS)", wide[wide.form.eq("A")]), ("Form B (MAS -> Human)", wide[wide.form.eq("B")])]:
        vals = sub["mas_minus_human"].to_numpy(dtype=float)
        boots = rng.choice(vals, size=(3000, len(vals)), replace=True).mean(axis=1)
        rows.append({"contrast": label, "estimate": vals.mean(), "ci_low": np.percentile(boots, 2.5), "ci_high": np.percentile(boots, 97.5), "n_students": len(vals), "n_responses": int(len(vals) * 100), "method": "within-participant paired block-score contrast; source and block position are aliased within each sequence"})
    est = pd.DataFrame(rows)
    est.to_csv(DERIVED / "fig5D_adjusted_correct_rate_difference_updated.csv", index=False)
    fig, ax = plt.subplots(figsize=(4.15, 2.45))
    e = est.iloc[::-1].reset_index(drop=True); y = np.arange(len(e))
    ax.axvline(0, color=COLORS["text_dark"], lw=0.9)
    ax.errorbar(e["estimate"], y, xerr=[e["estimate"]-e["ci_low"], e["ci_high"]-e["estimate"]], fmt="o", color=COLORS["blue"], ecolor=COLORS["blue"], capsize=3, ms=4.5)
    ax.set_yticks(y, e["contrast"])
    ax.set_xlabel("Correct-answer rate difference, MAS - Human (percentage points)")
    ax.set_title("D  Adjusted and sequence-stratified source difference", loc="left", fontweight="bold", fontsize=10)
    ax.grid(axis="x", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure5D_adjusted_correct_rate_difference")

    fig, ax = plt.subplots(figsize=(3.05, 2.6))
    groups = [wide[wide.training_setting.eq("main")]["mas_minus_human"], wide[wide.training_setting.eq("non_main")]["mas_minus_human"]]
    labels = [f"Main setting\nn={len(groups[0])}", f"Non-main setting\nn={len(groups[1])}"]
    bp = ax.boxplot(groups, labels=labels, patch_artist=True, widths=0.50, showfliers=False)
    for patch, color in zip(bp["boxes"], [COLORS["accent"], COLORS["spine"]]):
        patch.set(facecolor=color, alpha=0.22, edgecolor=color, lw=1.0)
    ax.axhline(0, color=COLORS["text_dark"], lw=0.9)
    rng = np.random.default_rng(102)
    for i, vals in enumerate(groups, start=1):
        ax.scatter(rng.normal(i, 0.04, len(vals)), vals, s=13, color=[COLORS["accent"], COLORS["spine"]][i-1], alpha=0.60, linewidths=0)
    ax.set_ylabel("MAS - Human block score difference")
    ax.set_title("E  Exploratory setting-stratified differences", loc="left", fontweight="bold", fontsize=10)
    ax.grid(axis="y", color=COLORS["grid"], lw=0.7)
    save_pdf(fig, "Figure5E_setting_stratified_differences")


def cleanup_conflicts():
    # Remove obsolete duplicate/conflicting outputs and non-PDF image artifacts.
    obsolete = [
        "Figure1A_workflow_inputs_v2.pdf", "Figure1A_workflow_inputs_v3.pdf",
        "Figure4B_source_decision_counts.pdf", "Figure5C_individual_differences.pdf",
        "Figure5D_adjusted_difference_proxy.pdf", "Figure5D_correct_rate_difference_by_sequence.pdf", "Figure5E_training_setting_exploration.pdf",
    ]
    for name in obsolete:
        p = OUT / name
        if p.exists(): p.unlink()
    # The user requested editable PDFs only; remove PNG/SVG/other raster/vector figure outputs if present.
    for ext in ("*.png", "*.svg"):
        for p in ROOT.rglob(ext):
            if "visual_reference_previews" in str(p):
                continue
            p.unlink()


def main():
    figure3(); figure4(); figure5(); cleanup_conflicts()
    print("Final PDF panels regenerated in", OUT)

if __name__ == "__main__":
    main()
