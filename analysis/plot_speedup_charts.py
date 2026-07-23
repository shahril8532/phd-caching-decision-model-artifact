"""
Regenerate the cold-access-time vs caching-speedup scatter charts (per system,
and all three systems combined) directly from the raw repeated-measures
benchmark CSVs in ../data/<System>/benchmark_run_*.csv.

These charts already appear in the thesis (Chapter 4, and inside the
*_Phase2_Aggregated_Analysis.xlsx workbooks), built at the time from the same
underlying data. This script exists purely so an examiner or reader can
regenerate them independently, without needing Excel or the original
matplotlib session, as part of this artifact's reproducibility guarantee.

Each relationship is classified using the exact same Equation 5.1 one-sample
t-test decision rule as analysis/decision_rule.py (CACHE / DO_NOT_CACHE /
BORDERLINE), so the colours in these charts are consistent with that script's
output and with the thesis's Chapter 5 decision table.

Usage:
    python3 plot_speedup_charts.py                  # writes all 4 charts to ../figures/
    python3 plot_speedup_charts.py --system iTeams   # just one system

Requires: matplotlib (pip install matplotlib), and optionally scipy for exact
p-values (falls back to decision_rule.py's pure-Python approximation).
"""
import argparse
import math
import os
import sys

# Reuse the exact same t-test / decision-rule implementation as decision_rule.py
# so chart colours can never drift out of sync with the published decision table.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decision_rule import load_runs, one_tailed_p_from_t  # noqa: E402

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SYSTEMS = ["iTeams", "Khairat", "VBS"]
COLORS = {"CACHE": "#2ca02c", "DO_NOT_CACHE": "#d62728", "BORDERLINE": "#ff7f0e"}
LABELS = {"CACHE": "CACHE", "DO_NOT_CACHE": "DO_NOT_CACHE", "BORDERLINE": "BORDERLINE"}
MARKERS = {"iTeams": "o", "Khairat": "s", "VBS": "^"}


def classify(data_dir):
    """Return list of dicts: name, cold_mean, speedup_mean, decision."""
    from collections import defaultdict
    rows, _ = load_runs(data_dir)
    by_rel = defaultdict(lambda: {"speedup": [], "cold": []})
    for row in rows:
        key = (row["model"], row["method"])
        by_rel[key]["speedup"].append(float(row["speedup_pct"]))
        by_rel[key]["cold"].append(float(row["avg_cold_ms"]))

    out = []
    for (model, method), v in sorted(by_rel.items()):
        speedups = v["speedup"]
        n = len(speedups)
        mean = sum(speedups) / n
        cold_mean = sum(v["cold"]) / len(v["cold"])
        if n > 1:
            var = sum((x - mean) ** 2 for x in speedups) / (n - 1)
            sd = math.sqrt(var)
        else:
            sd = 0.0
        if sd == 0:
            t_stat = float("inf") if mean != 0 else 0.0
            p = 0.0 if mean != 0 else 1.0
        else:
            t_stat = mean / (sd / math.sqrt(n))
            p = one_tailed_p_from_t(t_stat, n - 1)

        if p < 0.05 and mean > 0:
            decision = "CACHE"
        elif p < 0.05 and mean < 0:
            decision = "DO_NOT_CACHE"
        else:
            decision = "BORDERLINE"

        out.append({"name": f"{model}.{method}", "cold_mean": cold_mean,
                     "speedup_mean": mean, "decision": decision})
    return out


def plot_leader_labels(ax, points, x0, y0, y_step, sort_key=None):
    """Place labels for a small cluster of points in a vertical stack with
    leader lines, so nearby points never produce overlapping text (this is
    the fix for the label-overlap bug found in the original workbook charts,
    where DO_NOT_CACHE/BORDERLINE points sitting close together on a log-x
    axis had their text labels collide)."""
    pts = sorted(points, key=sort_key) if sort_key else points
    for i, p in enumerate(pts):
        ax.annotate(
            p["name"],
            xy=(p["cold_mean"], p["speedup_mean"]),
            xytext=(x0, y0 + i * y_step),
            fontsize=8.5, color="#333333",
            arrowprops=dict(arrowstyle="-", color="#888888", lw=0.7, shrinkA=3, shrinkB=5),
            va="center", ha="left", zorder=4,
        )


