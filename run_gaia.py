#!/usr/bin/env python3
"""
GAIA Dataset Evaluation Runner.

This script provides functionality to run evaluations on the GAIA dataset using the Agent system.
It integrates with the existing CLI infrastructure while adding GAIA-specific evaluation capabilities.
"""

import os
# Disable progress bars early before imports
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"

import json
import argparse
from datetime import datetime
from pathlib import Path
import shutil
from threading import Lock
import logging
import pandas as pd
import sqlalchemy
from tqdm import tqdm
from datasets import load_dataset, Dataset
from huggingface_hub import snapshot_download
import uuid
import asyncio
from ii_agent.db.models import Session, Event
from ii_agent.agents.anthropic_fc import AnthropicFC
from ii_agent.browser.browser import Browser
from ii_agent.prompts.gaia_system_prompt import GAIA_SYSTEM_PROMPT
from ii_agent.tools.bash_tool import BashTool
from ii_agent.tools.browser_tools import (
    BrowserClickTool,
    BrowserEnterTextTool,
    BrowserGetSelectOptionsTool,
    BrowserNavigationTool,
    BrowserPressKeyTool,
    BrowserRestartTool,
    BrowserScrollDownTool,
    BrowserScrollUpTool,
    BrowserSelectDropdownOptionTool,
    BrowserViewTool,
    BrowserWaitTool,
)
# Gemini tools disabled - no API key available
# from ii_agent.tools.advanced_tools.gemini import (
#     AudioUnderstandingTool,
#     AudioTranscribeTool,
#     YoutubeVideoUnderstandingTool,
# )
from ii_agent.tools.sequential_thinking_tool import SequentialThinkingTool
from ii_agent.tools.str_replace_tool_relative import StrReplaceEditorTool
from ii_agent.tools.text_inspector_tool import TextInspectorTool
from ii_agent.tools.visit_webpage_tool import VisitWebpageTool
from ii_agent.tools.visualizer import DisplayImageTool
from ii_agent.tools.web_search_tool import WebSearchTool
from ii_agent.utils import WorkspaceManager
from ii_agent.llm import get_client
from ii_agent.llm.context_manager.standard import StandardContextManager
from ii_agent.llm.token_counter import TokenCounter
from ii_agent.utils.constants import DEFAULT_MODEL, UPLOAD_FOLDER_NAME, PERSISTENT_DATA_ROOT
from utils import parse_common_args, get_persistent_path
from ii_agent.db.manager import DatabaseManager
from ii_agent.core.event import RealtimeEvent, EventType
from ii_agent.tools.youtube_transcript_tool import YoutubeTranscriptTool

# Global lock for thread-safe file appending
append_answer_lock = Lock()


def parse_args():
    """Parse command line arguments for GAIA evaluation."""
    parser = argparse.ArgumentParser(description="Run GAIA dataset evaluation")
    parser = parse_common_args(parser)

    # GAIA-specific arguments
    parser.add_argument(
        "--use-raw-dataset",
        action="store_true",
        help="Use raw GAIA dataset instead of annotated version",
    )
    parser.add_argument(
        "--set-to-run",
        type=str,
        choices=["validation", "test"],
        default="validation",
        help="Which dataset split to evaluate on",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        required=True,
        help="Name for this evaluation run (used in output filename)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent evaluation tasks",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Starting index in the dataset (inclusive)",
    )
    parser.add_argument(
        "--end-index",
        type=int,
        default=None,
        help="Ending index in the dataset (exclusive). If not specified, runs until the end of dataset",
    )
    parser.add_argument(
        "--task-uuid",
        type=str,
        nargs="+",
        help="Specify one or more task UUIDs to run only those specific tasks",
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default=None,
        help="Model ID to use for evaluation (e.g., 'deepseek-ai/DeepSeek-R1')",
    )
    parser.add_argument(
        "--model-provider",
        type=str,
        default=None,
        help="Model provider to use (e.g., 'chutes', 'anthropic')",
    )

    return parser.parse_args()


