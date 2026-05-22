import duckdb
import polars as pl
from pathlib import Path

print('[Optimization] Creating optimized Parquet cache...')

# Connect to DuckDB database
conn = duckdb.connect('enterprise_fabric.db')

# Read AMER region data
df = conn.execute('SELECT amount FROM ledger_entries WHERE region = \'AMER\'').fetchall()

# Convert to Polars and save as Parquet
amounts = [row[0] for row in df]
df_polars = pl.DataFrame({'amount': amounts})

# Create cache directory if needed
Path('./optimized_cache').mkdir(exist_ok=True)

# Save as Parquet
parquet_path = './optimized_cache/index.parquet'
df_polars.write_parquet(parquet_path)

print(f'[OK] Optimized cache created: {parquet_path}')
print(f'  File size: {Path(parquet_path).stat().st_size / 1024:.2f} KB')
print(f'  Records: {len(amounts)}')

conn.close()
