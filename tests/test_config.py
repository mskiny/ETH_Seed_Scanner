"""
Test configuration loading and validation.
"""
import os
import json
import tempfile
import pytest
from eth_seed_scanner.config import load_config, validate_config

def test_load_config_missing_file():
    """Test loading a non-existent configuration file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.json")

def test_load_config_invalid_json():
    """Test loading an invalid JSON file raises JSONDecodeError."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write("This is not valid JSON")
        tmp_path = tmp.name
    
    try:
        with pytest.raises(json.JSONDecodeError):
            load_config(tmp_path)
    finally:
        os.unlink(tmp_path)

def test_validate_config_missing_scan_settings():
    """Test validation with missing scan_settings."""
    config = {"api_keys": {"etherscan": "test_key"}}
    with pytest.raises(ValueError, match="must include 'scan_settings'"):
        validate_config(config)

def test_validate_config_missing_derivation_paths():
    """Test validation with missing derivation_paths."""
    config = {
        "api_keys": {"etherscan": "test_key"},
        "scan_settings": {"gap_limit": 20}
    }
    with pytest.raises(ValueError, match="must include at least one derivation path"):
        validate_config(config)

def test_validate_config_invalid_gap_limit():
    """Test validation with invalid gap_limit."""
    config = {
        "api_keys": {"etherscan": "test_key"},
        "scan_settings": {
            "derivation_paths": ["m/44'/60'/0'/0/x"],
            "gap_limit": -1
        }
    }
    with pytest.raises(ValueError, match="must be greater than 0"):
        validate_config(config)

def test_validate_config_valid():
    """Test validation with valid config."""
    config = {
        "api_keys": {"etherscan": "test_key"},
        "scan_settings": {
            "derivation_paths": ["m/44'/60'/0'/0/x"],
            "gap_limit": 20
        }
    }
    # Should not raise any exceptions
    validate_config(config)
