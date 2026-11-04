import asyncio
import random
import time
from collections import deque

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from matching_engine import MatchingEngine

console = Console()

ENGINE_CAPACITY = 100_000
TOTAL_ORDERS = 20_000
UPDATE_INTERVAL = 0.15
TRADE_HISTORY_LIMIT = 10

engine = MatchingEngine(capacity=ENGINE_CAPACITY)
recent_orders = deque(maxlen=12)

metrics = {
    "submitted": 0,
    "buy_orders": 0,
    "sell_orders": 0,
    "started": 0.0,
    "elapsed": 0.0,
    "finished": False,
}


def generate_order():
    side = random.choice([1, -1])
    price = random.randint(95, 105)
    quantity = random.randint(1, 20)
    return side, price, quantity


def build_dashboard():
    stats = engine.stats()
    snapshot = engine.snapshot()

    bids, asks = {}, {}

    for order in snapshot:
        price = order["price"]
        qty = order["quantity"]

        if order["side"] == "BUY":
            bids[price] = bids.get(price, 0) + qty
        else:
            asks[price] = asks.get(price, 0) + qty

    depth = Table(
        title="LIVE ORDER BOOK",
        box=box.SIMPLE_HEAVY,
        expand=True,
    )
    depth.add_column("Bid Qty", justify="right", style="green")
    depth.add_column("Bid Price", justify="right", style="bold green")
    depth.add_column("Ask Price", justify="right", style="bold red")
    depth.add_column("Ask Qty", justify="right", style="red")

    bid_levels = sorted(bids.items(), reverse=True)[:8]
    ask_levels = sorted(asks.items())[:8]

    for i in range(max(1, len(bid_levels), len(ask_levels))):
        bid = bid_levels[i] if i < len(bid_levels) else None
        ask = ask_levels[i] if i < len(ask_levels) else None

        depth.add_row(
            str(bid[1]) if bid else "-",
            f"{bid[0]:.2f}" if bid else "-",
            f"{ask[0]:.2f}" if ask else "-",
            str(ask[1]) if ask else "-",
        )

    elapsed = max(
        time.perf_counter() - metrics["started"],
        0.000001,
    )
    throughput = metrics["submitted"] / elapsed

    status = "COMPLETED" if metrics["finished"] else "RUNNING"
    status_style = "green" if metrics["finished"] else "yellow"

    summary = Table.grid(expand=True, padding=(0, 1))
    for _ in range(4):
        summary.add_column(ratio=1)

    summary.add_row(
        Panel(
            f"[bold cyan]{metrics['submitted']:,}[/]\nOrders submitted"
        ),
        Panel(
            f"[bold green]{stats['trades']:,}[/]\nTrades executed"
        ),
        Panel(
            f"[bold yellow]{stats['volume']:,}[/]\nTraded quantity"
        ),
        Panel(
            f"[bold magenta]{throughput:,.0f}[/]\nOrders/sec"
        ),
    )

    summary.add_row(
        Panel(
            f"[bold]{stats['resting_orders']:,}[/]\nResting orders"
        ),
        Panel(
            f"[bold]{stats['last_trade_price']:.2f}[/]\nLast trade price"
        ),
        Panel(
            f"[green]{metrics['buy_orders']:,}[/]\nBuy orders"
        ),
        Panel(
            f"[red]{metrics['sell_orders']:,}[/]\nSell orders"
        ),
    )

    order_table = Table(
        title="RECENT ORDERS",
        box=box.SIMPLE,
        expand=True,
    )

    for name in ("Side", "Price", "Qty", "Filled", "Status"):
        order_table.add_column(
            name,
            justify="right" if name != "Side" else "left",
        )

    for order in recent_orders:
        color = "green" if order["side"] == "BUY" else "red"

        order_table.add_row(
            f"[{color}]{order['side']}[/]",
            f"{order['price']:.2f}",
            str(order["quantity"]),
            str(order["filled"]),
            order["status"],
        )

    # Fetch actual executions directly from the matching engine.
    trades_table = Table(
        title="ACTUAL ENGINE TRADE HISTORY",
        box=box.SIMPLE,
        expand=True,
    )

    trades_table.add_column("Trade ID", justify="right")
    trades_table.add_column("Buyer Order ID", justify="right")
    trades_table.add_column("Seller Order ID", justify="right")
    trades_table.add_column("Price", justify="right")
    trades_table.add_column("Quantity", justify="right")

    actual_trades = engine.get_trades()

    if actual_trades:
        # Display the latest executions first.
        for trade in reversed(actual_trades[-TRADE_HISTORY_LIMIT:]):
            trades_table.add_row(
                str(trade["trade_id"]),
                str(trade["buy_order_id"]),
                str(trade["sell_order_id"]),
                f"{trade['price']:.2f}",
                str(trade["quantity"]),
            )
    else:
        trades_table.add_row("-", "-", "Waiting for trades...", "-", "-")

    footer = Text.from_markup(
        f"Status: [{status_style}]{status}[/]  |  "
        "Press Ctrl+C to exit"
    )

    return Group(
        Panel(
            "[bold cyan]CHRONOSMATCH[/]  "
            "[white]Matching Engine Simulator[/]\n"
            "[dim]Actual engine executions | Price-time matching[/]",
            border_style="cyan",
        ),
        summary,
        depth,
        order_table,
        trades_table,
        Panel(footer, box=box.ROUNDED),
    )


async def run_simulation(live):
    metrics["started"] = time.perf_counter()
    last_refresh = 0.0

    for i in range(TOTAL_ORDERS):
        side, price, quantity = generate_order()
        side_name = "BUY" if side == 1 else "SELL"

        if side == 1:
            metrics["buy_orders"] += 1
        else:
            metrics["sell_orders"] += 1

        result = engine.submit(side, price, quantity)
        metrics["submitted"] += 1

        recent_orders.appendleft({
            "side": side_name,
            "price": price,
            "quantity": quantity,
            "filled": result["filled_quantity"],
            "status": str(result["status"]),
        })

        now = time.perf_counter()

        if now - last_refresh >= UPDATE_INTERVAL:
            live.update(build_dashboard())
            last_refresh = now

        if (i + 1) % 100 == 0:
            await asyncio.sleep(0)

    metrics["elapsed"] = time.perf_counter() - metrics["started"]
    metrics["finished"] = True

    live.update(build_dashboard())


async def main():
    with Live(
        console=console,
        refresh_per_second=8,
        screen=True,
        transient=False,
    ) as live:
        await run_simulation(live)

        # Keep the completed dashboard on screen.
        while True:
            live.update(build_dashboard())
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

    console.print("\n[bold cyan]ChronosMatch stopped.[/]")
    console.print(f"Orders submitted: {metrics['submitted']:,}")
    console.print(f"Elapsed time: {metrics['elapsed']:.3f} seconds")
    console.print(f"Final statistics: {engine.stats()}")