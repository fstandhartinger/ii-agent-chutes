import subprocess
import sys
import re

# Run the tests
result = subprocess.run(
    [sys.executable, 'tests/test_chutes_fast.py'],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace'
)

# Extract test results from stdout
stdout = result.stdout
test_results = []

# Find all test results
for line in stdout.split('\n'):
    if '=== Test' in line and ':' in line:
        test_name = line.strip()
    elif '✅' in line and 'passed' in line:
        test_results.append((test_name, 'PASSED'))
    elif '❌' in line and 'failed' in line:
        test_results.append((test_name, 'FAILED'))

# Find summary
summary_match = re.search(r'Passed: (\d+)/(\d+)', stdout)
if summary_match:
    passed = int(summary_match.group(1))
    total = int(summary_match.group(2))
else:
    passed = sum(1 for _, status in test_results if status == 'PASSED')
    total = len(test_results)

# Print results
print("Test Results Summary")
print("=" * 40)
for test, status in test_results:
    print(f"{test}: {status}")

print(f"\nTotal: {passed}/{total} tests passed")

# Check for errors in stderr
if result.stderr and 'error' in result.stderr.lower():
    print("\n⚠️  Errors detected in logs:")
    error_lines = [line for line in result.stderr.split('\n') if 'error' in line.lower()]
    for line in error_lines[:5]:  # Show first 5 error lines
        print(f"  - {line.strip()}")

# Exit code
sys.exit(0 if passed == total else 1) 