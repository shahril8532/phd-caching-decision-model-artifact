<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

/**
 * Null-safe confirmation experiment (thesis Section 4.4.4).
 *
 * For each listed relationship, measures on the SAME sampled records:
 *   - cold access (fresh model instance, no cache)                    = as BenchmarkCaching
 *   - warm access via Cache::remember()                               = as BenchmarkCaching
 *   - warm access via a null-safe wrapper that stores a sentinel value,
 *     so that a null relationship result CAN be served from the cache
 *
 * Prediction: relationships that resolve to null are slower with Cache::remember()
 * (warm query count stays at 1) but faster with the null-safe wrapper (warm query count 0).
 * Relationships that return data behave the same under both.
 *
 * Read-only on the database. Writes/reads only temporary "nullsafe:*" cache keys,
 * which are deleted after every sample.
 *
 * Install: copy to app/Console/Commands/BenchmarkNullSafe.php
 * Run (example):
 *   php artisan benchmark:nullsafe --rel=PushNotification.daerah --rel=Tugas.disahkanOleh --rel=ActivityLog.user
 * Output: storage/app/nullsafe_results.csv (one row per run per relationship)
 */
class BenchmarkNullSafe extends Command
{
    protected $signature = 'benchmark:nullsafe
        {--rel=* : relationship as Model.method (model class in App\\Models)}
        {--runs=10 : number of independent runs}
        {--samples=30 : parent records sampled per relationship per run}
        {--ttl=300 : cache TTL in seconds}
        {--pause=10 : seconds to wait between runs}
        {--output=nullsafe_results.csv : output CSV in storage/app}';

    protected $description = 'A1 confirmation: Cache::remember() vs null-safe caching on the same relationships';

    private const NULL_SENTINEL = '__A1_NULL__';

    public function handle(): int
    {
        $store = config('cache.default');
        $this->info("cache.default = {$store}");
        if ($store !== 'redis') {
            $this->error('Cache store is not redis. Fix .env (CACHE_STORE / CACHE_DRIVER) and run php artisan config:clear first.');
            return 1;
        }

        $rels = $this->option('rel');
        if (empty($rels)) {
            $this->error('Give at least one --rel=Model.method');
            return 1;
        }
        $runs = (int) $this->option('runs');
        $samples = (int) $this->option('samples');
        $ttl = (int) $this->option('ttl');
        $rows = [];

        for ($run = 1; $run <= $runs; $run++) {
            $this->info("Run {$run}/{$runs}");
            foreach ($rels as $rel) {
                [$modelShort, $method] = explode('.', $rel, 2);
                $modelClass = 'App\\Models\\' . $modelShort;
                if (! class_exists($modelClass)) {
                    $this->warn("  skip {$rel}: class {$modelClass} not found");
                    continue;
                }

                $ids = $modelClass::query()->inRandomOrder()->limit($samples)->pluck('id');
                if ($ids->isEmpty()) {
                    $this->warn("  skip {$rel}: no records");
                    continue;
                }

                $cold = $warmR = $warmN = $qCold = $qWarmR = $qWarmN = [];
                $nullCount = 0;

                foreach ($ids as $id) {
                    $loader = function () use ($modelClass, $id, $method) {
                        $v = $modelClass::find($id)?->{$method};
                        if ($v instanceof \Illuminate\Database\Eloquent\Collection) {
                            $v->count();
                        }
                        return $v;
                    };
                    $keyR = "nullsafe:R:{$modelShort}:{$id}:{$method}";
                    $keyN = "nullsafe:N:{$modelShort}:{$id}:{$method}";
                    Cache::forget($keyR);
                    Cache::forget($keyN);

                    // COLD (identical to BenchmarkCaching)
                    DB::flushQueryLog(); DB::enableQueryLog();
                    $t = microtime(true);
                    $value = $loader();
                    $cold[] = (microtime(true) - $t) * 1000;
                    $qCold[] = count(DB::getQueryLog());
                    DB::disableQueryLog();
                    if ($value === null) {
                        $nullCount++;
                    }

                    // VARIANT R: Cache::remember (populate, then timed warm access)
                    Cache::remember($keyR, $ttl, $loader);
                    DB::flushQueryLog(); DB::enableQueryLog();
                    $t = microtime(true);
                    Cache::remember($keyR, $ttl, $loader);
                    $warmR[] = (microtime(true) - $t) * 1000;
                    $qWarmR[] = count(DB::getQueryLog());
                    DB::disableQueryLog();

                    // VARIANT N: null-safe wrapper (populate, then timed warm access)
                    $this->nullSafe($keyN, $ttl, $loader);
                    DB::flushQueryLog(); DB::enableQueryLog();
                    $t = microtime(true);
                    $this->nullSafe($keyN, $ttl, $loader);
                    $warmN[] = (microtime(true) - $t) * 1000;
                    $qWarmN[] = count(DB::getQueryLog());
                    DB::disableQueryLog();

                    Cache::forget($keyR);
                    Cache::forget($keyN);
                }

                $avg = fn (array $a) => count($a) ? array_sum($a) / count($a) : 0.0;
                $c = $avg($cold); $r = $avg($warmR); $n = $avg($warmN);
                $rows[] = [
                    'run' => $run,
                    'model' => $modelShort,
                    'method' => $method,
                    'samples' => count($ids),
                    'null_share' => round($nullCount / count($ids), 3),
                    'avg_cold_ms' => round($c, 4),
                    'avg_warm_remember_ms' => round($r, 4),
                    'avg_warm_nullsafe_ms' => round($n, 4),
                    'speedup_remember_pct' => $c > 0 ? round(($c - $r) / $c * 100, 2) : 0,
                    'speedup_nullsafe_pct' => $c > 0 ? round(($c - $n) / $c * 100, 2) : 0,
                    'q_cold' => round($avg($qCold), 2),
                    'q_warm_remember' => round($avg($qWarmR), 2),
                    'q_warm_nullsafe' => round($avg($qWarmN), 2),
                ];
                $this->line(sprintf('  %-32s null=%.0f%% cold=%.3f remember=%.3f nullsafe=%.3f',
                    $rel, 100 * $nullCount / count($ids), $c, $r, $n));
            }
            if ($run < $runs) {
                sleep((int) $this->option('pause'));
            }
        }

        $file = storage_path('app/' . $this->option('output'));
        $fp = fopen($file, 'w');
        fputcsv($fp, array_keys($rows[0]));
        foreach ($rows as $row) {
            fputcsv($fp, $row);
        }
        fclose($fp);
        $this->info('Saved ' . count($rows) . " rows to {$file}");
        return 0;
    }

    /** Like Cache::remember(), but stores a sentinel so that a null result is cached too. */
    private function nullSafe(string $key, int $ttl, \Closure $loader)
    {
        $v = Cache::get($key);
        if ($v === null) {
            $v = $loader();
            Cache::put($key, $v ?? self::NULL_SENTINEL, $ttl);
        }
        return $v === self::NULL_SENTINEL ? null : $v;
    }
}
