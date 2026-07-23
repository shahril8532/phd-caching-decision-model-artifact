<?php

namespace App\Console\Commands;

use App\Models\AdminNotification;
use App\Models\ContributionRecord;
use App\Models\ContributionSetting;
use App\Models\DeathClaim;
use App\Models\Dependent;
use App\Models\DependentChange;
use App\Models\DependentChangeRequest;
use App\Models\Hubungan;
use App\Models\Jawatan;
use App\Models\LoginLog;
use App\Models\Lorong;
use App\Models\MemberNotification;
use App\Models\MembershipRenewal;
use App\Models\PaymentApproval;
use App\Models\Pegawai;
use App\Models\Register;
use App\Models\RegisterRejection;
use App\Models\SponsorRelationship;
use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

/**
 * Benchmark cold (uncached) vs warm (Redis-cached) access time for every
 * Eloquent relationship listed in relationships_for_benchmark_khairat.csv.
 *
 * IMPORTANT: run this only on the isolated TEST clone of khairat kematian
 * (khairat_testing_n8nsamarinda.xyz) — never on the live production server.
 * It writes/reads temporary "bench:*" cache keys and does NOT modify any
 * database rows.
 *
 * Setup before running (same as the iTeams harness):
 *   1. In .env on the test server: CACHE_STORE=redis, REDIS_CLIENT=phpredis,
 *      REDIS_HOST=127.0.0.1, REDIS_PORT=6379, REDIS_DB=1 (use a DB index
 *      other services on the same Redis instance are not using).
 *   2. Neutralize MAIL_* / SmtpSetting so no real emails go out during testing.
 *   3. Copy this file to app/Console/Commands/BenchmarkCaching.php
 *   4. Copy relationships_for_benchmark_khairat.csv to
 *      storage/app/relationships_for_benchmark_khairat.csv
 *   5. php artisan config:clear
 *
 * Run:
 *   php artisan benchmark:relationships --samples=30 --ttl=300 \
 *     --input=relationships_for_benchmark_khairat.csv \
 *     --output=benchmark_results_khairat.csv
 *
 * Output: storage/app/benchmark_results_khairat.csv — one row per
 * relationship with average cold time, warm time, speedup %, and
 * query-count reduction. Same column schema as the iTeams results, so it
 * merges directly into the same analysis pipeline.
 */
class BenchmarkCaching extends Command
{
    protected $signature = 'benchmark:relationships
        {--samples=30 : how many random parent records to sample per relationship}
        {--ttl=300 : cache TTL in seconds used for the warm-access test}
        {--input=relationships_for_benchmark_khairat.csv : CSV file in storage/app with columns model,method,type}
        {--output=benchmark_results_khairat.csv : output CSV file written to storage/app}';

    protected $description = 'Benchmark cold vs Redis-cached access time for each Eloquent relationship in the khairat kematian CSV inventory';

    /** Map short model names (as they appear in the CSV) to fully-qualified class names. */
    protected array $modelMap = [
        'AdminNotification' => AdminNotification::class,
        'ContributionRecord' => ContributionRecord::class,
        'ContributionSetting' => ContributionSetting::class,
        'DeathClaim' => DeathClaim::class,
        'Dependent' => Dependent::class,
        'DependentChange' => DependentChange::class,
        'DependentChangeRequest' => DependentChangeRequest::class,
        'Hubungan' => Hubungan::class,
        'Jawatan' => Jawatan::class,
        'LoginLog' => LoginLog::class,
        'Lorong' => Lorong::class,
        'MemberNotification' => MemberNotification::class,
        'MembershipRenewal' => MembershipRenewal::class,
        'PaymentApproval' => PaymentApproval::class,
        'Pegawai' => Pegawai::class,
        'Register' => Register::class,
        'RegisterRejection' => RegisterRejection::class,
        'SponsorRelationship' => SponsorRelationship::class,
        'User' => User::class,
        // PaymentSetting, SmtpSetting have no relationships (lookup/config
        // tables) — not needed here.
    ];

    public function handle(): int
    {
        $samples = (int) $this->option('samples');
        $ttl = (int) $this->option('ttl');
        $inputFile = storage_path('app/' . $this->option('input'));
        $outputFile = storage_path('app/' . $this->option('output'));

        if (! file_exists($inputFile)) {
            $this->error("Input CSV not found: {$inputFile}");
            $this->line('Copy relationships_for_benchmark_khairat.csv into storage/app/ first.');
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
