
"""
ChronosMatch - Latency and Throughput Benchmark

Measures:
- Throughput across repeated runs
- Per-batch average latency and percentiles
- Sampled individual-call latency percentiles
- Engine statistics
- Run-to-run performance variation

CSV reports:
- benchmark_runs.csv
- benchmark_batches.csv
- benchmark_sampled_latency.csv

Requires the compiled matching_engine Cython extension.
"""

import csv
import random
import statistics
import time
from math import ceil
from pathlib import Path

from matching_engine import MatchingEngine


# -------------------- CONFIGURATION --------------------

TOTAL_ORDERS = 100_000
WARMUP_ORDERS = 5_000
TOTAL_RUNS = 5
BATCH_SIZE = 500
SAMPLE_EVERY = 100
ENGINE_CAPACITY = TOTAL_ORDERS + WARMUP_ORDERS
RANDOM_SEED = 42

OUTPUT_DIR = Path(__file__).resolve().parent


# -------------------- HELPERS --------------------

def percentile(values, percent):
    """Calculate the nearest-rank percentile."""
    if not values:
        return 0.0

    ordered = sorted(values)
    rank = max(1, ceil(percent / 100 * len(ordered)))
    return ordered[rank - 1]


def generate_orders(count, seed):
    """Generate a reproducible workload."""
    rng = random.Random(seed)

    return [
        (
            rng.choice((1, -1)),
            rng.randint(95, 105),
            rng.randint(1, 10),
        )
        for _ in range(count)
    ]


def make_engine():
    return MatchingEngine(capacity=ENGINE_CAPACITY)


def warm_up(orders):
    """Exercise the engine before collecting benchmark results."""
    engine = make_engine()

    for side, price, quantity in orders:
        engine.submit(side, price, quantity)


def write_csv(filename, rows, fieldnames):
    """Write dictionaries to a CSV file."""
    path = OUTPUT_DIR / filename

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV saved: {path}")


# -------------------- BATCH BENCHMARK --------------------

def run_batch_benchmark(orders, run_number):
    engine = make_engine()
    batch_rows = []

    total_start = time.perf_counter_ns()

    for batch_number, start_index in enumerate(
        range(0, len(orders), BATCH_SIZE), start=1
    ):
        batch = orders[start_index:start_index + BATCH_SIZE]

        batch_start = time.perf_counter_ns()

        for side, price, quantity in batch:
            engine.submit(side, price, quantity)

        batch_end = time.perf_counter_ns()

        elapsed_ns = batch_end - batch_start
        average_us = elapsed_ns / len(batch) / 1000

        batch_rows.append({
            "run": run_number,
            "batch": batch_number,
            "orders": len(batch),
            "elapsed_ns": elapsed_ns,
            "average_us_per_order": average_us,
        })

    total_end = time.perf_counter_ns()

    total_elapsed_ns = total_end - total_start
    total_seconds = total_elapsed_ns / 1_000_000_000

    # Percentiles below describe batch-average latency, not
    # the latency distribution of individual orders.
    batch_averages = [
        row["average_us_per_order"] for row in batch_rows
    ]

    result = {
        "run": run_number,
        "orders": len(orders),
        "elapsed_seconds": total_seconds,
        "throughput_orders_sec": len(orders) / total_seconds,
        "batch_mean_us": statistics.fmean(batch_averages),
        "batch_p50_us": percentile(batch_averages, 50),
        "batch_p95_us": percentile(batch_averages, 95),
        "batch_p99_us": percentile(batch_averages, 99),
        "batch_max_us": max(batch_averages),
        "trades": engine.stats()["trades"],
        "volume": engine.stats()["volume"],
        "resting_orders": engine.stats()["resting_orders"],
        "last_trade_price": engine.stats()["last_trade_price"],
    }

    return result, batch_rows


# -------------------- SAMPLED CALL LATENCY --------------------

def run_sampled_latency(orders):
    """
    Measure every Nth submit call.

    The measured call has timer overhead. The sample is not a
    complete per-order latency distribution and is not used for
    throughput calculation.
    """
    engine = make_engine()
    samples = []

    for index, (side, price, quantity) in enumerate(orders):
        if index % SAMPLE_EVERY == 0:
            start_ns = time.perf_counter_ns()

            result = engine.submit(side, price, quantity)

            end_ns = time.perf_counter_ns()

            samples.append({
                "order_index": index + 1,
                "side": side,
                "price": price,
                "quantity": quantity,
                "elapsed_us": (end_ns - start_ns) / 1000,
                "status": result["status"],
                "filled_quantity": result["filled_quantity"],
                "remaining_quantity": result["remaining_quantity"],
            })
        else:
            engine.submit(side, price, quantity)

    return samples


# -------------------- REPORTING --------------------

def print_batch_table(results):
    print()
    print("=" * 100)
    print("BATCH-AVERAGE LATENCY (microseconds per order)")
    print("=" * 100)

    print(
        f"{'Run':>4} {'Throughput':>15} {'Mean':>12} "
        f"{'P50':>12} {'P95':>12} {'P99':>12} {'Max batch':>14}"
    )
    print("-" * 100)

    for row in results:
        print(
            f"{row['run']:>4} "
            f"{row['throughput_orders_sec']:>15,.0f} "
            f"{row['batch_mean_us']:>12.4f} "
            f"{row['batch_p50_us']:>12.4f} "
            f"{row['batch_p95_us']:>12.4f} "
            f"{row['batch_p99_us']:>12.4f} "
            f"{row['batch_max_us']:>14.4f}"
        )


