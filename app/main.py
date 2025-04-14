#!/usr/bin/env python
"""
ETH_Seed_Scanner - Main Module

Entry point for the Ethereum Seed Scanner application that discovers 
active Ethereum wallets derived from BIP39 seed phrases.
"""
import os
import sys
import click
import logging
import pandas as pd
import asyncio
from typing import Optional, List, Dict, Any

from app.config import load_config
from app.logger import setup_logger
from app.scan import scan_seed_phrase
from app.output_utils import export_results

def read_seed_phrases(seed_file: str) -> List[str]:
    """
    Read seed phrases from a file, one per line.
    Lines starting with # are treated as comments and ignored.
    
    Args:
        seed_file: Path to the file containing seed phrases
        
    Returns:
        List of seed phrases
    """
    seeds = []
    try:
        with open(seed_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    seeds.append(line)
        return seeds
    except Exception as e:
        raise ValueError(f"Failed to read seed file: {str(e)}")

async def async_main(config: Dict[str, Any], seed_phrase: str = None, seed_file: str = None, 
                     debug: bool = False, format_type: str = 'csv', timestamp: bool = True):
    """
    Main asynchronous entry point for the ETH Seed Scanner.
    
    Args:
        config: Configuration dictionary
        seed_phrase: Optional seed phrase to scan (single mode)
        seed_file: Optional path to file with seed phrases (batch mode)
        debug: Whether to enable debug logging
        format_type: Output format (csv or excel)
        timestamp: Whether to include timestamp in filenames
    """
    setup_logger(debug)
    logger = logging.getLogger(__name__)
    logger.info("Starting ETH_Seed_Scanner")
    
    # Override config settings with command line options
    if format_type:
        config['output_settings'] = config.get('output_settings', {})
        config['output_settings']['format'] = format_type
    
    # Get output path from config
    output_path = config.get('output_settings', {}).get('output_path', 'results/scan')
    
    # Validate configuration
    # validate_config(config)  # This function is not defined in the provided code
    
    if seed_phrase:
        # Single seed phrase mode
        # if not validate_seed_phrase(seed_phrase):  # This function is not defined in the provided code
        #     logger.error("Invalid seed phrase")
        #     return
        
        # Call scan_seed_phrase with the provided seed phrase
        results = await scan_seed_phrase(seed_phrase, config)
        if results:
            export_results(results, output_path=output_path, 
                           use_timestamp=timestamp, format_type=format_type,
                           config=config)
        
    elif seed_file:
        # Batch mode - scan multiple seed phrases from file
        if not os.path.exists(seed_file):
            logger.error(f"Seed file not found: {seed_file}")
            return
            
        with open(seed_file, 'r') as f:
            seeds = []
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                seeds.append(line)
        
        if not seeds:
            logger.error("No valid seed phrases found in file")
            return
            
        # Process each seed phrase
        all_results = []
        for i, seed in enumerate(seeds):
            logger.info(f"Processing seed phrase {i+1}/{len(seeds)}")
            # if not validate_seed_phrase(seed):  # This function is not defined in the provided code
            #     logger.warning(f"Skipping invalid seed phrase {i+1}")
            #     continue
                
            # Scan the seed phrase
            seed_results = await scan_seed_phrase(seed, config)
            all_results.extend(seed_results)
        
        # Export combined results
        results = all_results
        
        # Export the combined results if we have processed multiple seeds
        if all_results:
            export_results(all_results, output_path=output_path, 
                           use_timestamp=timestamp, format_type=format_type,
                           config=config)
    
    else:
        logger.error("Either --seed or --seed-file must be provided")
        return

@click.command()
@click.option('--seed', help='BIP39 seed phrase to scan (Warning: sensitive data)')
@click.option('--seed-file', help='Path to file containing seed phrases (one per line)')
@click.option('--config', default='config/config.json', help='Path to configuration file')
@click.option('--output', default='results/output.csv', help='Path to output file')
@click.option('--debug/--no-debug', default=False, help='Enable debug logging')
@click.option('--timestamp/--no-timestamp', default=True, help='Add timestamp to output filename')
@click.option('--format', 'format_type', type=click.Choice(['csv', 'excel']), default='csv', 
              help='Output file format (csv or excel)')
def main(seed: Optional[str], seed_file: Optional[str], config: str, output: str, 
         debug: bool, timestamp: bool, format_type: str):
    """ETH_Seed_Scanner: Ethereum wallet discovery tool that scans for active wallets derived from seed phrases."""
    
    # Initialize logger
    log_level = logging.DEBUG if debug else logging.INFO
    logger = setup_logger(log_level)
    logger.info("Starting ETH_Seed_Scanner")
    
    # Load configuration
    config_data = load_config(config)
    logger.info(f"Configuration loaded from {config}")
    
    # Run the async main function with an event loop
    asyncio.run(async_main(config_data, seed, seed_file, debug, format_type, timestamp))

if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
