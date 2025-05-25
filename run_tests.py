import subprocess
import sys

# Run the tests and capture output
result = subprocess.run(
    [sys.executable, 'test_chutes_fast.py'],
    capture_output=True,
    text=True
)

# Print stdout
print("=== STDOUT ===")
print(result.stdout)

# Print stderr
print("\n=== STDERR ===")
print(result.stderr)

# Print return code
print(f"\n=== Return Code: {result.returncode} ===") 