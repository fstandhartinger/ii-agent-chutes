#!/usr/bin/env python3
"""
Persistent Storage Setup Script

This script helps set up and migrate data to the persistent storage directory at /var/data.
It can be used to:
1. Check if persistent storage is available
2. Migrate existing data to persistent storage
3. Set up the directory structure
"""

import os
import sys
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

# Add parent directory to path to import ii_agent
sys.path.append(str(Path(__file__).parent.parent))

# Define constants directly to avoid import issues
PERSISTENT_DATA_ROOT = "/var/data"
PERSISTENT_WORKSPACE_ROOT = f"{PERSISTENT_DATA_ROOT}/workspace"
PERSISTENT_DB_PATH = f"{PERSISTENT_DATA_ROOT}/events.db"
PERSISTENT_LOGS_PATH = f"{PERSISTENT_DATA_ROOT}/agent_logs.txt"


def check_persistent_storage() -> bool:
    """Check if persistent storage directory exists and is writable."""
    try:
        if not os.path.exists(PERSISTENT_DATA_ROOT):
            print(f"❌ Persistent storage directory does not exist: {PERSISTENT_DATA_ROOT}")
            return False
        
        # Test write permissions
        test_file = Path(PERSISTENT_DATA_ROOT) / "test_write"
        try:
            test_file.write_text("test")
            test_file.unlink()
            print(f"✅ Persistent storage is available and writable: {PERSISTENT_DATA_ROOT}")
            return True
        except PermissionError:
            print(f"❌ Persistent storage exists but is not writable: {PERSISTENT_DATA_ROOT}")
            return False
    except Exception as e:
        print(f"❌ Error checking persistent storage: {e}")
        return False


def setup_directory_structure():
    """Create the necessary directory structure in persistent storage."""
    if not check_persistent_storage():
        return False
    
    directories = [
        PERSISTENT_DATA_ROOT,
        PERSISTENT_WORKSPACE_ROOT,
        Path(PERSISTENT_DB_PATH).parent,
        Path(PERSISTENT_LOGS_PATH).parent,
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        except Exception as e:
            print(f"❌ Failed to create directory {directory}: {e}")
            return False
    
    return True


def migrate_database(source_db: str = "events.db") -> bool:
    """Migrate the SQLite database to persistent storage."""
    if not os.path.exists(source_db):
        print(f"ℹ️  No existing database found at {source_db}")
        return True
    
    if os.path.exists(PERSISTENT_DB_PATH):
        print(f"⚠️  Database already exists at {PERSISTENT_DB_PATH}")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Database migration skipped")
            return True
    
    try:
        # Copy the database file
        shutil.copy2(source_db, PERSISTENT_DB_PATH)
        print(f"✅ Database migrated from {source_db} to {PERSISTENT_DB_PATH}")
        
        # Update workspace paths in the database
        update_database_paths()
        return True
    except Exception as e:
        print(f"❌ Failed to migrate database: {e}")
        return False


def update_database_paths():
    """Update workspace paths in the database to use persistent storage."""
    try:
        conn = sqlite3.connect(PERSISTENT_DB_PATH)
        cursor = conn.cursor()
        
        # Get all sessions with local workspace paths
        cursor.execute("SELECT id, workspace_dir FROM session WHERE workspace_dir NOT LIKE '/var/data%'")
        sessions = cursor.fetchall()
        
        for session_id, old_workspace in sessions:
            # Extract the session UUID from the old path
            old_path = Path(old_workspace)
            session_uuid = old_path.name
            
            # Create new persistent path
            new_workspace = str(Path(PERSISTENT_WORKSPACE_ROOT) / session_uuid)
            
            # Update the database
            cursor.execute(
                "UPDATE session SET workspace_dir = ? WHERE id = ?",
                (new_workspace, session_id)
            )
            print(f"Updated session {session_id}: {old_workspace} -> {new_workspace}")
        
        conn.commit()
        conn.close()
        print(f"✅ Updated {len(sessions)} session workspace paths")
    except Exception as e:
        print(f"❌ Failed to update database paths: {e}")


def migrate_workspace_files(source_workspace: str = "workspace") -> bool:
    """Migrate workspace files to persistent storage."""
    if not os.path.exists(source_workspace):
        print(f"ℹ️  No existing workspace found at {source_workspace}")
        return True
    
    try:
        # Copy all workspace directories
        source_path = Path(source_workspace)
        for session_dir in source_path.iterdir():
            if session_dir.is_dir():
                dest_dir = Path(PERSISTENT_WORKSPACE_ROOT) / session_dir.name
                if dest_dir.exists():
                    print(f"⚠️  Workspace already exists: {dest_dir}")
                    continue
                
                shutil.copytree(session_dir, dest_dir)
                print(f"✅ Migrated workspace: {session_dir} -> {dest_dir}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to migrate workspace files: {e}")
        return False


def migrate_logs(source_logs: str = "agent_logs.txt") -> bool:
    """Migrate log files to persistent storage."""
    if not os.path.exists(source_logs):
        print(f"ℹ️  No existing logs found at {source_logs}")
        return True
    
    try:
        if os.path.exists(PERSISTENT_LOGS_PATH):
            # Append to existing logs
            with open(source_logs, 'r') as src, open(PERSISTENT_LOGS_PATH, 'a') as dst:
                dst.write("\n--- Migrated logs ---\n")
                dst.write(src.read())
        else:
            # Copy logs
            shutil.copy2(source_logs, PERSISTENT_LOGS_PATH)
        
        print(f"✅ Logs migrated from {source_logs} to {PERSISTENT_LOGS_PATH}")
        return True
    except Exception as e:
        print(f"❌ Failed to migrate logs: {e}")
        return False


def main():
    """Main migration function."""
    print("🚀 Setting up persistent storage for ii-agent-chutes")
    print("=" * 50)
    
    # Check if persistent storage is available
    if not check_persistent_storage():
        print("\n❌ Persistent storage is not available. Exiting.")
        return
    
    # Set up directory structure
    print("\n📁 Setting up directory structure...")
    if not setup_directory_structure():
        print("❌ Failed to set up directory structure. Exiting.")
        return
    
    # Migrate data
    print("\n📦 Migrating existing data...")
    
    # Migrate database
    print("\n🗄️  Migrating database...")
    migrate_database()
    
    # Migrate workspace files
    print("\n📂 Migrating workspace files...")
    migrate_workspace_files()
    
    # Migrate logs
    print("\n📝 Migrating logs...")
    migrate_logs()
    
    print("\n✅ Persistent storage setup complete!")
    print(f"📍 Data location: {PERSISTENT_DATA_ROOT}")
    print("\nNext steps:")
    print("1. Restart your application to use persistent storage")
    print("2. Verify that new sessions are created in the persistent directory")
    print("3. Consider backing up your old local files before removing them")


if __name__ == "__main__":
    main() 