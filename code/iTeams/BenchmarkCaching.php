<?php

namespace App\Console\Commands;

use App\Models\ActivityLog;
use App\Models\Daerah;
use App\Models\DeviceRegistration;
use App\Models\Group;
use App\Models\Jabatan;
use App\Models\KategoriTugas;
use App\Models\Keberadaan;
use App\Models\Pegawai;
use App\Models\PegawaiSekolah;
use App\Models\Permission;
use App\Models\Pkg;
use App\Models\Ppd;
use App\Models\PushNotification;
use App\Models\Rangkaian;
use App\Models\Sekolah;
use App\Models\Tugas;
use App\Models\TugasImage;
use App\Models\TugasPegawai;
use App\Models\Unit;
use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

/**
 * Benchmark cold (uncached) vs warm (Redis-cached) access time for every
 * Eloquent relationship listed in relationships_for_benchmark.csv.
 *
 * IMPORTANT: run this only on the isolated TEST clone of iTeams — never on
 * the live ptismelaka production server. It writes/reads temporary "bench:*"
 * cache keys and does NOT modify any database rows.
 *
 * Setup before running:
 *   1. In .env on the test server: CACHE_DRIVER=redis, REDIS_CLIENT=predis (or phpredis),
 *      REDIS_HOST=127.0.0.1, REDIS_PORT=6379, REDIS_DB=1 (use a DB index other services
 *      on the same Redis instance are not using, e.g. n8n's Redis usually sits on DB 0).
 *   2. composer require predis/predis   (skip if the phpredis PHP extension is already installed)
 *   3. Copy this file to app/Console/Commands/BenchmarkCaching.php
 *   4. Copy relationships_for_benchmark.csv to storage/app/relationships_for_benchmark.csv
 *   5. php artisan config:clear
 *
 * Run:
 *   php artisan benchmark:relationships --samples=30 --ttl=300
 *
 * Output: storage/app/benchmark_results.csv — one row per relationship with
 * average cold time, warm time, speedup %, and query-count reduction.
 * Import this CSV back into the Relationship Inventory spreadsheet (join on
 * model + method) to feed Phase 2 (correlation analysis).
 */
class BenchmarkCaching extends Command
{
    protected $signature = 'benchmark:relationships
        {--samples=30 : how many random parent records to sample per relationship}
        {--ttl=300 : cache TTL in seconds used for the warm-access test}
        {--input=relationships_for_benchmark.csv : CSV file in storage/app with columns model,method,type}
        {--output=benchmark_results.csv : output CSV file written to storage/app}';

    protected $description = 'Benchmark cold vs Redis-cached access time for each Eloquent relationship in the CSV inventory';

    /** Map short model names (as they appear in the CSV) to fully-qualified class names. */
    protected array $modelMap = [
        'ActivityLog' => ActivityLog::class,
        'Daerah' => Daerah::class,
        'DeviceRegistration' => DeviceRegistration::class,
        'Group' => Group::class,
        'Jabatan' => Jabatan::class,
        'KategoriTugas' => KategoriTugas::class,
        'Keberadaan' => Keberadaan::class,
        'Pegawai' => Pegawai::class,
        'PegawaiSekolah' => PegawaiSekolah::class,
        'Permission' => Permission::class,
        'Pkg' => Pkg::class,
        'Ppd' => Ppd::class,
        'PushNotification' => PushNotification::class,
        'Rangkaian' => Rangkaian::class,
        'Sekolah' => Sekolah::class,
        'Tugas' => Tugas::class,
        'TugasImage' => TugasImage::class,
        'TugasPegawai' => TugasPegawai::class,
        'Unit' => Unit::class,
        'User' => User::class,
        // Isp, Jenistalian, Kelajuan, Lokasirouter, Kontrak, Jpn, SmtpSetting,
        // TelegramSetting have no relationships (lookup tables) — not needed here.
    ];

    public function handle(): int
    {
        $samples = (int) $this->option('samples');
        $ttl = (int) $this->option('ttl');
        $inputFile = storage_path('app/' . $this->option('input'));
        $outputFile = storage_path('app/' . $this->option('output'));

        if (! file_exists($inputFile)) {
            $this->error("Input CSV not found: {$inputFile}");
            $this->line('Copy relationships_for_benchmark.csv into storage/app/ first.');
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
