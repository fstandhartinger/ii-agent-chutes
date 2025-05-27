"""Utilities for Pro plan validation and management."""

import os

def get_prime_number() -> int:
    """Get the prime number from environment variables.
    
    Returns:
        The prime number for Pro key validation
    """
    # Get from environment variable
    prime_from_env = os.getenv('PRO_PRIME')
    if prime_from_env:
        try:
            return int(prime_from_env)
        except ValueError:
            pass
    
    # Fallback for development (this should be overridden in production)
    print("WARNING: PRO_PRIME not set in environment variables, using fallback")
    return 982451  # Development fallback

def validate_pro_key(pro_key: str) -> bool:
    """Validates if a Pro key is valid based on the prime number logic.
    
    Args:
        pro_key: The hex string to validate
        
    Returns:
        bool indicating if the key is valid
    """
    try:
        PRO_PRIME = get_prime_number()
        
        # Convert hex to decimal
        decimal_value = int(pro_key, 16)
        
        # Check if it's a valid number and a multiple of our prime
        if decimal_value <= 0:
            return False
            
        return decimal_value % PRO_PRIME == 0
    except (ValueError, TypeError):
        return False

def generate_pro_key() -> str:
    """Generates a new valid Pro key.
    
    Returns:
        A hex string that is a valid Pro key
    """
    import random
    
    PRO_PRIME = get_prime_number()
    
    # Generate a random multiplier (1-1000)
    multiplier = random.randint(1, 1000)
    
    # Calculate the decimal value
    decimal_value = PRO_PRIME * multiplier
    
    # Convert to hex and ensure it's 8 characters
    hex_value = format(decimal_value, 'X')
    
    # Pad with zeros if necessary to make it 8 characters
    return hex_value.zfill(8)

def extract_pro_key_from_query(query_params: dict) -> str | None:
    """Extracts the Pro key from query parameters.
    
    Args:
        query_params: Dictionary of query parameters
        
    Returns:
        The Pro key if present and valid, None otherwise
    """
    pro_key = query_params.get('pro_user_key')
    if not pro_key:
        return None
        
    if validate_pro_key(pro_key):
        return pro_key
        
    return None 