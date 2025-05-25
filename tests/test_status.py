import subprocess
import sys

print("Running tests and saving output...")

# Run the tests and save to file
with open('test_output.txt', 'w', encoding='utf-8') as f:
    result = subprocess.run(
        [sys.executable, 'test_chutes_fast.py'],
        stdout=f,
        stderr=subprocess.STDOUT,
        text=True
    )

print(f"Tests completed with return code: {result.returncode}")
print("\nReading test output from file...")

# Read and display the output
with open('test_output.txt', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Find key information
lines = content.split('\n')
for i, line in enumerate(lines):
    # Print test headers and results
    if '=== Test' in line or '✅' in line or '❌' in line or 'Passed:' in line:
        print(line)
    # Also print a few lines after errors
    elif 'error' in line.lower() or 'failed' in line.lower():
        print(line)
        # Print next 2 lines for context
        for j in range(1, 3):
            if i + j < len(lines):
                print(lines[i + j])

print("\nFull output saved to: test_output.txt") 