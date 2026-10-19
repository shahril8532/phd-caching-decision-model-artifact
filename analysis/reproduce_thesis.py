"""Reproduce every statistic reported in Chapter 4 of the thesis from the raw CSVs (artifact v1.4.0, thesis v44).

Eager-load frequency is the model-attributed count in data/eager_load/eager_load_counts.csv
(see analysis/eager_load_scan.py and PROVENANCE.md); the name-based count used up to v1.3.0
is printed alongside it for comparison.

Usage:  python3 analysis/reproduce_thesis.py
Output is grouped by thesis section/table so each number can be checked directly.
"""
import collections, warnings
import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.model_selection import LeaveOneOut, RepeatedKFold, cross_val_predict, cross_val_score
from statsmodels.stats.power import TTestPower
from common import load, SYSTEMS
warnings.filterwarnings('ignore')

ALL = {}
print('=' * 78)
for s in SYSTEMS:
    R = load(s); ALL.update({(s, k): v for k, v in R.items()})
    ks = sorted(R); C = np.array([R[k]['cold'] for k in ks]); S = np.array([R[k]['mean'] for k in ks])
    sign = collections.Counter(R[k]['sign'] for k in ks); rule = collections.Counter(R[k]['cls'] for k in ks)
    agree = sum({'CW': 'CACHE', 'NCW': 'DO_NOT_CACHE', 'UNST': 'BORDERLINE'}[R[k]['sign']] == R[k]['cls'] for k in ks)
    pr = stats.pearsonr(C, S); sr = stats.spearmanr(C, S)
    print(f'\n### {s}: n = {len(ks)} relationships (after exclusions)')
    print(f'Section 4.3  sign-consistency: {dict(sign)}   cold range {C.min():.3f}-{C.max():.3f} ms')
    import csv, os
    from common import DATA
    decl = [r for r in csv.DictReader(open(os.path.join(DATA, 'eager_load', 'eager_load_counts.csv'))) if r['system'] == s]
    z_decl = sum(int(r['eager_model_attributed']) == 0 for r in decl); z_an = sum(R[k]['eager'] == 0 for k in ks)
    print(f'Section 4.2  eager-loaded nowhere: {z_decl} of {len(decl)} inventoried relationships ({100*z_decl/len(decl):.1f}%); '
          f'{z_an} of {len(ks)} analysed ({100*z_an/len(ks):.1f}%)   [name-based scan: '
          f'{sum(int(r["eager_name_based_scan"]) == 0 for r in decl)} of {len(decl)}]')
    print(f'             relationships with fewer than 30 sampled records: {sum(R[k]["samples"] < 30 for k in ks)}')
    print(f'Table 4.4    Pearson r = {pr[0]:.3f} (p = {pr[1]:.4f}); Spearman rho = {sr[0]:.3f} (p = {sr[1]:.4f})')
    y = (S > 0).astype(int); minority = min(y.sum(), len(y) - y.sum())
    if minority < 2:
        print(f'Table 4.5    LOOCV not possible (minority class size {minority}); majority baseline {100*max(y.mean(),1-y.mean()):.2f}%')
    else:
        for name, X in [('cold only', C.reshape(-1, 1)),
                        ('multivariate', np.column_stack([C, [R[k]['eager'] for k in ks], [R[k]['wr'] for k in ks]]))]:
            pred = cross_val_predict(LogisticRegression(penalty='l2', C=1.0, max_iter=1000), X, y, cv=LeaveOneOut())
            print(f'Table 4.5    LOOCV {name}: {100*(pred==y).mean():.2f}% vs baseline {100*max(y.mean(),1-y.mean()):.2f}%; '
                  f'minority identified {int(((pred==0)&(y==0)).sum())} of {int((y==0).sum())}; '
                  f'majority cases predicted as minority {int(((pred==0)&(y==1)).sum())}')
    if len(set(y)) > 1:
        for name, X in [('cold only', C.reshape(-1, 1)),
                        ('multivariate', np.column_stack([C, [R[k]['eager'] for k in ks], [R[k]['wr'] for k in ks]]))]:
            r2 = LinearRegression().fit(X, S).score(X, S)
            cv = cross_val_score(LinearRegression(), X, S, cv=RepeatedKFold(n_splits=10, n_repeats=10, random_state=0), scoring='r2')
            print(f'Sec 4.4.3    OLS {name}: in-sample R2 = {r2:.3f}; median CV R2 over 100 folds = {np.median(cv):.1f}')
    print(f'Table 4.7    Equation 4.1: {dict(rule)}; agreement with sign-consistency {agree}/{len(ks)}')
    sa = sum((R[k]['cold'] > R[k]['write']) == (R[k]['cls'] == 'CACHE') for k in ks)
    print(f'Sec 4.8      single-access rule (cold > write overhead) correct {sa}/{len(ks)} ({100*sa/len(ks):.1f}%)')
    print('Table 4.8    amortised rule agreement: ' + '; '.join(
        f'N={N}: {sum((R[k]["write"] < N*(R[k]["cold"]-R[k]["warm"])) == (R[k]["cls"]=="CACHE") for k in ks)}/{len(ks)}'
        for N in [1, 2, 5, 10, 20, 50, 100]))
    if s == 'iTeams':
        w = np.array([R[k]['write'] for k in ks])
        print(f'Sec 4.8      corr(write overhead, cold) = {np.corrcoef(w, C)[0,1]:.3f}; median(write - cold) = {np.median(w-C):.3f} ms')
    none = C.sum(); warmed = lambda k: R[k]['cold'] * (1 - R[k]['mean'] / 100)
    naive = sum(warmed(k) for k in ks); model = sum(warmed(k) if R[k]['cls'] == 'CACHE' else R[k]['cold'] for k in ks)
    print(f'Table 4.9    no caching {none:.3f} ms; naive {naive:.3f} ms; decision model {model:.3f} ms; '
          f'improvement {naive-model:.3f} ms ({100*(naive-model)/naive:.2f}%)')
    print(f'Sec 4.7.1    Shapiro-Wilk rejects normality for {sum(stats.shapiro(R[k]["sp"])[1] < .05 for k in ks)} relationships')
    wag = 0
    for k in ks:
        pw = stats.wilcoxon(R[k]['sp'])[1]
        wag += ('CACHE' if pw < .05 and R[k]['mean'] > 0 else 'DO_NOT_CACHE' if pw < .05 else 'BORDERLINE') == R[k]['cls']
    print(f'Sec 4.7.1    Wilcoxon signed-rank classification agrees for {wag}/{len(ks)}')
    tm = sum(R[k]['samples'] * (R[k]['cold'] + R[k]['write'] + R[k]['warm']) for k in ks) * 10 / 1000
    print(f'Sec 4.11     measured access time over ten runs: {tm:.0f} s')

