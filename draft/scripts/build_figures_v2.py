#!/usr/bin/env python3
"""Regenerate survey figures and Table 1 stats from corpus_v2.csv.

Outputs:
  draft/figures/map_landscape_v2.png   TF-IDF+SVD+t-SNE semantic map with density
                                       contours, colored by category
  draft/figures/growth_timeline_v2.png two-panel quarterly output figure using seed
                                       corpus only -- the supplement is recency-biased
                                       by construction and would distort trends
  stdout: Table 1 (markdown) with per-category counts and % posted 2026
"""

import csv
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "artifacts" / "corpus_v2.csv"
FIGS = ROOT / "draft" / "figures"
LATEX_FIGS = ROOT / "draft" / "latex" / "figures"

CATS = ["deployment", "training", "evaluation", "research", "foundations"]
LABEL = {
    "deployment": "Deployment-time self-evolution",
    "training": "Training-time self-iteration",
    "evaluation": "Self-evaluation",
    "research": "Auto Research",
    "foundations": "Foundations, limits & safety",
}
COLOR = {  # dataviz reference palette, fixed slot order
    "deployment": "#2a78d6",
    "training": "#1baf7a",
    "evaluation": "#eda100",
    "research": "#008300",
    "foundations": "#4a3aa7",
}
TEXT_PRIMARY, TEXT_SECONDARY = "#0b0b0b", "#52514e"
GRID = "#eceae6"
PANEL_BG = "#fbfaf7"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 9.5,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.5,
    "figure.dpi": 150,
    "savefig.dpi": 300,
})

FIGS.mkdir(parents=True, exist_ok=True)
LATEX_FIGS.mkdir(parents=True, exist_ok=True)

