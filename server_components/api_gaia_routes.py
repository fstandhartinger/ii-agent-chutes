"""
Handles API routes related to running GAIA benchmarks.
"""
import os
import logging
import json
import uuid
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from .common import create_cors_response # Relative import
from .config import app_config # Relative import

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/api/gaia/run")
async def run_gaia_benchmark_endpoint(request: Request):
    """API endpoint to run GAIA benchmark evaluation."""
    try:
        # Check for GAIA dependencies (datasets, huggingface_hub)
        try:
            import datasets
            import huggingface_hub
            logger.info("GAIA API: Dependencies (datasets, huggingface_hub) found.")
        except ImportError as e:
            logger.error(f"GAIA API: Dependencies not installed. Missing: {str(e)}")
            return create_cors_response({
                "status": "error", 
                "message": f"GAIA dependencies not installed. Missing: {str(e)}. Please install with: pip install datasets huggingface-hub"
            }, 400)
        
        data = await request.json()
        set_to_run = data.get("set_to_run", "validation")
        run_name_prefix = data.get("run_name", "api-run")
        run_name = f"{run_name_prefix}-{uuid.uuid4()}" # Ensure unique run name
        max_tasks = data.get("max_tasks", 5)
        model_id = data.get("model_id", None)
        model_provider = data.get("model_provider", None)
        
        logger.info(f"GAIA API: Received request to run benchmark. Run name: {run_name}, Set: {set_to_run}, Max tasks: {max_tasks}, Model: {model_id}, Provider: {model_provider}")

        current_args = app_config.get_args()
        if not current_args:
            logger.error("GAIA API: Application arguments not available via app_config.")
            return create_cors_response({"status": "error", "message": "Server configuration error: Args missing."}, 500)

        # Define output and logs directory based on server structure
        # Assuming 'output' and 'logs' directories are at the project root
        # If current_args.workspace is /some/path/workspace, then project_root is /some/path
        project_root = Path(os.getcwd()) # Fallback to CWD if no better base path
        if hasattr(current_args, 'workspace') and current_args.workspace:
             # Heuristic: if workspace is 'data/workspace', project_root is 'data' parent.
             # This might need adjustment based on actual deployment structure.
             # For simplicity, using CWD as the base for output/logs for now.
             pass


        output_dir = project_root / "output" / set_to_run
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logs_dir = project_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"{run_name}.log"
        
        # Workspace path for the benchmark script
        # The benchmark script itself might create subdirectories within this workspace
        benchmark_workspace_path = getattr(current_args, 'workspace', "workspace") # Default to "workspace" if not in args

        cmd = [
            "python", "run_gaia.py", # Assuming run_gaia.py is in the project root
            "--run-name", run_name,
            "--set-to-run", set_to_run,
            "--end-index", str(max_tasks), # end-index is exclusive, so max_tasks is correct
            "--minimize-stdout-logs",
            "--workspace", str(benchmark_workspace_path), # Pass the main workspace dir
            "--logs-path", str(log_file) # Log for the benchmark script itself
        ]
        
        if model_id and model_provider:
            cmd.extend(["--model-id", model_id, "--model-provider", model_provider])
        
        logger.info(f"GAIA API: Executing benchmark command: {' '.join(cmd)}")
        
        env = os.environ.copy()
        env["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        env["TQDM_DISABLE"] = "1" # For tqdm progress bars
        
        try:
            # Using subprocess.Popen for potentially long-running non-blocking execution if needed in future,
            # but for now, a blocking run with timeout is fine for an API endpoint.
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=3600,  # 60 minutes
                env=env,
                cwd=str(project_root) # Ensure script runs from project root
            )
            
            if result.stdout: logger.debug(f"GAIA API: Benchmark stdout: {result.stdout[:1000]}...")
            if result.stderr: logger.warning(f"GAIA API: Benchmark stderr: {result.stderr[:1000]}...")
            
            if result.returncode == 0:
                results_file_path = output_dir / f"{run_name}.jsonl"
                if results_file_path.exists():
                    benchmark_results = []
                    with open(results_file_path, 'r') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    benchmark_results.append(json.loads(line))
                                except json.JSONDecodeError as e_json:
                                    logger.warning(f"GAIA API: Failed to parse result line from {results_file_path}: {e_json} - Line: '{line.strip()}'")
                    
                    total_tasks_processed = len(benchmark_results)
                    # Prediction might be null or empty if a task failed internally in run_gaia.py
                    completed_tasks_with_prediction = len([r for r in benchmark_results if r.get('prediction')]) 
                    
                    summary_stats = {
                        "total_tasks_processed_by_script": total_tasks_processed,
                        "tasks_with_successful_prediction": completed_tasks_with_prediction,
                        "completion_rate_of_predictions": (completed_tasks_with_prediction / total_tasks_processed) if total_tasks_processed > 0 else 0,
                        "run_name": run_name,
                        "set_to_run": set_to_run,
                        "results_file": str(results_file_path.relative_to(project_root))
                    }
                    logger.info(f"GAIA API: Benchmark successful. Summary: {summary_stats}")
                    return create_cors_response({
                        "status": "success", 
                        "results": benchmark_results,
                        "summary": summary_stats
                    })
                else:
                    error_msg = f"GAIA API: Benchmark script completed but results file not found at {results_file_path}. "
                    if result.stderr: error_msg += f"Stderr: {result.stderr}"
                    logger.error(error_msg)
                    return create_cors_response({"status": "error", "message": error_msg}, 404)
            else:
                error_msg = f"GAIA API: Benchmark script failed with return code {result.returncode}. "
                if result.stderr: error_msg += f"Error: {result.stderr}"
                elif result.stdout: error_msg += f"Output: {result.stdout}" # In case error details are in stdout
                logger.error(error_msg)
                return create_cors_response({"status": "error", "message": error_msg}, 500)
                
        except subprocess.TimeoutExpired:
            logger.error("GAIA API: Benchmark execution timed out (60 minutes).")
            return create_cors_response({"status": "error", "message": "Benchmark execution timed out (60 minutes)"}, 408)
        except FileNotFoundError:
            logger.error("GAIA API: run_gaia.py script not found. Ensure it's in the project root and executable.")
            return create_cors_response({"status": "error", "message": "run_gaia.py script not found. Check server configuration."}, 500)
        except Exception as e_subproc:
            logger.error(f"GAIA API: Subprocess error during benchmark: {str(e_subproc)}", exc_info=True)
            return create_cors_response({"status": "error", "message": f"Failed to run benchmark due to subprocess error: {str(e_subproc)}"}, 500)
        
    except Exception as e_main:
        logger.error(f"GAIA API: General error running GAIA benchmark: {str(e_main)}", exc_info=True)
        return create_cors_response({"status": "error", "message": f"Error running GAIA benchmark: {str(e_main)}"}, 500)