def plot_system(system, data_dir, out_path):
    pts = classify(data_dir)

    fig, ax = plt.subplots(figsize=(13.35, 8.10), dpi=100)
    for decision in ["CACHE", "DO_NOT_CACHE", "BORDERLINE"]:
        sub = [p for p in pts if p["decision"] == decision]
        if sub:
            ax.scatter([p["cold_mean"] for p in sub], [p["speedup_mean"] for p in sub],
                       color=COLORS[decision], edgecolor="black", linewidth=0.6, s=70,
                       label=LABELS[decision], zorder=3)

    # Only label the non-CACHE points (small in number, and the ones an examiner
    # will want to identify by name); CACHE points stay unlabeled to avoid clutter.
    to_label = [p for p in pts if p["decision"] != "CACHE"]
    if to_label:
        xs = [p["cold_mean"] for p in to_label]
        x0 = min(xs) * 1.35
        plot_leader_labels(ax, to_label, x0=x0, y0=-8, y_step=-11,
                            sort_key=lambda p: p["cold_mean"])

    ax.axhline(0, color="gray", linestyle="--", linewidth=1, zorder=1)
    ax.set_xscale("log")
    ax.set_xlabel("Cold Access Time - mean of 10 runs (ms, log scale)")
    ax.set_ylabel("Speedup (%) - mean of 10 runs")
    ax.set_title(f"{system}: Cold Access Time vs Caching Speedup "
                 f"(n={len(pts)} relationships, Equation 5.1 decision, 10 runs each)",
                 fontweight="bold")
    ax.grid(True, which="both", linestyle=":", linewidth=0.5, alpha=0.6)
    ax.legend(loc="lower right", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    print(f"wrote {out_path}  ({len(pts)} relationships, "
          f"{sum(1 for p in pts if p['decision']=='CACHE')} CACHE / "
          f"{sum(1 for p in pts if p['decision']=='DO_NOT_CACHE')} DO_NOT_CACHE / "
          f"{sum(1 for p in pts if p['decision']=='BORDERLINE')} BORDERLINE)")


def plot_combined(all_pts_by_system, out_path):
    fig, ax = plt.subplots(figsize=(14.85, 8.85), dpi=100)
    for system in SYSTEMS:
        pts = all_pts_by_system[system]
        colors = [COLORS[p["decision"]] for p in pts]
        ax.scatter([p["cold_mean"] for p in pts], [p["speedup_mean"] for p in pts],
                   c=colors, marker=MARKERS[system], edgecolor="black", linewidth=0.6,
                   s=70, label=f"{system} (n={len(pts)})", zorder=3)

    ax.axhline(0, color="gray", linestyle="--", linewidth=1, zorder=1)
    ax.set_xscale("log")
    ax.set_xlabel("Cold Access Time, mean of 10 runs (ms, log scale)")
    ax.set_ylabel("Speedup (%)")
    ax.set_title("Cold Access Time (log scale) vs Speedup % - iTeams, Khairat, and VBS combined\n"
                 "(marker shape = system, colour = Equation 5.1 decision: green=CACHE, red=DO_NOT_CACHE, orange=BORDERLINE)",
                 fontweight="bold", fontsize=11)
    ax.grid(True, which="both", linestyle=":", linewidth=0.5, alpha=0.6)
    ax.legend(loc="lower right", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    print(f"wrote {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=SYSTEMS, default=None,
                         help="Only regenerate this system's chart (default: all + combined)")
    parser.add_argument("--data-root", default="../data")
    parser.add_argument("--out-dir", default="../figures")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    systems = [args.system] if args.system else SYSTEMS

    all_pts = {}
    for system in systems:
        data_dir = os.path.join(args.data_root, system)
        out_path = os.path.join(args.out_dir, f"speedup_chart_{system.lower()}.png")
        pts = classify(data_dir)
        all_pts[system] = pts
        plot_system(system, data_dir, out_path)

    if not args.system:
        combined_out = os.path.join(args.out_dir, "speedup_chart_combined.png")
        plot_combined(all_pts, combined_out)


if __name__ == "__main__":
    main()