with open(CORPUS, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
print(f"{len(rows)} corpus rows")


def save_figure(fig, filename):
    """Write the manuscript PNG and keep the LaTeX figure copy in sync."""
    out = FIGS / filename
    fig.savefig(out, facecolor="white", bbox_inches="tight", dpi=300)
    shutil.copy2(out, LATEX_FIGS / filename)
    print(f"wrote {out}")
    print(f"copied {LATEX_FIGS / filename}")


def quarter(r):
    d = r["pub_date"] or ""
    if len(d) < 7:
        return None
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}Q{(m - 1) // 3 + 1}"


def style_spines(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines["left"].set_color("#d8d7d2")
    ax.spines["bottom"].set_color("#d8d7d2")
    ax.tick_params(color="#b8b5ae", labelcolor=TEXT_SECONDARY)

# ---------------- Table 1 ----------------
print("\n### Table 1 (markdown)\n")
print("| Category | Sub-threads | Papers | of which supplement | % posted 2026 |")
print("|---|---|---:|---:|---:|")
SUBS = {
    "deployment": "output refinement · test-time training · harness/skill evolution",
    "training": "self-reward RL · CoT self-training · self-distillation · self-play (incl. zero-data) · embodied",
    "evaluation": "judges · process/reward models · verifiers · rubrics · meta-evaluation",
    "research": "AI scientists · evolutionary program discovery",
    "foundations": "theory · limits · safety",
}
for cat in CATS:
    sub = [r for r in rows if r["category"] == cat]
    supp = sum(1 for r in sub if r["source"] == "supplement")
    y26 = sum(1 for r in sub if r["year"] == "2026") / max(len(sub), 1)
    print(f"| {LABEL[cat]} | {SUBS[cat]} | {len(sub)} | {supp} | {y26:.0%} |")
dep = [r for r in rows if r["category"] == "deployment"]
sc = Counter(r["subcategory"] for r in dep)
print(f"\ndeployment subcats: {dict(sc)}")

# ---------------- semantic map ----------------
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import TSNE
from sklearn.neighbors import KernelDensity

texts = [(r["title"] or "") + ". " + (r["summary"] or "")[:1200] for r in rows]
X = TfidfVectorizer(max_features=30000, stop_words="english",
                    sublinear_tf=True).fit_transform(texts)
Z = TruncatedSVD(n_components=60, algorithm="arpack", random_state=0).fit_transform(X)
P = TSNE(n_components=2, random_state=0, perplexity=40,
         init="random", learning_rate="auto").fit_transform(Z)
P = (P - P.mean(axis=0)) / P.std(axis=0)

fig, ax = plt.subplots(figsize=(7.0, 4.6), dpi=300)
ax.set_facecolor(PANEL_BG)

# Plot high-volume categories first and smaller, more coherent groups last.
plot_order = ["training", "deployment", "evaluation", "research", "foundations"]
for cat in plot_order:
    idx = np.array([i for i, r in enumerate(rows) if r["category"] == cat])
    size = 10 if cat in {"research", "foundations"} else 8
    alpha = 0.68 if cat in {"research", "foundations"} else 0.42
    ax.scatter(P[idx, 0], P[idx, 1], s=size, c=COLOR[cat], alpha=alpha,
               linewidths=0, label=f"{LABEL[cat]} (n={len(idx)})", rasterized=True)

xpad = 0.35
ypad = 0.35
xmin, xmax = P[:, 0].min() - xpad, P[:, 0].max() + xpad
ymin, ymax = P[:, 1].min() - ypad, P[:, 1].max() + ypad
xx, yy = np.meshgrid(np.linspace(xmin, xmax, 130), np.linspace(ymin, ymax, 130))
grid = np.c_[xx.ravel(), yy.ravel()]

for cat in CATS:
    idx = np.array([i for i, r in enumerate(rows) if r["category"] == cat])
    pts = P[idx]
    kde = KernelDensity(bandwidth=0.34, kernel="gaussian").fit(pts)
    dens = np.exp(kde.score_samples(grid)).reshape(xx.shape)
    levels = np.quantile(dens, [0.90, 0.965])
    if np.unique(levels).size == len(levels):
        ax.contour(xx, yy, dens, levels=levels, colors=[COLOR[cat]],
                   linewidths=[1.0, 1.7], alpha=0.78)

label_offsets = {
    "deployment": (-0.10, -0.48),
    "training": (-0.35, 0.36),
    "evaluation": (-0.55, -0.03),
    "research": (0.24, -0.45),
    "foundations": (0.30, 0.40),
}
DIRECT_LABEL = {
    "deployment": "Deployment",
    "training": "Training",
    "evaluation": "Self-evaluation",
    "research": "Auto Research",
    "foundations": "Foundations/safety",
}
for cat in CATS:
    idx = np.array([i for i, r in enumerate(rows) if r["category"] == cat])
    pts = P[idx]
    center = np.median(pts, axis=0)
    dx, dy = label_offsets[cat]
    txt = ax.text(center[0] + dx, center[1] + dy, DIRECT_LABEL[cat],
                  color=COLOR[cat], fontsize=8.7, fontweight="bold",
                  ha="center", va="center")
    txt.set_path_effects([pe.withStroke(linewidth=3.8, foreground="white", alpha=0.92)])


ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)
ax.set_xticks([])
ax.set_yticks([])
for s in ax.spines.values():
    s.set_color("#d8d7d2")
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels, loc="lower right", framealpha=0.94, edgecolor="#d8d7d2",
          frameon=True, borderpad=0.6, handletextpad=0.4, markerscale=1.5, fontsize=7.8)
fig.tight_layout()
save_figure(fig, "map_landscape_v2.png")
plt.close(fig)

# ---------------- growth timeline (seed corpus only) ----------------
seed = [r for r in rows if r["source"] == "seed"]
quarters = sorted({q for r in seed if (q := quarter(r))})
partial_quarter = quarters[-1]
plot_quarters = quarters[:-1]
partial_n = sum(1 for r in seed if quarter(r) == partial_quarter)
x = np.arange(len(plot_quarters))
counts = {
    cat: np.array([
        sum(1 for r in seed if r["category"] == cat and quarter(r) == q)
        for q in plot_quarters
    ], dtype=float)
    for cat in CATS
}
totals = np.array([
    sum(1 for r in seed if quarter(r) == q)
    for q in plot_quarters
], dtype=float)
shares = {
    cat: np.divide(counts[cat], totals, out=np.zeros_like(totals), where=totals > 0)
    for cat in CATS
}

