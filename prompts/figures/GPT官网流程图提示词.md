# GPT 官网流程图提示词

以下五段提示词分别用于生成 Figure 1A、Figure 1B、Figure 2A、Figure 3A、Figure 4A 的构图参考。成图用于 PPT 手工临摹，因此优先保证信息层级、连线逻辑、版式与配色清楚；不要追求照片质感。

## Figure 1A：项目全流程

```text
Create a publication-quality scientific workflow infographic for a peer-reviewed medical-education paper. This is panel (A), titled “Study workflow: Human versus UroEmas-generated urology examination items”. Use a clean flat-vector editorial style, white background, no gradients, no 3D, no shadows, no decorative stock icons, no hospital logo, and no people portraits. The final composition must be horizontal, with an exact 2:1 aspect ratio suitable for a 9.0 × 4.5 inch figure.

Use DejaVu Sans–like typography. Make all text crisp, correctly spelled, and large enough to trace manually in PowerPoint. Put “(A)” in bold at the upper-left. Use dark gray #2A251F for main text, warm light-gray #E3DFD8 for subtle separators, and #9E9A93 for neutral outlines. Human must always use dark blue #313E96 with pale blue fill #D9DCF1. MAS/UroEmas must always use terracotta red #B86758 with pale terracotta fill #F2DFDB. Use purple #7C5CFF, ochre #B8954B, and teal #2F8F83 only for shared analytical stages. Never swap the Human and MAS colors.

Organize the diagram as two parallel source lanes that converge into shared evaluation and examination stages:

TOP BLUE LANE — Human:
1. “Human expert item bank”
   subtitle: “Word → TXT → structured JSON”
2. “Human candidate pool”
3. “First-round sample”
   subtitle: “70 items”

BOTTOM TERRACOTTA LANE — UroEmas / MAS:
1. “Human bank + item-writing specifications” as inputs
2. “MAS item generation” with three compact sequential substeps:
   “Stem and options” → “Answer and explanation” → “Test-point restoration”
3. “Machine screening”
   subtitle: “Readability, similarity, QGEval, ULM”
4. “MAS candidate pool”
5. “First-round sample”
   subtitle: “70 items”

After the two 70-item boxes, merge both lanes into the following shared left-to-right stages:
4. “Blinded expert evaluation”
   small internal labels: “3 experts”, “QGEval”, “ULM”, “source guess”, “major defects”
5. “Major-defect validation”
   show two small branches beneath it:
   “Primary 70/group: 0 major defects”
   “Validation samples: low-score 50 + mid-score 50”
6. “Second-round selection”
   split back into two color-coded boxes:
   blue “Human exam (P), 50 items”
   terracotta “UroEmas exam (M), 50 items”
7. “Randomized two-sequence student test”
   show two balanced mini-lanes:
   “Form A: Human → MAS, n=25”
   “Form B: MAS → Human, n=25”
8. “Statistical analysis and reporting”
   subtitle: “Quality, reliability, accuracy, fatigue, time, and cost”

Use clear arrowheads and avoid crossing connectors. Show the two source lanes as visually equal in importance. Place compact numbered stage badges 1–8 above the major stages. The flow must read unambiguously from left to right. Keep every listed element; do not omit or invent sample sizes. Use “ULM”, never “LLM”, anywhere in the figure. Output only the finished infographic, with no caption outside the artwork.
```

## Figure 1B：安全审核详细流程

```text
Create a detailed, publication-quality medical item safety-review flowchart for panel (B), titled “Major-defect screening and validation workflow”. Use a clean flat-vector style on a pure white background, exact 2:1 horizontal aspect ratio for a 9.0 × 4.5 inch scientific figure. No gradients, no 3D, no shadows, no decorative icons, no logos, and no photographic elements. The figure will be manually traced in PowerPoint, so prioritize precise geometry, readable text, and unmistakable decision logic.

Typography should resemble DejaVu Sans. Put bold “(B)” at the upper-left. Use dark gray #2A251F for text and #9E9A93 for neutral outlines. Human uses blue #313E96 with pale fill #D9DCF1. MAS uses terracotta #B86758 with pale fill #F2DFDB. Shared review stages use purple #7C5CFF, ochre #B8954B, teal #2F8F83, or neutral gray #6F6F6F. Never use the Human or MAS colors for a non-source category.

Construct the flow from left to right with explicit decision diamonds and a visible audit trail:

INPUTS, two stacked source boxes:
- blue “Human items”
- terracotta “UroEmas / MAS items”
Both arrows enter “Source labels removed and item IDs retained”.

PRIMARY SCREENING SET:
- “First-round blinded set”
  subtitle: “70 Human + 70 MAS items”

PARALLEL REVIEW, split into two branches:
Upper branch, purple:
- “Model-based major-defect review”
- subtitle: “Rubric-constrained item-level assessment”
Lower branch, ochre:
- “Human expert major-defect review”
- subtitle: “Independent item-level assessment”

Between or beside the parallel branches, show one clearly grouped seven-domain checklist titled “Prespecified major-defect domains” with exactly these seven labels:
1. “Stem defect”
2. “Option defect”
3. “Format defect”
4. “Scoring defect”
5. “Fairness defect”
6. “Clinical-currency defect”
7. “Linked-item structure defect”

Merge both review branches into a decision diamond:
“Any major defect?”
Create two outputs:
- “Yes” → red-outlined “Flag item and record defect domain/reason” → “Revise or reject”
- “No” → teal “Retain as no major defect”

Then show the observed primary result in a compact neutral callout:
“Primary first-round result: 0/70 Human and 0/70 MAS items with major defects”

VALIDATION BRANCH beneath the primary flow:
- “Rubric validation sampling from the full banks”
- split into “Low-score stratum: 50 items” and “Mid-score stratum: 50 items”
- merge into “Repeat model and human expert review using the same seven-domain rubric”
- final output: “Evaluate rubric discrimination and reviewer agreement”
- add a small status note: “Model results available; human validation results pending”

Add a thin audit-trail strip along the bottom containing: “blinded source”, “traceable item ID”, “domain-level 0/1 flags”, and “written reasons”. Use solid arrows for the main flow and dashed arrows only for the separate validation branch. Avoid connector crossings and keep all text inside boxes. Do not invent adjudication outcomes beyond those explicitly stated. Output only the finished flowchart.
```

