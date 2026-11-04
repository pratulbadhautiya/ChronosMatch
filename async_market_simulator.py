
import asyncio
import random
import time

from ring_buffer import RingBuffer
from matching_engine import MatchingEngine

TOTAL_ORDERS = 100_000
BATCH_SIZE = 256


async def producer(buffer, total_orders):
    """Generate orders and put them into the ring buffer."""
    produced = 0

    while produced < total_orders:
        batch_count = min(BATCH_SIZE, total_orders - produced)

        for _ in range(batch_count):
            side = random.choice((1, -1))
            price = random.randint(99, 101)
            quantity = random.randint(1, 10)

            while not buffer.put(side, price, quantity):
                await asyncio.sleep(0)

            produced += 1

        await asyncio.sleep(0)

    return produced


async def consumer(buffer, engine, total_orders):
    """Read buffered orders and submit them to the Cython engine."""
    consumed = 0

    while consumed < total_orders:
        order = buffer.get()

        if order is None:
            await asyncio.sleep(0)
            continue

        engine.submit(
            order["side"],
            order["price"],
            order["quantity"],
        )
        consumed += 1

        if consumed % BATCH_SIZE == 0:
            await asyncio.sleep(0)

    return consumed


async def main():
    buffer = RingBuffer(capacity=1024)
    engine = MatchingEngine(capacity=TOTAL_ORDERS + 1)

    try:
        print("ChronosMatch Integrated Market Simulator")
        print(f"Target orders: {TOTAL_ORDERS:,}")

        start = time.perf_counter()

        produced, consumed = await asyncio.gather(
            producer(buffer, TOTAL_ORDERS),
            consumer(buffer, engine, TOTAL_ORDERS),
        )

        elapsed = time.perf_counter() - start
        stats = engine.stats()

        print("\n===== INTEGRATED RESULTS =====")
        print(f"Orders produced : {produced:,}")
        print(f"Orders consumed : {consumed:,}")
        print(f"Elapsed time    : {elapsed:.3f} seconds")
        print(f"Throughput      : {consumed / elapsed:,.0f} orders/sec")
        print(f"Trades executed : {stats['trades']:,}")
        print(f"Traded volume   : {stats['volume']:,}")
        print(f"Resting orders  : {stats['resting_orders']:,}")
        print(f"Last trade price: {stats['last_trade_price']}")
        print("All orders consumed:", produced == consumed)
        print("==============================")

    finally:
        buffer.close()


if __name__ == "__main__":
    asyncio.run(main())
