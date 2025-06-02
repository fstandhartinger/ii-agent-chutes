#!/usr/bin/env python3
"""
Admin script to backup and cleanup server data.
Requires ADMIN_KEY environment variable to be set.
"""

import os
import sys
import requests
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Backup and cleanup server data")
    parser.add_argument("--url", default="https://ii-agent-chutes.onrender.com", help="Server URL")
    parser.add_argument("--backup", action="store_true", help="Download backup before cleanup")
    parser.add_argument("--cleanup", action="store_true", help="Perform cleanup")
    parser.add_argument("--stats", action="store_true", help="Show server statistics")
    args = parser.parse_args()
    
    # Get admin key from environment
    admin_key = os.getenv("ADMIN_KEY")
    if not admin_key:
        print("ERROR: ADMIN_KEY environment variable not set")
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {admin_key}"
    }
    
    # Show stats if requested
    if args.stats:
        print("Fetching server statistics...")
        try:
            response = requests.get(f"{args.url}/admin/stats", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                print("\n=== Server Statistics ===")
                print(f"Server Time: {stats.get('server_time', 'N/A')}")
                
                if 'system' in stats:
                    print("\nSystem:")
                    for key, value in stats['system'].items():
                        print(f"  {key}: {value}")
                
                if 'database' in stats:
                    print("\nDatabase:")
                    for key, value in stats['database'].items():
                        print(f"  {key}: {value}")
                
                if 'workspace' in stats:
                    print("\nWorkspace:")
                    for key, value in stats['workspace'].items():
                        print(f"  {key}: {value}")
                
                if 'logs' in stats:
                    print("\nLogs:")
                    for key, value in stats['logs'].items():
                        print(f"  {key}: {value}")
            else:
                print(f"Failed to get stats: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error getting stats: {e}")
    
    # Download backup if requested
    if args.backup:
        print("\nDownloading backup...")
        try:
            response = requests.get(f"{args.url}/admin/download_data", headers=headers, stream=True)
            if response.status_code == 200:
                filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Backup saved to: {filename}")
            else:
                print(f"Failed to download backup: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error downloading backup: {e}")
    
    # Perform cleanup if requested
    if args.cleanup:
        print("\nPerforming cleanup...")
        try:
            response = requests.post(f"{args.url}/admin/cleanup", headers=headers)
            if response.status_code == 200:
                result = response.json()
                print("\n=== Cleanup Results ===")
                print(f"Workspaces deleted: {result.get('workspaces_deleted', 0)}")
                print(f"Bytes freed: {result.get('bytes_freed_from_workspaces', 0):,}")
                print(f"Database rows deleted: {result.get('db_rows_deleted', 0)}")
                if result.get('errors'):
                    print("\nErrors:")
                    for error in result['errors']:
                        print(f"  - {error}")
            else:
                print(f"Failed to perform cleanup: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error performing cleanup: {e}")

if __name__ == "__main__":
    main() 