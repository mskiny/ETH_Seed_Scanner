"""
ETH_Seed_Scanner - Scan Module

Implements the core scanning functionality for Ethereum wallet discovery.
"""
import logging
import asyncio
from typing import Dict, Any, List, Callable
import os
from web3 import Web3

from app.wallet import WalletDeriver
from app.api import EtherscanAPI

logger = logging.getLogger(__name__)

async def scan_seed_phrase(seed_phrase: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scan a seed phrase for active Ethereum wallets.
    
    Args:
        seed_phrase: BIP39 seed phrase to scan
        config: Configuration dictionary
        
    Returns:
        List of scanned wallet addresses with metadata
    """
    logger.info("Starting seed phrase scan")
    
    # Validate seed phrase before processing
    is_valid, validation_error = validate_seed_phrase(seed_phrase)
    if not is_valid:
        from app.logger import log_seed_phrase_error
        log_seed_phrase_error(seed_phrase, validation_error)
        return []
    
    # Get gap limit from config
    gap_limit = config.get('scan_settings', {}).get('gap_limit', 10)
    logger.debug(f"Using gap limit of {gap_limit}")
    
    # Create API instance for blockchain data
    api = EtherscanAPI(api_key=config.get('api_keys', {}).get('etherscan', ''))
    
    # Derive addresses from seed phrase
    wallet_deriver = WalletDeriver(
        derivation_paths=config.get('scan_settings', {}).get('derivation_paths', []),
        gap_limit=gap_limit
    )
    
    # Derive all addresses for the seed phrase (up to 100 per path)
    addresses = wallet_deriver.derive_all_addresses(seed_phrase)
    logger.info(f"Derived {len(addresses)} addresses from seed phrase")
    
    # Check for options in config
    check_balance = config.get('scan_settings', {}).get('check_balance', True)
    check_transactions = config.get('scan_settings', {}).get('check_transactions', True)
    include_private_keys = config.get('scan_settings', {}).get('include_private_keys', True)
    
    # Add blockchain data to addresses
    enriched_addresses = await enrich_addresses(
        addresses, 
        api=api,
        check_balance=check_balance,
        check_transactions=check_transactions,
        gap_limit=gap_limit
    )
    
    # Add seed phrase to each address for reference
    for address in enriched_addresses:
        address['seed_phrase'] = seed_phrase
    
    # Handle private keys based on config - DO NOT MASK if include_private_keys is true
    if not include_private_keys:
        for address in enriched_addresses:
            if "private_key" in address:
                address["private_key"] = "[MASKED]"
    
    # Filter addresses based on gap limit logic
    final_addresses = apply_gap_limit(enriched_addresses, gap_limit)
    
    logger.info(f"Found {len([a for a in final_addresses if a.get('used', False)])} used addresses")
    
    return final_addresses

def apply_gap_limit(addresses: List[Dict[str, Any]], gap_limit: int) -> List[Dict[str, Any]]:
    """
    Apply gap limit logic to filter addresses.
    For each path, include all addresses up to 'gap_limit' consecutive unused addresses
    after the last used address.
    
    Args:
        addresses: List of enriched addresses
        gap_limit: Number of consecutive unused addresses to allow
        
    Returns:
        Filtered list of addresses
    """
    # Group addresses by their derivation path pattern (not individual paths)
    addresses_by_path = {}
    for addr in addresses:
        # Extract the path pattern (everything before the last /)
        full_path = addr.get('path', '')
        if '/' in full_path:
            # Get base path pattern (e.g., m/44'/60'/0'/0/x) 
            path_pattern = full_path[:full_path.rfind('/')] + '/x'
        else:
            path_pattern = full_path
            
        if path_pattern not in addresses_by_path:
            addresses_by_path[path_pattern] = []
        addresses_by_path[path_pattern].append(addr)
    
    # Process each path separately
    final_addresses = []
    for path_pattern, path_addresses in addresses_by_path.items():
        # Sort addresses by index to maintain order
        path_addresses.sort(key=lambda x: x.get('index', 0))
        
        # Find the highest index of a used address
        highest_used_idx = -1
        for i, addr in enumerate(path_addresses):
            if addr.get('used', False):
                highest_used_idx = i
        
        # If no used addresses found, include up to gap_limit addresses
        if highest_used_idx == -1:
            cutoff_idx = min(gap_limit, len(path_addresses))
            final_addresses.extend(path_addresses[:cutoff_idx])
            logger.debug(f"No used addresses found for path pattern {path_pattern}, including first {cutoff_idx} addresses")
            continue
        
        # Find the index value of the last used address
        last_used_addr = path_addresses[highest_used_idx]
        last_used_index = last_used_addr.get('index', 0)
        
        # Include all addresses up to gap_limit after the last used address
        cutoff_idx = min(highest_used_idx + gap_limit + 1, len(path_addresses))
        final_addresses.extend(path_addresses[:cutoff_idx])
        
        # Calculate how many addresses we're scanning past the last used one
        addresses_after_last_used = cutoff_idx - highest_used_idx - 1
        
        logger.debug(f"Path pattern {path_pattern}: Last used address at index {last_used_index}, including {addresses_after_last_used} more addresses after it")
    
    return final_addresses

async def enrich_addresses(
    addresses: List[Dict[str, Any]], 
    api: EtherscanAPI,
    check_balance: bool = True,
    check_transactions: bool = True,
    gap_limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Add additional information to addresses like balance and transaction history.
    
    Args:
        addresses: List of derived addresses
        api: API instance for fetching data
        check_balance: Whether to check address balances
        check_transactions: Whether to check transaction history
        gap_limit: Gap limit for scanning
        
    Returns:
        Enriched address information
    """
    # Group addresses by their derivation path
    addresses_by_path = {}
    for addr in addresses:
        path = addr.get('path', '')
        if path not in addresses_by_path:
            addresses_by_path[path] = []
        addresses_by_path[path].append(addr)
    
    # Process each path separately
    results = []
    
    for path, path_addresses in addresses_by_path.items():
        # Sort addresses by index to maintain order
        path_addresses.sort(key=lambda x: x.get('index', 0))
        
        # Process addresses in small batches to avoid rate limiting
        batch_size = 5
        
        for i in range(0, len(path_addresses), batch_size):
            batch = path_addresses[i:i+batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}/{(len(path_addresses) + batch_size - 1)//batch_size} for path {path}")
            
            # Fetch data concurrently for each address in the batch
            for address_info in batch:
                address = address_info['address']
                address_info['used'] = False
                address_info['balance'] = 0
                address_info['transaction_count'] = 0
                address_info['etherscan_url'] = f"https://etherscan.io/address/{address}"
                address_info['first_tx_date'] = None
                address_info['last_tx_date'] = None
                
                try:
                    # Check balance if enabled
                    if check_balance:
                        balance = await api.get_balance(address)
                        address_info['balance'] = balance
                        
                        # If has balance, mark as used
                        if balance > 0:
                            address_info['used'] = True
                    
                    # Check transactions if enabled
                    if check_transactions:
                        # Check transaction count
                        tx_count = await api.get_transaction_count(address)
                        address_info['transaction_count'] = tx_count
                        
                        # If has transactions, mark as used
                        if int(tx_count) > 0:
                            address_info['used'] = True
                            
                            # Fetch transaction dates for used addresses
                            tx_dates = await api.get_transaction_dates(address)
                            address_info['first_tx_date'] = tx_dates['first_tx_date']
                            address_info['last_tx_date'] = tx_dates['last_tx_date']
                except Exception as e:
                    logger.error(f"Error checking transactions for {address}: {str(e)}")
                    address_info['transaction_count'] = 0
                
                results.append(address_info)
    
    return results

def validate_seed_phrase(seed_phrase: str) -> tuple:
    """
    Validate if a seed phrase is in correct BIP39 format.
    
    Args:
        seed_phrase: Seed phrase to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if the seed phrase is None or empty
    if not seed_phrase or len(seed_phrase.strip()) == 0:
        return False, "Seed phrase is empty"
    
    # Check word count
    words = seed_phrase.strip().split()
    valid_counts = [12, 15, 18, 21, 24]
    word_count = len(words)
    
    if word_count not in valid_counts:
        return False, f"Invalid word count: {word_count} (expected one of {valid_counts})"
    
    # Use mnemonic library for BIP39 validation
    try:
        from mnemonic import Mnemonic
        mnemo = Mnemonic("english")
        if not mnemo.check(seed_phrase):
            return False, "Not a valid BIP39 mnemonic (checksum failure or invalid words)"
    except Exception as e:
        return False, f"Validation error: {str(e)}"
    
    # All validation passed
    return True, ""
