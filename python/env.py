import os
from typing import Dict
import shlex  # For safely splitting quoted values

def load_dotenv(file_path: str = '.env') -> Dict[str, str]:
    """
    Load a .env file and return its contents as a dictionary.
    
    Args:
        file_path (str): Path to the .env file. Defaults to '.env' in the current directory.
    
    Returns:
        Dict[str, str]: A dictionary of {key: value} pairs.
    
    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If a line doesn't contain exactly one '='.
    """
    env_vars = {}
    if not os.path.exists(file_path):
        raise FileNotFoundError(f".env file not found at {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue  # Skip empty lines and comments
            
            if '=' not in line:
                raise ValueError(f"Invalid line {line_num}: '{line}' (missing '=')")
            
            key, value = line.split('=', 1)
            key = key.strip()
            if not key:
                raise ValueError(f"Invalid line {line_num}: empty key")
            
            # Handle quoted values (e.g., "value with space")
            if value.strip().startswith('"') and value.strip().endswith('"'):
                value = shlex.split(value)[0]  # Safely unquote
            else:
                value = value.strip()
            
            env_vars[key] = value
    
    return env_vars

# Example usage:
if __name__ == "__main__":
    try:
        config = load_dotenv()
        print(config)  # Output: {'DATABASE_IP': '192.168.1.100', 'API_SERVER_IP': '10.0.0.50', ...}
        
        # Access a specific value
        db_ip = config.get('DATABASE_IP', 'localhost')
        print(f"Database IP: {db_ip}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading .env: {e}")
