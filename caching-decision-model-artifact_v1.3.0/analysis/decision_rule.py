"""Apply the thesis decision rule (Equation 4.1) to one system and list every relationship.

Equation 4.1:  t = mean(s) / (SD / sqrt(n)),  df = n - 1,  two-tailed p.
    p < 0.05 and mean > 0  -> CACHE
    p < 0.05 and mean < 0  -> DO_NOT_CACHE
    otherwise              -> BORDERLINE

Relationships listed in data/excluded_relationships.csv (non-functional
declarations, thesis Section 3.5.3) are excluded unless --all is given.

Usage:
    python3 analysis/decision_rule.py iTeams
    python3 analysis/decision_rule.py Khairat
    python3 analysis/decision_rule.py VBS [--all]
"""
import sys
from common import load, SYSTEMS

if len(sys.argv) < 2 or sys.argv[1] not in SYSTEMS:
    print(__doc__); sys.exit(1)
R = load(sys.argv[1], exclude='--all' not in sys.argv)
print(f"{'relationship':34}{'type':15}{'mean %':>9}{'SD':>8}{'t':>9}{'p (2-tail)':>12}  sign  decision")
for k in sorted(R):
    v = R[k]
    print(f"{k:34}{v['type']:15}{v['mean']:9.2f}{v['sd']:8.2f}{v['t']:9.2f}{v['p']:12.2e}  {v['sign']:4}  {v['cls']}")
agree = sum({'CW': 'CACHE', 'NCW': 'DO_NOT_CACHE', 'UNST': 'BORDERLINE'}[v['sign']] == v['cls'] for v in R.values())
print(f"\n{len(R)} relationships; agreement with sign-consistency classification: {agree}/{len(R)}")
