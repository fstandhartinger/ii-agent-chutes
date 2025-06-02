#!/usr/bin/env python3
"""
Server Diagnostic Script

Gathers comprehensive statistics about the database, workspaces, logs, and server health.
Useful for monitoring production server health and debugging issues.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import psutil
import re
from typing import Dict, List, Any, Optional

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent))

try:
    from ii_agent.db.manager import DatabaseManager, get_default_db_path
    from ii_agent.utils.constants import PERSISTENT_DATA_ROOT, PERSISTENT_WORKSPACE_ROOT, PERSISTENT_DB_PATH, PERSISTENT_LOGS_PATH
except ImportError as e:
    print(f"Warning: Could not import ii_agent modules: {e}")
    print("Some features may not work correctly.")
    PERSISTENT_DATA_ROOT = "/var/data"
    PERSISTENT_WORKSPACE_ROOT = f"{PERSISTENT_DATA_ROOT}/workspace"
    PERSISTENT_DB_PATH = f"{PERSISTENT_DATA_ROOT}/events.db"
    PERSISTENT_LOGS_PATH = f"{PERSISTENT_DATA_ROOT}/agent_logs.txt"


def format_bytes(bytes_value: int) -> str:
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def get_file_stats(file_path: Path) -> Dict[str, Any]:
    """Get detailed statistics about a file."""
    if not file_path.exists():
        return {"exists": False}
    
    stat = file_path.stat()
    return {
        "exists": True,
        "size": stat.st_size,
        "size_human": format_bytes(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "permissions": oct(stat.st_mode)[-3:],
    }


def get_directory_stats(dir_path: Path, max_depth: int = 2) -> Dict[str, Any]:
    """Get detailed statistics about a directory and its contents."""
    if not dir_path.exists():
        return {"exists": False}
    
    total_size = 0
    file_count = 0
    dir_count = 0
    file_types = {}
    largest_files = []
    
    try:
        for item in dir_path.rglob("*"):
            if item.is_file():
                file_count += 1
                size = item.stat().st_size
                total_size += size
                
                # Track file types
                suffix = item.suffix.lower() or "no_extension"
                file_types[suffix] = file_types.get(suffix, 0) + 1
                
                # Track largest files
                largest_files.append({
                    "path": str(item.relative_to(dir_path)),
                    "size": size,
                    "size_human": format_bytes(size)
                })
            elif item.is_dir():
                dir_count += 1
        
        # Sort largest files and keep top 10
        largest_files.sort(key=lambda x: x["size"], reverse=True)
        largest_files = largest_files[:10]
        
    except PermissionError:
        return {"exists": True, "error": "Permission denied"}
    
    return {
        "exists": True,
        "total_size": total_size,
        "total_size_human": format_bytes(total_size),
        "file_count": file_count,
        "dir_count": dir_count,
        "file_types": file_types,
        "largest_files": largest_files,
    }


def get_database_stats() -> Dict[str, Any]:
    """Get comprehensive database statistics."""
    db_path = get_default_db_path() if 'get_default_db_path' in globals() else PERSISTENT_DB_PATH
    
    # Check if database exists
    if not os.path.exists(db_path):
        # Try local database
        db_path = "events.db"
        if not os.path.exists(db_path):
            return {"error": "Database not found"}
    
    stats = {
        "database_path": db_path,
        "file_stats": get_file_stats(Path(db_path))
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Basic table counts
        cursor.execute("SELECT COUNT(*) FROM session")
        stats["total_sessions"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM event")
        stats["total_events"] = cursor.fetchone()[0]
        
        # Session statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT device_id) as unique_devices,
                MIN(created_at) as first_session,
                MAX(created_at) as last_session
            FROM session
        """)
        row = cursor.fetchone()
        stats["unique_devices"] = row[0]
        stats["first_session"] = row[1]
        stats["last_session"] = row[2]
        
        # Event type breakdown
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM event
            GROUP BY event_type
            ORDER BY count DESC
        """)
        stats["event_types"] = dict(cursor.fetchall())
        
        # Recent activity (last 24 hours)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM session 
            WHERE created_at > ?
        """, (yesterday,))
        stats["sessions_last_24h"] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM event 
            WHERE timestamp > ?
        """, (yesterday,))
        stats["events_last_24h"] = cursor.fetchone()[0]
        
        # Average events per session
        if stats["total_sessions"] > 0:
            stats["avg_events_per_session"] = stats["total_events"] / stats["total_sessions"]
        else:
            stats["avg_events_per_session"] = 0
        
        # Check for Pro usage table
        try:
            cursor.execute("SELECT COUNT(*) FROM pro_usage")
            stats["total_pro_usage_records"] = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT pro_key, SUM(sonnet_requests) as total_requests
                FROM pro_usage
                GROUP BY pro_key
                ORDER BY total_requests DESC
                LIMIT 10
            """)
            stats["top_pro_users"] = [
                {"pro_key": row[0][:4] + "****", "requests": row[1]}
                for row in cursor.fetchall()
            ]
        except sqlite3.OperationalError:
            stats["pro_usage_available"] = False
        
        conn.close()
        
    except Exception as e:
        stats["error"] = str(e)
    
    return stats


