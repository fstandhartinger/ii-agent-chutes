import subprocess
import sys
import time

def run_test_with_output(test_name):
    """Run a single test and capture its output."""
    print(f"\n{'='*60}")
    print(f"Running: {test_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Run the test
    result = subprocess.run(
        [sys.executable, test_name],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Print stdout
    if result.stdout:
        print("\n--- STDOUT ---")
        print(result.stdout)
    
    # Print stderr (contains logging output)
    if result.stderr:
        print("\n--- STDERR (Logging Output) ---")
        print(result.stderr)
    
    # Print summary
    print(f"\n--- SUMMARY ---")
    print(f"Return Code: {result.returncode}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Status: {'SUCCESS' if result.returncode == 0 else 'FAILED'}")
    
    return result.returncode == 0

if __name__ == "__main__":
    test_file = sys.argv[1] if len(sys.argv) > 1 else 'test_chutes_fast.py'
    
    print(f"Test Runner for Windows")
    print(f"Running test file: {test_file}")
    
    success = run_test_with_output(test_file)
    
    if success:
        print("\n✅ All tests completed successfully!")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1) 