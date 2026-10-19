# Changelog

## 1.4.0 (October 2026), matches thesis v44

- Eager-load frequency is now counted per model: every `with()`, `load()` and `loadMissing()` call in the application code (app/, routes/, resources/views/) attributed to the model on which it is made (`analysis/eager_load_scan.py`, `data/eager_load/`). The earlier name-based count, kept in `relationship_inventories/`, credited each relationship name to every relationship of that name and missed some call sites. Only the eager-load results of thesis Sections 4.2 and 4.4.2 to 4.4.4 change; their conclusions do not.
- The two checks behind this change are included: 20 random relationships (`check_20_relationships.csv`) and 12 further relationships counted by hand (`hand_check_12_relationships.csv`, 12 of 12 agree).
- New `PROVENANCE.md`: the archived output files are byte-identical to those on the test server (35 of 35), run dates and gaps, the interpreter version reconstructed from server logs, and the differences between the archived harness files and the copies that were run (comments only).
- New `code/*/relationships_for_benchmark*_as_run.csv`: the input lists actually used (dry-run failures removed).
- README: the VBS single-run file is the first of its ten runs (no separate pilot); collection procedure and environment described.
- `reproduce_thesis.py` prints the eager-load descriptive counts and both eager-load versions of the Section 4.4.4 comparison.

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