def analyze_log_files() -> Dict[str, Any]:
    """Analyze log files for patterns and statistics."""
    log_stats = {}
    
    # Check different possible log locations
    log_paths = [
        Path(PERSISTENT_LOGS_PATH),
        Path("agent_logs.txt"),
        Path("logs/agent_logs.txt"),
    ]
    
    for log_path in log_paths:
        if log_path.exists():
            log_stats[str(log_path)] = analyze_single_log_file(log_path)
    
    return log_stats


def analyze_single_log_file(log_path: Path) -> Dict[str, Any]:
    """Analyze a single log file for patterns."""
    stats = get_file_stats(log_path)
    
    if not stats["exists"]:
        return stats
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        stats["total_lines"] = len(lines)
        
        # Count different log levels
        log_levels = {"ERROR": 0, "WARNING": 0, "INFO": 0, "DEBUG": 0}
        websocket_errors = 0
        connection_events = 0
        llm_calls = 0
        token_usage = {"input": 0, "output": 0}
        
        # Patterns to look for
        patterns = {
            "websocket_disconnect": r"Client disconnected|WebSocket.*disconnect",
            "websocket_error": r"WebSocket.*error|filedescriptor.*out of range",
            "connection_established": r"connection.*established|WebSocket connection accepted",
            "llm_call": r"USING.*LLM PROVIDER|Model:",
            "chutes_call": r"CHUTES.*response|chutes.*request",
            "anthropic_call": r"ANTHROPIC.*response|anthropic.*request",
            "token_usage": r"tokens?.*(\d+)",
        }
        
        pattern_counts = {key: 0 for key in patterns.keys()}
        
        for line in lines:
            # Count log levels
            for level in log_levels:
                if level in line:
                    log_levels[level] += 1
                    break
            
            # Count specific patterns
            for pattern_name, pattern in patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    pattern_counts[pattern_name] += 1
            
            # Extract token usage if possible
            token_match = re.search(r'(\d+)\s*tokens?', line, re.IGNORECASE)
            if token_match:
                tokens = int(token_match.group(1))
                if "input" in line.lower():
                    token_usage["input"] += tokens
                elif "output" in line.lower():
                    token_usage["output"] += tokens
        
        stats.update({
            "log_levels": log_levels,
            "pattern_counts": pattern_counts,
            "estimated_token_usage": token_usage,
        })
        
        # Get recent errors (last 100 lines)
        recent_errors = []
        for line in lines[-100:]:
            if "ERROR" in line:
                recent_errors.append(line.strip())
        
        stats["recent_errors"] = recent_errors[-10:]  # Last 10 errors
        
    except Exception as e:
        stats["analysis_error"] = str(e)
    
    return stats


