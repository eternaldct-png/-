# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8", "numpy>=1.26", "pillow>=10"]
# ///
"""Render reusable paper plots from supplied data or an explicit illustrative demo."""

import argparse
import json
from itertools import cycle
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Patch
from PIL import Image

matplotlib.use("Agg")

# One visual language: gray is the baseline or raw data, blue is the result being
# claimed, vermilion marks the second arm or extra pixels. Sizes are CVPR column
# width (3.35 in) and text width (7 in) with 7 to 8 pt type.
GRAY, BLUE, ORANGE, GREEN, PURPLE = "0.45", "#0072B2", "#D55E00", "#009E73", "#7851A9"
COLORS = (BLUE, ORANGE, GREEN, PURPLE)
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.titlesize": 8,
        "axes.titlelocation": "left",
        "axes.labelsize": 8,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "legend.frameon": False,
        "axes.edgecolor": "0.3",
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "grid.color": "0.9",
        "grid.linewidth": 0.6,
        "lines.linewidth": 1.5,
        "figure.constrained_layout.use": True,
        "pdf.fonttype": 42,
        "savefig.dpi": 180,
    }
)


def label_end(ax, x, y, text, color):
    """Write a series name just past its last point.

    Args:
        ax (Axes): Target plotting axes.
        x (float): Last x value.
        y (float): Last y value.
        text (str): Series name.
        color (str): Series color.
    """
    ax.annotate(
        text, (x, y), (5, 0), textcoords="offset points", color=color, va="center"
    )


def accuracy_latency(data):
    """Plot measured settings by model family without fitting a trend.

    Args:
        data (dict): Family rows with names, latency_ms and score arrays.

    Returns:
        (Figure): Accuracy versus latency plot.
    """
    fig, ax = plt.subplots(figsize=(3.35, 2.4))
    for row, color in zip(data["tradeoff"], cycle(COLORS)):
        order = np.argsort(row["latency_ms"])
        x, y = np.array(row["latency_ms"])[order], np.array(row["score"])[order]
        ax.plot(x, y, "o-", color=color, markersize=4)
        label_end(ax, x[-1], y[-1], row["family"], color)
    ax.set(xlabel="Latency (ms), lower is better", ylabel="AP (%), higher is better")
    ax.margins(x=0.22)
    ax.grid()
    return fig


def draw_pairs(ax, row):
    """Draw matched absolute scores on one task's scale.

    Args:
        ax (Axes): Target plotting axes.
        row (dict): Labels, before, after and axis title.
    """
    y = np.arange(len(row["labels"]))
    ax.hlines(y, row["before"], row["after"], color="0.8", linewidth=2)
    ax.scatter(
        row["before"],
        y,
        s=26,
        facecolors="white",
        edgecolors=GRAY,
        linewidths=1.2,
        label="Baseline",
        zorder=3,
    )
    ax.scatter(row["after"], y, s=26, color=BLUE, label="Treatment", zorder=3)
    ax.set(
        yticks=y,
        yticklabels=row["labels"],
        xlabel=row["xlabel"],
        ylim=(len(y) - 0.5, -0.5),
    )
    ax.tick_params(axis="y", length=0)
    ax.locator_params(axis="x", nbins=6, steps=[1, 2, 5, 10])
    ax.grid(axis="x")


def paired_scores(data):
    """Show matched baseline and treatment point estimates.

    Args:
        data (dict): Paired absolute scores under paired.

    Returns:
        (Figure): Dumbbell comparison.
    """
    fig, ax = plt.subplots(figsize=(3.35, 1.9))
    draw_pairs(ax, data["paired"])
    fig.legend(*ax.get_legend_handles_labels(), loc="outside upper left", ncol=2)
    return fig


def draw_intervals(ax, row):
    """Draw supplied paired-difference intervals on a delta axis.

    Args:
        ax (Axes): Target plotting axes.
        row (dict): Labels, point, low, high and axis title.
    """
    y = np.arange(len(row["labels"]))
    ax.axvline(0, color="0.4", linewidth=0.8, ls="--")
    ax.hlines(y, row["low"], row["high"], color=BLUE, linewidth=1.8)
    ax.scatter(
        row["point"],
        y,
        s=26,
        facecolors=[
            BLUE if lo > 0 or hi < 0 else "white"
            for lo, hi in zip(row["low"], row["high"])
        ],
        edgecolors=BLUE,
        zorder=3,
    )
    ax.set(
        yticks=y,
        yticklabels=row["labels"],
        xlabel=row["xlabel"],
        ylim=(len(y) - 0.5, -0.5),
    )
    ax.tick_params(axis="y", length=0)
    ax.locator_params(axis="x", nbins=6, steps=[1, 2, 5, 10])
    ax.grid(axis="x")


