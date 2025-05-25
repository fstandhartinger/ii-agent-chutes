# GAIA Benchmark Setup Guide

## Overview

The GAIA benchmark functionality requires additional Python dependencies that are not installed by default. This guide explains how to set up the GAIA benchmark feature.

## Required Dependencies

The GAIA benchmark requires the following Python packages:
- `datasets>=3.6.0` - For loading the GAIA dataset
- `huggingface-hub>=0.31.1` - For downloading datasets from Hugging Face
- `sqlalchemy>=2.0.0` - For database operations (already included in main dependencies)

## Installation

### Option 1: Install via pip (Recommended)

```bash
pip install datasets huggingface-hub
```

### Option 2: Install via pyproject.toml

The dependencies have been moved to the main dependencies list in `pyproject.toml`. To install all dependencies including GAIA support:

```bash
pip install -e .
```

### Option 3: Install optional dependencies (if using older version)

```bash
pip install -e ".[gaia]"
```

## Verification

To verify that the GAIA dependencies are properly installed, you can run:

```python
import datasets
import huggingface_hub
print("GAIA dependencies are properly installed!")
```

## Usage

Once the dependencies are installed, you can:

1. **Via Web Interface**: Navigate to `/gaia` in the frontend and click "Run GAIA Benchmark"
2. **Via Command Line**: Run `python run_gaia.py --help` for command-line options

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'datasets'**
   - Solution: Install the missing dependencies using the commands above

2. **Permission errors during installation**
   - Solution: Use `pip install --user datasets huggingface-hub` for user-level installation

3. **Network issues downloading datasets**
   - Solution: Ensure you have a stable internet connection and access to Hugging Face Hub

### Production Deployment

For production deployments (e.g., on Render, Heroku, etc.), make sure to:

1. Update your `requirements.txt` or `pyproject.toml` to include the GAIA dependencies
2. Rebuild your deployment after adding the dependencies
3. Verify the installation in your deployment logs

## Dataset Information

The GAIA benchmark uses datasets from Hugging Face Hub:
- **Validation Set**: Used for development and testing
- **Test Set**: Used for final evaluation

The first time you run the benchmark, it will download the dataset (approximately 1-2 GB), which may take a few minutes depending on your internet connection.

## Performance Notes

- The benchmark can be resource-intensive, especially for larger task sets
- Consider limiting the number of tasks for demo purposes using the `max_tasks` parameter
- Each task can take several minutes to complete depending on complexity

## Support

If you encounter issues with the GAIA benchmark setup, please:
1. Check that all dependencies are properly installed
2. Verify your internet connection for dataset downloads
3. Check the application logs for detailed error messages 