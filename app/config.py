"""
ETH_Seed_Scanner - Configuration Module

Handles loading and validating configuration from config.json and .env files.
"""
import os
import json
import logging
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config/config.json") -> Dict[str, Any]:
    """
    Load and validate configuration from config.json and environment variables.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dict containing merged configuration from file and environment variables
        
    Raises:
        FileNotFoundError: If the configuration file does not exist
        json.JSONDecodeError: If the configuration file is not valid JSON
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Ensure config file exists
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Load configuration from file
    try:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {str(e)}")
        raise
    
    # Override with environment variables where applicable
    if 'api_keys' in config:
        config['api_keys']['etherscan'] = os.getenv('ETHERSCAN_API_KEY', config['api_keys'].get('etherscan', ''))
    
    # Validate configuration
    validate_config(config)
    
    return config

def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate the configuration to ensure all required fields are present.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ValueError: If configuration is missing required fields or contains invalid values
    """
    # Validate API keys
    if 'api_keys' not in config or not config['api_keys'].get('etherscan'):
        logger.warning("Etherscan API key not found. API functionality will be limited.")
    
    # Validate scan settings
    if 'scan_settings' not in config:
        raise ValueError("Configuration must include 'scan_settings'")
    
    scan_settings = config['scan_settings']
    
    # Check if derivation paths are specified
    if 'derivation_paths' not in scan_settings or not scan_settings['derivation_paths']:
        raise ValueError("Configuration must include at least one derivation path")
    
    # Check gap limit
    if 'gap_limit' not in scan_settings or not isinstance(scan_settings['gap_limit'], int):
        raise ValueError("Configuration must include a valid 'gap_limit' as an integer")
    
    if scan_settings['gap_limit'] <= 0:
        raise ValueError("'gap_limit' must be greater than 0")
    
    # Additional validations can be added here
    
    logger.debug("Configuration validation successful")

def create_default_config(config_path: str = "config/config.json") -> None:
    """
    Create a default configuration file if one does not exist.
    
    Args:
        config_path: Path where the configuration file should be created
    """
    default_config = {
        "api_keys": {
            "etherscan": ""  # This should be populated from .env
        },
        "scan_settings": {
            "derivation_paths": [
                "m/44'/60'/0'/0/x",  # BIP44 standard for ETH/MetaMask
                "m/44'/60'/x'/0/0",   # Account-level variation
                "m/44'/60'/0'/x"      # No change address variation
            ],
            "gap_limit": 20,
            "batch_size": 5,
            "threads": 4,
            "check_balance": True,
            "check_transactions": True,
            "include_private_keys": False
        },
        "output_settings": {
            "csv_fields": [
                "address",
                "path",
                "index",
                "balance",
                "tx_count",
                "first_tx_date"
            ],
            "mask_private_keys": True
        }
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # Write default config to file
    with open(config_path, 'w', encoding='utf-8') as config_file:
        json.dump(default_config, config_file, indent=2)
    
    logger.info(f"Created default configuration at {config_path}")
