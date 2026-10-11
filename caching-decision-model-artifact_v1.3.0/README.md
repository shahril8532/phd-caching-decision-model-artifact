# A Design-Time Decision Model for Determining Cache-Worthy Relationships in ORM-Based Database Applications

Reproducibility artifact, **version 1.3.0** (October 2026). All versions on Zenodo: <https://doi.org/10.5281/zenodo.21505973> (this DOI always resolves to the latest version). Previous version: v1.2.0, <https://doi.org/10.5281/zenodo.23054249>.

PhD research of **Shahril bin Mohd Isa**, Fakulti Teknologi Maklumat dan Komunikasi (FTMK), Universiti Teknikal Malaysia Melaka (UTeM). Supervisor: Assoc. Prof. Ts. Dr. Nurul Akmar Emran. Co-supervisor: Dr. Nurul Izrin binti Md Saleh.

This artifact contains the raw benchmark data, relationship inventories, benchmark harness code and analysis scripts that reproduce every statistic, table and figure in Chapter 4 of the thesis.

## What the research is about

ORM frameworks such as Laravel's Eloquent hide the runtime cost of a data access behind simple object syntax (for example `$model->relatedItems`), so developers cannot tell in advance which relationships are worth caching. The thesis proposes a decision rule (Equation 4.1): a two-tailed one-sample t-test applied to a relationship's own speedup measured over ten repeated runs, returning `CACHE`, `DO_NOT_CACHE` or `BORDERLINE`.

| System | Description | Relationships analysed |
|---|---|---|
| iTeams | ICT and network task-management system (JPNM) | 59 (63 benchmarked, 4 excluded as non-functional) |
| Khairat Kematian | Community death-benefit fund system | 36 |
| VBS | Vehicle Booking System (JPNM) | 16 |

Result: 105 `CACHE`, 4 `DO_NOT_CACHE`, 2 `BORDERLINE`. Every relationship classified `DO_NOT_CACHE` resolves to null for every sampled record. Laravel's `Cache::remember()` never serves a cached null, so each access pays a cache round-trip without a hit. A confirmation experiment with a null-safe cache wrapper removes the regression (thesis Section 4.4.4).

## Repository structure

```
code/
  iTeams/, Khairat/, VBS/     Benchmark harness (Laravel Artisan command) and relationship list per system
  nullsafe/                   BenchmarkNullSafe.php: confirmation experiment (Cache::remember vs null-safe)
data/
  iTeams/, Khairat/, VBS/     10 repeated benchmark runs per system (benchmark_run_*.csv) and the single pilot run
  relationship_inventories/   Static inventory per system (type, eager-load count, write-operation count)
  excluded_relationships.csv  The 4 iTeams relationships excluded as non-functional (thesis Section 3.5.3)
  null_fk_evidence.csv        Aggregate NULL / dangling foreign-key counts behind the non-CACHE relationships
  nullsafe/                   Results of the null-safe confirmation experiment
analysis/
  common.py                   Shared loader and Equation 4.1
  decision_rule.py            Equation 4.1 for one system, relationship by relationship
  reproduce_thesis.py         Every statistic in Chapter 4, labelled by thesis section and table
  nullsafe_summary.py         Summary of the confirmation experiment
  plot_figures.py             Regenerates Figures 4.1 to 4.5 into figures/
figures/                      Figures 4.1 to 4.5 as produced by plot_figures.py
```

## How the data was collected

Each relationship was benchmarked on an isolated test clone of its system (never on a live production system) with the harness in `code/<System>/`. For each sampled parent record (up to 30 per relationship; every record where fewer exist):

1. **Cold access**: a fresh model instance resolves the relationship with no cache, timed and query-counted.
2. **Cache write**: the first `Cache::remember()` call, timed (this call also runs the loader).
3. **Warm access**: a second `Cache::remember()` call, timed and query-counted.

The whole benchmark was run ten times per system, ten seconds apart.

`benchmark_run_*.csv` columns:

| Column | Meaning |
|---|---|
| `model`, `method`, `type` | The Eloquent relationship |
| `samples` | Parent records sampled in that run |
| `avg_cold_ms`, `avg_warm_ms` | Mean access time without and with caching |
| `speedup_pct` | `(cold - warm) / cold * 100` |
| `avg_query_count_cold`, `avg_query_count_warm` | Mean database queries without and with caching |
| `avg_cache_write_overhead_ms` | Mean time of the cache-populating call |

`nullsafe_*.csv` columns: `run`, `model`, `method`, `samples`, `null_share` (share of sampled records resolving to null), `avg_cold_ms`, `avg_warm_remember_ms`, `avg_warm_nullsafe_ms`, `speedup_remember_pct`, `speedup_nullsafe_pct`, `q_cold`, `q_warm_remember`, `q_warm_nullsafe`.

## Reproducing the results

```bash
pip install -r requirements.txt
cd analysis
python3 reproduce_thesis.py        # Tables 4.4 to 4.9 and all statistics in Chapter 4
python3 decision_rule.py iTeams    # Equation 4.1, relationship by relationship (also Khairat, VBS)
python3 nullsafe_summary.py        # confirmation experiment, Section 4.4.4
python3 plot_figures.py            # Figures 4.1 to 4.5
```

`decision_rule.py iTeams --all` includes the four excluded relationships, which reproduces the one case where the formal rule and the sign-consistency classification differed before exclusion (`Unit.pkg`, mean -19.86%, p = 0.0061, sign varies across runs).

## Notes and limitations

- 40 of the 111 relationships were measured on fewer than 30 records because their tables held fewer rows; for those, the ten runs re-measure largely the same records (thesis Section 3.8).
- Production database snapshots and configuration files are not included, to protect personal data. `null_fk_evidence.csv` gives the aggregate counts that support Section 4.4.4.
- The null-safe experiment was run separately from the main benchmark (October 2026); compare its times only within that experiment.

## License

Code: MIT. Data: CC BY 4.0. See `LICENSE`.

## Citation

See `CITATION.cff`.