def load_gaia_dataset(use_raw_dataset: bool, set_to_run: str) -> Dataset:
    """Load the GAIA dataset, downloading if necessary."""
    data_dir = Path("data/gaia")
    
    try:
        if not data_dir.exists():
            print(f"GAIA dataset not found at {data_dir}, downloading...")
            if use_raw_dataset:
                print("Downloading from gaia-benchmark/GAIA...")
                snapshot_download(
                    repo_id="gaia-benchmark/GAIA",
                    repo_type="dataset",
                    local_dir=str(data_dir),
                    ignore_patterns=[".gitattributes", "README.md"],
                    resume_download=True,
                    max_workers=1,  # Reduce parallel downloads to avoid issues
                )
            else:
                # WARNING: this dataset is gated: make sure you visit the repo to require access
                print("Downloading from smolagents/GAIA-annotated...")
                print("NOTE: This dataset is gated. Make sure you have access on Hugging Face.")
                snapshot_download(
                    repo_id="smolagents/GAIA-annotated",
                    repo_type="dataset",
                    local_dir=str(data_dir),
                    ignore_patterns=[".gitattributes", "README.md"],
                    resume_download=True,
                    max_workers=1,  # Reduce parallel downloads to avoid issues
                )
            print("Download completed successfully!")
        else:
            print(f"Using existing GAIA dataset at {data_dir}")

        def preprocess_file_paths(row):
            if len(row["file_name"]) > 0:
                row["file_name"] = f"data/gaia/2023/{set_to_run}/" + row["file_name"]
            return row

        # Check if the dataset script exists
        dataset_script = data_dir / "GAIA.py"
        if not dataset_script.exists():
            raise FileNotFoundError(f"Dataset script not found at {dataset_script}. The download may have failed.")

        print(f"Loading dataset from {dataset_script}...")
        eval_ds = load_dataset(
            str(dataset_script),
            name="2023_all",
            split=set_to_run,
            trust_remote_code=True,
            download_mode="reuse_dataset_if_exists",
        )

        eval_ds = eval_ds.rename_columns(
            {"Question": "question", "Final answer": "true_answer", "Level": "task"}
        )
        eval_ds = eval_ds.map(preprocess_file_paths)
        
        print(f"Successfully loaded {len(eval_ds)} examples from {set_to_run} split")
        return eval_ds
        
    except Exception as e:
        print(f"Error loading GAIA dataset: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def append_answer(entry: dict, jsonl_file: str) -> None:
    """Append a single answer to the output JSONL file."""
    jsonl_path = Path(jsonl_file)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with append_answer_lock, open(jsonl_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")
    assert jsonl_path.exists(), "File not found!"
    print("Answer exported to file:", jsonl_path.resolve())


def get_examples_to_answer(answers_file: str, eval_ds: Dataset) -> list[dict]:
    """Get list of examples that haven't been answered yet."""
    print(f"Loading answers from {answers_file}...")
    try:
        # Check if file exists first
        if not Path(answers_file).exists():
            print("No previous results file found. Starting new.")
            done_questions = []
        else:
            # Read the file properly
            with open(answers_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                done_questions = []
                for line in lines:
                    if line.strip():  # Skip empty lines
                        try:
                            data = json.loads(line)
                            if "question" in data:
                                done_questions.append(data["question"])
                        except json.JSONDecodeError:
                            continue
            print(f"Found {len(done_questions)} previous results!")
    except Exception as e:
        print("Error when loading records: ", e)
        print("No usable records! ▶️ Starting new.")
        done_questions = []
    return [
        line for line in eval_ds.to_list() if line["question"] not in done_questions
    ]


async def answer_single_question(
    example: dict,
    answers_file: str,
    logger: logging.Logger,
    client,
    context_manager,
    container_workspace: bool,
) -> None:
    """Process a single GAIA question using the agent."""
    # Create workspace using task_id with persistent storage support
    task_id = example["task_id"]
    base_workspace = get_persistent_path("workspace", f"{PERSISTENT_DATA_ROOT}/workspace")
    workspace_path = Path(base_workspace) / task_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created workspace directory for task {task_id}: {workspace_path}")
    
    # Log storage type
    if str(workspace_path).startswith(PERSISTENT_DATA_ROOT):
        logger.info(f"Using persistent storage for GAIA task {task_id}")
    else:
        logger.info(f"Using local storage for GAIA task {task_id}")

    # Initialize database manager
    db_manager = DatabaseManager()

    # Create a new session with the task_id as session_id
    session_id = uuid.UUID(task_id)

    # Check if session exists and handle accordingly
    existing_session = db_manager.get_session_by_id(session_id)
    if existing_session:
        logger.info(f"Found existing session {session_id}, removing old events...")
        with db_manager.get_session() as session:
            # Delete all events for this session
            session.query(Event).filter(Event.session_id == str(session_id)).delete()
            # Delete the session itself
            session.query(Session).filter(Session.id == str(session_id)).delete()
            logger.info(f"Removed old session and events for {session_id}")
            # remove all files in workspace
            try:
                shutil.rmtree(workspace_path, ignore_errors=True)
                workspace_path.mkdir(parents=True, exist_ok=True)
                logger.info(
                    f"Cleaned up and recreated workspace directory: {workspace_path}"
                )
            except Exception as e:
                logger.warning(
                    f"Error during workspace cleanup: {e}. Continuing anyway..."
                )

    try:
        db_manager.create_session(
            session_uuid=session_id,
            workspace_path=workspace_path,
            device_id="gaia-eval",
        )
        logger.info(
            f"Created new session {session_id} with workspace at {workspace_path}"
        )
    except sqlalchemy.exc.IntegrityError as e:
        logger.error(f"Failed to create session: {e}")
        return

    # Copy required files to workspace if they exist
    if example["file_name"]:
        source_file = Path(example["file_name"])
        if source_file.exists():
            # Create upload directory in workspace
            upload_dir = workspace_path / UPLOAD_FOLDER_NAME
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Copy the file to workspace
            dest_file = upload_dir / f"file{source_file.suffix}"
            shutil.copy2(source_file, dest_file)

            # check if same file name but with png extension exists (replace source_file extension with png)
            png_file = source_file.with_suffix(".png")
            if png_file.exists() and source_file.suffix != ".png":
                # copy png file to workspace
                dest_png_file = upload_dir / "file.png"
                shutil.copy2(png_file, dest_png_file)
                logger.info(f"Copied file {png_file} to {dest_png_file}")

            logger.info(f"Copied file {source_file} to {dest_file}")

            # Update file path in example to point to workspace
            # convert dest_file to absolute path
            example["file_name"] = str(dest_file.absolute())
        else:
            logger.warning(f"Source file not found: {source_file}")

    # Create workspace manager for this question
    workspace_manager = WorkspaceManager(
        root=workspace_path, container_workspace=container_workspace
    )

    browser = Browser()
    # Create message queue
    message_queue = asyncio.Queue()

    tools = [
        SequentialThinkingTool(),
        WebSearchTool(),
        VisitWebpageTool(),
        StrReplaceEditorTool(
            workspace_manager=workspace_manager, message_queue=message_queue
        ),
        BashTool(workspace_root=workspace_path, require_confirmation=False),
        BrowserNavigationTool(browser=browser),
        BrowserRestartTool(browser=browser),
        BrowserScrollDownTool(browser=browser),
        BrowserScrollUpTool(browser=browser),
        BrowserViewTool(browser=browser),
        BrowserWaitTool(browser=browser),
        BrowserClickTool(browser=browser),
        BrowserEnterTextTool(browser=browser),
        BrowserPressKeyTool(browser=browser),
        BrowserGetSelectOptionsTool(browser=browser),
        BrowserSelectDropdownOptionTool(browser=browser),
        TextInspectorTool(workspace_manager=workspace_manager),
        DisplayImageTool(workspace_manager=workspace_manager),
        # Gemini tools disabled - no API key available
        # YoutubeVideoUnderstandingTool(workspace_manager=workspace_manager),
        # AudioUnderstandingTool(workspace_manager=workspace_manager),
        # AudioTranscribeTool(workspace_manager=workspace_manager),
        YoutubeTranscriptTool(),
    ]

    system_prompt = GAIA_SYSTEM_PROMPT

    # Create agent instance for this question
    agent = AnthropicFC(
        system_prompt=system_prompt,
        client=client,
        tools=tools,
        workspace_manager=workspace_manager,
        message_queue=message_queue,
        logger_for_agent_logs=logger,
        context_manager=context_manager,
        max_output_tokens_per_turn=32768,
        max_turns=200,
        session_id=session_id,  # Pass the session_id from database manager
    )

    # Create background task for message processing
    message_task = agent.start_message_processing()

    augmented_question = """You have one question to answer. It is paramount that you provide a correct answer.
Give it all you can: I know for a fact that you have access to all the relevant tools to solve it and find the correct answer (the answer does exist).
Failure or 'I cannot answer' or 'None found' will not be tolerated, success will be rewarded.
Run verification steps if that's needed, you must make sure you find the correct answer! Here is the task:

""" + example["question"]

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Add user message to the event queue to save to database
        await message_queue.put(
            RealtimeEvent(
                type=EventType.USER_MESSAGE, content={"text": augmented_question}
            )
        )

        # Run agent with question-specific workspace
        loop = asyncio.get_running_loop()
        final_result = await loop.run_in_executor(
            None,  # Uses default ThreadPoolExecutor
            lambda: agent.run_agent(
                augmented_question,
                resume=True,
                files=[example["file_name"]] if example["file_name"] else [],
            ),
        )

        output = str(final_result)

        iteration_limit_exceeded = (
            "Agent stopped due to iteration limit or time limit." in output
        )
        raised_exception = False
        exception = None

    except Exception as e:
        logger.error(f"Error processing question: {e}")
        output = None
        iteration_limit_exceeded = False
        exception = e
        raised_exception = True
    finally:
        # Cleanup tasks
        message_task.cancel()
        try:
            # Wait for the task to be cancelled and process remaining messages
            await message_task
            # Wait for all messages to be processed
            await message_queue.join()
        except asyncio.CancelledError:
            pass

    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get token counts
    token_counts = 0  # TODO: add this

    annotated_example = {
        "agent_name": "anthropic-fc",
        "question": example["question"],
        "augmented_question": augmented_question,
        "prediction": output,
        "iteration_limit_exceeded": iteration_limit_exceeded,
        "agent_error": str(exception) if raised_exception else None,
        "task": example["task"],
        "task_id": task_id,
        "true_answer": example["true_answer"],
        "start_time": start_time,
        "end_time": end_time,
        "token_counts": token_counts,
        "workspace_id": task_id,
    }

    append_answer(annotated_example, answers_file)


def main():
    """Main entry point for GAIA evaluation."""
    args = parse_args()
    print(f"Starting GAIA evaluation with arguments: {args}")

    # Setup logging
    # Ensure logs directory exists
    Path(args.logs_path).parent.mkdir(parents=True, exist_ok=True)
    if os.path.exists(args.logs_path):
        os.remove(args.logs_path)
    logger = logging.getLogger("gaia_eval")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.FileHandler(args.logs_path))
    logger.propagate = False
    if not args.minimize_stdout_logs:
        logger.addHandler(logging.StreamHandler())

    # Initialize LLM client
    # Use provided model or fall back to default
    if args.model_id and args.model_provider:
        model_name = args.model_id
        provider = args.model_provider
        # For chutes provider, we need to use the chutes-openai client
        if provider == "chutes":
            client = get_client(
                "chutes-openai",
                model_name=model_name,
                use_caching=False,
                project_id=args.project_id,
                region=args.region,
            )
        else:
            # For anthropic or other providers
            client = get_client(
                provider,
                model_name=model_name,
                use_caching=False,
                project_id=args.project_id,
                region=args.region,
                thinking_tokens=2048 if provider == "anthropic-direct" else None,
            )
    else:
        # Default to anthropic-direct with DEFAULT_MODEL
        client = get_client(
            "anthropic-direct",
            model_name=DEFAULT_MODEL,
            use_caching=False,
            project_id=args.project_id,
            region=args.region,
            thinking_tokens=2048,
        )

    # Initialize token counter and context manager
    token_counter = TokenCounter()
    context_manager = StandardContextManager(
        token_counter=token_counter,
        logger=logger,
        token_budget=120_000,
    )

    # Load dataset and get tasks to run
    eval_ds = load_gaia_dataset(args.use_raw_dataset, args.set_to_run)
    print("Loaded evaluation dataset:")
    print(pd.DataFrame(eval_ds)["task"].value_counts())

    # If task_uuid is provided, filter dataset to only those tasks
    if args.task_uuid:
        eval_ds = eval_ds.filter(lambda x: x["task_id"] in args.task_uuid)
        print("Length of eval_ds: ", len(eval_ds))
        if len(eval_ds) == 0:
            raise ValueError(f"No tasks found with UUIDs {args.task_uuid}")
        print(f"Running {len(eval_ds)} tasks with UUIDs: {args.task_uuid}")
    else:
        # Slice dataset based on start and end indices
        if args.end_index is None:
            args.end_index = len(eval_ds)
        if (
            args.start_index < 0
            or args.end_index > len(eval_ds)
            or args.start_index >= args.end_index
        ):
            raise ValueError(
                f"Invalid range: start_index={args.start_index}, end_index={args.end_index}, dataset_size={len(eval_ds)}"
            )

        eval_ds = eval_ds.select(range(args.start_index, args.end_index))
        print(
            f"Running evaluation on examples {args.start_index} to {args.end_index - 1} (total: {len(eval_ds)} examples)"
        )

    answers_file = f"output/{args.set_to_run}/{args.run_name}.jsonl"
    # Ensure output directory exists
    Path(answers_file).parent.mkdir(parents=True, exist_ok=True)
    tasks_to_run = get_examples_to_answer(answers_file, eval_ds)

    async def process_tasks():
        # Create semaphore to limit concurrent tasks
        sem = asyncio.Semaphore(args.concurrency)

        async def process_with_semaphore(example):
            async with sem:
                return await answer_single_question(
                    example,
                    answers_file,
                    logger,
                    client,
                    context_manager,
                    args.use_container_workspace,
                )

        # Create tasks with semaphore
        tasks = [process_with_semaphore(example) for example in tasks_to_run]

        # Process tasks with progress bar (if not disabled)
        if os.environ.get("TQDM_DISABLE", "0") == "1":
            # No progress bar
            print(f"Processing {len(tasks)} GAIA tasks...")
            for f in asyncio.as_completed(tasks):
                await f
            print("All tasks completed.")
        else:
            # With progress bar
            for f in tqdm(
                asyncio.as_completed(tasks), total=len(tasks), desc="Processing GAIA tasks"
            ):
                await f

    # Run the async task processing
    asyncio.run(process_tasks())

    print("All GAIA tasks processed.")


if __name__ == "__main__":
    main()
