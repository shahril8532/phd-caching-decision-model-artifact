"""Shared loader for the reproducibility scripts (thesis v44, artifact v1.4.0).

Reads the raw per-run CSVs in data/<System>/benchmark_run_*.csv, the static
relationship inventories (eager-load and write-operation counts), and the list
of excluded non-functional relationships, and aggregates every relationship
over its ten repeated runs.
"""
import csv, glob, math, os
from collections import defaultdict
import numpy as np
from scipy import stats

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'data')
SYSTEMS = ['iTeams', 'Khairat', 'VBS']
INVENTORY = {
    'iTeams': ('iTeams_relationship_inventory.csv', 'Method Name', 'Eager-Load Hits'),
    'Khairat': ('Khairat_relationship_inventory.csv', 'Method', 'Eager-Load Hits (codebase-wide)'),
    'VBS': ('VBS_relationship_inventory.csv', 'Method Name', 'Eager-Load Hits'),
}
ALPHA = 0.05


def excluded():
    with open(os.path.join(DATA, 'excluded_relationships.csv'), newline='', encoding='utf-8') as f:
        return {(r['system'], r['relationship']) for r in csv.DictReader(f)}


def inventory(system):
    fn, mcol, ecol = INVENTORY[system]
    out = {}
    with open(os.path.join(DATA, 'relationship_inventories', fn), newline='', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if not r.get('Relationship Type'):
                continue  # note rows
            key = r['Source Model'] + '.' + r[mcol]
            out[key] = (float(r[ecol] or 0), float(r['Write Ops Hits (related model)'] or 0))
    return out


def classify(r):
    """Equation 4.1: two-tailed one-sample t-test on the repeated speedups."""
    if r['p'] < ALPHA and r['mean'] > 0:
        return 'CACHE'
    if r['p'] < ALPHA and r['mean'] < 0:
        return 'DO_NOT_CACHE'
    return 'BORDERLINE'


def eager_counts(system):
    """Model-attributed eager-load counts (artifact v1.4.0): every with()/load()/loadMissing() call in the
    application's own code (app/, routes/, resources/views/) attributed to the model on which it is made.
    The name-based counts used up to v1.3.0 are kept in the relationship inventories for comparison."""
    out = {}
    with open(os.path.join(DATA, 'eager_load', 'eager_load_counts.csv'), newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['system'] == system:
                out[r['relationship']] = (float(r['eager_model_attributed']), float(r['eager_name_based_scan']))
    return out


def load(system, exclude=True):
    files = sorted(glob.glob(os.path.join(DATA, system, '*run*[0-9].csv')))
    by = defaultdict(lambda: defaultdict(list))
    types = {}
    for fp in files:
        with open(fp, newline='') as f:
            for row in csv.DictReader(f):
                k = row['model'] + '.' + row['method']
                types[k] = row['type']
                for c in ['avg_cold_ms', 'avg_warm_ms', 'speedup_pct', 'avg_query_count_cold',
                          'avg_query_count_warm', 'avg_cache_write_overhead_ms', 'samples']:
                    by[k][c].append(float(row[c]))
    inv = inventory(system)
    eag = eager_counts(system)
    ex = excluded() if exclude else set()
    rels = {}
    for k, v in by.items():
        if (system, k) in ex:
            continue
        sp = np.array(v['speedup_pct']); n = len(sp); m = sp.mean(); sd = sp.std(ddof=1)
        t = m / (sd / math.sqrt(n)); p = 2 * stats.t.sf(abs(t), n - 1)
        qc = np.array(v['avg_query_count_cold']); qw = np.array(v['avg_query_count_warm'])
        r = dict(system=system, rel=k, type=types[k], n=n, sp=sp, mean=m, sd=sd, t=t, p=p, d=m / sd,
                 cold=np.mean(v['avg_cold_ms']), warm=np.mean(v['avg_warm_ms']),
                 write=np.mean(v['avg_cache_write_overhead_ms']), samples=np.mean(v['samples']),
                 qc=qc.mean(), qw=qw.mean(),
                 # share of sampled records resolving to null (thesis Section 4.4.4):
                 # a record returning data costs 2 queries cold and 0 warm; a null result
                 # costs the same number of queries cold and warm.
                 null_share=float(np.mean(1 - (qc - qw) / 2)),
                 eager=eag[k][0], eager_name=inv.get(k, (0, 0))[0], wr=inv.get(k, (0, 0))[1],
                 sign='CW' if sp.min() > 0 else 'NCW' if sp.max() < 0 else 'UNST')
        r['cls'] = classify(r)
        rels[k] = r
    return rels
