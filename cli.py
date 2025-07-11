#!/usr/bin/env python3
"""
CLI for interacting with the Agent.

This script provides a command-line interface for interacting with the Agent,
allowing users to send queries and receive responses in a terminal environment.
"""

import os
import argparse
import logging
import asyncio
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

from ii_agent.core.event import RealtimeEvent, EventType
from ii_agent.utils.constants import SONNET_4, PERSISTENT_DATA_ROOT
from utils import parse_common_args, create_workspace_manager_for_connection
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from ii_agent.tools import get_system_tools
from ii_agent.prompts.system_prompt import SYSTEM_PROMPT
from ii_agent.agents.anthropic_fc import AnthropicFC
from ii_agent.utils import WorkspaceManager
from ii_agent.llm import get_client
from ii_agent.llm.context_manager.file_based import FileBasedContextManager
from ii_agent.llm.context_manager.standard import StandardContextManager
from ii_agent.llm.token_counter import TokenCounter
from ii_agent.db.manager import DatabaseManager

MAX_OUTPUT_TOKENS_PER_TURN = 32768
MAX_TURNS = 200


async def async_main():
    """Async main entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="CLI for interacting with the Agent")
    parser = parse_common_args(parser)

    args = parser.parse_args()

    if os.path.exists(args.logs_path):
        os.remove(args.logs_path)
    logger_for_agent_logs = logging.getLogger("agent_logs")
    logger_for_agent_logs.setLevel(logging.DEBUG)
    # Prevent propagation to root logger to avoid duplicate logs
    logger_for_agent_logs.propagate = False
    logger_for_agent_logs.addHandler(logging.FileHandler(args.logs_path))
    if not args.minimize_stdout_logs:
        logger_for_agent_logs.addHandler(logging.StreamHandler())

    # Initialize console
    console = Console()

    # Initialize database manager (will use persistent storage if available)
    db_manager = DatabaseManager()

    # Create a new workspace manager for the CLI session
    workspace_manager, session_id = create_workspace_manager_for_connection(
        args.workspace, args.use_container_workspace
    )
    workspace_path = workspace_manager.root

    # Create a new session and get its workspace directory
    actual_session_id, actual_workspace_path = db_manager.create_session(
        session_uuid=session_id, workspace_path=workspace_manager.root
    )
    logger_for_agent_logs.info(
        f"Using session {actual_session_id} with workspace at {actual_workspace_path}"
    )

    # Log storage type
    if str(workspace_manager.root).startswith(PERSISTENT_DATA_ROOT):
        console.print(f"[green]Using persistent storage at: {workspace_manager.root}[/green]")
    else:
        console.print(f"[yellow]Using local storage at: {workspace_manager.root}[/yellow]")

    # Print welcome message
    if not args.minimize_stdout_logs:
        console.print(
            Panel(
                "[bold]Agent CLI[/bold]\n\n"
                + f"Session ID: {session_id}\n"
                + f"Workspace: {workspace_path}\n\n"
                + "Type your instructions to the agent. Press Ctrl+C to exit.\n"
                + "Type 'exit' or 'quit' to end the session.",
                title="[bold blue]Agent CLI[/bold blue]",
                border_style="blue",
                padding=(1, 2),
            )
        )
    else:
        logger_for_agent_logs.info(
            f"Agent CLI started with session {session_id}. Waiting for user input. Press Ctrl+C to exit. Type 'exit' or 'quit' to end the session."
        )

    # Initialize LLM client
    client = get_client(
        "anthropic-direct",
        model_name=SONNET_4,
        use_caching=False,
        project_id=args.project_id,
        region=args.region,
    )

    # Initialize workspace manager with the session-specific workspace
    workspace_manager = WorkspaceManager(
        root=workspace_path, container_workspace=args.use_container_workspace
    )

    # Initialize token counter
    token_counter = TokenCounter()

    # Create context manager based on argument
    if args.context_manager == "file-based":
        context_manager = FileBasedContextManager(
            workspace_manager=workspace_manager,
            token_counter=token_counter,
            logger=logger_for_agent_logs,
            token_budget=120_000,
        )
    else:  # standard
        context_manager = StandardContextManager(
            token_counter=token_counter,
            logger=logger_for_agent_logs,
            token_budget=120_000,
        )

    queue = asyncio.Queue()
    tools = get_system_tools(
        client=client,
        workspace_manager=workspace_manager,
        message_queue=queue,
        container_id=args.docker_container_id,
        ask_user_permission=args.needs_permission,
        tool_args={
            "deep_research": False,
            "pdf": True,
            "media_generation": False,
            "audio_generation": False,
            "browser": True,
        },
    )
    agent = AnthropicFC(
        system_prompt=SYSTEM_PROMPT,
        client=client,
        workspace_manager=workspace_manager,
        tools=tools,
        message_queue=queue,
        logger_for_agent_logs=logger_for_agent_logs,
        context_manager=context_manager,
        max_output_tokens_per_turn=MAX_OUTPUT_TOKENS_PER_TURN,
        max_turns=MAX_TURNS,
        session_id=session_id,  # Pass the session_id from database manager
    )

    # Create background task for message processing
    message_task = agent.start_message_processing()

    # Main interaction loop
    try:
        loop = asyncio.get_running_loop()
        while True:
            # Use async input
            user_input = await loop.run_in_executor(None, lambda: input("User input: "))

            agent.message_queue.put_nowait(
                RealtimeEvent(type=EventType.USER_MESSAGE, content={"text": user_input})
            )

            if user_input.lower() in ["exit", "quit"]:
                console.print("[bold]Exiting...[/bold]")
                logger_for_agent_logs.info("Exiting...")
                break

            logger_for_agent_logs.info("\nAgent is thinking...")
            try:
                # Run synchronous method in executor
                result = await loop.run_in_executor(
                    None,  # Uses default ThreadPoolExecutor
                    lambda: agent.run_agent(user_input, resume=True),
                )
                logger_for_agent_logs.info(f"Agent: {result}")
            except Exception as e:
                logger_for_agent_logs.info(f"Error: {str(e)}")
                logger_for_agent_logs.debug("Full error:", exc_info=True)

            logger_for_agent_logs.info("\n" + "-" * 40 + "\n")

    except KeyboardInterrupt:
        console.print("\n[bold]Session interrupted. Exiting...[/bold]")
        loop.stop()
    finally:
        # Cleanup tasks
        message_task.cancel()

    console.print("[bold]Goodbye![/bold]")


if __name__ == "__main__":
    asyncio.run(async_main())
