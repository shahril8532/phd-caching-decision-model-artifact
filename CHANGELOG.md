# Changelog

## 1.3.0 (October 2026), matches thesis v23

- Four iTeams belongsTo relationships whose foreign-key column does not exist (Pegawai.sekolah, Sekolah.pegawai, Unit.ppd, Unit.pkg) are excluded from analysis as non-functional; listed in `data/excluded_relationships.csv`. Raw data are unchanged.
- Equation 4.1 is now two-tailed, as in the thesis (v1.2.0 used a one-tailed p-value).
- New `analysis/reproduce_thesis.py` reproduces every statistic in Chapter 4; new `analysis/common.py` shared loader.
- Null-share of each relationship derived from cold and warm query counts (thesis Section 4.4.4).
- New null-safe confirmation experiment: `code/nullsafe/BenchmarkNullSafe.php`, `data/nullsafe/`, `analysis/nullsafe_summary.py`.
- New `data/null_fk_evidence.csv` (aggregate counts only, no personal data).
- Post-hoc power analysis scripts removed: the thesis uses a sensitivity analysis (minimum detectable |d| = 1.0) instead of observed power. Figures replaced by Figures 4.1 to 4.5 of the thesis (`analysis/plot_figures.py`).
- README and CITATION updated.

## 1.2.0 (July 2026)

- Initial public release with raw benchmark data, inventories, harness and analysis scripts.