def paired_intervals(data):
    """Plot supplied intervals without deriving them from absolute endpoints.

    Args:
        data (dict): Paired changes under effects.

    Returns:
        (Figure): Forest plot of paired effects.
    """
    fig, ax = plt.subplots(figsize=(3.35, 1.9))
    draw_intervals(ax, data["effects"])
    ax.set_title("Paired change with supplied 95% CI")
    return fig


def seed_ablation(data):
    """Show individual runs with their mean and sample standard deviation.

    Args:
        data (dict): Ablation labels and arrays of repeated-run scores.

    Returns:
        (Figure): Repeated-run ablation plot.
    """
    fig, ax = plt.subplots(figsize=(3.35, 2.1))
    for y, row in enumerate(data["seeds"]):
        values = np.asarray(row["scores"])
        ax.scatter(values, np.full(len(values), y - 0.17), s=14, color=GRAY, alpha=0.75)
        ax.errorbar(
            values.mean(),
            y + 0.17,
            xerr=values.std(ddof=1),
            fmt="o",
            color=BLUE,
            markersize=4,
            capsize=2.5,
        )
    ax.set(
        yticks=range(len(data["seeds"])),
        yticklabels=[r["label"] for r in data["seeds"]],
        xlabel="AP (%)",
        ylim=(len(data["seeds"]) - 0.5, -0.5),
        title="Gray: runs. Blue: mean ± sample SD",
    )
    ax.tick_params(axis="y", length=0)
    ax.locator_params(axis="x", nbins=6, steps=[1, 2, 5, 10])
    ax.grid(axis="x")
    return fig


def learning_curves(data):
    """Plot recorded learning curves and explicitly labelled supplied bands.

    Args:
        data (dict): Curves with steps, mean, low, high and a band label.

    Returns:
        (Figure): Learning curves with supplied uncertainty bands.
    """
    fig, ax = plt.subplots(figsize=(3.35, 2.4))
    for row, color in zip(data["learning"]["curves"], cycle((GRAY, *COLORS))):
        ax.fill_between(
            row["steps"], row["low"], row["high"], color=color, alpha=0.15, linewidth=0
        )
        ax.plot(row["steps"], row["mean"], color=color)
        label_end(ax, row["steps"][-1], row["mean"][-1], row["label"], color)
    ax.set(
        xlabel="Optimizer updates",
        ylabel="Validation AP (%)",
        title=data["learning"]["band_label"],
    )
    ax.margins(x=0.02)
    ax.set_xlim(right=ax.get_xlim()[1] * 1.22)
    ax.grid()
    return fig


def small_multiples(data):
    """Keep separate tasks on separate axes with the same visual encoding.

    Args:
        data (dict): Per-task paired-score rows under tasks.

    Returns:
        (Figure): Two or more task panels.
    """
    fig, axes = plt.subplots(1, len(data["tasks"]), figsize=(7, 2), squeeze=False)
    for ax, row in zip(axes[0], data["tasks"]):
        draw_pairs(ax, row)
        ax.set_title(row["task"])
    fig.legend(
        *axes[0, 0].get_legend_handles_labels(), loc="outside upper right", ncol=2
    )
    return fig


def draw_grid(ax, rows, columns):
    """Style an image-like matrix with white cell gaps and labels on its edges.

    Args:
        ax (Axes): Target plotting axes.
        rows (list): Row labels.
        columns (list): Column labels.
    """
    ax.set(
        xticks=range(len(columns)),
        xticklabels=columns,
        yticks=range(len(rows)),
        yticklabels=rows,
    )
    ax.set_xticks(np.arange(-0.5, len(columns)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(rows)), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="both", length=0)
    ax.spines[:].set_visible(False)


def error_heatmap(data):
    """Show error rates with each column's own denominator in its label.

    Args:
        data (dict): Error matrix, row labels and denominator-aware column labels.

    Returns:
        (Figure): Annotated error-rate heatmap.
    """
    row = data["errors"]
    values = np.asarray(row["values"])
    fig, ax = plt.subplots(figsize=(3.6, 1.9))
    ax.imshow(values, cmap="Oranges", vmin=0, vmax=100, aspect="auto")
    for index in np.ndindex(values.shape):
        color = "white" if values[index] > 65 else "0.1"
        ax.text(
            index[1],
            index[0],
            f"{values[index]:.3g}",
            ha="center",
            va="center",
            color=color,
        )
    draw_grid(ax, row["labels"], row["columns"])
    ax.xaxis.tick_top()
    return fig


