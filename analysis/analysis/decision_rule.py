"""
Independent Python re-implementation of Equation 5.1 (the caching decision
rule) from:

  Shahril bin Mohd Isa, "A Decision Model for Determining What to Cache in
  ORM-Based Database Applications: Balancing Performance and Resource Cost"
  (PhD thesis / proposal, Universiti Teknikal Malaysia Melaka)

This script is provided so the t-test based decision rule can be verified
independently of the Excel workbooks (openpyxl formulas + LibreOffice
recalculation) used in the thesis itself. It reads the raw per-run
benchmark CSVs in ../data/<System>/benchmark_run_*.csv, aggregates the
per-relationship speedup percentage across the 10 repeated runs, and
applies a one-sample t-test (H0: mean speedup == 0) exactly as described
in thesis Section 5.2.2 / Equation 5.1:

    t = mean(speedup) / (stdev(speedup) / sqrt(n))

Decision rule (one-tailed, alpha = 0.05):
    p < 0.05 and mean(speedup) > 0  -> CACHE
    p < 0.05 and mean(speedup) < 0  -> DO_NOT_CACHE
    otherwise                       -> BORDERLINE

Usage:
    python3 decision_rule.py ../data/iTeams
    python3 decision_rule.py ../data/Khairat
    python3 decision_rule.py ../data/VBS

Requires: Python 3.8+, and either scipy (preferred, for an exact t
distribution p-value) or falls back to a pure-Python approximation if
scipy is not installed.
"""

import csv
import glob
import math
import os
import sys
from collections import defaultdict

try:
    from scipy import stats as _scipy_stats
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False


def one_tailed_p_from_t(t: float, df: int) -> float:
    """One-tailed p-value for a t-statistic with df degrees of freedom."""
    if HAVE_SCIPY:
        return float(_scipy_stats.t.sf(abs(t), df))
    # Fallback: crude numerical integration of the t-distribution PDF.
    # Good enough to cross-check the Excel/TDIST result to ~3 decimals.
    def t_pdf(x, v):
        coeff = math.gamma((v + 1) / 2) / (math.sqrt(v * math.pi) * math.gamma(v / 2))
        return coeff * (1 + x * x / v) ** (-(v + 1) / 2)
    hi = abs(t)
    n_steps = 20000
    upper_bound = hi + 50
    step = (upper_bound - hi) / n_steps
    area = 0.0
    x = hi
    for _ in range(n_steps):
        area += t_pdf(x, df) * step
        x += step
    return area


def load_runs(data_dir: str):
    """Load all benchmark_run_*.csv files in data_dir; return list of dict rows."""
    pattern = os.path.join(data_dir, "*run*[0-9].csv")
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No benchmark_run_*.csv files found in {data_dir}")
    all_rows = []
    for fp in files:
        with open(fp, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_rows.append(row)
    return all_rows, files


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    data_dir = sys.argv[1]
    rows, files = load_runs(data_dir)
    print(f"Loaded {len(rows)} rows from {len(files)} run files in {data_dir}\n")

    by_relationship = defaultdict(list)
    for row in rows:
        key = (row["model"], row["method"], row["type"])
        by_relationship[key].append(float(row["speedup_pct"]))

    header = f"{'model':20}{'method':16}{'type':14}{'n':4}{'mean%':>9}{'sd':>9}{'t':>9}{'p':>10}  decision"
    print(header)
    print("-" * len(header))

    agree_count = 0
    total = 0
    for (model, method, rtype), speedups in sorted(by_relationship.items()):
        n = len(speedups)
        mean = sum(speedups) / n
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

        total += 1
        print(f"{model:20}{method:16}{rtype:14}{n:<4}{mean:>9.2f}{sd:>9.2f}{t_stat:>9.3f}{p:>10.4f}  {decision}")

    print(f"\n{total} relationships evaluated using Equation 5.1 (one-sample t-test, alpha=0.05, one-tailed).")
    print("Cross-check these decisions against the *_Phase2_Aggregated_Analysis.xlsx")
    print("'Aggregated Analysis' sheet (columns O-R) from the main thesis repository.")


if __name__ == "__main__":
    main()
