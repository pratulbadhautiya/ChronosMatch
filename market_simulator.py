
import random
import time
import statistics

from matching_engine import MatchingEngine


def run_benchmark(number_of_orders=10_000):
    engine = MatchingEngine(capacity=number_of_orders + 1)
    latencies_ns = []

    start = time.perf_counter_ns()

    for _ in range(number_of_orders):
        side = random.choice((1, -1))
        price = random.randint(99, 101)
        quantity = random.randint(1, 10)

        order_start = time.perf_counter_ns()
        engine.submit(side, price, quantity)
        order_end = time.perf_counter_ns()

        latencies_ns.append(order_end - order_start)

    total_ns = time.perf_counter_ns() - start
    stats = engine.stats()

    sorted_latencies = sorted(latencies_ns)
    p99_index = min(
        len(sorted_latencies) - 1,
        int(len(sorted_latencies) * 0.99)
    )

    print("\n===== CHRONOSMATCH BENCHMARK =====")
    print(f"Orders submitted : {number_of_orders:,}")
    print(f"Elapsed time     : {total_ns / 1_000_000:.2f} ms")
    print(f"Throughput       : {number_of_orders / (total_ns / 1e9):,.0f} orders/sec")
    print(f"Average latency  : {statistics.mean(latencies_ns) / 1_000:.2f} µs")
    print(f"P99 latency      : {sorted_latencies[p99_index] / 1_000:.2f} µs")
    print(f"Trades executed  : {stats['trades']:,}")
    print(f"Traded volume    : {stats['volume']:,}")
    print(f"Resting orders   : {stats['resting_orders']:,}")
    print("==================================\n")


if __name__ == "__main__":
    run_benchmark()
