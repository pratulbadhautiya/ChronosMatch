
# ChronosMatch
### Cython-Powered Limit Order Matching Engine & Market Simulator

ChronosMatch is a Python-based trading engine project that simulates a limit-order market using a Cython-compiled matching engine. It includes market simulation scripts, a Rich-powered live terminal dashboard, an mmap-based ring buffer experiment, and performance/testing utilities.

## Features

- **Cython matching engine:** Compiled extension for order processing.
- **Price-time matching:** Matches compatible buy and sell orders according to price priority.
- **Live terminal dashboard:** Displays market depth, recent orders, trade activity, and engine statistics using Rich.
- **Market simulation:** Generates simulated buy and sell limit orders.
- **Ring buffer experiment:** Uses memory-mapped storage to explore producer-consumer data transfer.
- **Benchmarking:** Scripts for measuring throughput and sampled latency.
- **Testing:** Unit, capacity-edge, randomized matching, and ring-buffer tests.

## Project Structure

```text
ChronosMatch-Git/
├── matching_engine.pyx
├── matching_engine.c
├── matching_engine.cp313-win_amd64.pyd
├── matching_engine2.pyx
├── matching_engine_backup.pyx
├── ring_buffer.py
├── terminal_dashboard.py
├── market_simulator.py
├── async_market_simulator.py
├── latency_benchmark.py
├── stress_test.py
├── setup.py
├── test_matching_engine.py
├── test_matching_randomized.py
├── test_capacity_edge.py
├── test_ring_buffer.py
├── benchmark_runs.csv
├── benchmark_batches.csv
└── benchmark_sampled_latency.csv
```

Generated files, test artifacts, and local build outputs may vary by environment.

## Requirements

- Windows
- Python 3.13, 64-bit
- Microsoft C++ Build Tools compatible with your Python installation
- Cython and setuptools for building the extension
- Rich for the terminal dashboard

## Installation

Open PowerShell in the project directory:

```powershell
cd D:\gitdemo\ChronosMatch-Git
```

Install the required packages:

```powershell
py -3.13 -m pip install cython setuptools rich
```

### Run the Existing Compiled Engine

If the compatible compiled extension is already present, verify it:

```powershell
py -3.13 -c "from matching_engine import MatchingEngine; e=MatchingEngine(); print(e.stats()); print(e.snapshot())"
```

### Build the Cython Extension

Use an **x64 Native Tools Command Prompt for Visual Studio** and navigate to the project directory.

Verify that the compiler targets x64 and that Python is 64-bit before rebuilding.

```powershell
py -3.13 setup.py build_ext --inplace
```

The build environment must use an x64-compatible compiler toolchain. A 32-bit linker configuration can fail even when Python is 64-bit.

## Run the Live Terminal Dashboard

```powershell
py -3.13 .\terminal_dashboard.py
```

The dashboard displays:

- Submitted order count
- Executed trades and traded quantity
- Orders-per-second estimate
- Resting order count
- Last trade price
- Aggregated bid/ask depth
- Recent orders and trade activity

The current dashboard generates simulated orders; it does not connect to a live exchange. Press `Ctrl+C` to stop it.

## Run the Simulators

Run the scripts individually:

```powershell
py -3.13 .\market_simulator.py
```

```powershell
py -3.13 .\async_market_simulator.py
```

## Run Tests

```powershell
py -3.13 -m unittest -v test_matching_engine.py
```

```powershell
py -3.13 .\test_capacity_edge.py
```

```powershell
py -3.13 .\test_matching_randomized.py
```

```powershell
py -3.13 .\test_ring_buffer.py
```

## Benchmarking

Run the benchmark script:

```powershell
py -3.13 .\latency_benchmark.py
```

The project also contains CSV files with benchmark-related data. Results depend on the machine, compiler configuration, workload, and measurement method.

Do not interpret local benchmark results as a guarantee of production trading latency. Sampled function-call latency and overall order throughput are different measurements.

## Technical Notes and Limitations

- This project is a trading-engine simulation and learning project.
- The terminal market data is simulated rather than supplied by a real exchange.
- An mmap-backed ring buffer experiment does not, by itself, establish safe, atomic, zero-copy interprocess communication.
- Production use would require additional work on concurrency, order cancellation and replacement, persistence, recovery, validation, risk controls, and deployment.
- Benchmark results are environment-dependent and should be reproduced under controlled conditions.

## Future Improvements

- Add order cancellation and replacement.
- Add persistent order and trade records.
- Improve benchmark reproducibility and percentile reporting.
- Add risk checks and configurable trading scenarios.
- Improve monitoring, logging, and fault recovery.
- Evaluate interprocess communication and concurrency guarantees.

## Author

**Pratul Badhautiya**

GitHub: [@pratulbadhautiya](https://github.com/pratulbadhautiya)

## Disclaimer

ChronosMatch is an educational and experimental software project. It is not a production-ready trading system and should not be used to execute real financial transactions.
