#!/usr/bin/env python3
"""
Simple script to generate Pro keys for testing purposes.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.utils.pro_utils import generate_pro_key, validate_pro_key

def main():
    print("Pro Key Generator")
    print("================")
    
    # Generate a new key
    new_key = generate_pro_key()
    print(f"Generated Pro Key: {new_key}")
    
    # Validate the key
    is_valid = validate_pro_key(new_key)
    print(f"Key is valid: {is_valid}")
    
    # Show example URL
    print(f"\nExample URL: http://localhost:3000/?pro_user_key={new_key}")
    
    print("\nTo use this key:")
    print("1. Copy the URL above")
    print("2. Open it in your browser")
    print("3. Try selecting Claude Sonnet 4 from the model dropdown")

if __name__ == "__main__":
    main() 