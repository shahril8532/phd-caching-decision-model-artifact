"""Regenerate thesis Figures 4.1 to 4.5 from the raw CSVs into figures/.
Usage:  python3 analysis/plot_figures.py
"""
import os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import load, SYSTEMS, ROOT
OUT = os.path.join(ROOT, 'figures'); os.makedirs(OUT, exist_ok=True)
COL = {'CACHE': '#2ca02c', 'DO_NOT_CACHE': '#d62728', 'BORDERLINE': '#ff7f0e'}
MK = {'iTeams': 'o', 'Khairat': 's', 'VBS': '^'}
data = {s: load(s) for s in SYSTEMS}
NAME = {'iTeams': 'iTeams', 'Khairat': 'Khairat', 'VBS': 'VBS'}

def scatter(s, fname, figno):
    R = data[s]; fig, ax = plt.subplots(figsize=(13.35, 8.10), dpi=100)
    for c in COL:
        pts = [v for v in R.values() if v['cls'] == c]
        if pts:
            ax.scatter([v['cold'] for v in pts], [v['mean'] for v in pts], color=COL[c], edgecolor='black', linewidth=0.6, s=70, label=c, zorder=3)
    lab = [v for v in R.values() if v['cls'] != 'CACHE']
    for i, v in enumerate(sorted(lab, key=lambda v: v['mean'])):
        ax.annotate(v['rel'], xy=(v['cold'], v['mean']), xytext=(v['cold'] * 1.3, -12 - 9 * i), fontsize=9,
                    arrowprops=dict(arrowstyle='-', color='#888', lw=0.7))
    ax.axhline(0, color='gray', ls='--', lw=1, zorder=1); ax.set_xscale('log')
    ax.set_xlabel('Cold Access Time - mean of 10 runs (ms, log scale)'); ax.set_ylabel('Speedup (%) - mean of 10 runs')
    ax.set_title(f'{NAME[s]}: Cold Access Time vs Caching Speedup (n={len(R)} relationships, Equation 4.1 decision, 10 runs each)', fontweight='bold')
    ax.grid(True, which='both', ls=':', lw=0.5, alpha=0.6); ax.legend(loc='lower right', framealpha=0.9)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, fname), dpi=100); plt.close(fig)

scatter('iTeams', 'fig4_1_iteams.png', '4.1')
scatter('Khairat', 'fig4_2_khairat.png', '4.2')
scatter('VBS', 'fig4_3_vbs.png', '4.3')

fig, ax = plt.subplots(figsize=(14.85, 8.85), dpi=100)
for s, R in data.items():
    ax.scatter([v['cold'] for v in R.values()], [v['mean'] for v in R.values()], c=[COL[v['cls']] for v in R.values()],
               marker=MK[s], edgecolor='black', linewidth=0.6, s=70, label=f'{s} (n={len(R)})', zorder=3)
ax.axhline(0, color='gray', ls='--', lw=1, zorder=1); ax.set_xscale('log')
ax.set_xlabel('Cold Access Time, mean of 10 runs (ms, log scale)'); ax.set_ylabel('Speedup (%)')
ax.set_title('Cold Access Time (log scale) vs Speedup % - iTeams, Khairat, and VBS combined\n(marker shape = system, colour = Equation 4.1 decision: green=CACHE, red=DO_NOT_CACHE, orange=BORDERLINE)', fontweight='bold', fontsize=11)
ax.grid(True, which='both', ls=':', lw=0.5, alpha=0.6); ax.legend(loc='lower right', framealpha=0.9)
fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig4_4_combined.png'), dpi=100); plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(19, 7), sharey=True)
for ax, (s, R) in zip(axes, data.items()):
    rs = sorted(R.items(), key=lambda kv: abs(kv[1]['d']))
    ax.scatter(range(len(rs)), [abs(v['d']) for k, v in rs], c=[COL[v['cls']] for k, v in rs], s=48, edgecolors='black', linewidths=0.5, zorder=3)
    ax.axhline(1.0, color='black', ls='--', lw=1.2)
    ax.text(len(rs) * 0.45, 0.65, 'minimum detectable |d| = 1.0\n(n = 10, alpha = 0.05, power = 0.80)', fontsize=8.5)
    lab = [(j, k, v) for j, (k, v) in enumerate(rs) if v['cls'] != 'CACHE']
    nb = sum(1 for x in lab if x[2]['cls'] == 'BORDERLINE')
    for idx, (j, k, v) in enumerate(lab):
        ty = 0.25 * (2.6 ** idx) if v['cls'] == 'BORDERLINE' else 25 * (1.9 ** (idx - nb))
        if s == 'iTeams': ty = 2.0
        ax.annotate(k, xy=(j, abs(v['d'])), xytext=(j + max(3, len(rs) * 0.12), ty), fontsize=8.5, color='#444',
                    arrowprops=dict(arrowstyle='-', color='#999', lw=0.7), va='center')
    ax.set_yscale('log'); ax.set_title(f'{s} (n={len(rs)} relationships)', fontsize=12.5); ax.set_xlabel('Relationships (sorted by |d|)'); ax.grid(alpha=0.25, which='both')
axes[0].set_ylabel("Absolute effect size |Cohen's d| (log scale)")
h = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markeredgecolor='black', markersize=9, label=l) for l, c in COL.items()]
fig.legend(handles=h, loc='upper center', ncol=3, bbox_to_anchor=(0.5, 1.04), frameon=False)
fig.suptitle('Effect size per relationship against the minimum detectable effect (Equation 4.1, n = 10 repeated runs)', y=1.10, fontsize=13.5)
plt.tight_layout(); plt.savefig(os.path.join(OUT, 'fig4_5_effect_size.png'), dpi=180, bbox_inches='tight'); plt.close(fig)
print('figures written to', OUT)
