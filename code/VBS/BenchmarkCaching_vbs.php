<?php

namespace App\Console\Commands;

use App\Models\Booking;
use App\Models\Driver;
use App\Models\Jawatan;
use App\Models\Pegawai;
use App\Models\Pengguna;
use App\Models\Sektor;
use App\Models\Unit;
use App\Models\User;
use App\Models\Vehicle;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

/**
 * Benchmark cold (uncached) vs warm (Redis-cached) access time for every
 * Eloquent relationship listed in relationships_for_benchmark_vbs.csv.
 *
 * This is the same benchmarking procedure used for iTeams and the Khairat
 * Kematian system (Chapter 3, Section 3.5.1), applied here to the Vehicle
 * Booking System (VBS) as a candidate third case-study system.
 *
 * IMPORTANT: run this only on an ISOLATED TEST CLONE of VBS — never on a
 * live production copy. It writes/reads temporary "bench:*" cache keys and
 * does NOT modify any database rows.
 *
 * Setup before running:
 *   1. In .env on the test server: CACHE_STORE=redis (Laravel 9 still reads
 *      CACHE_DRIVER=redis — set BOTH to be safe), REDIS_CLIENT=phpredis (or
 *      predis), REDIS_HOST=127.0.0.1, REDIS_PORT=6379, REDIS_DB=1 (use a DB
 *      index other services on the same Redis instance are not using).
 *   2. composer require predis/predis   (skip if the phpredis PHP extension
 *      is already installed)
 *   3. Copy this file to app/Console/Commands/BenchmarkCaching.php
 *   4. Copy relationships_for_benchmark_vbs.csv to
 *      storage/app/relationships_for_benchmark_vbs.csv
 *   5. php artisan config:clear
 *
 * Run (single pilot pass, 30 samples per relationship):
 *   php artisan benchmark:relationships-vbs --samples=30 --ttl=300
 *
 * For the full repeated-measures protocol used for iTeams/Khairat (10 runs,
 * 10-second gap between runs), run the command 10 times with --output set
 * to a different file each time, e.g.:
 *   php artisan benchmark:relationships-vbs --samples=30 --output=benchmark_run_vbs_1.csv
 *   sleep 10
 *   php artisan benchmark:relationships-vbs --samples=30 --output=benchmark_run_vbs_2.csv
 *   ... (repeat through _10.csv)
 *
 * Output: storage/app/benchmark_results_vbs.csv (or the --output filename
 * given) — one row per relationship with average cold time, warm time,
 * speedup %, and query-count reduction. Download the CSV(s) from the server
 * and add them to the PhD 2027/fasa_1_benchmark_vbs/ folder for analysis.
 */
class BenchmarkCachingVbs extends Command
{
    protected $signature = 'benchmark:relationships-vbs
        {--samples=30 : how many random parent records to sample per relationship}
        {--ttl=300 : cache TTL in seconds used for the warm-access test}
        {--input=relationships_for_benchmark_vbs.csv : CSV file in storage/app with columns model,method,type}
        {--output=benchmark_results_vbs.csv : output CSV file written to storage/app}';

    protected $description = 'Benchmark cold vs Redis-cached access time for each Eloquent relationship in the VBS CSV inventory';

    /** Map short model names (as they appear in the CSV) to fully-qualified class names. */
    protected array $modelMap = [
        'Booking' => Booking::class,
        'Driver' => Driver::class,
        'Jawatan' => Jawatan::class,
        'Pegawai' => Pegawai::class,
        'Pengguna' => Pengguna::class,
        'Sektor' => Sektor::class,
        'Unit' => Unit::class,
        'User' => User::class,
        'Vehicle' => Vehicle::class,
        // Post has no relationships (standalone content model) — not needed here.
    ];

