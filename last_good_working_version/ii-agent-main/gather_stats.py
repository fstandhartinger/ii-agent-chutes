#!/usr/bin/env python3
"""
Server Statistics Gatherer

This script collects various statistics about workspaces, databases, and logs
on the server including:
- Number of sessions
- Number of LLM calls
- Number of agentic runs
- File and folder sizes
- Log file sizes
- LLM input/output token counts (if available)
"""

import os
import json
import glob
import re
from datetime import datetime
from collections import defaultdict
import subprocess

class ServerStatsGatherer:
    def __init__(self):
        self.stats = {
            "sessions": 0,
            "llm_calls": 0,
            "agentic_runs": 0,
            "file_sizes": {},
            "folder_sizes": {},
            "log_sizes": {},
            "llm_tokens": {"input": 0, "output": 0},
            "timestamp": datetime.now().isoformat(),
        }
        
        # Try to find the base directories
        self.base_dir = os.getcwd()
        
        # These paths need to be adjusted based on actual server structure
        self.workspace_dir = None
        self.db_dir = None
        self.log_dir = None
        
        self.find_directories()
    
    def find_directories(self):
        """Attempt to discover the workspace, database and log directories"""
        print("Searching for workspace, database and log directories...")
        
        # Look for common directory names
        potential_dirs = [
            "/app/workspace", 
            "/app/data",
            "/app/db",
            "/app/logs",
            "/data",
            "/logs",
            "/var/log",
            "/home/render/workspace",
            "/home/render/data",
            "/home/render/db",
            "/home/render/logs"
        ]
        
        for directory in potential_dirs:
            if os.path.exists(directory) and os.path.isdir(directory):
                print(f"Found directory: {directory}")
                
                # Try to determine the purpose of the directory
                if any(name in directory.lower() for name in ["workspace", "workspaces"]):
                    self.workspace_dir = directory
                    print(f"Set workspace directory to: {directory}")
                elif any(name in directory.lower() for name in ["db", "data", "database"]):
                    self.db_dir = directory
                    print(f"Set database directory to: {directory}")
                elif any(name in directory.lower() for name in ["log", "logs"]):
                    self.log_dir = directory
                    print(f"Set log directory to: {directory}")
    
    def get_directory_size(self, path):
        """Get the size of a directory and its contents in bytes"""
        total_size = 0
        
        # Use du command for efficiency on Linux systems
        try:
            output = subprocess.check_output(['du', '-sb', path], stderr=subprocess.STDOUT)
            size_str = output.decode().split()[0]
            return int(size_str)
        except (subprocess.SubprocessError, ValueError, IndexError):
            # Fall back to Python implementation
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp) and not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
            
            return total_size
    
    def format_size(self, size_bytes):
        """Format bytes to human-readable format"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ("B", "KB", "MB", "GB", "TB")
        i = 0
        while size_bytes >= 1024 and i < len(size_names)-1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"
    
    def count_sessions_from_files(self):
        """Count sessions by looking at relevant files"""
        session_count = 0
        
        # Define patterns to look for in filenames or content
        session_patterns = [
            "*session*", 
            "*chat*",
            "*conversation*"
        ]
        
        dirs_to_check = [d for d in [self.workspace_dir, self.db_dir] if d]
        
        for directory in dirs_to_check:
            for pattern in session_patterns:
                matching_files = glob.glob(os.path.join(directory, "**", pattern), recursive=True)
                print(f"Found {len(matching_files)} files matching '{pattern}' in {directory}")
                
                # Count sessions from files
                for file_path in matching_files:
                    try:
                        # Try to parse as JSON if it's a JSON file
                        if file_path.endswith('.json'):
                            with open(file_path, 'r') as f:
                                data = json.load(f)
                                # Look for session IDs or conversation structure
                                if isinstance(data, dict) and ('session_id' in data or 'conversation' in data):
                                    session_count += 1
                                elif isinstance(data, list) and len(data) > 0:
                                    # Could be a list of messages
                                    session_count += 1
                        
                        # For other files, check if they contain session-like content
                        else:
                            session_count += 1
                    except (json.JSONDecodeError, IOError):
                        # Count the file as a potential session if we can't parse it
                        session_count += 1
        
        return session_count
    
    def count_llm_calls_and_tokens(self):
        """Count LLM API calls and tokens by examining log files and other sources"""
        llm_calls = 0
        input_tokens = 0
        output_tokens = 0
        
        # Define patterns to look for in log files
        llm_patterns = [
            r"llm|openai|claude|anthropic|completion|chat|token",
        ]
        
        # Token count patterns
        token_patterns = [
            r"input_tokens[\"']?\s*[:=]\s*(\d+)",
            r"output_tokens[\"']?\s*[:=]\s*(\d+)",
            r"tokens\s*[:=]\s*(\d+)",
            r"token_count\s*[:=]\s*(\d+)",
            r"usage[\"']?[\"']?total_tokens[\"']?\s*[:=]\s*(\d+)"
        ]
        
        # Look in log files
        if self.log_dir:
            log_files = glob.glob(os.path.join(self.log_dir, "**", "*.log"), recursive=True)
            log_files += glob.glob(os.path.join(self.log_dir, "**", "*.txt"), recursive=True)
            
            for log_file in log_files:
                try:
                    with open(log_file, 'r', errors='ignore') as f:
                        content = f.read()
                        
                        # Count API calls
                        for pattern in llm_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            llm_calls += len(matches)
                        
                        # Extract token counts
                        for pattern in token_patterns:
                            for match in re.finditer(pattern, content, re.IGNORECASE):
                                try:
                                    token_count = int(match.group(1))
                                    
                                    # Determine if input or output based on pattern
                                    if 'input' in match.group(0).lower():
                                        input_tokens += token_count
                                    elif 'output' in match.group(0).lower():
                                        output_tokens += token_count
                                    else:
                                        # If unclear, split evenly
                                        input_tokens += token_count // 2
                                        output_tokens += token_count // 2
                                except (IndexError, ValueError):
                                    pass
                except IOError:
                    pass
        
        # Also check workspace and db directories for relevant JSON files
        dirs_to_check = [d for d in [self.workspace_dir, self.db_dir] if d]
        
        for directory in dirs_to_check:
            json_files = glob.glob(os.path.join(directory, "**", "*.json"), recursive=True)
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        
                        # Check if this looks like an LLM response
                        if isinstance(data, dict):
                            # Look for OpenAI-like structure
                            if 'choices' in data or 'model' in data or 'usage' in data:
                                llm_calls += 1
                                
                                # Extract token counts if available
                                if 'usage' in data and isinstance(data['usage'], dict):
                                    if 'prompt_tokens' in data['usage']:
                                        input_tokens += int(data['usage']['prompt_tokens'])
                                    if 'completion_tokens' in data['usage']:
                                        output_tokens += int(data['usage']['completion_tokens'])
                except (json.JSONDecodeError, IOError):
                    pass
        
        return llm_calls, input_tokens, output_tokens
    
    def count_agentic_runs(self):
        """Count agentic runs by examining logs and files"""
        agentic_runs = 0
        
        # Patterns that might indicate agentic runs
        agent_patterns = [
            r"agent[_\s]run",
            r"agentic",
            r"tool[_\s]call",
            r"function[_\s]call",
            r"action[_\s]result",
            r"step[_\s]id"
        ]
        
        # Check logs first
        if self.log_dir:
            log_files = glob.glob(os.path.join(self.log_dir, "**", "*.log"), recursive=True)
            
            for log_file in log_files:
                try:
                    with open(log_file, 'r', errors='ignore') as f:
                        content = f.read()
                        
                        # If multiple patterns are found in the same file, it's likely an agentic run
                        pattern_matches = 0
                        for pattern in agent_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                pattern_matches += 1
                        
                        if pattern_matches >= 2:  # Require at least 2 patterns to match
                            agentic_runs += 1
                except IOError:
                    pass
        
        # Also check for JSON files that might contain agent runs
        dirs_to_check = [d for d in [self.workspace_dir, self.db_dir] if d]
        
        for directory in dirs_to_check:
            json_files = glob.glob(os.path.join(directory, "**", "*.json"), recursive=True)
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        
                        # Check for agentic structures
                        if isinstance(data, dict):
                            # Look for agent-related keys
                            agent_keys = ['agent', 'tool_calls', 'actions', 'steps', 'function_calls']
                            if any(key in data for key in agent_keys):
                                agentic_runs += 1
                            
                            # Check for arrays of steps/actions
                            elif 'messages' in data and isinstance(data['messages'], list):
                                for msg in data['messages']:
                                    if isinstance(msg, dict) and any(key in msg for key in ['tool_call', 'function_call']):
                                        agentic_runs += 1
                                        break
                except (json.JSONDecodeError, IOError):
                    pass
        
        return agentic_runs
    
    def gather_all_stats(self):
        """Gather all statistics about the server"""
        print("\n" + "="*50)
        print("Starting Server Statistics Gathering")
        print("="*50)
        
        # Find directories if not already set
        if not any([self.workspace_dir, self.db_dir, self.log_dir]):
            self.find_directories()
            
            # Let user know what we found
            print("\nDetected directories:")
            print(f"Workspace directory: {self.workspace_dir or 'Not found'}")
            print(f"Database directory: {self.db_dir or 'Not found'}")
            print(f"Log directory: {self.log_dir or 'Not found'}")
        
        # Allow user to set directories manually if not found
        if not self.workspace_dir:
            user_input = input("\nWorkspace directory not found. Please enter path (or leave blank to skip): ")
            if user_input.strip():
                self.workspace_dir = user_input.strip()
        
        if not self.db_dir:
            user_input = input("Database directory not found. Please enter path (or leave blank to skip): ")
            if user_input.strip():
                self.db_dir = user_input.strip()
        
        if not self.log_dir:
            user_input = input("Log directory not found. Please enter path (or leave blank to skip): ")
            if user_input.strip():
                self.log_dir = user_input.strip()
        
        print("\nGathering statistics...")
        
        # Count sessions
        print("\nCounting sessions...")
        self.stats["sessions"] = self.count_sessions_from_files()
        print(f"Found {self.stats['sessions']} sessions")
        
        # Count LLM calls and tokens
        print("\nCounting LLM calls and tokens...")
        llm_calls, input_tokens, output_tokens = self.count_llm_calls_and_tokens()
        self.stats["llm_calls"] = llm_calls
        self.stats["llm_tokens"]["input"] = input_tokens
        self.stats["llm_tokens"]["output"] = output_tokens
        print(f"Found {llm_calls} LLM calls")
        print(f"Input tokens: {input_tokens}")
        print(f"Output tokens: {output_tokens}")
        
        # Count agentic runs
        print("\nCounting agentic runs...")
        self.stats["agentic_runs"] = self.count_agentic_runs()
        print(f"Found {self.stats['agentic_runs']} agentic runs")
        
        # Get file and folder sizes
        print("\nGathering file and folder sizes...")
        
        dirs_to_check = {
            "workspace": self.workspace_dir,
            "database": self.db_dir,
            "logs": self.log_dir
        }
        
        for name, directory in dirs_to_check.items():
            if directory and os.path.exists(directory):
                size_bytes = self.get_directory_size(directory)
                self.stats["folder_sizes"][name] = {
                    "bytes": size_bytes,
                    "human_readable": self.format_size(size_bytes)
                }
                print(f"{name.capitalize()} directory size: {self.format_size(size_bytes)}")
                
                # Get sizes of subdirectories
                for subdir in os.listdir(directory):
                    subdir_path = os.path.join(directory, subdir)
                    if os.path.isdir(subdir_path):
                        size_bytes = self.get_directory_size(subdir_path)
                        self.stats["folder_sizes"][f"{name}/{subdir}"] = {
                            "bytes": size_bytes,
                            "human_readable": self.format_size(size_bytes)
                        }
        
        # Get log file sizes specifically
        if self.log_dir and os.path.exists(self.log_dir):
            log_files = glob.glob(os.path.join(self.log_dir, "**", "*.log"), recursive=True)
            for log_file in log_files:
                if os.path.exists(log_file):
                    size_bytes = os.path.getsize(log_file)
                    self.stats["log_sizes"][os.path.basename(log_file)] = {
                        "bytes": size_bytes,
                        "human_readable": self.format_size(size_bytes)
                    }
        
        print("\n" + "="*50)
        print("Statistics Gathering Complete")
        print("="*50)
        
        return self.stats
    
    def save_stats_to_file(self, output_file="server_stats.json"):
        """Save the gathered statistics to a JSON file"""
        with open(output_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        print(f"\nStatistics saved to {output_file}")
    
    def print_summary(self):
        """Print a summary of the gathered statistics"""
        print("\n" + "="*50)
        print("Server Statistics Summary")
        print("="*50)
        print(f"Timestamp: {self.stats['timestamp']}")
        print(f"Total sessions: {self.stats['sessions']}")
        print(f"Total LLM calls: {self.stats['llm_calls']}")
        print(f"Total agentic runs: {self.stats['agentic_runs']}")
        
        # Print token usage
        total_tokens = self.stats['llm_tokens']['input'] + self.stats['llm_tokens']['output']
        print(f"Total LLM tokens: {total_tokens}")
        print(f"  - Input tokens: {self.stats['llm_tokens']['input']}")
        print(f"  - Output tokens: {self.stats['llm_tokens']['output']}")
        
        # Print directory sizes
        print("\nDirectory sizes:")
        for name, size_info in self.stats['folder_sizes'].items():
            print(f"  - {name}: {size_info['human_readable']}")
        
        # Print largest log files
        if self.stats['log_sizes']:
            print("\nLargest log files:")
            sorted_logs = sorted(self.stats['log_sizes'].items(), 
                                key=lambda x: x[1]['bytes'], reverse=True)
            for name, size_info in sorted_logs[:5]:  # Show top 5
                print(f"  - {name}: {size_info['human_readable']}")


if __name__ == "__main__":
    gatherer = ServerStatsGatherer()
    gatherer.gather_all_stats()
    gatherer.print_summary()
    
    # Save stats to file
    gatherer.save_stats_to_file()
    
    print("\nYou can view the full statistics in the generated server_stats.json file.")
    print("To gather statistics again in the future, simply run this script again.")