fig = plt.figure(figsize=(7.4, 5.6), dpi=300)
gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 0.85], hspace=0.18)
ax_count = fig.add_subplot(gs[0])
ax_share = fig.add_subplot(gs[1], sharex=ax_count)

markers = {
    "deployment": "o",
    "training": "s",
    "evaluation": "^",
    "research": "D",
    "foundations": "v",
}
linestyles = {
    "deployment": "-",
    "training": "--",
    "evaluation": "-.",
    "research": ":",
    "foundations": (0, (3, 1, 1, 1)),
}

ax_count.plot(x, totals, color="#1c1c1c", linewidth=2.2, marker="o",
              markersize=4.5, label=f"Total seed corpus (n={len(seed)})", zorder=4)
for cat in CATS:
    vals = counts[cat].copy()
    vals[vals == 0] = np.nan
    ax_count.plot(x, vals, color=COLOR[cat], linewidth=1.65,
                  linestyle=linestyles[cat], marker=markers[cat], markersize=4.2,
                  label=LABEL[cat], alpha=0.95)

ax_count.set_yscale("log")
ax_count.set_ylim(1, max(totals) * 1.65)
ax_count.set_ylabel("Papers per quarter\n(log scale)", color=TEXT_SECONDARY)
ax_count.grid(axis="y", which="major", color=GRID, linewidth=0.8)
ax_count.set_axisbelow(True)
style_spines(ax_count)
ax_count.set_title("RSI-related arXiv output accelerates sharply in the seed corpus",
                   loc="left", fontsize=12, color=TEXT_PRIMARY,
                   fontweight="bold", pad=8)
ax_count.text(x[-1] + 0.05, totals[-1], "501 in 2026Q2",
              color=TEXT_PRIMARY, fontsize=8.4, va="center", ha="left")
ax_count.annotate("partial 2026Q3 omitted\n(14 seed papers before early July)",
                  xy=(x[-1], 1.25), xytext=(x[-2] - 0.1, 1.25),
                  color=TEXT_SECONDARY, fontsize=8.1, ha="right", va="bottom",
                  arrowprops=dict(arrowstyle="-", color="#b8b5ae", lw=0.8))
plt.setp(ax_count.get_xticklabels(), visible=False)
ax_count.tick_params(axis="x", which="both", length=0)

for cat in CATS:
    ax_share.plot(x, shares[cat] * 100, color=COLOR[cat], linewidth=1.8,
                  linestyle=linestyles[cat], marker=markers[cat], markersize=4.0,
                  alpha=0.95)

ax_share.set_ylabel("Category share\nof quarter", color=TEXT_SECONDARY)
ax_share.set_ylim(0, 100)
ax_share.set_yticks([0, 25, 50, 75, 100])
ax_share.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
ax_share.grid(axis="y", color=GRID, linewidth=0.8)
ax_share.set_axisbelow(True)
style_spines(ax_share)
ax_share.set_xticks(x)
ax_share.set_xticklabels(plot_quarters, rotation=35, ha="right")

legend_handles = [
    Line2D([0], [0], color="#1c1c1c", linewidth=2.2, marker="o",
           markersize=4.5, label="Total")
]
legend_handles.extend(
    Line2D([0], [0], color=COLOR[cat], linewidth=1.8,
           linestyle=linestyles[cat], marker=markers[cat], markersize=4.2,
           label=LABEL[cat])
    for cat in CATS
)
fig.legend(handles=legend_handles, loc="lower center", ncol=3, frameon=False,
           bbox_to_anchor=(0.5, -0.025), columnspacing=1.35, handlelength=2.2)
fig.subplots_adjust(top=0.90, bottom=0.24, left=0.12, right=0.98, hspace=0.18)
save_figure(fig, "growth_timeline_v2.png")
print(f"omitted partial quarter from Figure 2: {partial_quarter} (n={partial_n})")
plt.close(fig)
