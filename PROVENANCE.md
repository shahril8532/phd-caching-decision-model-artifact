# Provenance record (artifact v1.4.0)

This file records how the archived files relate to the files that remain on the benchmark server. The check was made on 18 October 2026 by the first author, with read-only commands on the server `n8nsamarinda`; the outputs were compared with this artifact.

## 1. Benchmark output files

Every benchmark output file in `data/` was compared, by SHA-256, with the file of the same run still held in `storage/app/` of the corresponding test copy. All 35 are byte-identical. The first 16 hexadecimal digits are given below.

| System | Test copy on the server | Files compared | Result |
|---|---|---|---|
| iTeams | `/var/www/iteams_testing_n8nsamarinda_xyz` | single run + 10 runs + `nullsafe_iteams.csv` | 12 of 12 identical |
| Khairat Kematian | `/var/www/khairat_testing_n8nsamarinda_xyz` | single run + 10 runs + `nullsafe_khairat.csv` | 12 of 12 identical |
| VBS | `/var/www/vbs_n8nsamarinda_xyz` | runs 2 to 10 + the single-run file + `nullsafe_vbs.csv` | 11 of 11 identical |

| File | SHA-256 (first 16) | File | SHA-256 (first 16) |
|---|---|---|---|
| iTeams/benchmark_results.csv | a8b99945a89ac96c | Khairat/benchmark_results_khairat.csv | 7008384df3cf4dd5 |
| iTeams/benchmark_run_1.csv | 66a4786521799cf5 | Khairat/benchmark_run_khairat_1.csv | 94d78ccaa0a8e6e5 |
| iTeams/benchmark_run_2.csv | 056f256de5b2a9cd | Khairat/benchmark_run_khairat_2.csv | 29cfb4b431515c67 |
| iTeams/benchmark_run_3.csv | a8440b12d598e73f | Khairat/benchmark_run_khairat_3.csv | 86365d107829af05 |
| iTeams/benchmark_run_4.csv | 1315990457af0262 | Khairat/benchmark_run_khairat_4.csv | 58783cb50f3b529a |
| iTeams/benchmark_run_5.csv | ad0c80550862a1d0 | Khairat/benchmark_run_khairat_5.csv | 77bc262adc73d3f9 |
| iTeams/benchmark_run_6.csv | a6098e462d1167f6 | Khairat/benchmark_run_khairat_6.csv | f86d2744263aafb5 |
| iTeams/benchmark_run_7.csv | 4b0c5f053d06e6ef | Khairat/benchmark_run_khairat_7.csv | 67bcb4422013284f |
| iTeams/benchmark_run_8.csv | 235f9658097a0f7f | Khairat/benchmark_run_khairat_8.csv | baa0173457350c75 |
| iTeams/benchmark_run_9.csv | c5af9adc7eaaccc3 | Khairat/benchmark_run_khairat_9.csv | dee1d37889fcc9c3 |
| iTeams/benchmark_run_10.csv | a75d7f733a4ab9b0 | Khairat/benchmark_run_khairat_10.csv | d1560a3ea226492c |
| nullsafe/nullsafe_iteams.csv | 93905e2560e22bfd | nullsafe/nullsafe_khairat.csv | 2a55cecb79fdbc5d |

| File | SHA-256 (first 16) |
|---|---|
| VBS/benchmark_result_vbs.csv (= benchmark_run_vbs_1.csv) | 217f96be7c3924a0 |
| VBS/benchmark_run_vbs_2.csv | f02deea234de07d0 |
| VBS/benchmark_run_vbs_3.csv | bcff5302c7403bed |
| VBS/benchmark_run_vbs_4.csv | a97cec5ad1b71a0c |
| VBS/benchmark_run_vbs_5.csv | a836063cd87efb89 |
| VBS/benchmark_run_vbs_6.csv | 88ec890d2c0eaae4 |
| VBS/benchmark_run_vbs_7.csv | 98ed401eec89c34b |
| VBS/benchmark_run_vbs_8.csv | b94d614b76a08855 |
| VBS/benchmark_run_vbs_9.csv | 9874e890f07d544c |
| VBS/benchmark_run_vbs_10.csv | d3c00a200b9dd5fb |
| nullsafe/nullsafe_vbs.csv | 6970befbec7f9a93 |

## 2. When and how the runs were made

From the modification times of the output files and the server's shell history (commands containing `benchmark:` only):

