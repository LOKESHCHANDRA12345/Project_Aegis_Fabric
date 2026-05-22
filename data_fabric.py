import duckdb
import random
import string

# Connect to DuckDB database
conn = duckdb.connect('enterprise_fabric.db')

# Create the ledger_entries table
conn.execute('''
    CREATE TABLE IF NOT EXISTS ledger_entries (
        entry_id INTEGER,
        account_id VARCHAR,
        region VARCHAR,
        amount DOUBLE
    )
''')

# Define regions
regions = ['AMER', 'EMEA', 'APAC']

# Generate 25,000 random entries
batch_size = 1000
total_entries = 25000

print(f"Generating {total_entries} ledger entries...")

for batch_start in range(0, total_entries, batch_size):
    batch_end = min(batch_start + batch_size, total_entries)
    batch_data = []

    for i in range(batch_start, batch_end):
        entry_id = i + 1
        account_id = f"ACC-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        region = random.choice(regions)
        amount = round(random.uniform(100.0, 999999.99), 2)

        batch_data.append((entry_id, account_id, region, amount))

    # Insert batch
    conn.executemany(
        'INSERT INTO ledger_entries (entry_id, account_id, region, amount) VALUES (?, ?, ?, ?)',
        batch_data
    )

    print(f"Inserted {batch_end} entries...")

# Verify the data
result = conn.execute('SELECT COUNT(*) as total_entries FROM ledger_entries').fetchall()
print(f"\nTotal entries in table: {result[0][0]}")

# Show sample data
print("\nSample entries:")
sample = conn.execute('SELECT * FROM ledger_entries LIMIT 5').fetchall()
for row in sample:
    print(f"  {row}")

# Show regional breakdown
print("\nRegional breakdown:")
breakdown = conn.execute('''
    SELECT region, COUNT(*) as count, AVG(amount) as avg_amount
    FROM ledger_entries
    GROUP BY region
    ORDER BY region
''').fetchall()
for row in breakdown:
    print(f"  {row[0]}: {row[1]} entries, Avg Amount: ${row[2]:,.2f}")

conn.close()
print("\nDatabase populated successfully!")
