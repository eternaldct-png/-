# Research and Experiment Tracker Issues

Use this layout for every GitHub tracker issue that records dataset builds, baseline reproductions, training sweeps, or ablation studies. Keep individual experiment rows in the tracker issue and keep project skills (`SKILL.md`) compact: skills hold reusable know-how, reproduction commands, paths, weight hashes, settled findings, figure generation scripts, and a champion summary table, never raw wave-by-wave logs.

## Canonical Issue Layout

Every tracker issue follows five sections in exact order:

### 1. Top Reproduction Accordion (`> [!IMPORTANT]` + closed `<details>`)

Start the issue body with a closed reproduction block containing exact code revisions, environment pins, dataset/cache paths, starting weight digests (`sha256` or `md5`), and copy-pasteable training, evaluation, and figure-generation commands:

````markdown
> [!IMPORTANT]
> <details>
> <summary><b>How to reproduce</b>: code, environment, data, weights, training and evaluation</summary>
>
> **Code:** branch [`<branch>`](https://github.com/<org>/<repo>/tree/<branch>) ([`<sha7>`](https://github.com/<org>/<repo>/commit/<full-sha>)), scripts in `<path>/` (`train.py`, `eval.py`).
>
> **Environment:** `<venv-path>` (`torch <ver>`, `<key-deps>`).
>
> **Data:** `<host>:<dataset-or-cache-path>` (`<train-count>` train / `<val-count>` val images).
>
> **Starting weights:** `<path>/<weight>.pt` (`sha256:<prefix>`).
>
> ```bash
> # Train
> python train.py --config <cfg> --weights <weight>.pt --device 0,1,2,3
>
> # Evaluate
> python eval.py best.pt --data <data.yaml> --save-json predictions.json
> ```
>
> </details>
````

### 2. Concise Overview Bullets (Never an Unformatted Text Blob)

Immediately below the reproduction accordion, summarize the research question and headline results using 2-3 structured top-level bullets (`- **Goal:**`, `- **Key Findings:**`) with short indented sub-bullets and inline links (`[`sha7`](url)`, `[`#N`](url)`). Never write a wall-of-text paragraph blob.

```markdown
- **Goal:** Compare `<factors>` on `<benchmarks>` against [`#<ref-issue>`](url) `<baseline>` from identical `<init-weights>`.
  - **Architectures & Inits:** `<arch-A>` (`<init-A>`) vs. `<arch-B>` (`<init-B>`).
  - **Ablated Factors:** `<factor-1>`, `<factor-2>`, and `<factor-3>` ([`<sha7>`](url)).
- **Key Findings:**
  - **<Winner / Factor 1> ([`<sha7>`](url)):** Reaches **`<metric>`** (`+<delta>` over `<baseline>`).
  - **<Falsified Factor 2> ([`<sha7>`](url)):** Drops `<metric>` to `<val>` because `<1-line root cause>`.
```

### 3. Top `### Summary` Figure & Table (Baselines + Champions)

Place the primary comparison figure (replaced in-place on every update) and the `### Summary` table right below the overview bullets so readers see the visual state, baselines, and best runs without opening any accordion:

- **In-place Summary figure:** Render the project's comparison chart (multi-metric scatter, Pareto frontier, paired delta intervals, or same-epoch learning curves) using a project skill script or the [CVPR plotting guide](../../paper-write/references/cvpr.md) ([`plots.py`](../../paper-write/assets/cvpr/plots.py)) and place it at the top of `### Summary`.
- **Summary table rules:**
  - Put reference baselines (`(ref)`) first, followed by the champion or leading row of each ablation group.
  - Name what changed in plain English (`Model`, `Change`), never internal shortcodes (`E4`, `Q5`, `run-1`).
  - Include a `Code` column linking the exact training commit (`[`sha7`](https://github.com/<org>/<repo>/commit/<full-sha>)`) and a `Progress` column (`✅ 25/25`, `🟡 12/25`, `⏹️ 12/25`, `❌`).
  - Bold numeric winners within comparable settings. Use `-` for inapplicable cells and `pending` for unmeasured cells on active runs.

```markdown
### Summary

![<Experiment comparison: Metric A vs. Metric B>](https://github.com/user-attachments/assets/<uuid>)

| Model | Change | Code | Progress | Primary Metric | Secondary Metric |
| --- | --- | --- | --- | --- | --- |
| `<baseline>` (ref) | `<default recipe>` | [`<sha7>`](url) | ✅ 25/25 | 37.80 | 57.60 |
| **`<ablation-winner>`** | `<factor change>` | [`<sha7>`](url) | ✅ 25/25 (best ep25) | **38.16** | **58.39** |
```

### 4. Closed `<details>` Ablation Group & Visual Evidence Sections (Identical Column Schema)

Group all individual runs and qualitative/diagnostic visual evidence under `### Ablation Groups` (or `### Trainings` / `### Benchmarks` / `### Examples`) into closed `<details>` blocks:

- **Blank-line rule:** Always keep a blank line after `<summary>...</summary>` and before `</details>`. Without those blank lines GitHub renders tables and images as raw text. Never use `<details open>`.
- **Summary clause:** `<summary><b>1. Group Title</b>: what the block compares and headline takeaway</summary>`.
- **Uniform table schema:** Reuse the exact same metric columns and column order as `### Summary`. Training tables may add `Host: GPUs` and `Run` (linking the W&B run); standalone benchmark tables may add `Eval code` and `Epoch` when post-hoc evaluation code differs from training code.

```markdown
### Ablation Groups

<details>
<summary><b>1. <Group Title></b>: <what this block compares and headline number></summary>

| Model | Change | Host: GPUs | Code | Progress | Primary Metric | Secondary Metric | Run |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **`<run-name>`** | `<change>` | `<host>: 0,1` | [`<sha7>`](url) | ✅ 25/25 | **38.16** | **58.39** | [W&B](url) |

</details>
```

### 5. `### Comments` Index

- List deep-dive root-cause analyses, code audits, or overflow tables (when an issue approaches GitHub's 65,536-character limit) under `### Comments` at the bottom, each with a linked title and a one-line summary.

## Figures, In-Place Replacement, and Visual Evidence for Claims

Every tracker issue and scheduled update loop should pair tables with visual evidence uploaded via `gh --attach` (`gh >= 2.99.0`), never by committing image files to git branches.

### 1. Quantitative Comparison Figures (In-Place Replacement on Updates)

- **Generator source:** Use the project skill's dedicated plotting script (under `.agents/skills/<skill>/scripts/`) or adapt a function from [`paper-write/assets/cvpr/plots.py`](../../paper-write/assets/cvpr/plots.py) (`accuracy_latency`, `paired_scores`, `paired_intervals`, `seed_ablation`, `learning_curves`, `small_multiples`, `error_heatmap`) following [CVPR visual style](../../paper-write/references/cvpr.md) (neutral gray `0.45` for baselines, Okabe-Ito accents `#0072B2` blue, `#D55E00` vermilion, `#009E73` green, `#7851A9` purple for ablations, direct labels, no top/right spines). Always inspect the rendered PNG before uploading.
- **Replace older figures in-place on each update:** When new runs or epochs finish (including during scheduled cron/loop checks), regenerate the figure to `/tmp/<fig>.png`, replace the old `![...](https://github.com/user-attachments/assets/...)` line in the issue body with `![<alt text>](/tmp/<fig>.png)`, and run:
  ```bash
  gh issue edit <N> --repo <owner>/<repo> --body-file /tmp/issue_new.md --attach /tmp/<fig>.png
  ```
  `gh` uploads `/tmp/<fig>.png` to GitHub `user-attachments` (inheriting repository permissions) and rewrites the local path in the Markdown body to the new permanent asset URL in a single atomic edit, keeping the issue clean without accumulating outdated charts.

### 2. Qualitative & Diagnostic Evidence for Claims (Annotated Predictions, Montages, Histograms)

Whenever you claim a model behavior, failure mode, or dataset issue (for example, *"Model A misses rare classes / fails on relational queries / suffers from duplicate boxes while Model B fixes it"*, or *"threshold $\tau$ separates true copies from look-alikes"*), attach visual proof via `gh issue edit --attach` or `gh issue comment --attach`:

- **Annotated prediction montages (`qualitative_grid`):** Show side-by-side crops or full images comparing **Ground Truth** vs. **Baseline prediction** vs. **Ablation prediction** on representative win and failure cases, with boxes/masks/keypoints and confidence scores drawn.
- **Diagnostic charts & histograms:** Attach score/confidence histograms, per-slice or per-class accuracy delta bars, confusion matrices, or error heatmaps that prove the mechanism behind the aggregate metric change.
- **Collapsible presentation:** Wrap qualitative montages and diagnostic sub-figures in closed `<details>` accordions so the issue stays scannable:
  ```markdown
  <details>
  <summary><b>Visual evidence: <claim or failure mode></b>: <N side-by-side prediction pairs / distribution chart></summary>

  ![<Side-by-side comparison: Baseline left, Ablation right>](/tmp/qualitative_comparison.png)

  </details>
  ```

## Live-Update Protocol

1. **Fetch live body without trailing-newline drift:**
   ```bash
   gh issue view <N> --repo <owner>/<repo> --json body -q .body > /tmp/issue_orig.md
   ```
2. **Regenerate figure(s) and patch body in place:** Update rows, progress, and summary winners in Python. Replace any outdated figure URL with the new local `/tmp/<fig>.png` path so `gh --attach` swaps it in place. Verify that no existing run row was dropped and that the body contains no em-dashes, en-dashes, semicolons, section signs, `<details open>`, or unformatted paragraph blobs.
3. **Push once with `--attach` and confirm round-trip:**
   ```bash
   gh issue edit <N> --repo <owner>/<repo> --body-file /tmp/issue_new.md --attach /tmp/<fig>.png
   ```
