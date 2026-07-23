"""
Post-hoc statistical power analysis for the Equation 5.1 one-sample t-test
decision rule, computed the same way G*Power computes power for a
"t tests - Means: Difference from constant (one sample case)" design.

This directly addresses the small-sample-size limitation acknowledged in
the thesis (Section 3.8 / 6.5): with n = 10 repeated runs per relationship,
how much statistical power did each relationship's t-test actually have to
detect the effect size that was observed? A BORDERLINE classification with
low power is a genuine "inconclusive" result; a CACHE/DO_NOT_CACHE
classification with high power is a well-supported decision, not an
artifact of a lucky/unlucky small sample.

Usage:
    python3 power_analysis.py ../data/iTeams
    python3 power_analysis.py ../data/Khairat
    python3 power_analysis.py ../data/VBS

Requires: statsmodels (pip install statsmodels)
"""

import csv
import glob
import math
import os
import sys
from collections import defaultdict

from statsmodels.stats.power import TTestPower

ALPHA = 0.05
POWER_TARGET = 0.80


def load_runs(data_dir: str):
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
    return all_rows


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    data_dir = sys.argv[1]
    rows = load_runs(data_dir)

    by_relationship = defaultdict(list)
    for row in rows:
        key = (row["model"], row["method"], row["type"])
        by_relationship[key].append(float(row["speedup_pct"]))

    analysis = TTestPower()

    header = (
        f"{'model':20}{'method':16}{'type':14}{'n':4}{'cohens_d':>10}"
        f"{'power':>9}{'n_for_80%':>11}  decision"
    )
    print(header)
    print("-" * len(header))

    underpowered = []
    for (model, method, rtype), speedups in sorted(by_relationship.items()):
        n = len(speedups)
        mean = sum(speedups) / n
        var = sum((x - mean) ** 2 for x in speedups) / (n - 1) if n > 1 else 0
        sd = math.sqrt(var)
        if sd == 0:
            continue
        d = mean / sd  # Cohen's d for one-sample t-test

        power = analysis.power(effect_size=abs(d), nobs=n, alpha=ALPHA, alternative="larger")

        try:
            n_needed = analysis.solve_power(
                effect_size=abs(d), power=POWER_TARGET, alpha=ALPHA, alternative="larger"
            )
            n_needed_str = f"{n_needed:.1f}"
        except Exception:
            n_needed_str = "n/a"

        # one-tailed t-test decision, matching decision_rule.py / Equation 5.1
        t_stat = mean / (sd / math.sqrt(n))
        from scipy import stats as scipy_stats
        p = float(scipy_stats.t.sf(abs(t_stat), n - 1))
        if p < ALPHA and mean > 0:
            decision = "CACHE"
        elif p < ALPHA and mean < 0:
            decision = "DO_NOT_CACHE"
        else:
            decision = "BORDERLINE"

        if power < POWER_TARGET:
            underpowered.append((model, method, rtype, power, decision))

        print(
            f"{model:20}{method:16}{rtype:14}{n:<4}{d:>10.2f}"
            f"{power:>9.3f}{n_needed_str:>11}  {decision}"
        )

    print(f"\n{len(by_relationship)} relationships analysed. Target power = {POWER_TARGET}, alpha = {ALPHA} (one-tailed).")
    if underpowered:
        print(f"\n{len(underpowered)} relationship(s) below {POWER_TARGET} power:")
        for model, method, rtype, power, decision in underpowered:
            print(f"  {model}.{method} ({rtype}): power={power:.3f}, decision={decision}")
    else:
        print(f"\nAll relationships achieved >= {POWER_TARGET} power at n=10 given their observed effect size.")


if __name__ == "__main__":
    main()
