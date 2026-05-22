import duckdb
import polars as pl
import time
from pathlib import Path

print("=" * 80)
print("DATA ACCESS LAYER BENCHMARK")
print("=" * 80)

db_path = 'enterprise_fabric.db'
parquet_path = Path('./optimized_cache/index.parquet')

# Benchmark parameters
WARMUP_ITERATIONS = 3
BENCHMARK_ITERATIONS = 10

results = {}

# ============================================================================
# BENCHMARK 1: Unoptimized Raw DuckDB Query
# ============================================================================
print("\n[1] Benchmarking unoptimized DuckDB query...")
print("    Query: SELECT SUM(amount) FROM ledger_entries WHERE region = 'AMER'")

conn = duckdb.connect(db_path)

# Warmup runs
for i in range(WARMUP_ITERATIONS):
    conn.execute("SELECT SUM(amount) FROM ledger_entries WHERE region = 'AMER'").fetchone()

# Benchmark runs
execution_times = []
for i in range(BENCHMARK_ITERATIONS):
    start_time = time.perf_counter()
    result = conn.execute("SELECT SUM(amount) FROM ledger_entries WHERE region = 'AMER'").fetchone()[0]
    end_time = time.perf_counter()

    execution_times.append((end_time - start_time) * 1000)  # Convert to milliseconds

unoptimized_avg = sum(execution_times) / len(execution_times)
unoptimized_min = min(execution_times)
unoptimized_max = max(execution_times)
unoptimized_result = result

print(f"    [OK] Average: {unoptimized_avg:.4f} ms")
print(f"    [OK] Min: {unoptimized_min:.4f} ms")
print(f"    [OK] Max: {unoptimized_max:.4f} ms")
print(f"    [OK] Result: {unoptimized_result:,.2f}")

results['unoptimized'] = {
    'avg': unoptimized_avg,
    'min': unoptimized_min,
    'max': unoptimized_max,
    'result': unoptimized_result
}

conn.close()

# ============================================================================
# BENCHMARK 2: Optimized Parquet Index Query
# ============================================================================
print("\n[2] Benchmarking optimized Parquet index query...")

if not parquet_path.exists():
    print(f"    [SKIP] Parquet cache not found at {parquet_path}")
    print(f"    [INFO] Run optimizer_agent.py first to generate the optimized index.")
    optimized_available = False
else:
    print(f"    [OK] Parquet cache found at {parquet_path}")
    print(f"    [OK] File size: {parquet_path.stat().st_size / 1024:.2f} KB")

    # Warmup runs
    for i in range(WARMUP_ITERATIONS):
        df = pl.read_parquet(parquet_path)
        result = df.select(pl.col('amount').sum()).item()

    # Benchmark runs
    execution_times = []
    for i in range(BENCHMARK_ITERATIONS):
        start_time = time.perf_counter()
        df = pl.read_parquet(parquet_path)
        result = df.select(pl.col('amount').sum()).item()
        end_time = time.perf_counter()

        execution_times.append((end_time - start_time) * 1000)  # Convert to milliseconds

    optimized_avg = sum(execution_times) / len(execution_times)
    optimized_min = min(execution_times)
    optimized_max = max(execution_times)
    optimized_result = result

    print(f"    [OK] Average: {optimized_avg:.4f} ms")
    print(f"    [OK] Min: {optimized_min:.4f} ms")
    print(f"    [OK] Max: {optimized_max:.4f} ms")
    print(f"    [OK] Result: {optimized_result:,.2f}")

    results['optimized'] = {
        'avg': optimized_avg,
        'min': optimized_min,
        'max': optimized_max,
        'result': optimized_result
    }

    optimized_available = True

# ============================================================================
# GENERATE COMPARISON MATRIX
# ============================================================================
print("\n" + "=" * 80)
print("BENCHMARK SUMMARY")
print("=" * 80)

if optimized_available:
    # Calculate improvement metrics
    speedup = results['unoptimized']['avg'] / results['optimized']['avg']
    improvement = ((results['unoptimized']['avg'] - results['optimized']['avg']) / results['unoptimized']['avg']) * 100
    time_saved_per_query = results['unoptimized']['avg'] - results['optimized']['avg']

    # Create comparison table
    comparison_data = [
        ['Metric', 'Unoptimized (DuckDB)', 'Optimized (Parquet)', 'Improvement'],
        ['-' * 12, '-' * 22, '-' * 22, '-' * 18],
        ['Average Time (ms)', f"{results['unoptimized']['avg']:.4f}", f"{results['optimized']['avg']:.4f}", f"{improvement:+.1f}%"],
        ['Min Time (ms)', f"{results['unoptimized']['min']:.4f}", f"{results['optimized']['min']:.4f}", '-'],
        ['Max Time (ms)', f"{results['unoptimized']['max']:.4f}", f"{results['optimized']['max']:.4f}", '-'],
        ['Result Value', f"{results['unoptimized']['result']:,.2f}", f"{results['optimized']['result']:,.2f}", 'Match' if results['unoptimized']['result'] == results['optimized']['result'] else 'MISMATCH'],
        ['-' * 12, '-' * 22, '-' * 22, '-' * 18],
        ['Speedup Factor', '1.0x (baseline)', f"{speedup:.2f}x faster", f"{(speedup - 1) * 100:.0f}% faster"],
        ['Time Saved / Query', '-', f"-{time_saved_per_query:.4f} ms", '-'],
    ]

    print("\n")
    for row in comparison_data:
        print(f"  {row[0]:<15} | {row[1]:<22} | {row[2]:<22} | {row[3]:<18}")

    print("\n" + "-" * 80)
    print(f"[OK] Optimization delivers {speedup:.2f}x speedup ({improvement:.1f}% improvement)")
    print(f"[OK] Each query execution saves {time_saved_per_query:.4f} ms with Parquet index")
    if results['unoptimized']['result'] == results['optimized']['result']:
        print(f"[OK] Results validated: Both approaches return identical results")
    else:
        print(f"[ERROR] WARNING: Result mismatch detected!")

else:
    # Show unoptimized-only results
    summary_data = [
        ['Metric', 'Unoptimized (DuckDB)'],
        ['-' * 12, '-' * 22],
        ['Average Time (ms)', f"{results['unoptimized']['avg']:.4f}"],
        ['Min Time (ms)', f"{results['unoptimized']['min']:.4f}"],
        ['Max Time (ms)', f"{results['unoptimized']['max']:.4f}"],
        ['Result Value', f"{results['unoptimized']['result']:,.2f}"],
    ]

    print("\n")
    for row in summary_data:
        print(f"  {row[0]:<15} | {row[1]:<22}")

    print("\n" + "-" * 80)
    print("[INFO] Optimized index not available. Run optimizer_agent.py to enable full comparison.")

print("\n" + "=" * 80)
