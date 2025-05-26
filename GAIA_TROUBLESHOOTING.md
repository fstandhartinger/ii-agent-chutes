# GAIA Benchmark Troubleshooting Guide

## Common Issues and Solutions

### 1. "Fetching files" Progress Bar Error

**Problem**: The benchmark fails with a "Fetching files" progress bar that stops at a low percentage.

**Solution**: 
- This is caused by the Hugging Face Hub trying to download the GAIA dataset
- We've disabled progress bars by setting environment variables:
  ```bash
  export HF_HUB_DISABLE_PROGRESS_BARS=1
  export TQDM_DISABLE=1
  ```
- The download will continue in the background without the progress bar

### 2. Asyncio Task Destruction Errors

**Problem**: You see errors like "Task was destroyed but it is pending!"

**Solution**:
- These errors occur when WebSocket connections are closed while agent tasks are running
- This is typically harmless for the GAIA benchmark itself
- The benchmark runs in a subprocess and is isolated from WebSocket issues

### 3. Missing Dependencies

**Problem**: ImportError for datasets or huggingface_hub

**Solution**:
```bash
pip install datasets huggingface-hub pandas sqlalchemy tqdm
```

### 4. Dataset Download Failures

**Problem**: The GAIA dataset fails to download

**Possible Causes**:
1. **Network Issues**: Check your internet connection
2. **Hugging Face Access**: Some datasets require authentication
3. **Disk Space**: Ensure you have at least 2GB free space

**Solutions**:
- Run the test script to diagnose: `python test_gaia_setup.py`
- For gated datasets, log in to Hugging Face: `huggingface-cli login`
- Check disk space: `df -h`
- Try manual download with resume:
  ```python
  from huggingface_hub import snapshot_download
  snapshot_download(
      repo_id="gaia-benchmark/GAIA",
      repo_type="dataset",
      local_dir="data/gaia",
      resume_download=True,
      max_workers=1
  )
  ```

### 5. Subprocess Errors

**Problem**: "run_gaia.py script not found" or similar subprocess errors

**Solution**:
- Ensure you're running from the correct directory (project root)
- Check that run_gaia.py exists and is executable
- On Windows, you might need to use `python.exe` instead of `python`

### 6. Timeout Errors

**Problem**: "Benchmark execution timed out"

**Solution**:
- The default timeout is 60 minutes
- For larger task sets, this might not be enough
- Reduce the number of tasks with `max_tasks` parameter
- Or modify the timeout in `ws_server.py`

## Debugging Steps

1. **Test Setup**:
   ```bash
   python test_gaia_setup.py
   ```

2. **Check Logs**:
   - Server logs: Check the console output where the server is running
   - GAIA logs: Check `logs/` directory for detailed execution logs

3. **Manual Test**:
   ```bash
   python run_gaia.py --run-name test --set-to-run validation --end-index 1 --minimize-stdout-logs
   ```

4. **Environment Variables**:
   ```bash
   # Check if these are set
   echo $HF_HUB_DISABLE_PROGRESS_BARS
   echo $TQDM_DISABLE
   ```

## Improved Logging

The updated code now includes:
- Better error messages with stdout/stderr capture
- Logging of subprocess output for debugging
- Environment variable settings to disable progress bars
- Timeout and error handling improvements

## Contact Support

If you continue to experience issues:
1. Run `python test_gaia_setup.py` and save the output
2. Check the logs in the `logs/` directory
3. Include the full error message and logs when reporting issues 