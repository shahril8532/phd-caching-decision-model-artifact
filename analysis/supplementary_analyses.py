"""Supplementary analyses added in artifact v1.4.1 (thesis v66 onward, Section 4.6.3 and 4.7).
Read-only on archived artifact v1.4.0 data. No benchmark is re-run.
A: all 115 relationships (no post-hoc exclusion) vs 111.
B: null-share rule vs Equation 4.1, incl. leave-one-system-out threshold.
C: 95% CIs of mean speedup (BORDERLINE and narrowest CACHE).
D: relationships measured on few records.
"""
import sys, collections, math
import os
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats
from common import load, SYSTEMS
out = []
P = lambda *a: out.append(' '.join(str(x) for x in a))

def table49(R):
    ks = list(R); none = sum(R[k]['cold'] for k in ks)
    w = lambda k: R[k]['cold'] * (1 - R[k]['mean'] / 100)
    naive = sum(w(k) for k in ks); model = sum(w(k) if R[k]['cls'] == 'CACHE' else R[k]['cold'] for k in ks)
    return none, naive, model

P('=== A. With vs without the four post-hoc exclusions (iTeams) ===')
for ex in (True, False):
    tot = collections.Counter(); agree = n = 0
    for s in SYSTEMS:
        R = load(s, exclude=ex)
        tot.update(v['cls'] for v in R.values()); n += len(R)
        agree += sum({'CW': 'CACHE', 'NCW': 'DO_NOT_CACHE', 'UNST': 'BORDERLINE'}[v['sign']] == v['cls'] for v in R.values())
        if s == 'iTeams':
            none, naive, model = table49(R)
            P(f"  exclude={ex}: iTeams n={len(R)} {dict(collections.Counter(v['cls'] for v in R.values()))}; "
              f"Table4.9 none {none:.3f} naive {naive:.3f} model {model:.3f} improvement {naive-model:.3f} ms ({100*(naive-model)/naive:.2f}%)")
            if not ex:
                for k in sorted(R):
                    v = R[k]
                    if v['cls'] != 'CACHE' or v['sign'] != 'CW':
                        P(f"     {k:28} {v['cls']:12} sign {v['sign']:4} mean {v['mean']:7.2f} p {v['p']:.2g} null {v['null_share']:.3f} samples {v['samples']:.0f}")
    P(f"  exclude={ex}: all systems n={n} {dict(tot)}; Eq4.1 vs sign agreement {agree}/{n}")

P('\n=== B. Null-share rule vs Equation 4.1 (111 relationships) ===')
A = {}
for s in SYSTEMS:
    for k, v in load(s).items(): A[(s, k)] = v
def rule(v, tau): return 'DO_NOT_CACHE' if v['null_share'] >= tau else 'CACHE'
dec = {k: v for k, v in A.items() if v['cls'] != 'BORDERLINE'}
for tau in (0.5, 0.8, 0.9, 0.95, 0.99, 1.0 - 1e-9):
    ag = sum(rule(v, tau) == v['cls'] for v in dec.values())
    P(f"  tau={tau:.3f}: agreement with Eq4.1 on its {len(dec)} decisive cases {ag}/{len(dec)}; "
      f"BORDERLINE cases called DNC: {sum(rule(v,tau)=='DO_NOT_CACHE' for v in A.values() if v['cls']=='BORDERLINE')}/2")
P('  partly-null relationships (0<null<1): null share, speedup, class')
for k, v in sorted(A.items(), key=lambda kv: -kv[1]['null_share']):
    if 0 < v['null_share'] < 1 - 1e-9:
        P(f"     {k[0]:8} {k[1]:28} null {v['null_share']:.3f} speedup {v['mean']:7.2f} {v['cls']}")
P('  leave-one-system-out: tau chosen on two systems (grid 0.05..1.00), tested on the third')
grid = np.round(np.arange(0.05, 1.0001, 0.05), 2)
for test in SYSTEMS:
    train = {k: v for k, v in dec.items() if k[0] != test}; tst = {k: v for k, v in dec.items() if k[0] == test}
    best = max(grid, key=lambda t: (sum(rule(v, t - 1e-9) == v['cls'] for v in train.values()), -abs(t - 0.5)))
    ok = [t for t in grid if sum(rule(v, t - 1e-9) == v['cls'] for v in train.values()) == len(train)]
    acc = sum(rule(v, best - 1e-9) == v['cls'] for v in tst.values())
    P(f"     test {test:8}: perfect-on-train tau range {min(ok) if ok else None}-{max(ok) if ok else None}; chosen {best}; test agreement {acc}/{len(tst)}")
P('  Does Eq4.1 add any decision the null rule (tau=1, i.e. all sampled records null) misses?')
for k, v in A.items():
    r = rule(v, 1 - 1e-9)
    if v['cls'] != r: P(f"     differs: {k[0]} {k[1]} Eq4.1={v['cls']} null-rule={r} null={v['null_share']:.3f} mean={v['mean']:.2f}")

P('\n=== C. 95% confidence intervals of mean speedup (t, df=9) ===')
def ci(v):
    h = stats.t.ppf(0.975, v['n'] - 1) * v['sd'] / math.sqrt(v['n']); return v['mean'] - h, v['mean'] + h
for k, v in A.items():
    if v['cls'] == 'BORDERLINE':
        lo, hi = ci(v); P(f"  BORDERLINE {k[0]} {k[1]}: mean {v['mean']:.2f}% 95% CI [{lo:.1f}, {hi:.1f}] samples {v['samples']:.0f}")
cach = sorted([(v['mean'], k, ci(v)) for k, v in A.items() if v['cls'] == 'CACHE'])[:5]
for m, k, (lo, hi) in cach: P(f"  narrowest CACHE {k[0]} {k[1]}: mean {m:.2f}% CI [{lo:.1f}, {hi:.1f}]")
P(f"  CACHE relationships whose CI lower bound < 10%: {sum(ci(v)[0] < 10 for v in A.values() if v['cls']=='CACHE')}; < 20%: {sum(ci(v)[0] < 20 for v in A.values() if v['cls']=='CACHE')}")

P('\n=== D. Relationships measured on few records ===')
for th in (5, 10, 30):
    sel = [v for v in A.values() if v['samples'] < th]
    P(f"  samples < {th}: {len(sel)} relationships; classes {dict(collections.Counter(v['cls'] for v in sel))}")
sel = [v for v in A.values() if v['samples'] >= 10]
x = [v['cold'] for v in sel if v['system'] == 'Khairat']; y = [v['mean'] for v in sel if v['system'] == 'Khairat']
P(f"  Khairat Spearman(cold, speedup) with samples>=10: n={len(x)} rho={stats.spearmanr(x, y)[0]:.3f} p={stats.spearmanr(x, y)[1]:.3f}")
x = [v['cold'] for v in A.values() if v['system'] == 'Khairat']; y = [v['mean'] for v in A.values() if v['system'] == 'Khairat']
P(f"  Khairat Spearman(cold, speedup) all: n={len(x)} rho={stats.spearmanr(x, y)[0]:.3f}")
print('\n'.join(out))