def get_system_stats() -> Dict[str, Any]:
    """Get system resource statistics."""
    try:
        stats = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used,
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent,
            },
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
        }
        
        # Convert bytes to human readable
        for key in ["total", "available", "used"]:
            if key in stats["memory"]:
                stats["memory"][f"{key}_human"] = format_bytes(stats["memory"][key])
        
        for key in ["total", "used", "free"]:
            if key in stats["disk"]:
                stats["disk"][f"{key}_human"] = format_bytes(stats["disk"][key])
        
        # Get process information
        try:
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'cmdline']):
                if 'python' in proc.info['name'].lower():
                    python_processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "memory_mb": proc.info['memory_info'].rss / 1024 / 1024,
                        "cpu_percent": proc.info['cpu_percent'],
                        "cmdline": ' '.join(proc.info['cmdline'][:3]) if proc.info['cmdline'] else '',
                    })
            
            stats["python_processes"] = python_processes
        except Exception as e:
            stats["process_error"] = str(e)
        
    except ImportError:
        stats = {"error": "psutil not available - install with: pip install psutil"}
    except Exception as e:
        stats = {"error": str(e)}
    
    return stats


def get_workspace_stats() -> Dict[str, Any]:
    """Get statistics about workspace directories."""
    workspace_stats = {}
    
    # Check different possible workspace locations
    workspace_paths = [
        Path(PERSISTENT_WORKSPACE_ROOT),
        Path("workspace"),
        Path("data/workspace"),
    ]
    
    for workspace_path in workspace_paths:
        if workspace_path.exists():
            workspace_stats[str(workspace_path)] = get_directory_stats(workspace_path)
            
            # Get individual session statistics
            session_dirs = []
            try:
                for session_dir in workspace_path.iterdir():
                    if session_dir.is_dir():
                        session_stats = get_directory_stats(session_dir, max_depth=1)
                        session_stats["name"] = session_dir.name
                        session_dirs.append(session_stats)
                
                # Sort by size and keep top 10
                session_dirs.sort(key=lambda x: x.get("total_size", 0), reverse=True)
                workspace_stats[str(workspace_path)]["largest_sessions"] = session_dirs[:10]
                workspace_stats[str(workspace_path)]["total_sessions"] = len(session_dirs)
                
            except Exception as e:
                workspace_stats[str(workspace_path)]["session_analysis_error"] = str(e)
    
    return workspace_stats


def check_network_connections() -> Dict[str, Any]:
    """Check for active network connections (WebSocket related)."""
    try:
        connections = psutil.net_connections(kind='inet')
        
        stats = {
            "total_connections": len(connections),
            "by_status": {},
            "by_port": {},
            "websocket_ports": [],
        }
        
        for conn in connections:
            # Count by status
            status = conn.status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Count by local port
            if conn.laddr:
                port = conn.laddr.port
                stats["by_port"][port] = stats["by_port"].get(port, 0) + 1
                
                # Check for common WebSocket ports
                if port in [8000, 8080, 3000, 5000, 80, 443]:
                    stats["websocket_ports"].append({
                        "port": port,
                        "status": status,
                        "remote": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    })
        
        return stats
        
    except Exception as e:
        return {"error": str(e)}


