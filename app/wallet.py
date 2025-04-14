"""
ETH_Seed_Scanner - Wallet Module

Handles seed phrase validation and Ethereum wallet derivation using BIP39/BIP44 standards.
"""
import logging
from typing import Dict, Any, List, Optional
import binascii
import hashlib
import hmac
from mnemonic import Mnemonic
import bip32utils
from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)

class WalletDeriver:
    """Class for deriving Ethereum wallets from seed phrases using HD wallet standards."""
    
    def __init__(self, derivation_paths: List[str], gap_limit: int = 20):
        """
        Initialize the wallet deriver with derivation paths and gap limit.
        
        Args:
            derivation_paths: List of derivation path patterns to use
            gap_limit: Number of consecutive unused addresses before stopping derivation
        """
        self.derivation_paths = derivation_paths
        self.gap_limit = gap_limit
        self.mnemonic_validator = Mnemonic("english")
        # Enable unaudited HD wallet features in eth_account
        Account.enable_unaudited_hdwallet_features()
        logger.debug(f"Initialized WalletDeriver with {len(derivation_paths)} paths and gap_limit={gap_limit}")
    
    def validate_seed_phrase(self, seed_phrase: str) -> bool:
        """
        Validate that a seed phrase can be used to derive a wallet.
        
        Args:
            seed_phrase: BIP39 seed phrase to validate
            
        Returns:
            True if the seed phrase is valid, False otherwise
        """
        try:
            # Use the mnemonic library for validation
            return self.mnemonic_validator.check(seed_phrase)
        except Exception as e:
            logger.debug(f"Invalid seed phrase: {str(e)}")
            return False
    
    def _prepare_derivation_path(self, path_pattern: str, index: int) -> str:
        """
        Prepare derivation path by replacing 'x' with the index.
        
        Args:
            path_pattern: Path pattern with 'x' placeholder
            index: Index to replace 'x' with
            
        Returns:
            Complete derivation path
        """
        return path_pattern.replace('x', str(index))
    
    def derive_address(self, seed_phrase: str, path: str) -> Dict[str, str]:
        """
        Derive a single Ethereum address from a seed phrase using a specific path.
        
        Args:
            seed_phrase: BIP39 seed phrase
            path: Full derivation path (with index already inserted)
            
        Returns:
            Dictionary with address, path, and private key
        """
        try:
            # Use eth_account to derive address from mnemonic and path
            account = Account.from_mnemonic(
                mnemonic=seed_phrase,
                account_path=path
            )
            
            # Extract address and private key
            address = account.address
            private_key = account.key.hex()
            
            # Return address info
            return {
                "address": address,
                "path": path,
                "private_key": private_key
            }
        except Exception as e:
            logger.error(f"Error deriving address for path {path}: {str(e)}")
            # Return dummy address in case of error (for testing)
            return {
                "address": "0x0000000000000000000000000000000000000000",
                "path": path,
                "private_key": "error",
                "error": str(e)
            }
    
    def derive_addresses_for_path(self, seed_phrase: str, path_pattern: str, max_addresses: int = 100) -> List[Dict[str, str]]:
        """
        Derive addresses for a specific derivation path with a maximum limit.
        
        Args:
            seed_phrase: BIP39 seed phrase
            path_pattern: Derivation path pattern with 'x' placeholder
            max_addresses: Maximum number of addresses to derive
            
        Returns:
            List of derived addresses
        """
        addresses = []
        
        # Scan all addresses up to max_addresses
        # We'll handle gap limit in the scan.py file after we check for balances
        for i in range(max_addresses):
            try:
                path = self._prepare_derivation_path(path_pattern, i)
                address_info = self.derive_address(seed_phrase, path)
                
                # Add index for reference
                address_info["index"] = i
                
                # Initialize used flag (will be updated by API check)
                address_info["used"] = False
                
                addresses.append(address_info)
                
                # Log progress every 20 addresses
                if (i + 1) % 20 == 0:
                    logger.debug(f"Derived {i + 1} addresses for path {path_pattern}")
                
            except Exception as e:
                logger.error(f"Error deriving address for {path_pattern} at index {i}: {str(e)}")
        
        return addresses
    
    def derive_all_addresses(self, seed_phrase: str) -> List[Dict[str, str]]:
        """
        Derive Ethereum addresses from a seed phrase using all configured derivation paths.
        
        Args:
            seed_phrase: BIP39 seed phrase
            
        Returns:
            List of dictionaries with address, path, and private key
        """
        if not self.validate_seed_phrase(seed_phrase):
            logger.error("Invalid seed phrase")
            return []
        
        all_addresses = []
        
        # Process each derivation path
        for path_pattern in self.derivation_paths:
            try:
                # Derive addresses for this path (up to 100 max)
                # We'll derive in batches of 20 initially and dynamically scan more if needed
                derived_addresses = self.derive_addresses_for_path(
                    seed_phrase, 
                    path_pattern, 
                    max_addresses=100  # Maximum to protect against infinite scanning
                )
                
                all_addresses.extend(derived_addresses)
                logger.debug(f"Derived {len(derived_addresses)} addresses for path {path_pattern}")
                
            except Exception as e:
                logger.error(f"Error deriving addresses for path pattern {path_pattern}: {str(e)}")
        
        logger.info(f"Derived a total of {len(all_addresses)} addresses across all paths")
        return all_addresses