## Figure 2A：专家综合质量评价流程

```text
Create a sophisticated but highly legible scientific workflow diagram for panel (A) of Figure 2, titled “Blinded expert comprehensive quality-evaluation workflow”. The topic is comparison of Human-written versus UroEmas/MAS-generated urology examination questions. Use a clean journal-ready flat-vector design, white background, exact 2:1 horizontal aspect ratio for a 9.0 × 4.5 inch figure. No gradients, no shadows, no 3D, no decorative clip art, no logos, and no photographic people. The artwork will be manually reproduced in PowerPoint, so use a precise grid, clear arrow routing, and readable labels.

Put bold “(A)” at the upper-left. Typography should resemble DejaVu Sans. Use #2A251F for text, #E3DFD8 for subtle separators, and #9E9A93 for neutral borders. Human source boxes must be blue #313E96 with pale blue #D9DCF1. MAS source boxes must be terracotta #B86758 with pale terracotta #F2DFDB. Use purple #7C5CFF for QGEval, ochre #B8954B for ULM, orange-red #D97757 for source identification, teal #2F8F83 for major-defect review, and neutral gray for blinding/data-management steps.

Build the diagram in five aligned stages from left to right:

STAGE 1 — Balanced item inputs:
- blue “Human items, n=70”
- terracotta “UroEmas / MAS items, n=70”

STAGE 2 — Blinding and allocation:
- merge both sources into “De-identification and source blinding”
- then “Common structured rating workbook”
- retain a small audit label: “item IDs preserved”

STAGE 3 — Independent expert review:
- one central box “Three human experts”
- subtitle: “Experts 1, 3, and 4; independent item-level ratings”
- show three small parallel reviewer symbols or columns, but do not use portraits

STAGE 4 — Four parallel evaluation modules, each with its own color and compact details:
1. Purple “QGEval”
   subtitle: “7 dimensions; total 35 points”
2. Ochre “ULM”
   subtitle: “16 dimensions; total 76 points”
   add small note: “native 5-, 4-, and 3-point dimension scales”
3. Orange-red “Source identification”
   subtitle: “Guessed Human versus MAS”
4. Teal “Major-defect review”
   subtitle: “7 prespecified defect domains”

STAGE 5 — Analysis outputs, arranged as a tidy matrix rather than one overcrowded box:
Top row, quality analyses:
- “Overall non-inferiority: QGEval and ULM”
- “23 per-dimension comparisons”
- “Quality by cognitive level”
Bottom row, model and reliability analyses:
- “Source × cognitive-level mixed model”
- “Inter-rater ICC: QGEval and ULM”
- “Expert source-identification accuracy and confusion matrix”

Add a slim statistical-method footer inside the artwork:
“Item-level analysis; three experts; 95% CIs for quality/ICC; 90% CIs for source-identification accuracy.”

Use fork-and-join connectors with arrowheads. Keep the four rating modules visually parallel and equally weighted. Do not imply that QGEval or ULM is produced by the source-identification task. Do not combine QGEval and ULM into a single scale. Use “ULM”, never “LLM”. Keep all stated sample sizes and point totals exact. Output only the completed infographic, without an external caption or explanatory prose.
```

## Figure 3A：学生随机双序列测试流程

