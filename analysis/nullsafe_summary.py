"""Summarise the null-safe confirmation experiment (thesis Section 4.4.4).

Reads data/nullsafe/nullsafe_*.csv (produced by code/nullsafe/BenchmarkNullSafe.php)
and reports, per relationship, the speedup under Cache::remember() and under the
null-safe variant, with a Wilcoxon signed-rank test over the ten paired runs.
Usage:  python3 analysis/nullsafe_summary.py
"""
import csv, glob, os
from collections import defaultdict
import numpy as np
from scipy import stats
from common import DATA

rows = []
for fp in sorted(glob.glob(os.path.join(DATA, 'nullsafe', 'nullsafe_*.csv'))):
    sysname = os.path.basename(fp)[9:-4]
    with open(fp, newline='') as f:
        for r in csv.DictReader(f):
            r['system'] = sysname; rows.append(r)
g = defaultdict(list)
for r in rows:
    g[(r['system'], r['model'] + '.' + r['method'])].append(r)
print(f"{'system':8} {'relationship':28} {'samples':>7} {'null':>6} {'remember %':>11} {'neg runs':>8} {'null-safe %':>12} {'min':>6} {'q warm R/N':>11} {'Wilcoxon p':>10}")
neg_total = runs_total = 0
for (s, rel), rs in g.items():
    R = np.array([float(r['speedup_remember_pct']) for r in rs]); N = np.array([float(r['speedup_nullsafe_pct']) for r in rs])
    null = np.mean([float(r['null_share']) for r in rs])
    qr = np.mean([float(r['q_warm_remember']) for r in rs]); qn = np.mean([float(r['q_warm_nullsafe']) for r in rs])
    p = stats.wilcoxon(N, R)[1]
    if null >= 0.99:
        neg_total += int((R < 0).sum()); runs_total += len(R)
    print(f"{s:8} {rel:28} {int(float(rs[0]['samples'])):7d} {null:6.3f} {R.mean():11.1f} {int((R<0).sum()):8d} {N.mean():12.1f} {N.min():6.1f} {qr:5.2f}/{qn:4.2f} {p:10.4f}")
print(f"\nRelationships resolving to null for (almost) all records: Cache::remember() slower than cold in {neg_total} of {runs_total} runs")
