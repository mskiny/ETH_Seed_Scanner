#!/usr/bin/env python
"""
Output utilities for ETH_Seed_Scanner

This module provides functions for exporting scan results to different formats
including CSV and Excel, with support for timestamped filenames.
"""
import os
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

def get_timestamped_filename(base_path: str, extension: str = 'csv') -> str:
    """
    Generate a timestamped filename.
    
    Args:
        base_path: Base path for the file
        extension: File extension without dot
        
    Returns:
        Path with timestamp inserted before extension
    """
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # Create directory if it doesn't exist
    directory = os.path.dirname(base_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    # Generate filename with timestamp
    if '.' in os.path.basename(base_path):
        # If there's already an extension, replace it
        filename = f"{os.path.splitext(base_path)[0]}_{timestamp}.{extension}"
    else:
        # Otherwise just append the timestamp and extension
        filename = f"{base_path}_{timestamp}.{extension}"
    
    return filename

def export_results(results: List[Dict[str, Any]], output_path: str, 
                  use_timestamp: bool = False, format_type: str = 'csv',
                  config: Optional[Dict[str, Any]] = None) -> str:
    """
    Export wallet scanning results to the specified format.
    
    Args:
        results: List of wallet scan results
        output_path: Path to save the output file
        use_timestamp: Whether to append a timestamp to the filename
        format_type: Output format ('csv' or 'excel')
        config: Configuration dictionary for additional export options
        
    Returns:
        The path to the saved file
    """
    if not results:
        logger.warning("No results to export")
        return ""
    
    # Convert results to DataFrame
    df = pd.DataFrame(results)
    
    # Filter by used addresses if configured
    if config and config.get('output_settings', {}).get('show_only_used_addresses', False):
        used_count = len(df[df['used'] == True])
        total_count = len(df)
        df = df[df['used'] == True]
        logger.info(f"Filtered output to show only used addresses ({used_count} of {total_count} total addresses)")
    
    # Determine file extension based on format type
    extension = 'xlsx' if format_type.lower() == 'excel' else 'csv'
    
    # Generate final path with timestamp if requested
    final_path = output_path
    if use_timestamp:
        # If a file extension is provided in the output_path, replace it
        if '.' in os.path.basename(output_path):
            base_path = os.path.splitext(output_path)[0]
            final_path = get_timestamped_filename(base_path, extension)
        else:
            final_path = get_timestamped_filename(output_path, extension)
    elif format_type.lower() == 'excel' and not output_path.endswith('.xlsx'):
        # If Excel format is requested but filename doesn't end with .xlsx
        final_path = os.path.splitext(output_path)[0] + '.xlsx'
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    
    # Export based on format type
    if format_type.lower() == 'excel':
        export_to_excel(df, final_path, config)
    else:
        df.to_csv(final_path, index=False)
        logger.info(f"Results exported to CSV: {final_path}")
    
    return final_path


def export_to_excel(df: pd.DataFrame, output_path: str, config: Optional[Dict[str, Any]] = None) -> None:
    """
    Export results to an Excel file with formatted headers and filters.
    Uses the field order specified in config.json.
    
    Args:
        df: DataFrame containing the scan results
        output_path: Path to save the Excel file
        config: Configuration dictionary for additional export options
    """
    try:
        # Load config to get field order
        config_path = 'config/config.json'
        field_order = []
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if 'output_settings' in config and 'fields' in config['output_settings']:
                        field_order = config['output_settings']['fields']
                        logger.debug(f"Using field order from config: {field_order}")
        except Exception as e:
            logger.warning(f"Could not load field order from config: {str(e)}")
        
        # Remove balance_eth as requested
        if 'balance_eth' in df.columns:
            df = df.drop('balance_eth', axis=1)
            
        # Create Excel writer
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        
        # Order columns based on field_order, if specified
        columns = df.columns.tolist()
        ordered_columns = []
        
        # Add columns in the order specified in config, if they exist in the DataFrame
        for field in field_order:
            if field in columns:
                ordered_columns.append(field)
        
        # Add any remaining columns that weren't in the config
        for col in columns:
            if col not in ordered_columns:
                ordered_columns.append(col)
        
        # Reorder the DataFrame columns
        if ordered_columns:
            df = df[ordered_columns]
        
        # Convert to Excel
        df.to_excel(writer, index=False, sheet_name='Wallet Scan Results')
        
        # Get the workbook and the worksheet
        workbook = writer.book
        worksheet = writer.sheets['Wallet Scan Results']
        
        # Format the header row
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9D9D9',
            'border': 1
        })
        
        # Format for transaction dates
        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd',
            'align': 'center'
        })
        
        # Apply header formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
            # Auto-fit column width (max 50 characters)
            max_width = min(max(df[value].astype(str).str.len().max(), len(str(value))), 50)
            worksheet.set_column(col_num, col_num, max_width + 2)
            
            # Apply date formatting to date columns
            if value in ['first_tx_date', 'last_tx_date']:
                worksheet.set_column(col_num, col_num, 12, date_format)
        
        # Format 'used' column as Yes/No instead of True/False
        if 'used' in df.columns:
            used_col_idx = df.columns.get_loc('used')
            yes_no_format = workbook.add_format({'align': 'center'})
            
            for row_num in range(1, len(df) + 1):
                used_value = df.iloc[row_num - 1]['used']
                display_value = 'Yes' if used_value else 'No'
                worksheet.write(row_num, used_col_idx, display_value, yes_no_format)
        
        # Format seed phrase column for better readability
        if 'seed_phrase' in df.columns:
            seed_phrase_col_idx = df.columns.get_loc('seed_phrase')
            worksheet.write(0, seed_phrase_col_idx, "Source Seed Phrase", header_format)
        
        # Format etherscan_url column as hyperlinks
        if 'etherscan_url' in df.columns:
            etherscan_url_col_idx = df.columns.get_loc('etherscan_url')
            worksheet.write(0, etherscan_url_col_idx, "Etherscan Link", header_format)
            
            for row_num in range(1, len(df) + 1):
                url = df.iloc[row_num - 1]['etherscan_url']
                address = df.iloc[row_num - 1]['address']
                worksheet.write(row_num, etherscan_url_col_idx, f"View {address[:6]}...{address[-4:]}", workbook.add_format({'align': 'center', 'font_color': 'blue', 'underline': True}))
        
        writer.close()
        logger.info(f"Results exported to Excel: {output_path}")
    except Exception as e:
        logger.error(f"Failed to export to Excel: {str(e)}")
        # Fallback to CSV
        csv_path = os.path.splitext(output_path)[0] + '.csv'
        df.to_csv(csv_path, index=False)
        logger.warning(f"Exported to CSV instead: {csv_path}")