def confusion_matrix(data):
    """Display confusion counts with each reference class's support in its label.

    Args:
        data (dict): Class names and an integer confusion matrix.

    Returns:
        (Figure): Confusion matrix with counts.
    """
    row = data["confusion"]
    values = np.asarray(row["counts"])
    fig, ax = plt.subplots(figsize=(3.35, 2.9))
    ax.imshow(values, cmap="Blues", vmin=0)
    for index in np.ndindex(values.shape):
        color = "white" if values[index] > values.max() / 2 else "0.1"
        ax.text(
            index[1],
            index[0],
            str(values[index]),
            ha="center",
            va="center",
            color=color,
        )
    support = [f"{name} (n={n})" for name, n in zip(row["classes"], values.sum(axis=1))]
    draw_grid(ax, support, row["classes"])
    ax.set(xlabel="Predicted class", ylabel="Reference class")
    return fig


def patient_ecdf(data):
    """Show patient-level paired differences without fitting a distribution.

    Args:
        data (dict): Patient deltas and their unit under patients.

    Returns:
        (Figure): Empirical cumulative distribution of paired changes.
    """
    values = np.sort(data["patients"]["deltas"])
    fig, ax = plt.subplots(figsize=(3.35, 2.3))
    ax.step(
        np.r_[values[0], values],
        np.r_[0, np.arange(1, len(values) + 1) / len(values)],
        where="post",
        color=BLUE,
    )
    ax.axvline(0, color="0.4", linewidth=0.8)
    ax.text(
        0.97, 0.06, f"n = {len(values)}", transform=ax.transAxes, ha="right", color=GRAY
    )
    ax.set(
        xlabel=data["patients"]["xlabel"], ylabel="Fraction of patients", ylim=(0, 1.02)
    )
    ax.grid()
    return fig


def qualitative_grid(data):
    """Compare original frames, binary masks and visible prediction errors.

    Args:
        data (dict): Image and binary-mask paths relative to the input JSON, plus case labels.

    Returns:
        (Figure): Original, reference, prediction and error panels.
    """
    cases = data["qualitative"]
    fig, axes = plt.subplots(
        len(cases), 4, figsize=(7, 0.8 + 1.35 * len(cases)), squeeze=False
    )
    for axes_row, row in zip(axes, cases):
        image = plt.imread(Path(data["_base"]) / row["image"])
        target, prediction = [
            np.asarray(Image.open(Path(data["_base"]) / row[key]).convert("L")) > 127
            for key in ("target", "prediction")
        ]
        errors = np.zeros((*target.shape, 4))
        errors[prediction & ~target] = (*matplotlib.colors.to_rgb(ORANGE), 0.85)
        errors[target & ~prediction] = (*matplotlib.colors.to_rgb(BLUE), 0.85)
        for ax in axes_row:
            ax.imshow(image, cmap="gray")
            ax.set_axis_off()
        axes_row[0].text(
            -0.04,
            0.5,
            row["label"],
            transform=axes_row[0].transAxes,
            rotation=90,
            ha="right",
            va="center",
        )
        axes_row[1].contour(target, levels=[0.5], colors=[BLUE], linewidths=1.2)
        axes_row[2].contour(prediction, levels=[0.5], colors=[ORANGE], linewidths=1.2)
        axes_row[3].imshow(errors)
    for ax, title in zip(
        axes[0], ("Input", "Reference", "Prediction", "Extra / missed")
    ):
        ax.set_title(title, loc="center")
    fig.legend(
        handles=[
            Patch(color=ORANGE, label="Extra (prediction only)"),
            Patch(color=BLUE, label="Missed (reference only)"),
        ],
        loc="outside lower right",
        ncol=2,
    )
    return fig