A = ALL; N = len(A)
print('\n' + '=' * 78 + f'\n### All systems: {N} relationships  {dict(collections.Counter(v["cls"] for v in A.values()))}')
dnc = sorted([(k, v['p']) for k, v in A.items() if v['cls'] == 'DO_NOT_CACHE'], key=lambda x: x[1])
print(f'Sec 4.7.2    Bonferroni threshold {0.05/N:.2e}; DO_NOT_CACHE p-values: ' + ', '.join(f'{k[1]} {p:.1e}' for k, p in dnc))
ps = sorted(v['p'] for v in A.values()); bh = max([i + 1 for i, p in enumerate(ps) if p <= (i + 1) / N * 0.05] or [0])
print(f'             Benjamini-Hochberg: {bh} of {N} tests significant; all CACHE p below Bonferroni: '
      f'{all(v["p"] < 0.05/N for v in A.values() if v["cls"]=="CACHE")}')
print(f'Sec 4.7      power of a two-tailed one-sample t-test, n = 10, |d| = 1.0: '
      f'{TTestPower().power(effect_size=1.0, nobs=10, alpha=0.05, alternative="two-sided"):.3f}')
d = {c: [abs(v['d']) for v in A.values() if v['cls'] == c] for c in ['CACHE', 'DO_NOT_CACHE', 'BORDERLINE']}
print(f'             median |d|: CACHE {np.median(d["CACHE"]):.2f}, DO_NOT_CACHE {np.median(d["DO_NOT_CACHE"]):.2f}; '
      f'smallest decisive {min(d["CACHE"]+d["DO_NOT_CACHE"]):.2f}; BORDERLINE {[float(round(x,2)) for x in sorted(d["BORDERLINE"])]}')
for k, v in A.items():
    if v['cls'] != 'CACHE':
        print(f'             {k[0]:8s} {k[1]:28s} {v["cls"]:13s} mean {v["mean"]:6.2f}%  SD {v["sd"]:5.2f}  t {v["t"]:7.2f}  p {v["p"]:.2g}  cold {v["cold"]:.3f} ms  null share {v["null_share"]:.3f}')
eps = 1e-6
grp = {'always null': [v for v in A.values() if v['null_share'] > 1 - eps],
       'partly null': [v for v in A.values() if eps <= v['null_share'] <= 1 - eps],
       'never null': [v for v in A.values() if v['null_share'] < eps]}
for g, vs in grp.items():
    print(f'Sec 4.4.4    {g}: n = {len(vs)}, speedup {min(v["mean"] for v in vs):.2f}% to {max(v["mean"] for v in vs):.2f}%')
rho = stats.spearmanr([v['null_share'] for v in A.values()], [v['mean'] for v in A.values()])
print(f'Sec 4.4.4    Spearman(null share, speedup) rho = {rho[0]:.2f}, p = {rho[1]:.1e}')
ec = [v['eager'] for v in A.values() if v['cls'] == 'DO_NOT_CACHE']; eo = [v['eager'] for v in A.values() if v['cls'] == 'CACHE']
print(f'Sec 4.4.4    eager-load median DO_NOT_CACHE {np.median(ec)} vs CACHE {np.median(eo)}; Mann-Whitney p = {stats.mannwhitneyu(ec, eo)[1]:.2f}; '
      f'DO_NOT_CACHE counts {sorted((k[1], int(v["eager"])) for k, v in A.items() if v["cls"] == "DO_NOT_CACHE")}')
en = [v['eager_name'] for v in A.values() if v['cls'] == 'DO_NOT_CACHE']; eon = [v['eager_name'] for v in A.values() if v['cls'] == 'CACHE']
print(f'             (name-based scan, v1.3.0: median {np.median(en)} vs {np.median(eon)}; Mann-Whitney p = {stats.mannwhitneyu(en, eon)[1]:.2f})')
