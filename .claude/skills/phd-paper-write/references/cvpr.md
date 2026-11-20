# CVPR writing and layout

Use these patterns with the paper's current author kit. Build instructions are in [latex.md](latex.md).

## Rules and message

- Check the target year and track. Workshop paper limits differ from workshop-proposal limits.
- [CVPR 2027](https://cvpr.thecvf.com/Conferences/2027/AuthorGuidelines), checked 2026-11-15: eight main-content pages, including figures and tables. Cited references and the mandatory anonymous LLM Usage Statement may occupy extra pages. Recheck before submission.
- Align title, abstract, teaser and conclusion around one supported finding. Abstract: problem, approach, result, limitation. Include only useful, traceable numbers.
- Organize results by question, with findings first and the necessary controls beside them. Define technical terms. Prefer "extra predictions" and "invalid output" when those are the scorer's meanings.
- Match model, cohort, budget, checkpoint policy and scorer before claiming improvement. Keep paired-difference intervals on a delta axis. Overlapping intervals do not establish equivalence.

## First-page teaser

- Show one visual argument. Combine panels only when they answer the same question. Label synthetic illustrations as schematics.
- A `figure*` inside the introduction may land on page two. If the current kit uses `\@maketitle`, this preamble hook places a teaser in its full-width title area. It needs `graphicx` and `capt-of`.

```latex
\usepackage{graphicx,capt-of}
\makeatletter
\g@addto@macro\@maketitle{%
  \par\centering
  \includegraphics[width=\textwidth]{fig/teaser.pdf}\par
  \captionof{figure}{Task, cohort, comparison and main observation.}
  \label{fig:teaser}
}
\makeatother
```

- Inspect page one in named and anonymous builds. Keep the method overview near its explanation. Preserve readable full-width task visuals when they supply central evidence.

## Tables

- Prefer thin rules to repeated group-heading rows. Use short row labels, grouped column headers, explicit units and consistent precision. Timing captions state hardware and batch size. Drop columns that are constant or bookkeeping (status, checkpoint) and state constants in the caption. Name the actual input source, such as the detector that produced the boxes, never internal run codes. Spell out abbreviated headers (Truncated, not Trunc.).
- Bold declared numeric winners within comparable settings, including ties. Mark a selected configuration separately. If exposure differs, disclose it and call maxima descriptive.
- Generate every cell from a results file, never from copied literals. Give display labels one owner (a label map) applied before formatting. Merge related ablations only while every panel stays legible. Before and after any table edit, diff the displayed numbers and provenance and keep both identical.

### Copy a table layout

Use [tables.tex](../assets/cvpr/tables.tex) to render the gallery with the current author kit, `booktabs` and `amssymb`. Copy individual snippets into the paper, not the gallery driver. All values are illustrative.

- [Mixed directions](../assets/cvpr/tables/mixed-metrics.tex): AP ↑, latency ↓, selected-design symbol and numeric winners.
- [Grouped columns](../assets/cvpr/tables/grouped-columns.tex): task headers with `\multicolumn` and `\cmidrule`.
- [Row blocks](../assets/cvpr/tables/row-blocks.tex): thin rules and winners within each scale.
- [Component ablation](../assets/cvpr/tables/component-ablation.tex): checkmarks and baseline-relative changes.
- [Repeated runs](../assets/cvpr/tables/repeated-runs.tex): mean ± SD, bold mean only.
- [Paired changes](../assets/cvpr/tables/paired-changes.tex): absolute endpoints and a separate supplied CI for the difference.
- [Efficiency](../assets/cvpr/tables/efficiency.tex): accuracy ↑, parameter count, compute and latency ↓.
- [Missing values and ties](../assets/cvpr/tables/missing-and-ties.tex): bold ties, unmeasured `--`, inapplicable `N/A`.
- [Related panels](../assets/cvpr/tables/multi-panel.tex): two legible ablations in one full-width float.
- [Per-class support](../assets/cvpr/tables/per-class-support.tex): support counts and row-wise model comparisons.

## Choose a plot by the question

[plots.py](../assets/cvpr/plots.py) contains independent drawing functions. From the `paper-write` skill directory, generate the illustrative gallery, then adapt its JSON inputs or copy the relevant function:

```bash
uv run assets/cvpr/plots.py --demo --output-dir /tmp/cvpr-gallery
uv run assets/cvpr/plots.py --data results.json --plot paired_intervals --output-dir fig
```

- `accuracy_latency`: measured accuracy versus latency, one curve per model family.
- `paired_scores`: matched absolute scores as dumbbells.
- `paired_intervals`: supplied paired changes and CIs on a delta axis. Open markers are supplied intervals that include zero.
- `seed_ablation`: individual runs, mean and sample SD. Supply at least two runs per arm.
- `learning_curves`: recorded scores with explicitly labelled, supplied uncertainty bands.
- `small_multiples`: separate task/view axes using consistent encoding.
- `error_heatmap`: error rates with a separate denominator in each column label.
- `confusion_matrix`: raw counts that preserve class support.
- `patient_ecdf`: the distribution of within-patient changes, without a fitted density.
- `qualitative_grid`: input, reference, prediction and extra/missed-pixel overlays.
- `pipeline`: editable vector boxes and arrows for the experiment protocol.
- `teaser`: matched scores and their supplied paired-change intervals side by side.

- `--demo` writes illustrative JSON, synthetic masks, individual PDFs/PNGs and both galleries. Only demo mode stamps the figures.
- Real JSON needs only the selected function's keys. Qualitative paths are relative to that JSON. Replace demo values with verified records and retain actual missingness and interval definitions.
- Gray marks baselines or raw runs, blue the treatment, vermilion the second arm or extra pixels. Use marker fill and direct labels as well as color.
- Inspect at final column or full width. Separate crowded end labels or use a legend. The gallery preserves relative figure sizes. The plotter preserves supplied intervals and performs no statistical tests.

## Main paper and supplement

- Keep headline evidence, essential controls and material limitations in the main paper. Move detailed sweeps, redundant plots and supporting diagnostics with explicit references. Preserve the implication of negative results.
- Cut repetition before shrinking fonts. Do not change margins to fit. Check the year's restrictions on supplementary results.
- Flush floats before counting main pages. For a combined document using `hyperref`, adapt this boundary and numbering pattern. Reuse the existing bibliography pipeline at the indicated point.

```latex
\clearpage
\typeout{MAIN_CONTENT_PAGES=\number\numexpr\value{page}-1\relax}
% References and required disclosures go here.
\clearpage
\appendix
\setcounter{table}{0}
\setcounter{figure}{0}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\theHtable}{supp.\arabic{table}}
\renewcommand{\theHfigure}{supp.\arabic{figure}}
\typeout{SUPPLEMENT_START_PAGE=\thepage}
\input{supplement}
```

- Verify main-content pages separately from total PDF pages. Resolve missing references, clipping and overflow. Check fonts, anonymity, float order and exported PDF boundaries. Disclose actual tool use.
- If syncing a hosted editor is requested, inspect its compiled PDF too. Layout work does not authorize submission or new experiments.

## Published examples

These illustrate choices, not mandatory conventions or predictors of acceptance:

- [CV4Clinic 2026, Tables 4–5](https://openaccess.thecvf.com/content/CVPR2026W/CV4Clinic2026/papers/Demir_How_Useful_Are_Vision_Foundation_Model_Features_for_Out-of-the-Box_Disease_CVPRW_2026_paper.pdf): thin rules, short condition labels, bold within settings.
- [PHAROS-AIF-MIH 2026, Table 1](https://openaccess.thecvf.com/content/CVPR2026W/PHAROS-AIF-MIH/papers/Wu_Attention_Consistent_Longitudinal_Medical_Visual_Question_Answering_Guided_by_Vision_CVPRW_2026_paper.pdf): one rule separates comparator methods from the proposed method.
