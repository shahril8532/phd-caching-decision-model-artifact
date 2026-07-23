"""
Generates figures/power_analysis_chart.png: post-hoc statistical power per
relationship (Equation 5.1, n=10 repeated runs), one panel per system,
sorted by achieved power, colour-coded by CACHE/DO_NOT_CACHE/BORDERLINE
decision, with a dashed reference line at the conventional 0.80 power
target. Every BORDERLINE relationship is directly labelled with its name.
This is the script used to generate Figure 5.1 in the thesis.

Usage:
    python3 plot_power_analysis.py

Requires: matplotlib, statsmodels, scipy
"""

import csv
import glob
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.stats.power import TTestPower
from scipy import stats as scipy_stats

ALPHA = 0.05
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(HERE, "..", "data")
OUT_PATH = os.path.join(HERE, "..", "figures", "power_analysis_chart.png")

SYSTEMS = {
    "iTeams": os.path.join(DATA_ROOT, "iTeams"),
    "Khairat": os.path.join(DATA_ROOT, "Khairat"),
    "VBS": os.path.join(DATA_ROOT, "VBS"),
}

COLORS = {"CACHE": "#2e7d32", "DO_NOT_CACHE": "#c62828", "BORDERLINE": "#f9a825"}


def load_relationships(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "*run*[0-9].csv")))
    rows = []
    for fp in files:
        with open(fp, newline="") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    by_rel = {}
    for row in rows:
        key = f"{row['model']}.{row['method']}"
        by_rel.setdefault(key, []).append(float(row["speedup_pct"]))
    return by_rel


def main():
    analysis = TTestPower()
    fig, axes = plt.subplots(1, 3, figsize=(19, 7), sharey=True)

    for ax, (sysname, path) in zip(axes, SYSTEMS.items()):
        by_rel = load_relationships(path)
        results = []
        for name, speedups in by_rel.items():
            n = len(speedups)
            mean = sum(speedups) / n
            var = sum((x - mean) ** 2 for x in speedups) / (n - 1) if n > 1 else 0
            sd = math.sqrt(var)
            if sd == 0:
                continue
            d = mean / sd
            power = analysis.power(effect_size=abs(d), nobs=n, alpha=ALPHA, alternative="larger")
            t_stat = mean / (sd / math.sqrt(n))
            p = float(scipy_stats.t.sf(abs(t_stat), n - 1))
            if p < ALPHA and mean > 0:
                decision = "CACHE"
            elif p < ALPHA and mean < 0:
                decision = "DO_NOT_CACHE"
            else:
                decision = "BORDERLINE"
            results.append((name, power, decision))

        results.sort(key=lambda r: r[1])
        xs = list(range(len(results)))
        ys = [r[1] for r in results]
        cs = [COLORS[r[2]] for r in results]
        n_res = len(results)

        ax.scatter(xs, ys, c=cs, s=48, zorder=3, edgecolors="black", linewidths=0.5, alpha=0.85)
        ax.axhline(0.80, color="black", linestyle="--", linewidth=1.2, zorder=2)

        # Label placed well below the 0.80 line, away from x=0, so it never
        # collides with a data point near the threshold or with the
        # per-relationship BORDERLINE labels added below.
        ax.text(n_res * 0.62, 0.735, "power = 0.80 target", fontsize=8.8, color="black")

        ax.set_title(f"{sysname} (n={n_res} relationships)", fontsize=12.5, pad=10)
        ax.set_xlabel("Relationships (sorted by power)", fontsize=10)
        ax.set_ylim(-0.08, 1.12)
        ax.set_xlim(-n_res * 0.06 - 1, n_res + n_res * 0.06)
        ax.grid(alpha=0.25, zorder=1)
        ax.tick_params(labelsize=9)

        # Directly label every BORDERLINE point with its relationship name,
        # offset with a leader line so the label never sits on the marker
        # or on top of another label.
        borderline_pts = [(x, y, name) for x, (name, y, dec) in zip(xs, results) if dec == "BORDERLINE"]
        for j, (x, y, name) in enumerate(borderline_pts):
            ax.annotate(
                name,
                xy=(x, y),
                xytext=(x + max(1.5, n_res * 0.05), y + 0.10 + j * 0.12),
                fontsize=8.3,
                color="#8a5a00",
                fontweight="bold",
                arrowprops=dict(arrowstyle="-", color="#8a5a00", lw=0.9),
                ha="left",
                va="center",
                zorder=4,
            )

    axes[0].set_ylabel("Post-hoc statistical power", fontsize=11)

    handles = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markeredgecolor='black',
                   markersize=9, label=lbl)
        for lbl, c in COLORS.items()
    ]
    fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.06), frameon=False, fontsize=10.5)
    fig.suptitle("Post-hoc statistical power per relationship (Equation 5.1, n=10 repeated runs)", y=1.13, fontsize=13.5)
    plt.tight_layout()

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    plt.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