def main():
    """Main diagnostic function."""
    print("🔍 Server Diagnostic Report")
    print("=" * 50)
    print(f"Generated at: {datetime.now().isoformat()}")
    print()
    
    # Gather all statistics
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "database": get_database_stats(),
        "workspaces": get_workspace_stats(),
        "logs": analyze_log_files(),
        "system": get_system_stats(),
        "network": check_network_connections(),
    }
    
    # Print summary
    print("📊 SUMMARY")
    print("-" * 20)
    
    db_stats = diagnostics["database"]
    if "error" not in db_stats:
        print(f"📁 Database: {db_stats.get('total_sessions', 0)} sessions, {db_stats.get('total_events', 0)} events")
        print(f"📈 Recent activity: {db_stats.get('sessions_last_24h', 0)} sessions, {db_stats.get('events_last_24h', 0)} events (24h)")
        if db_stats.get("file_stats", {}).get("exists"):
            print(f"💾 DB size: {db_stats['file_stats']['size_human']}")
    else:
        print(f"❌ Database error: {db_stats['error']}")
    
    workspace_stats = diagnostics["workspaces"]
    total_workspace_size = 0
    total_workspace_files = 0
    for path, stats in workspace_stats.items():
        if stats.get("exists") and "error" not in stats:
            total_workspace_size += stats.get("total_size", 0)
            total_workspace_files += stats.get("file_count", 0)
            print(f"📂 Workspace {path}: {stats.get('total_sessions', 0)} sessions, {format_bytes(stats.get('total_size', 0))}")
    
    system_stats = diagnostics["system"]
    if "error" not in system_stats:
        print(f"🖥️  System: {system_stats.get('cpu_percent', 0):.1f}% CPU, {system_stats['memory']['percent']:.1f}% RAM")
        print(f"💿 Disk: {system_stats['disk']['percent']:.1f}% used ({system_stats['disk']['used_human']} / {system_stats['disk']['total_human']})")
    
    network_stats = diagnostics["network"]
    if "error" not in network_stats:
        print(f"🌐 Network: {network_stats.get('total_connections', 0)} connections")
        if network_stats.get("websocket_ports"):
            print(f"🔌 WebSocket ports active: {len(network_stats['websocket_ports'])}")
    
    print()
    print("📄 Full report saved to: diagnostic_report.json")
    
    # Save detailed report to file
    with open("diagnostic_report.json", "w") as f:
        json.dump(diagnostics, f, indent=2, default=str)
    
    # Also create a human-readable summary
    with open("diagnostic_summary.txt", "w") as f:
        f.write("SERVER DIAGNOSTIC SUMMARY\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        f.write("DATABASE STATISTICS:\n")
        f.write("-" * 20 + "\n")
        if "error" not in db_stats:
            f.write(f"Total sessions: {db_stats.get('total_sessions', 0)}\n")
            f.write(f"Total events: {db_stats.get('total_events', 0)}\n")
            f.write(f"Unique devices: {db_stats.get('unique_devices', 0)}\n")
            f.write(f"Sessions (24h): {db_stats.get('sessions_last_24h', 0)}\n")
            f.write(f"Events (24h): {db_stats.get('events_last_24h', 0)}\n")
            f.write(f"Avg events/session: {db_stats.get('avg_events_per_session', 0):.2f}\n")
            if db_stats.get("file_stats", {}).get("exists"):
                f.write(f"Database size: {db_stats['file_stats']['size_human']}\n")
        else:
            f.write(f"ERROR: {db_stats['error']}\n")
        
        f.write(f"\nWORKSPACE STATISTICS:\n")
        f.write("-" * 20 + "\n")
        f.write(f"Total workspace size: {format_bytes(total_workspace_size)}\n")
        f.write(f"Total workspace files: {total_workspace_files}\n")
        
        f.write(f"\nSYSTEM RESOURCES:\n")
        f.write("-" * 20 + "\n")
        if "error" not in system_stats:
            f.write(f"CPU usage: {system_stats.get('cpu_percent', 0):.1f}%\n")
            f.write(f"Memory usage: {system_stats['memory']['percent']:.1f}% ({system_stats['memory']['used_human']} / {system_stats['memory']['total_human']})\n")
            f.write(f"Disk usage: {system_stats['disk']['percent']:.1f}% ({system_stats['disk']['used_human']} / {system_stats['disk']['total_human']})\n")
        
        f.write(f"\nNETWORK CONNECTIONS:\n")
        f.write("-" * 20 + "\n")
        if "error" not in network_stats:
            f.write(f"Total connections: {network_stats.get('total_connections', 0)}\n")
            f.write(f"WebSocket ports active: {len(network_stats.get('websocket_ports', []))}\n")
    
    print("📄 Human-readable summary saved to: diagnostic_summary.txt")
    print()
    print("🚀 To run this on your production server:")
    print("   python diagnose_server.py")
    print()
    print("💡 Tip: Run this periodically to monitor server health!")


if __name__ == "__main__":
    main() 