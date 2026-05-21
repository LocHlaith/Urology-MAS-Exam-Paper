# gpt-image2 prompt for Figure 1

Use the following prompt in the web UI. The figure text is intentionally short because image models often damage long labels. Regenerate if any label is misspelled.

## Main prompt

Create a polished scientific workflow figure for a medical AI validation manuscript.

Canvas and output:
- Wide landscape figure, 16:9 aspect ratio, white background, crisp vector-infographic look, high resolution.
- Target journal style: npj Digital Medicine / Nature Portfolio methods figure.
- Use clean line-art icons, structured pastel panels, thin navy outlines, generous white space, no photorealistic background.
- The figure must look like a finished manuscript Figure 1, not a PowerPoint draft.

Title at top left:
`Figure 1 | Auditable MAS workflow and two-sequence validation design`

Overall layout:
- One integrated horizontal workflow with five labeled sections A-E.
- Use three large vertical lanes separated by subtle dashed blue divider lines:
  - Left lane: `L1 | Inputs and blueprint`
  - Middle lane: `L2 | MAS generation and safety gate`
  - Right lane: `L3 | Validation design and endpoints`
- Use panel letters A, B, C, D, E in bold black.
- Main flow direction is left to right. Use thick black or navy arrows. Use a funnel shape for candidate filtering.

Visual style:
- Human source color: deep navy outline, pale blue fill.
- MAS / AI source color: muted coral outline, pale coral fill.
- Reference / guideline material: amber outline, pale yellow fill.
- Validation / endpoint material: teal outline, very pale teal fill.
- Safety warning / defect flags: muted red or coral accents.
- Use simple icons: database, book, prompt card, API chip, JSON brackets, checklist shield, expert group, lock, randomized A/B card, outcome dashboard.
- Keep all text horizontal and readable. Use bold headings and smaller short subtitles.

Exact content to draw:

A. `Inputs and MAS generation`
- Box: `Human expert bank` with subtitle `Word/TXT -> JSON; n=775`
- Box: `Authorized source materials` with subtitle `CUA/EAU guidelines; textbook; syllabus`
- Box: `Exam blueprint constraints` with subtitle `A1/A2/A3-A4/B/X; topics; cognitive levels`
- Arrow into MAS pipeline.
- Box: `Batch prompt builder`
- Box: `Model generation`
- Box: `Robust JSON extraction`
- Box: `MAS candidate bank` with subtitle `new_bank_*.json; n=3,676`

B. `AI safety gate`
- Draw a prominent vertical checklist shield or gate.
- Checklist items:
  `Answer-key legality`
  `Guideline consistency`
  `Single best answer`
  `Stem and option clarity`
  `Major / critical defect flag`
- Add a small note under this section:
  `Machine annotation = QC/proxy only`

C. `Expert intake review`
- Box: `Parallel expert intake review`
- Subtitle: `Safety and assembly control before administration`
- Add a lock boundary between this box and final outcomes:
  `Source key locked until blind rating is complete`
- Make clear that this review is separate from final blind outcome rating.

D. `Randomized two-sequence exam`
- Box: `Final examination blocks`
- Subtitle: `Human block n=50 | MAS block n=50`
- Draw two horizontal arms:
  `Form A n=25: Human -> MAS`
  `Form B n=25: MAS -> Human`
- Draw cohort setting below:
  `Final cohort n=50`
  `Main setting n=32`
  `Non-main setting n=18`

E. `Endpoint domains`
- Draw a clean outcome dashboard with six compact tiles:
  `Expert quality noninferiority`
  `Major / critical defects`
  `Cognitive-level boundaries`
  `Source detectability`
  `Student performance`
  `Workflow efficiency`
- Add one small bottom note:
  `Workflow efficiency requires workflow-level time/cost data`

Critical scientific constraints:
- Do not imply that AI replaces experts.
- Do not show machine scores as the final primary endpoint.
- Do not compare Human and MAS step-by-step labor time.
- Do not use examinee completion time as workflow efficiency.
- Do not reverse the A/B order. Form A is Human -> MAS. Form B is MAS -> Human.
- Do not mention three campuses or PGY-stratified analysis.

Negative style constraints:
- No Chinese text inside the figure.
- No extra labels beyond the text specified above.
- No decorative gradients, bokeh, 3D glass effects, stock photos, or cartoon characters.
- Do not make separate disconnected mini figures. It must read as one cohesive manuscript workflow.
- Avoid tiny text. If there is not enough space, preserve the headings and shorten subtitles rather than adding clutter.

## Short repair prompt

Use this after the first generation if the structure is good but text or alignment is flawed:

`Keep the same scientific workflow composition, colors, and icons. Fix all spelling and label errors. Preserve exactly these labels: Form A n=25: Human -> MAS; Form B n=25: MAS -> Human; Human block n=50; MAS block n=50; Final cohort n=50; Main setting n=32; Non-main setting n=18. Make arrows cleaner, increase white space, and ensure no text overlaps.`

## Minimal-text fallback prompt

If gpt-image2 repeatedly corrupts text, use this simpler version and add text locally afterward:

`Create a clean wide scientific workflow infographic with five labeled sections A-E and three lanes: Inputs and blueprint, MAS generation and safety gate, Validation design and endpoints. Use pastel blue for Human, coral for MAS/AI, amber for guidelines, teal for validation. Include blank rounded boxes, line-art icons, arrows, a safety checklist gate, a lock boundary, two A/B sequence arms, and six endpoint tiles. Leave enough blank space inside boxes for labels to be added later. No fake text, no placeholder gibberish, no decorative background.`