def pipeline(data):
    """Draw an editable vector workflow diagram.

    Args:
        data (dict): Stage titles and descriptions under pipeline.

    Returns:
        (Figure): Workflow schematic.
    """
    stages = data["pipeline"]
    gap = 0.45
    slot = (7 + gap) / len(stages)
    fig, ax = plt.subplots(figsize=(7, 1.1))
    ax.set(xlim=(-0.05, 7.05), ylim=(0, 0.9), aspect="equal")
    ax.set_axis_off()
    for i, row in enumerate(stages):
        left, width = i * slot, slot - gap
        ax.add_patch(
            FancyBboxPatch(
                (left, 0.05),
                width,
                0.8,
                boxstyle="round,pad=0,rounding_size=0.08",
                facecolor="#F1F6FA",
                edgecolor=BLUE,
                linewidth=0.9,
            )
        )
        ax.text(
            left + width / 2,
            0.64,
            row["title"],
            ha="center",
            va="center",
            weight="bold",
        )
        ax.text(
            left + width / 2,
            0.34,
            row["detail"],
            ha="center",
            va="center",
            fontsize=7.5,
            color="0.3",
            linespacing=1.4,
        )
        if i:
            ax.annotate(
                "",
                (left - 0.04, 0.45),
                (left - gap + 0.04, 0.45),
                arrowprops={
                    "arrowstyle": "-|>",
                    "color": "0.35",
                    "linewidth": 1,
                    "mutation_scale": 8,
                    "shrinkA": 0,
                    "shrinkB": 0,
                },
            )
    return fig


def teaser(data):
    """Pair the same intervention's absolute scores and paired-difference intervals.

    Args:
        data (dict): Matched paired scores and supplied effect intervals.

    Returns:
        (Figure): Compact two-panel teaser.
    """
    fig, axes = plt.subplots(1, 2, figsize=(7, 2), sharey=True)
    draw_pairs(axes[0], data["paired"])
    draw_intervals(axes[1], data["effects"])
    axes[0].set_title("(a) Matched point estimates")
    axes[1].set_title("(b) Paired change with supplied 95% CI")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside upper right", ncol=2)
    return fig


PLOTS = {
    f.__name__: f
    for f in (
        accuracy_latency,
        paired_scores,
        paired_intervals,
        seed_ablation,
        learning_curves,
        small_multiples,
        error_heatmap,
        confusion_matrix,
        patient_ecdf,
        qualitative_grid,
        pipeline,
        teaser,
    )
}


def demo(output):
    """Write synthetic example inputs and return their plotting data.

    Args:
        output (Path): Directory for illustrative data and synthetic mask images.

    Returns:
        (dict): Example data with paths relative to output.
    """
    paired = {
        "labels": ["Task A", "Task B", "Task C"],
        "before": [61, 48, 57],
        "after": [68, 62, 56],
        "xlabel": "Instance F1 (%)",
    }
    data = {
        "note": "ILLUSTRATIVE DATA ONLY, replace with verified measurements",
        "tradeoff": [
            {"family": "Family A", "latency_ms": [1, 2, 4], "score": [51, 58, 63]},
            {"family": "Family B", "latency_ms": [1.5, 3, 5], "score": [54, 64, 68]},
            {
                "family": "Family C",
                "latency_ms": [1.2, 2.5, 4.5],
                "score": [56, 65, 70],
            },
        ],
        "paired": paired,
        "effects": {
            "labels": paired["labels"],
            "point": [7, 14, -1],
            "low": [2, 8, -5],
            "high": [11, 19, 3],
            "xlabel": "Paired ΔF1 (percentage points)",
        },
        "seeds": [
            {"label": "Baseline", "scores": [47.5, 48.1, 47.9]},
            {"label": "+ Ordering", "scores": [50.2, 51.1, 50.5]},
            {"label": "+ Auxiliary", "scores": [49.9, 50.8, 50.1]},
        ],
        "learning": {
            "band_label": "Line: mean. Band: supplied 95% interval",
            "curves": [
                {
                    "label": "Baseline",
                    "steps": [0, 100, 200, 400, 800],
                    "mean": [20, 35, 43, 47, 48],
                    "low": [18, 32, 40, 45, 46],
                    "high": [22, 38, 46, 49, 50],
                },
                {
                    "label": "Treatment",
                    "steps": [0, 100, 200, 400, 800],
                    "mean": [20, 37, 46, 51, 53],
                    "low": [18, 34, 43, 49, 51],
                    "high": [22, 40, 49, 53, 55],
                },
            ],
        },
        "tasks": [
            {
                "task": "Task A",
                "labels": ["Small", "Medium", "Large"],
                "before": [50, 61, 69],
                "after": [57, 64, 70],
                "xlabel": "F1 (%)",
            },
            {
                "task": "Task B",
                "labels": ["Small", "Medium", "Large"],
                "before": [42, 53, 64],
                "after": [46, 60, 66],
                "xlabel": "F1 (%)",
            },
        ],
        "errors": {
            "labels": ["Baseline", "Variant A", "Variant B"],
            "columns": [
                "Missed\n(% of refs)",
                "Extra\n(% of preds)",
                "Bad output\n(% of images)",
            ],
            "values": [[42, 37, 9], [35, 29, 8], [28, 25, 3]],
        },
        "confusion": {
            "classes": ["Liver", "Kidney", "Shadow"],
            "counts": [[85, 6, 9], [5, 42, 3], [4, 7, 19]],
        },
        "patients": {
            "deltas": [-9, -5, -3, -2, -1, 0, 1, 2, 3, 3, 4, 5, 6, 7, 9, 12],
            "xlabel": "Within-patient ΔF1 (percentage points)",
        },
        "pipeline": [
            {
                "title": "Frozen cohort",
                "detail": "Patient-level split\nFixed input hashes",
            },
            {
                "title": "Matched training",
                "detail": "Declared intervention\nBudget controls",
            },
            {
                "title": "Shared scoring",
                "detail": "Native resolution\nPaired uncertainty",
            },
        ],
        "qualitative": [],
    }
    folder = output / "demo-inputs"
    folder.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    yy, xx = np.mgrid[:96, :128]
    for i in range(2):
        image = np.clip(
            0.4
            + 0.15 * np.sin(xx / 8)
            + 0.1 * np.cos(yy / 9)
            + rng.normal(0, 0.07, xx.shape),
            0,
            1,
        )
        target = ((xx - 57) / (27 - i * 4)) ** 2 + ((yy - 48) / 23) ** 2 < 1
        prediction = ((xx - 63 - i * 4) / 29) ** 2 + ((yy - 46) / 20) ** 2 < 1
        row = {"label": f"Schematic {i + 1}"}
        for key, pixels in (
            ("image", image),
            ("target", target),
            ("prediction", prediction),
        ):
            path = folder / f"case-{i}-{key}.png"
            plt.imsave(path, pixels, cmap="gray", vmin=0, vmax=1)
            row[key] = str(path.relative_to(output))
        data["qualitative"].append(row)
    (output / "illustrative-data.json").write_text(json.dumps(data, indent=2) + "\n")
    return data


