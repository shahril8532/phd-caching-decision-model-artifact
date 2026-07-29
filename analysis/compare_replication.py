#!/usr/bin/env python3
"""
compare_replication.py

Compares the original measurement campaign against the replication campaign
and reports how often the decision rule (Equation 5.1) returns the same
classification for the same relationship.

Reads, relative to this file:
    ../data/<System>/benchmark_run_*.csv          original campaign  (10 runs)
    ../data/<System>/rerun/benchmark_runNN.csv    replication        (10 runs)

Filename patterns are deliberately strict so that stray files (for example a
single-run smoke test named benchmark_run1.csv) are not counted as a run.

Writes nothing. Run from anywhere:
    python3 analysis/compare_replication.py

Requires: numpy, scipy
"""
import csv, glob, os, sys
import numpy as np
from scipy import stats

ALPHA = 0.05
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, '..', 'data'))
SYSTEMS = ['iTeams', 'Khairat', 'VBS']


def classify(speedups):
    """Equation 5.1: one-sample t-test on a relationship's own speedup measurements."""
    x = np.asarray(speedups, dtype=float)
    n = x.size
    mean, sd = x.mean(), x.std(ddof=1)
    if sd == 0:
        return ('CACHE' if mean > 0 else 'DO_NOT_CACHE'), mean, sd, float('inf'), 0.0
    t = mean / (sd / np.sqrt(n))
    p = stats.t.sf(abs(t), n - 1)          # one-tailed, direction of observed mean
    if p < ALPHA and mean > 0:   d = 'CACHE'
    elif p < ALPHA and mean < 0: d = 'DO_NOT_CACHE'
    else:                        d = 'BORDERLINE'
    return d, mean, sd, t, p


def load(pattern):
    """Aggregate speedup_pct and avg_cold_ms per relationship across run files."""
    files = sorted(f for f in glob.glob(pattern)
                   if 'benchmark_result' not in os.path.basename(f))
    out = {}
    for f in files:
        with open(f, newline='', encoding='utf-8-sig') as fh:
            for row in csv.DictReader(fh):
                key = f"{row['model']}.{row['method']}"
                rec = out.setdefault(key, {'sp': [], 'cold': [], 'type': row.get('type', '')})
                rec['sp'].append(float(row['speedup_pct']))
                rec['cold'].append(float(row['avg_cold_ms']))
    return out, len(files)


def main():
    total_agree = total_n = 0
    changed = []
    print('=' * 78)
    print('REPLICATION AGREEMENT  --  decision rule (Eq. 5.1) applied to both campaigns')
    print('=' * 78)

    for system in SYSTEMS:
        orig, n_o = load(os.path.join(DATA, system, 'benchmark_run_*.csv'))
        rep,  n_r = load(os.path.join(DATA, system, 'rerun',
                                      'benchmark_run[0-9][0-9].csv'))
        for label, count in (('original', n_o), ('replication', n_r)):
            if count != 10:
                print(f"  WARNING [{system}] expected 10 {label} run files, found {count}")
        if not orig or not rep:
            print(f"\n{system}: data missing "
                  f"(original files {n_o}, replication files {n_r}) -- skipped")
            continue

        shared = [k for k in orig if k in rep and len(rep[k]['sp']) >= 3]
        agree = 0
        for k in shared:
            d_o = classify(orig[k]['sp'])[0]
            d_r, m_r, _, _, p_r = classify(rep[k]['sp'])
            if d_o == d_r:
                agree += 1
            else:
                changed.append((system, k, d_o, d_r,
                                classify(orig[k]['sp'])[1], m_r, p_r))
        total_agree += agree
        total_n += len(shared)

        c_o = np.mean([np.mean(orig[k]['cold']) for k in shared])
        c_r = np.mean([np.mean(rep[k]['cold'])  for k in shared])
        s_o = np.mean([np.mean(orig[k]['sp'])   for k in shared])
        s_r = np.mean([np.mean(rep[k]['sp'])    for k in shared])

        print(f"\n{system}  ({n_o} original runs, {n_r} replication runs)")
        print(f"  relationships compared : {len(shared)}")
        print(f"  agreement              : {agree}/{len(shared)} = {agree/len(shared)*100:.1f}%")
        print(f"  mean cold access (ms)  : {c_o:.3f} -> {c_r:.3f}  ({(c_r/c_o-1)*100:+.1f}%)")
        print(f"  mean speedup (%)       : {s_o:.1f} -> {s_r:.1f}")

    if total_n == 0:
        print('\nNo data found. Expected ../data/<System>/ and ../data/<System>/rerun/')
        return 1

    print('\n' + '-' * 78)
    print(f"OVERALL AGREEMENT: {total_agree}/{total_n} = {total_agree/total_n*100:.1f}%")
    print('-' * 78)
    if changed:
        print('\nClassifications that changed:')
        for sysname, k, a, b, m_o, m_r, p_r in changed:
            print(f"  {sysname:8s} {k:28s} {a} -> {b}")
            print(f"           mean speedup {m_o:+.2f}% -> {m_r:+.2f}%   (p = {p_r:.4f})")
    else:
        print('\nNo classification changed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
