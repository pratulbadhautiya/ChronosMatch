
# matching_engine.pyx
# Cython-based price-time priority matching engine

from libc.stdint cimport int64_t
from libc.stdlib cimport malloc, free

cdef struct Order:
    int64_t order_id
    int64_t price
    int64_t quantity
    int side  # 1 = BUY, -1 = SELL


cdef class MatchingEngine:
    cdef Order* orders
    cdef int capacity
    cdef int count
    cdef int64_t next_id
    cdef int64_t last_trade_price
    cdef int64_t trades
    cdef int64_t volume

    def __cinit__(self, int capacity=10000):
        self.orders = NULL

        if capacity < 1:
            raise ValueError("Capacity must be positive")

        self.orders = <Order*>malloc(capacity * sizeof(Order))
        if self.orders == NULL:
            raise MemoryError("Unable to allocate order book")

        self.capacity = capacity
        self.count = 0
        self.next_id = 1
        self.last_trade_price = 0
        self.trades = 0
        self.volume = 0

    def __dealloc__(self):
        if self.orders != NULL:
            free(self.orders)

    cpdef dict submit(self, int side, int64_t price, int64_t quantity):
        cdef int i, j, best_index
        cdef int64_t order_id
        cdef int64_t filled = 0
        cdef int64_t fill_qty
        cdef int64_t remaining = quantity

        if side != 1 and side != -1:
            raise ValueError("side must be 1 (BUY) or -1 (SELL)")
        if price <= 0 or quantity <= 0:
            raise ValueError("price and quantity must be positive")

        order_id = self.next_id
        self.next_id += 1

        # Repeatedly select the best-priced crossing opposite order.
        # Array order breaks price ties, preserving FIFO priority.
        while remaining > 0:
            best_index = -1

            for i in range(self.count):
                if side == 1:
                    # Incoming BUY can match SELL orders at or below its price.
                    if (self.orders[i].side == -1
                            and self.orders[i].price <= price):
                        if (best_index == -1
                                or self.orders[i].price
                                < self.orders[best_index].price):
                            best_index = i
                else:
                    # Incoming SELL can match BUY orders at or above its price.
                    if (self.orders[i].side == 1
                            and self.orders[i].price >= price):
                        if (best_index == -1
                                or self.orders[i].price
                                > self.orders[best_index].price):
                            best_index = i

            # No more crossing orders.
            if best_index == -1:
                break

            fill_qty = remaining
            if self.orders[best_index].quantity < fill_qty:
                fill_qty = self.orders[best_index].quantity

            remaining -= fill_qty
            self.orders[best_index].quantity -= fill_qty
            filled += fill_qty

            self.trades += 1
            self.volume += fill_qty
            # Execution price is the resting order's price.
            self.last_trade_price = self.orders[best_index].price

            # Remove a fully filled resting order.
            if self.orders[best_index].quantity == 0:
                for j in range(best_index, self.count - 1):
                    self.orders[j] = self.orders[j + 1]
                self.count -= 1

        # Store the unfilled remainder as a new resting order.
        if remaining > 0:
            if self.count >= self.capacity:
                raise OverflowError(
                    "Order book capacity reached; remaining quantity not stored"
                )

            self.orders[self.count].order_id = order_id
            self.orders[self.count].price = price
            self.orders[self.count].quantity = remaining
            self.orders[self.count].side = side
            self.count += 1

        if remaining == 0:
            status = "FILLED"
        elif filled > 0:
            status = "PARTIAL"
        else:
            status = "RESTING"

        return {
            "order_id": order_id,
            "filled_quantity": filled,
            "remaining_quantity": remaining,
            "status": status,
        }

    cpdef list snapshot(self):
        cdef int i
        cdef list result = []

        for i in range(self.count):
            result.append({
                "order_id": self.orders[i].order_id,
                "side": "BUY" if self.orders[i].side == 1 else "SELL",
                "price": self.orders[i].price,
                "quantity": self.orders[i].quantity,
            })

        return result

    cpdef dict stats(self):
        return {
            "resting_orders": self.count,
            "trades": self.trades,
            "volume": self.volume,
            "last_trade_price": self.last_trade_price,
        }
