#!/usr/bin/env python
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

scripts = [
    ('data_fabric.py', 'DATA GENERATION'),
    ('create_cache.py', 'OPTIMIZATION CACHE'),
    ('benchmark.py', 'PERFORMANCE BENCHMARK')
]

print("=" * 80)
print("PROJECT AEGIS FABRIC - COMPLETE PIPELINE")
print("=" * 80)

for script, title in scripts:
    print(f"\n{'=' * 80}")
    print(f"{title}: {script}")
    print("=" * 80)

    result = subprocess.run([sys.executable, script], capture_output=False)

    if result.returncode != 0:
        print(f"\n[ERROR] {script} failed with exit code {result.returncode}")
    else:
        print(f"\n[OK] {script} completed successfully")

print("\n" + "=" * 80)
print("PIPELINE COMPLETE")
print("=" * 80)
