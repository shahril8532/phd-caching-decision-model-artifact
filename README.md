# A Decision Model for Determining What to Cache in ORM-Based Database Applications

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21505973.svg)](https://doi.org/10.5281/zenodo.21505973)


Reproducibility artifact for the PhD research of **Shahril bin Mohd Isa**, Fakulti Teknologi Maklumat dan Komunikasi (FTMK), Universiti Teknikal Malaysia Melaka (UTeM), supervised by Assoc. Prof. Ts. Dr. Nurul Akmar Emran.

This repository contains the raw empirical data, benchmark harness code, and an independent analysis script supporting the thesis/proposal *"A Decision Model for Determining What to Cache in ORM-Based Database Applications: Balancing Performance and Resource Cost."*

## What this research is about

Object-Relational Mapping (ORM) frameworks such as Laravel's Eloquent hide the true performance cost of a data-access operation behind simple object syntax (e.g. `$model->relatedItems`). This makes it hard for developers to know, in advance, which ORM relationships are worth caching and which are not — caching the wrong ones can *degrade* performance rather than improve it.

This research proposes and empirically validates a **decision rule** (Equation 5.1: a one-sample t-test applied to repeated per-relationship speedup measurements) that classifies each ORM relationship as `CACHE`, `DO_NOT_CACHE`, or `BORDERLINE`, based purely on repeated, controlled measurement — no machine learning involved.

The rule is validated against three independently operated, production Laravel/Eloquent systems:

| System | Description | Users | Relationships benchmarked |
|---|---|---|---|
| **iTeams** | ICT and network task-management system (JPNM) | ~100 | 63 |
| **Khairat Kematian** | Community death-benefit fund management system | <300 members | 36 |
| **VBS** (Vehicle Booking System) | Transport-booking management system (JPNM) | ~200 | 16 |

## Repository structure

```
.
├── code/                          Benchmark harness (PHP artisan command) per system
│   ├── iTeams/BenchmarkCaching.php
│   ├── Khairat/BenchmarkCaching.php
│   └── VBS/BenchmarkCaching_vbs.php
├── data/
│   ├── iTeams/                    10 repeated benchmark runs + aggregated results (CSV)
│   ├── Khairat/                   10 repeated benchmark runs + aggregated results (CSV)
│   ├── VBS/                       10 repeated benchmark runs + aggregated results (CSV)
│   └── relationship_inventories/  Static relationship inventory per system (CSV)
├── analysis/
│   └── decision_rule.py           Independent Python re-implementation of Equation 5.1
├── LICENSE
├── CITATION.cff
└── README.md
```

## How the data was collected

For each system, every Eloquent relationship (`belongsTo`, `hasOne`, `hasMany`, `belongsToMany`) was benchmarked on an isolated test clone (never on the live production system) using the harness in `code/<System>/`:

1. **Cold access** — a fresh model instance resolves the relationship with no cache, timed and query-counted.
2. **Cache write** — the result is written to Redis via `Cache::remember`.
3. **Warm access** — the same relationship is resolved again, now served from Redis (cache hit), timed and query-counted.

This cold/warm/write cycle was repeated for a random sample of parent records per relationship, and the entire benchmark was run **10 independent times per system** (`data/<System>/benchmark_run_*.csv`) to support repeated-measures statistical testing rather than relying on a single-run snapshot.

Data dictionary for `benchmark_run_*.csv`:

| Column | Meaning |
|---|---|
| `model`, `method`, `type` | The Eloquent relationship being benchmarked (e.g. `Unit`, `pkg`, `belongsTo`) |
| `samples` | Number of parent records sampled |
| `avg_cold_ms` / `avg_warm_ms` | Mean access time (ms) without / with caching |
| `speedup_pct` | Percentage speedup from caching: `(cold - warm) / cold * 100` |
| `avg_query_count_cold` / `avg_query_count_warm` | Mean DB query count without / with caching |
| `avg_cache_write_overhead_ms` | Mean time to write the result to Redis |

## Reproducing the decision rule independently

The thesis computes Equation 5.1 (t-statistic, p-value, formal `CACHE`/`DO_NOT_CACHE`/`BORDERLINE` decision) as live Excel formulas inside the `*_Phase2_Aggregated_Analysis.xlsx` workbooks (not included here — see the main thesis document set). `analysis/decision_rule.py` re-implements the same one-sample t-test independently in Python, so the result can be verified without opening Excel:

```bash
pip install scipy   # optional but recommended for exact p-values
python3 analysis/decision_rule.py data/iTeams
python3 analysis/decision_rule.py data/Khairat
python3 analysis/decision_rule.py data/VBS
```

This has been verified to reproduce the thesis-cited figures exactly, e.g. for iTeams' `Unit.pkg` relationship: **t = -3.557, p = 0.0031, DO_NOT_CACHE** — matching Chapter 5, Table 5.1 of the thesis to 4 decimal places.

## Key finding

A relationship's own cold (uncached) access time, measured empirically and analysed through repeated-measures statistical testing, provides a reliable, system-specific basis for the caching decision. The decision-making *process* generalises across all three independently operated systems even where the underlying numeric measurements (and, in VBS's case, even the direction of the cold-time/speedup correlation) do not transfer directly between them — see the thesis, Chapter 5.6, for the full discussion of this generalisability boundary.

## Citation

If you use this data or code, please cite the thesis (see `CITATION.cff`).

## License

- **Code** (`code/`, `analysis/`): MIT License — see `LICENSE`.
- **Data** (`data/`): released under CC-BY-4.0 — attribution required, reuse permitted.

## Contact

Shahril bin Mohd Isa — shahril3421@gmail.com
Corresponding supervisor: Assoc. Prof. Ts. Dr. Nurul Akmar Emran — nurulakmar@utem.edu.my