| System | Date | Sequence | Gap between successive run files |
|---|---|---|---|
| iTeams | Sunday 19 July 2026, runs 10:55:20 to 10:57:27 (+08:00) | dry runs with `--samples=3`; single run `--samples=30` (10:36); loop `for i in 1..10 ... sleep 10` | 14.0 to 14.4 s |
| Khairat Kematian | Sunday 19 July 2026, runs 13:58:04 to 13:59:52 | dry runs with `--samples=3` (output `benchmark_dryrun_khairat.csv`, not archived); single run; loop 1..10 with `sleep 10` | 11.8 to 12.3 s |
| VBS | Monday 20 July 2026, 19:44:20 to 19:47:13 | single-run command (`--samples=30`, default output file) executed more than once, the last kept as run 1; loop `for i in 2..10 ... sleep 10` | 11.7 to 12.0 s (run 1 to run 2: 78.8 s) |
| Null-safe experiment | Sunday 11 October 2026 | `benchmark:nullsafe` with the twelve relationships of thesis Section 4.4.4 | |

VBS therefore has no separate pilot run; `data/VBS/benchmark_result_vbs.csv` is the same file as `benchmark_run_vbs_1.csv`.

## 3. Code that was run

| Archived file | Copy on the server | Difference |
|---|---|---|
| code/iTeams/BenchmarkCaching.php | identical (23ee70031bd8dc09) | none |
| code/Khairat/BenchmarkCaching.php | be58030ab958f974 | comments only (setup notes and section labels added for publication) |
| code/VBS/BenchmarkCaching_vbs.php | `app/Console/Commands/BenchmarkCachingVbs.php`, 05ee03c0b8782b8b | comments only |
| code/nullsafe/BenchmarkNullSafe.php | 3e2287da224a1f60 (all three copies) | one comment line (line 10) |

The relationship lists `code/*/relationships_for_benchmark*.csv` are the full static inventories. The lists actually used as input are `*_as_run.csv`: the inventories without the relationships that failed the dry run (iTeams 67 to 63, Khairat Kematian 51 to 48, VBS 19 to 16), exactly as reported in thesis Section 3.5.3. The iTeams list on the server uses Windows line endings, which the archived as-run copy keeps.

## 4. Environment

| Item | Value | Source |
|---|---|---|
| Command-line interpreter | PHP 8.4: 8.4.23 on 19 to 20 July 2026, 8.4.26 on 11 October 2026 | `php` in automatic alternatives mode pointing to PHP 8.4 with no manual change from June to September 2026 (`/var/log/alternatives.log`); patch levels from `/var/log/apt/history.log`; invoked as `php artisan` (author) |
| OPcache for the command line | disabled (`opcache.enable_cli = 0`) | `php -r` |
| Redis | 7.0.15, bound to 127.0.0.1 and ::1 only | `redis-cli` |
| MySQL | 8.0.46 on the same server (`DB_HOST` 127.0.0.1 or localhost) | `.env` of each test copy |
| Cache store | `redis` in each test copy | `.env` |
| Outbound mail | `MAIL_MAILER=log` (iTeams, Khairat Kematian); `MAIL_HOST=mailhog` (VBS) | `.env` |
| Reachability | iTeams and Khairat Kematian copies: no web address (command line only); VBS copy: web address on the test server, `APP_ENV=local` | nginx site configuration |
| Other applications on the host | the live Khairat Kematian application and other web applications, not stopped during benchmarking | nginx site configuration; author |

These values are the state of the server at the time of the check, except where a log gives the value at the time of the runs.

## 5. Eager-load counts

The eager-load count in `data/relationship_inventories/` came from a controller-layer scan that matched relationship names. A check on 20 random relationships (`data/eager_load/check_20_relationships.csv`) showed that it credited each name to every relationship of that name, whatever the model on which the call was made, and missed some call sites; write counts were close to the checked counts (16 of 20 within one operation, all within four). The scan was therefore replaced by `analysis/eager_load_scan.py`, which attributes every `with()`, `load()` and `loadMissing()` call in the application code (app/, routes/, resources/views/) to the model on which it is made. A further 12 random relationships were counted by hand against its output and agreed in all 12 (`data/eager_load/hand_check_12_relationships.csv`). The source code scanned is the copy of each system kept in the author's working folder: the iTeams backup of 18 July 2026, the Khairat Kematian test-copy backup of 19 July 2026, and the VBS copy.