def print_throughput_summary(results):
    values = [row["throughput_orders_sec"] for row in results]

    mean_value = statistics.fmean(values)

    print()
    print("=" * 60)
    print("THROUGHPUT SUMMARY")
    print("=" * 60)
    print(f"Orders per run : {TOTAL_ORDERS:,}")
    print(f"Runs           : {len(results)}")
    print(f"Mean           : {mean_value:,.0f} orders/sec")
    print(f"Median         : {statistics.median(values):,.0f} orders/sec")
    print(f"Minimum        : {min(values):,.0f} orders/sec")
    print(f"Maximum        : {max(values):,.0f} orders/sec")

    if mean_value:
        spread = (max(values) - min(values)) / mean_value * 100
        print(f"Max-min spread : {spread:.2f}% of mean throughput")


def print_sampled_latency(samples):
    values = [row["elapsed_us"] for row in samples]

    print()
    print("=" * 60)
    print("SAMPLED INDIVIDUAL-CALL LATENCY (microseconds)")
    print("=" * 60)
    print(f"Sampling interval: every {SAMPLE_EVERY}th order")
    print(f"Sample count     : {len(values):,}")

    if not values:
        print("No latency samples were collected.")
        return

    print(f"Mean             : {statistics.fmean(values):.4f} us")
    print(f"Minimum          : {min(values):.4f} us")
    print(f"P50              : {percentile(values, 50):.4f} us")
    print(f"P95              : {percentile(values, 95):.4f} us")
    print(f"P99              : {percentile(values, 99):.4f} us")
    print(f"Maximum          : {max(values):.4f} us")


def print_engine_stats(row):
    print()
    print("=" * 60)
    print("ENGINE STATISTICS - LAST BATCH RUN")
    print("=" * 60)
    print(f"Trades executed : {row['trades']:,}")
    print(f"Traded volume   : {row['volume']:,}")
    print(f"Resting orders  : {row['resting_orders']:,}")
    print(f"Last trade price: {row['last_trade_price']}")


# -------------------- MAIN --------------------

def main():
    if TOTAL_ORDERS <= 0 or TOTAL_RUNS <= 0:
        raise ValueError("TOTAL_ORDERS and TOTAL_RUNS must be positive")

    if WARMUP_ORDERS < 0 or BATCH_SIZE <= 0 or SAMPLE_EVERY <= 0:
        raise ValueError("Warm-up must be non-negative; batch and sample sizes must be positive")

    print("=" * 100)
    print("CHRONOSMATCH - LATENCY AND THROUGHPUT BENCHMARK")
    print("=" * 100)
    print(f"Orders per run : {TOTAL_ORDERS:,}")
    print(f"Warm-up orders : {WARMUP_ORDERS:,}")
    print(f"Runs           : {TOTAL_RUNS}")
    print(f"Batch size     : {BATCH_SIZE}")
    print(f"Sample interval: {SAMPLE_EVERY}")

    all_orders = generate_orders(
        WARMUP_ORDERS + TOTAL_ORDERS,
        RANDOM_SEED,
    )

    warmup_orders = all_orders[:WARMUP_ORDERS]
    measured_orders = all_orders[WARMUP_ORDERS:]

    print("\nWarming up engine...")
    warm_up(warmup_orders)

    results = []
    all_batch_rows = []

    print("\nRunning batch benchmarks...")

    for run_number in range(1, TOTAL_RUNS + 1):
        result, batch_rows = run_batch_benchmark(
            measured_orders, run_number
        )

        results.append(result)
        all_batch_rows.extend(batch_rows)

        print(
            f"Run {run_number}: "
            f"{result['throughput_orders_sec']:,.0f} orders/sec | "
            f"Batch mean {result['batch_mean_us']:.4f} us/order"
        )

    print_batch_table(results)
    print_throughput_summary(results)
    print_engine_stats(results[-1])

    print("\nRunning separate sampled-latency diagnostic...")
    samples = run_sampled_latency(measured_orders)
    print_sampled_latency(samples)

    # Save all reports in the project directory.
    write_csv(
        "benchmark_runs.csv",
        results,
        list(results[0].keys()),
    )

    write_csv(
        "benchmark_batches.csv",
        all_batch_rows,
        list(all_batch_rows[0].keys()),
    )

    write_csv(
        "benchmark_sampled_latency.csv",
        samples,
        list(samples[0].keys()) if samples else [
            "order_index", "side", "price", "quantity",
            "elapsed_us", "status", "filled_quantity",
            "remaining_quantity",
        ],
    )

    print()
    print("=" * 100)
    print("NOTES")
    print("=" * 100)
    print("- Batch percentiles describe batch averages, not individual orders.")
    print("- Individual-call percentiles describe sampled calls only.")
    print("- Sampling and timer overhead affect measured call latency.")
    print("- Throughput excludes per-order timers but includes batch timing.")
    print("- CSV files are overwritten each time this script runs.")
    print("- This benchmark alone does not establish production HFT readiness.")
    print("=" * 100)


if __name__ == "__main__":
    try:
        main()
    except ImportError as exc:
        print(f"\nERROR: Could not import matching_engine: {exc}")
        print("Build the Cython extension and run this script again.")
        raise SystemExit(1)
    except (OverflowError, MemoryError) as exc:
        print(f"\nERROR: Benchmark could not finish: {exc}")
        print("Check engine capacity and available memory.")
        raise SystemExit(1)
