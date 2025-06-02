#!/usr/bin/env python3
"""
Test script to verify GAIA benchmark setup and dependencies.
"""

import os
import sys
from pathlib import Path

# Disable progress bars
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"

def test_dependencies():
    """Test if all required dependencies are installed."""
    print("Testing GAIA dependencies...")
    
    dependencies = {
        "datasets": None,
        "huggingface_hub": None,
        "pandas": None,
        "sqlalchemy": None,
        "tqdm": None,
    }
    
    for dep in dependencies:
        try:
            module = __import__(dep)
            version = getattr(module, "__version__", "unknown")
            dependencies[dep] = version
            print(f"✓ {dep}: {version}")
        except ImportError as e:
            print(f"✗ {dep}: NOT INSTALLED - {e}")
            dependencies[dep] = None
    
    all_installed = all(v is not None for v in dependencies.values())
    return all_installed

def test_dataset_access():
    """Test if we can access the GAIA dataset."""
    print("\nTesting dataset access...")
    
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        
        # Check if the dataset exists
        try:
            dataset_info = api.dataset_info("gaia-benchmark/GAIA")
            print(f"✓ Can access gaia-benchmark/GAIA dataset")
            print(f"  Dataset size: {dataset_info.size_on_disk_str if hasattr(dataset_info, 'size_on_disk_str') else 'unknown'}")
        except Exception as e:
            print(f"✗ Cannot access gaia-benchmark/GAIA: {e}")
            return False
            
        # Check if data directory exists
        data_dir = Path("data/gaia")
        if data_dir.exists():
            print(f"✓ Data directory exists: {data_dir}")
            # Check for GAIA.py
            if (data_dir / "GAIA.py").exists():
                print(f"✓ Dataset script found: {data_dir / 'GAIA.py'}")
            else:
                print(f"⚠ Dataset script not found in {data_dir}")
        else:
            print(f"⚠ Data directory does not exist: {data_dir}")
            print("  The dataset will be downloaded on first run")
            
        return True
        
    except Exception as e:
        print(f"✗ Error testing dataset access: {e}")
        return False

def test_workspace():
    """Test workspace setup."""
    print("\nTesting workspace setup...")
    
    workspace_dir = Path("workspace")
    output_dir = Path("output")
    logs_dir = Path("logs")
    
    for dir_path, dir_name in [(workspace_dir, "Workspace"), (output_dir, "Output"), (logs_dir, "Logs")]:
        if dir_path.exists():
            print(f"✓ {dir_name} directory exists: {dir_path}")
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✓ Created {dir_name} directory: {dir_path}")
            except Exception as e:
                print(f"✗ Failed to create {dir_name} directory: {e}")
                return False
    
    return True

def main():
    """Run all tests."""
    print("GAIA Benchmark Setup Test")
    print("=" * 50)
    
    # Test dependencies
    deps_ok = test_dependencies()
    
    if not deps_ok:
        print("\n❌ Missing dependencies! Please install with:")
        print("   pip install datasets huggingface-hub pandas sqlalchemy tqdm")
        sys.exit(1)
    
    # Test dataset access
    dataset_ok = test_dataset_access()
    
    # Test workspace
    workspace_ok = test_workspace()
    
    print("\n" + "=" * 50)
    if deps_ok and dataset_ok and workspace_ok:
        print("✅ GAIA benchmark setup is complete!")
        print("\nYou can now run the benchmark with:")
        print("   python run_gaia.py --run-name test-run --set-to-run validation --end-index 1")
    else:
        print("❌ GAIA benchmark setup has issues. Please fix the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 