```text
Create a publication-quality scientific workflow diagram for panel (A) of Figure 3, titled “Randomized two-sequence student examination workflow”. This figure describes a crossover-style, counterbalanced comparison of Human-written and UroEmas/MAS-generated urology examination items. Use a clean journal-ready flat-vector design on a pure white background, with an exact 2:1 horizontal aspect ratio suitable for a 9.0 × 4.5 inch figure. No gradients, no 3D, no shadows, no logos, no decorative clip art, and no photographic people. The image will be manually traced in PowerPoint, so prioritize precise alignment, short readable labels, and unambiguous arrow routing.

Put bold “(A)” at the upper-left. Use DejaVu Sans–like typography. Use dark gray #2A251F for text, #E3DFD8 for separators, and #9E9A93 for neutral borders. Human must always use dark blue #313E96 with pale blue fill #D9DCF1. MAS/UroEmas must always use terracotta #B86758 with pale terracotta fill #F2DFDB. Use purple #7C5CFF, ochre #B8954B, and teal #2F8F83 only for shared allocation, data-capture, and analysis stages. Never swap the Human and MAS colors.

Build the main flow from left to right in five stages:

STAGE 1 — Participants:
- one neutral box: “Eligible urology trainees, n=50”

STAGE 2 — Counterbalanced allocation:
- one shared box: “Randomized two-sequence allocation”
- subtitle: “Balanced 1:1 assignment”
- split into two equally prominent horizontal lanes

STAGE 3 — Examination sequences:
- upper lane, labeled “Form A, n=25”: blue “Human block” → terracotta “MAS block”
- lower lane, labeled “Form B, n=25”: terracotta “MAS block” → blue “Human block”
- keep the two lanes equal in length and visual weight
- use arrowheads to make examination order unmistakable

STAGE 4 — Response capture:
- merge both lanes into one shared box: “Item-level response capture”
- show exactly three compact fields beneath it: “item score”, “block order”, and “total duration”

STAGE 5 — Prespecified analyses, split into two aligned output boxes:
- teal “Performance analyses” with three lines: “overall Human versus MAS”, “campus-stratified comparison”, and “cognitive-level comparison”
- purple “Psychometric and order analyses” with three lines: “classical test theory”, “internal consistency”, and “fatigue / sequence effects”

Add a separate slim callout along the bottom, visually distinct from the examination flow and connected by a dashed line only:
“Separate source-identification task: 48 students made pair-level decisions.”
Do not connect this callout as though all 50 examination participants completed it, and do not imply that source identification was item-level for students.

Use solid arrows for the main examination workflow and a dashed connector only for the separate 48-student task. Avoid crossing connectors. Keep all text inside boxes. Do not invent exclusions, attrition, washout periods, extra assessments, or sample sizes. Output only the finished workflow diagram, without an external caption or explanatory prose.
```

## Figure 4A：图灵测试与来源识别流程

```text
Create a publication-quality scientific workflow diagram for panel (A) of Figure 4, titled “Source-identification (Turing-test) workflow”. The study compares Human-written and UroEmas/MAS-generated urology examination items using separate expert and student source-identification tasks. Use a clean journal-ready flat-vector design on a pure white background, with an exact 2:1 horizontal aspect ratio suitable for a 9.0 × 4.5 inch figure. No gradients, no 3D, no shadows, no logos, no decorative clip art, and no photographic people. The image will be manually traced in PowerPoint, so use a precise grid, readable text, and explicit branch-specific logic.

Put bold “(A)” at the upper-left. Use DejaVu Sans–like typography. Use dark gray #2A251F for text, #E3DFD8 for separators, and #9E9A93 for neutral borders. Human must always use dark blue #313E96 with pale blue fill #D9DCF1. MAS/UroEmas must always use terracotta #B86758 with pale terracotta fill #F2DFDB. Use purple #7C5CFF for the expert branch, ochre #B8954B for the student branch, teal #2F8F83 for analysis outputs, and neutral gray for blinding and randomization. Never swap the Human and MAS colors.

Build the flow from left to right:

STAGE 1 — Source-known inputs, two stacked boxes:
- blue “Human items, n=70”
- terracotta “UroEmas / MAS items, n=70”
- add a small note outside the boxes: “True source retained in the study key only”

STAGE 2 — Blinding and presentation:
- merge both inputs into one neutral box: “Remove source labels and retain item IDs”
- then one neutral box: “Randomized blinded presentation”
- after this stage, split into two clearly separated horizontal branches

UPPER BRANCH — Expert item-level task:
- purple box: “Three human experts”
- subtitle: “140 items per expert”
- next box: “Item-level forced choice: Human or MAS”
- next output group containing exactly:
  1. “Expert accuracy with 90% CI”
  2. “Expert item-level confusion matrix”
  3. “Model of probability guessed MAS”

LOWER BRANCH — Student pair-level task:
- ochre box: “Students, n=48”
- next box: “Pair-level source-identification decision”
- subtitle: “Correct or incorrect pair only”
- next output box containing exactly: “Student accuracy with 90% CI”
- add a prominent small boundary note: “No item-level student guesses available”
- do not draw a student confusion matrix and do not connect the student branch to the expert model

At the far right, keep the branch-specific outputs aligned but separate. Add a small shared reference marker labeled “Chance accuracy = 50%” without presenting it as a study stage. Use solid arrows throughout the main flow. Avoid crossing connectors, keep all labels inside their intended boxes, and make the expert-versus-student unit-of-analysis distinction visually unmistakable. Do not invent adjudication, confidence ratings, exclusions, or additional sample sizes. Output only the finished workflow diagram, without an external caption or explanatory prose.
```