    public function handle(): int
    {
        $samples = (int) $this->option('samples');
        $ttl = (int) $this->option('ttl');
        $inputFile = storage_path('app/' . $this->option('input'));
        $outputFile = storage_path('app/' . $this->option('output'));

        if (! file_exists($inputFile)) {
            $this->error("Input CSV not found: {$inputFile}");
            $this->line('Copy relationships_for_benchmark_vbs.csv into storage/app/ first.');
            return 1;
        }

        $rows = array_map('str_getcsv', file($inputFile));
        $header = array_shift($rows);

        $results = [];

        foreach ($rows as $row) {
            [$modelShort, $method, $type] = $row;

            if (! isset($this->modelMap[$modelShort])) {
                $this->warn("Skipping {$modelShort}::{$method} — model not registered in \$modelMap.");
                continue;
            }
            $modelClass = $this->modelMap[$modelShort];

            $this->info("Benchmarking {$modelShort}::{$method} ({$type})...");

            $ids = $modelClass::query()->inRandomOrder()->limit($samples)->pluck('id');
            if ($ids->isEmpty()) {
                $this->warn("  No records found for {$modelShort}, skipping.");
                continue;
            }

            $coldTimes = [];
            $coldQueryCounts = [];
            $warmTimes = [];
            $warmQueryCounts = [];
            $writeOverheads = [];

            foreach ($ids as $id) {
                $cacheKey = "bench:{$modelShort}:{$id}:{$method}";
                Cache::forget($cacheKey);

                // --- COLD: fresh model instance, no relation pre-loaded, no cache ---
                DB::flushQueryLog();
                DB::enableQueryLog();
                $start = microtime(true);
                $fresh = $modelClass::find($id);
                $value = $fresh?->{$method};
                if ($value instanceof \Illuminate\Database\Eloquent\Collection) {
                    $value->count(); // force full resolution for hasMany/belongsToMany
                }
                $coldTimes[] = (microtime(true) - $start) * 1000;
                $coldQueryCounts[] = count(DB::getQueryLog());
                DB::disableQueryLog();

                // --- CACHE WRITE ---
                $start = microtime(true);
                Cache::remember($cacheKey, $ttl, function () use ($modelClass, $id, $method) {
                    return $modelClass::find($id)?->{$method};
                });
                $writeOverheads[] = (microtime(true) - $start) * 1000;

                // --- WARM: same key, should be a cache hit now ---
                DB::flushQueryLog();
                DB::enableQueryLog();
                $start = microtime(true);
                Cache::remember($cacheKey, $ttl, function () use ($modelClass, $id, $method) {
                    return $modelClass::find($id)?->{$method};
                });
                $warmTimes[] = (microtime(true) - $start) * 1000;
                $warmQueryCounts[] = count(DB::getQueryLog());
                DB::disableQueryLog();

                Cache::forget($cacheKey);
            }

            $avg = fn (array $arr) => count($arr) ? array_sum($arr) / count($arr) : 0.0;
            $avgCold = $avg($coldTimes);
            $avgWarm = $avg($warmTimes);
            $speedup = $avgCold > 0 ? (($avgCold - $avgWarm) / $avgCold) * 100 : 0.0;

            $results[] = [
                'model' => $modelShort,
                'method' => $method,
                'type' => $type,
                'samples' => count($ids),
                'avg_cold_ms' => round($avgCold, 3),
                'avg_warm_ms' => round($avgWarm, 3),
                'speedup_pct' => round($speedup, 1),
                'avg_query_count_cold' => round($avg($coldQueryCounts), 2),
                'avg_query_count_warm' => round($avg($warmQueryCounts), 2),
                'avg_cache_write_overhead_ms' => round($avg($writeOverheads), 3),
            ];

            $this->line(sprintf(
                '  cold: %.2fms | warm: %.2fms | speedup: %.1f%% | queries cold->warm: %.1f -> %.1f',
                $avgCold, $avgWarm, $speedup, $avg($coldQueryCounts), $avg($warmQueryCounts)
            ));
        }

        if (empty($results)) {
            $this->error('No results produced — check that $modelMap matches your CSV and that tables have data.');
            return 1;
        }

        $fp = fopen($outputFile, 'w');
        fputcsv($fp, array_keys($results[0]));
        foreach ($results as $row) {
            fputcsv($fp, $row);
        }
        fclose($fp);

        $this->info("Done. " . count($results) . " relationships benchmarked. Results saved to {$outputFile}");

        return 0;
    }
}
