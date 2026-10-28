
import mmap
import os
import struct

# Ring buffer configuration
CAPACITY = 1024

# Fields: sequence, side, price, quantity
# Q = unsigned 64-bit
# i = signed 32-bit
# q = signed 64-bit
RECORD = struct.Struct("<Q i q q")
HEADER = struct.Struct("<QQ")  # write_index, read_index

HEADER_SIZE = HEADER.size
SLOT_SIZE = RECORD.size
FILE_SIZE = HEADER_SIZE + CAPACITY * SLOT_SIZE

MAX_INT64 = (1 << 63) - 1


class RingBuffer:
    def __init__(self, path="chronos_ring.bin", capacity=CAPACITY):
        # Validate capacity before creating or truncating the file.
        if (
            isinstance(capacity, bool)
            or not isinstance(capacity, int)
            or capacity <= 0
        ):
            raise ValueError("capacity must be a positive integer")

        self.capacity = capacity
        self.record = RECORD
        self.header = HEADER
        self.slot_size = SLOT_SIZE
        self.header_size = HEADER_SIZE
        self.file_size = HEADER_SIZE + capacity * SLOT_SIZE
        self.path = path

        # Create/reset the backing file for this run.
        with open(path, "wb") as f:
            f.truncate(self.file_size)

        self.file = open(path, "r+b")

        try:
            self.mm = mmap.mmap(
                self.file.fileno(),
                self.file_size
            )
        except Exception:
            self.file.close()
            raise

        self.write_index = 0
        self.read_index = 0
        self._write_header()

    def _write_header(self):
        self.header.pack_into(
            self.mm,
            0,
            self.write_index,
            self.read_index
        )

    def put(self, side, price, quantity):
        # Validate all values before changing buffer state.
        if isinstance(side, bool) or not isinstance(side, int):
            raise ValueError("side must be 1 (BUY) or -1 (SELL)")

        if side not in (1, -1):
            raise ValueError("side must be 1 (BUY) or -1 (SELL)")

        if (
            isinstance(price, bool)
            or not isinstance(price, int)
            or price <= 0
            or price > MAX_INT64
        ):
            raise ValueError(
                "price must be a positive signed 64-bit integer"
            )

        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity <= 0
            or quantity > MAX_INT64
        ):
            raise ValueError(
                "quantity must be a positive signed 64-bit integer"
            )

        # Reject new orders when the buffer is full.
        if self.write_index - self.read_index >= self.capacity:
            return False

        offset = self.header_size + (
            self.write_index % self.capacity
        ) * self.slot_size

        self.record.pack_into(
            self.mm,
            offset,
            self.write_index + 1,
            side,
            price,
            quantity
        )

        self.write_index += 1
        self._write_header()

        return True

    def get(self):
        # Return None when the buffer is empty.
        if self.read_index >= self.write_index:
            return None

        offset = self.header_size + (
            self.read_index % self.capacity
        ) * self.slot_size

        sequence, side, price, quantity = (
            self.record.unpack_from(self.mm, offset)
        )

        self.read_index += 1
        self._write_header()

        return {
            "sequence": sequence,
            "side": side,
            "price": price,
            "quantity": quantity
        }

    def close(self):
        # Close resources safely and allow repeated close calls.
        mm = getattr(self, "mm", None)
        file = getattr(self, "file", None)

        if mm is not None and not mm.closed:
            mm.close()

        if file is not None and not file.closed:
            file.close()


if __name__ == "__main__":
    buffer = RingBuffer()

    try:
        print("Adding sample orders...")

        print("BUY added:", buffer.put(1, 100, 10))
        print("SELL added:", buffer.put(-1, 101, 5))

        print("\nReading orders:")
        print(buffer.get())
        print(buffer.get())

        print("Buffer empty:", buffer.get() is None)

    finally:
        buffer.close()

    print("\nRing buffer test finished.")
