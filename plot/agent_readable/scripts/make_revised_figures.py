#!/usr/bin/env python3
"""Generate revised Figure 3-5 panels after integrating 2026-05-26 first-author updates."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "derived_data"
OUT = ROOT / "figures" / "panels" / "revised"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 220,
})
COL_MAS = "#2B6CB0"
COL_HUM = "#9A5B1F"
COL_ACCENT = "#2F855A"
COL_GREY = "#6B7280"
COL_LIGHT = "#E5E7EB"
LEVELS = ["knowledge", "application", "reasoning"]
LEVEL_LABELS = {"knowledge": "Knowledge", "application": "Clinical\napplication", "reasoning": "Clinical\nreasoning"}

def ci_mean(x, reps=200, seed=1):
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    if len(x) == 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    boots = rng.choice(x, size=(reps, len(x)), replace=True).mean(axis=1)
    return float(x.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))

def diff_ci_by_group(df, group_col, value_col, source_col="source_true", reps=200, seed=1):
    rows=[]
    rng = np.random.default_rng(seed)
    for g, sub in df.groupby(group_col):
        a = sub.loc[sub[source_col].eq("MAS"), value_col].dropna().to_numpy(dtype=float)
        h = sub.loc[sub[source_col].eq("Human"), value_col].dropna().to_numpy(dtype=float)
        if len(a)==0 or len(h)==0: continue
        point = a.mean()-h.mean()
        boots=[]
        for _ in range(reps):
            boots.append(rng.choice(a, len(a), True).mean() - rng.choice(h, len(h), True).mean())
        rows.append({group_col:g,"estimate":point,"ci_low":np.percentile(boots,2.5),"ci_high":np.percentile(boots,97.5),"n_mas":len(a),"n_human":len(h)})
    return pd.DataFrame(rows)

def savefig(fig, name):
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)

def forest_panel(data, y_col, title, xlabel, name, xlim=None, margin=None, margin_label=None, color=COL_MAS, annotate_counts=True):
    d = data.copy()
    d["order"] = d[y_col].map({k:i for i,k in enumerate(LEVELS)}).fillna(99)
    d = d.sort_values("order", ascending=False)
    fig, ax = plt.subplots(figsize=(3.7, 2.3))
    y = np.arange(len(d))
    ax.axvline(0, color="#111827", lw=0.8, zorder=0)
    if margin is not None:
        ax.axvline(margin, color="#B91C1C", lw=0.9, ls="--", zorder=0)
        if margin_label:
            ax.text(margin, len(d)-0.35, margin_label, color="#B91C1C", fontsize=6, ha="right" if margin<0 else "left", va="bottom")
    ax.errorbar(d["estimate"], y, xerr=[d["estimate"]-d["ci_low"], d["ci_high"]-d["estimate"]], fmt="o", color=color, ecolor=color, elinewidth=1.1, capsize=2.5, ms=4)
    labels=[]
    for _, r in d.iterrows():
        base = LEVEL_LABELS.get(r[y_col], r[y_col])
        if annotate_counts and "n_mas" in r:
            base += f"\nMAS n={int(r.n_mas)}, Human n={int(r.n_human)}"
        labels.append(base)
    ax.set_yticks(y, labels)
    ax.set_xlabel(xlabel)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="x", color=COL_LIGHT, lw=0.6)
    if xlim: ax.set_xlim(*xlim)
    savefig(fig, name)

def figure3():
    item = pd.read_csv(DERIVED / "item_master.csv")[["item_id","cognitive_level","source_true"]]
    expert = pd.read_csv(DERIVED / "expert_ratings_updated.csv").merge(item[["item_id","cognitive_level"]], on="item_id", how="left")
    q = diff_ci_by_group(expert, "cognitive_level", "quality_score_5", reps=200, seed=3)
    q.to_csv(DERIVED / "fig3A_quality_by_cognitive_level_updated.csv", index=False)
    forest_panel(q, "cognitive_level", "A  Expert-rated quality by cognitive level", "Mean quality score difference, MAS - Human", "Figure3A_quality_by_cognitive_level_updated", xlim=(-0.55,0.55), margin=-0.30, margin_label="NI margin -0.30", color=COL_ACCENT)

    defect = pd.read_csv(DERIVED / "defect_adjudication_proxy.csv").merge(item[["item_id","cognitive_level"]], on="item_id", how="left")
    defect["any_major_or_critical_defect"] = ((defect["final_major_defect"].fillna(0)>0) | (defect["final_critical_defect"].fillna(0)>0)).astype(float)*100
    d = diff_ci_by_group(defect, "cognitive_level", "any_major_or_critical_defect", reps=200, seed=4)
    d.to_csv(DERIVED / "fig3B_defect_risk_by_cognitive_level_updated.csv", index=False)
    forest_panel(d, "cognitive_level", "B  Item-writing defect risk by cognitive level", "Defect-risk difference, MAS - Human (percentage points)", "Figure3B_defect_risk_by_cognitive_level_updated", xlim=(-12,12), color="#B45309")

    resp = pd.read_csv(DERIVED / "responses.csv").merge(item[["item_id","cognitive_level"]], on="item_id", how="left")
    resp["correct_pp"] = resp["correct"].astype(float)*100
    c = diff_ci_by_group(resp, "cognitive_level", "correct_pp", reps=200, seed=5)
    c.to_csv(DERIVED / "fig3C_student_accuracy_by_cognitive_level_updated.csv", index=False)
    forest_panel(c, "cognitive_level", "C  Student accuracy by cognitive level", "Correct-answer rate difference, MAS - Human (percentage points)", "Figure3C_student_accuracy_by_cognitive_level_updated", xlim=(-15,15), color=COL_MAS)

def figure4():
    src = pd.read_csv(DERIVED / "source_detection_updated.csv")
    src = src.dropna(subset=["source_guess"])
    src["correct_source_guess"] = (src.source_guess == src.source_true).astype(int)
    # A: balanced accuracy with simple bootstrap over judgments stratified by true source.
    mas = src[src.source_true.eq("MAS")]["correct_source_guess"].to_numpy()
    hum = src[src.source_true.eq("Human")]["correct_source_guess"].to_numpy()
    rng = np.random.default_rng(7)
    boot = []
    for _ in range(500):
        boot.append((rng.choice(mas, len(mas), True).mean() + rng.choice(hum, len(hum), True).mean())/2)
    bal = (mas.mean()+hum.mean())/2
    ci = np.percentile(boot, [2.5,97.5])
    pd.DataFrame([{"metric":"balanced_accuracy","estimate":bal,"ci_low":ci[0],"ci_high":ci[1],"n_judgments":len(src),"n_raters":src.rater_id.nunique(),"n_items":src.item_id.nunique()}]).to_csv(DERIVED / "fig4A_source_detection_accuracy_updated.csv", index=False)
    fig, ax = plt.subplots(figsize=(2.3,2.5))
    ax.axhspan(45,55,color="#DBEAFE",alpha=.8,label="Prespecified near-chance range")
    ax.axhline(50,color="#111827",lw=.8)
    ax.errorbar([0],[bal*100],yerr=[[bal*100-ci[0]*100],[ci[1]*100-bal*100]],fmt="o",color=COL_MAS,capsize=3,ms=5)
    ax.text(0.06, bal*100, f"{bal*100:.1f}%", va="center", fontsize=8)
    ax.set_xlim(-0.5,.8); ax.set_ylim(0,100); ax.set_xticks([0],["Expert\nsource judgments"])
    ax.set_ylabel("Balanced accuracy (%)")
    ax.set_title("A  Source-identification accuracy", loc="left", fontweight="bold")
    ax.text(.78,50,"Chance level = 50%",ha="right",va="bottom",fontsize=6)
    savefig(fig,"Figure4A_source_detection_accuracy_updated")

    # B: true x guessed stacked proportions.
    tab = pd.crosstab(src.source_true, src.source_guess).reindex(index=["Human","MAS"], columns=["Human","MAS"], fill_value=0)
    prop = tab.div(tab.sum(axis=1), axis=0)*100
    tab.to_csv(DERIVED / "fig4B_source_judgment_confusion_matrix_updated.csv")
    fig, ax = plt.subplots(figsize=(3.0,2.4))
    x=np.arange(len(prop))
    bottom=np.zeros(len(prop))
    for col, color, lab in [("Human", COL_HUM, "Guessed human"),("MAS", COL_MAS, "Guessed MAS")]:
        vals=prop[col].to_numpy()
        ax.bar(x, vals, bottom=bottom, color=color, width=.58, label=lab)
        for xi, v, b in zip(x, vals, bottom):
            if v>8: ax.text(xi, b+v/2, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=7)
        bottom+=vals
    ax.set_xticks(x,["Human-authored\nitems","MAS-generated\nitems"])
    ax.set_ylabel("Source judgments (%)")
    ax.set_ylim(0,100); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(.5,-.18), ncol=2)
    ax.set_title("B  Source-judgment confusion matrix", loc="left", fontweight="bold")
    savefig(fig,"Figure4B_source_judgment_confusion_matrix_updated")

    # C: source-task ratings.
    ratings = pd.read_csv(DERIVED / "source_task_ratings_updated.csv").dropna(subset=["source_task_rating_5"])
    data = [ratings.loc[ratings.source_true.eq(s), "source_task_rating_5"].to_numpy() for s in ["Human","MAS"]]
    fig, ax = plt.subplots(figsize=(2.9,2.5))
    bp = ax.boxplot(data, labels=["Human-authored\nitems","MAS-generated\nitems"], patch_artist=True, widths=.5, showfliers=False)
    for patch, color in zip(bp['boxes'], [COL_HUM, COL_MAS]):
        patch.set(facecolor=color, alpha=.25, edgecolor=color)
    for med in bp['medians']: med.set(color="#111827", lw=1.3)
    rng = np.random.default_rng(8)
    for i, vals in enumerate(data, start=1):
        ax.scatter(rng.normal(i, .045, size=len(vals)), vals, s=8, alpha=.45, color=[COL_HUM,COL_MAS][i-1], linewidths=0)
    ax.set_ylabel("Source-task item rating (1-5)")
    ax.set_ylim(1,5.1)
    ax.set_title("C  Ratings during source task", loc="left", fontweight="bold")
    savefig(fig,"Figure4C_source_task_ratings_updated")

def model_diff(data, subset_label="Overall", seed=11):
    # Fast participant-level bootstrap of MAS-Human correct-rate differences.
    # Within a sequence group, source and block position are aliased, so fully adjusted source coefficients are not identifiable.
    d = data.copy()
    student_rates = d.pivot_table(index="student_id", columns="source_true", values="correct", aggfunc="mean")
    student_rates = student_rates.dropna(subset=["MAS", "Human"])
    deltas = (student_rates["MAS"] - student_rates["Human"]).to_numpy(dtype=float) * 100
    rng = np.random.default_rng(seed)
    point = float(np.mean(deltas))
    boots = rng.choice(deltas, size=(1000, len(deltas)), replace=True).mean(axis=1)
    ci_low, ci_high = np.percentile(boots, [2.5, 97.5])
    return {"contrast": subset_label, "estimate": point, "ci_low": ci_low, "ci_high": ci_high, "n_students": len(deltas), "n_responses": len(d), "model_formula": "participant-level paired MAS-Human correct-rate contrast"}

def figure5():
    block = pd.read_csv(DERIVED / "block_scores.csv")
    wide = block.pivot_table(index=["student_id","form","training_setting"], columns="source_true", values="score_percent").reset_index()
    wide["mas_minus_human"] = wide["MAS"] - wide["Human"]
    wide.to_csv(DERIVED / "fig5_block_score_differences_updated.csv", index=False)
    # B paired scores
    fig, ax = plt.subplots(figsize=(3.1,2.7))
    for form, color in [("A", COL_HUM), ("B", COL_MAS)]:
        sub = wide[wide.form.eq(form)]
        for _, r in sub.iterrows():
            ax.plot([0,1], [r["Human"], r["MAS"]], color=color, alpha=.32, lw=.8)
        ax.scatter(np.zeros(len(sub)), sub["Human"], color=color, s=12, alpha=.65, label=f"Form {form}: " + ("Human→MAS" if form=="A" else "MAS→Human"))
        ax.scatter(np.ones(len(sub)), sub["MAS"], color=color, s=12, alpha=.65)
    ax.set_xticks([0,1],["Human-authored\nblock","MAS-generated\nblock"])
    ax.set_ylabel("Block score (%)")
    ax.set_title("B  Paired block scores by source and sequence", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(.5,-.19), ncol=1)
    ax.grid(axis="y", color=COL_LIGHT, lw=.6)
    savefig(fig,"Figure5B_paired_block_scores_updated")

    # C distribution by form
    fig, ax = plt.subplots(figsize=(2.7,2.6))
    groups=[wide[wide.form.eq("A")]["mas_minus_human"], wide[wide.form.eq("B")]["mas_minus_human"]]
    bp=ax.boxplot(groups, labels=["Form A\nHuman→MAS","Form B\nMAS→Human"], patch_artist=True, widths=.5, showfliers=False)
    for patch, color in zip(bp['boxes'], [COL_HUM,COL_MAS]): patch.set(facecolor=color, alpha=.24, edgecolor=color)
    ax.axhline(0,color="#111827",lw=.8)
    rng=np.random.default_rng(10)
    for i, vals in enumerate(groups, start=1): ax.scatter(rng.normal(i,.045,len(vals)), vals, s=12, alpha=.6, color=[COL_HUM,COL_MAS][i-1], linewidths=0)
    ax.set_ylabel("MAS - Human block score difference")
    ax.set_title("C  Within-participant differences by sequence", loc="left", fontweight="bold")
    ax.grid(axis="y", color=COL_LIGHT, lw=.6)
    savefig(fig,"Figure5C_individual_differences_by_sequence_updated")

    # D adjusted differences
    item = pd.read_csv(DERIVED / "item_master.csv")[["item_id","topic","cognitive_level"]]
    assign = pd.read_csv(DERIVED / "exam_form_assignment.csv")[["student_id","form","order_group","training_setting","training_year"]]
    resp = pd.read_csv(DERIVED / "responses.csv").merge(item,on="item_id",how="left").merge(assign,on="student_id",how="left", suffixes=("","_assign"))
    rows=[model_diff(resp,"Overall",11)]
    for form in ["A","B"]:
        rows.append(model_diff(resp[resp.form.eq(form)], f"Form {form} (" + ("Human→MAS" if form=="A" else "MAS→Human") + ")", 12+ord(form)))
    est=pd.DataFrame(rows)
    est.to_csv(DERIVED / "fig5D_correct_rate_difference_by_sequence_updated.csv", index=False)
    est.to_csv(DERIVED / "fig5D_adjusted_correct_rate_difference_updated.csv", index=False)  # backward-compatible alias
    fig, ax = plt.subplots(figsize=(3.5,2.3))
    e=est.iloc[::-1].reset_index(drop=True); y=np.arange(len(e))
    ax.axvline(0,color="#111827",lw=.8)
    ax.errorbar(e.estimate, y, xerr=[e.estimate-e.ci_low,e.ci_high-e.estimate], fmt="o", color=COL_MAS, ecolor=COL_MAS, capsize=2.5, ms=4)
    ax.set_yticks(y,e.contrast)
    ax.set_xlabel("Correct-answer rate difference, MAS - Human (percentage points)")
    ax.set_title("D  Source difference by sequence", loc="left", fontweight="bold")
    ax.grid(axis="x", color=COL_LIGHT, lw=.6)
    savefig(fig,"Figure5D_correct_rate_difference_by_sequence_updated")
    savefig(fig,"Figure5D_adjusted_correct_rate_difference_updated")  # backward-compatible alias

    # E setting stratified
    fig, ax = plt.subplots(figsize=(2.7,2.6))
    groups=[wide[wide.training_setting.eq("main")]["mas_minus_human"], wide[wide.training_setting.eq("non_main")]["mas_minus_human"]]
    labels=[f"Main setting\nn={len(groups[0])}", f"Non-main setting\nn={len(groups[1])}"]
    bp=ax.boxplot(groups, labels=labels, patch_artist=True, widths=.5, showfliers=False)
    for patch, color in zip(bp['boxes'], [COL_ACCENT,COL_GREY]): patch.set(facecolor=color, alpha=.24, edgecolor=color)
    ax.axhline(0,color="#111827",lw=.8)
    rng=np.random.default_rng(13)
    for i, vals in enumerate(groups, start=1): ax.scatter(rng.normal(i,.045,len(vals)), vals, s=12, alpha=.6, color=[COL_ACCENT,COL_GREY][i-1], linewidths=0)
    ax.set_ylabel("MAS - Human block score difference")
    ax.set_title("E  Exploratory setting-stratified differences", loc="left", fontweight="bold")
    ax.grid(axis="y", color=COL_LIGHT, lw=.6)
    savefig(fig,"Figure5E_setting_stratified_differences_updated")

def main():
    figure3(); figure4(); figure5()
    print(f"Wrote revised figure panels to {OUT}")

if __name__ == "__main__":
    main()