def contact_sheet(paths, output, width=14.4, gap=0.3):
    """Pack rendered PNGs at their true size into one titled overview image.

    Args:
        paths (list): PNG paths to show.
        output (Path): Overview image path.
        width (float): Maximum row width in inches.
        gap (float): Space between images and above each title in inches.
    """
    dpi = plt.rcParams["savefig.dpi"]
    rows, x = [], width
    for path in paths:
        image = plt.imread(path)
        if x + image.shape[1] / dpi > width:
            rows.append([])
            x = 0
        rows[-1].append((path.stem, image))
        x += image.shape[1] / dpi + gap
    heights = [max(im.shape[0] for _, im in row) / dpi + gap for row in rows]
    sheet_width = max(sum(im.shape[1] / dpi + gap for _, im in row) for row in rows)
    fig = plt.figure(figsize=(sheet_width, sum(heights)), layout="none")
    top = sum(heights)
    for row, height in zip(rows, heights):
        left = 0
        for name, image in row:
            h, w = image.shape[0] / dpi, image.shape[1] / dpi
            ax = fig.add_axes(
                [
                    left / sheet_width,
                    (top - gap - h) / sum(heights),
                    w / sheet_width,
                    h / sum(heights),
                ]
            )
            ax.imshow(image)
            ax.set_axis_off()
            ax.set_title(name, fontsize=8, color="0.3", pad=3)
            left += w + gap
        top -= height
    fig.savefig(output)
    plt.close(fig)


def main():
    """Render selected templates and a contact sheet from supplied or illustrative data."""
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--data", type=Path, help="JSON with the selected template's inputs"
    )
    source.add_argument(
        "--demo", action="store_true", help="write explicitly illustrative example data"
    )
    parser.add_argument("--plot", choices=["all", *PLOTS], default="all")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = demo(args.output_dir) if args.demo else json.loads(args.data.read_text())
    data["_base"] = args.output_dir if args.demo else args.data.resolve().parent
    names = list(PLOTS) if args.plot == "all" else [args.plot]
    with PdfPages(args.output_dir / "plot-gallery.pdf") as pdf:
        for name in names:
            fig = PLOTS[name](data)
            if args.demo:
                fig.supxlabel(data["note"], x=0.01, ha="left", fontsize=6, color="0.5")
            pdf.savefig(fig)
            for suffix in ("pdf", "png"):
                fig.savefig(args.output_dir / f"{name}.{suffix}")
            plt.close(fig)
    contact_sheet(
        [args.output_dir / f"{name}.png" for name in names],
        args.output_dir / "gallery.png",
    )


if __name__ == "__main__":
    main()
