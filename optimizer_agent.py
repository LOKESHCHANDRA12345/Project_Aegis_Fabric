import duckdb
import json
import os
from ollama import Client
from pathlib import Path

# Initialize clients
ollama_client = Client(host='http://localhost:11434')
db_path = 'enterprise_fabric.db'

# Ensure optimized_cache directory exists
cache_dir = Path('./optimized_cache')
cache_dir.mkdir(exist_ok=True)

# Target unoptimized query
TARGET_QUERY = "SELECT SUM(amount) FROM ledger_entries WHERE region = 'AMER'"

print("=" * 80)
print("OPTIMIZER AGENT - Query Optimization Pipeline")
print("=" * 80)

# Step 1: Connect and extract query execution footprint
print("\n[1] Connecting to database and extracting execution plan...")
conn = duckdb.connect(db_path)

try:
    explain_output = conn.execute(f"EXPLAIN {TARGET_QUERY}").fetchall()
    explain_text = "\n".join([str(row[0]) for row in explain_output])
    print(f"\nQuery: {TARGET_QUERY}")
    print(f"\nExecution Plan:\n{explain_text}")
except Exception as e:
    print(f"Error extracting execution plan: {e}")
    conn.close()
    exit(1)

# Step 2: Pass EXPLAIN plan to ollama model
print("\n[2] Sending execution plan to ollama (llama3.1:8b)...")

prompt = f"""You are a database optimization expert. I have an unoptimized SQL query and its execution plan.
Your job is to generate Python code that optimizes this query using Polars.

ORIGINAL QUERY:
{TARGET_QUERY}

EXECUTION PLAN:
{explain_text}

REQUIREMENTS:
1. Create a Python script that:
   - Uses polars to read the 'ledger_entries' table from the duckdb database 'enterprise_fabric.db'
   - Pre-filters and pre-aggregates data for the 'AMER' region
   - Saves the result as a binary Parquet index file at './optimized_cache/index.parquet'

2. Create a fast execution snippet that:
   - Reads the pre-computed Parquet file
   - Returns the final SUM(amount) calculation

Return ONLY a valid JSON object with this structure (no markdown, no extra text):
{{
    "optimization_script": "complete Python code using polars to create the index",
    "execution_script": "complete Python code to read from parquet and compute result",
    "explanation": "brief explanation of the optimization strategy"
}}"""

try:
    response = ollama_client.generate(
        model='llama3.1:8b',
        prompt=prompt,
        stream=False
    )

    response_text = response.get('response', '').strip()
    print(f"\nModel Response (first 500 chars):\n{response_text[:500]}...")

    # Parse JSON response
    json_start = response_text.find('{')
    json_end = response_text.rfind('}') + 1

    if json_start == -1 or json_end == 0:
        raise ValueError("No JSON object found in model response")

    json_str = response_text[json_start:json_end]
    optimization_payload = json.loads(json_str)

except json.JSONDecodeError as e:
    print(f"Error parsing JSON from model: {e}")
    print(f"Raw response: {response_text}")
    conn.close()
    exit(1)
except Exception as e:
    print(f"Error calling ollama: {e}")
    conn.close()
    exit(1)

print("\n[3] Executing optimization script...")

# Step 3: Execute optimization script with error handling and self-healing
max_retries = 2
retry_count = 0
optimization_success = False

while retry_count <= max_retries and not optimization_success:
    try:
        # Create a safe execution environment
        exec_globals = {
            'duckdb': duckdb,
            'Path': Path,
            '__builtins__': __builtins__,
        }

        optimization_script = optimization_payload.get('optimization_script', '')

        if not optimization_script:
            raise ValueError("No optimization_script in payload")

        print(f"Executing optimization script (attempt {retry_count + 1})...")
        exec(optimization_script, exec_globals)

        # Verify the parquet file was created
        parquet_path = Path('./optimized_cache/index.parquet')
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet file not created at {parquet_path}")

        print(f"✓ Optimization successful! Parquet file created at {parquet_path}")
        print(f"  File size: {parquet_path.stat().st_size / 1024:.2f} KB")
        optimization_success = True

    except Exception as e:
        print(f"✗ Error during optimization (attempt {retry_count + 1}): {type(e).__name__}: {e}")
        retry_count += 1

        if retry_count <= max_retries:
            print(f"\n[3.{retry_count}] Sending error back to model for self-healing...")

            error_prompt = f"""The optimization script failed with this error:

ERROR: {type(e).__name__}: {e}

ORIGINAL SCRIPT:
{optimization_script}

Please fix the script and return ONLY a valid JSON object with this structure:
{{
    "optimization_script": "corrected Python code",
    "execution_script": "corrected Python code to read from parquet",
    "explanation": "what was fixed"
}}"""

            try:
                error_response = ollama_client.generate(
                    model='llama3.1:8b',
                    prompt=error_prompt,
                    stream=False
                )

                error_response_text = error_response.get('response', '').strip()
                json_start = error_response_text.find('{')
                json_end = error_response_text.rfind('}') + 1
                json_str = error_response_text[json_start:json_end]
                optimization_payload = json.loads(json_str)

                print(f"Model correction received. Retrying...")

            except Exception as heal_error:
                print(f"Error during self-healing: {heal_error}")
                break
        else:
            print(f"✗ Max retries ({max_retries}) reached. Giving up on optimization.")

conn.close()

# Step 4: Execute fast execution script
if optimization_success:
    print("\n[4] Executing fast execution script from optimized cache...")

    try:
        exec_globals = {
            'Path': Path,
            '__builtins__': __builtins__,
        }

        execution_script = optimization_payload.get('execution_script', '')

        if not execution_script:
            raise ValueError("No execution_script in payload")

        # Capture the result by adding a return variable
        full_exec_script = execution_script + "\nresult = None\n"

        exec(execution_script, exec_globals)

        result = exec_globals.get('result', 'No result returned')

        print(f"\n✓ Execution completed successfully!")
        print(f"  Final Result: {result}")

        # Verify against original query for comparison
        print("\n[5] Verifying result against original query...")
        conn = duckdb.connect(db_path)
        original_result = conn.execute(TARGET_QUERY).fetchone()[0]
        conn.close()

        print(f"  Original Query Result: {original_result}")
        print(f"  Optimized Query Result: {result}")

        if original_result == result:
            print(f"  ✓ Results match! Optimization successful.")
        else:
            print(f"  ✗ Results differ! Original: {original_result}, Optimized: {result}")

    except Exception as e:
        print(f"✗ Error during execution: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("OPTIMIZER AGENT - Pipeline Complete")
print("=" * 80)
