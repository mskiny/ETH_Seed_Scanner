"""
ETH_Seed_Scanner - Logging Module

Sets up structured logging with configurable levels and handlers.
"""
import os
import logging
import sys
from datetime import datetime
from pathlib import Path

def setup_logger(log_level=logging.INFO, log_file=None):
    """
    Configure and return a logger with console and optional file handlers.
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Optional path to log file
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('app')
    logger.setLevel(log_level)
    logger.handlers = []  # Clear any existing handlers
    
    # Create formatter
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)
    
    # Create file handler if log_file specified
    if log_file is None:
        logs_dir = Path('logs')
        logs_dir.mkdir(exist_ok=True)
        log_file = logs_dir / f"eth_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)
    
    # Create separate error log handler
    error_log_file = logs_dir / f"eth_scan_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    error_handler = logging.FileHandler(error_log_file)
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)  # Only capture ERROR and above
    logger.addHandler(error_handler)
    
    # Log initial message
    logger.info(f"Logging initialized at level {logging.getLevelName(log_level)}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Error log file: {error_log_file}")
    
    return logger

def get_logger():
    """
    Get the app logger instance.
    
    Returns:
        Logger instance or creates a new one if none exists
    """
    logger = logging.getLogger('app')
    if not logger.handlers:
        return setup_logger()
    return logger

def log_seed_phrase_error(seed_phrase, error_message):
    """
    Log seed phrase validation errors with detailed diagnostics.
    
    This function logs to both the regular log (with basic info) and 
    the error log (with more details) to help troubleshooting.
    
    Args:
        seed_phrase: The problematic seed phrase
        error_message: The validation error message
    """
    logger = get_logger()
    
    # Create a safe version of the seed phrase for logging (first few words only)
    words = seed_phrase.strip().split()
    safe_phrase = ' '.join(words[:2]) + ' ...' if len(words) > 2 else seed_phrase
    
    # Log basic info to the main log
    logger.error(f"Invalid seed phrase: {error_message} - '{safe_phrase}'")
    
    # Log more detailed diagnostics to the error log
    error_details = []
    error_details.append(f"Error Type: Seed Phrase Validation Error")
    error_details.append(f"Error Message: {error_message}")
    error_details.append(f"Partial Seed: '{safe_phrase}'")
    
    # Word count diagnostics
    word_count = len(words)
    valid_counts = [12, 15, 18, 21, 24]
    error_details.append(f"Word Count: {word_count} (Valid counts are: {valid_counts})")
    error_details.append(f"Invalid Word Count: {'Yes' if word_count not in valid_counts else 'No'}")
    
    # Check for common spacing issues
    original_length = len(seed_phrase.split())
    cleaned_length = len(seed_phrase.strip().split())
    if original_length != cleaned_length:
        error_details.append(f"Spacing Issue: Extra spaces detected (original words: {original_length}, cleaned: {cleaned_length})")
    
    # Try to identify misspelled words
    try:
        from mnemonic import Mnemonic
        mnemo = Mnemonic("english")
        bip39_wordlist = set(mnemo.wordlist)
        
        invalid_words = []
        for i, word in enumerate(words):
            if word.strip() not in bip39_wordlist:
                invalid_words.append(f"{i+1}: '{word}' (not in BIP39 wordlist)")
                
                # Try to suggest corrections
                similar_words = []
                for valid_word in bip39_wordlist:
                    if valid_word.startswith(word[:2]) and len(valid_word) == len(word):
                        similar_words.append(valid_word)
                    
                if similar_words:
                    if len(similar_words) > 5:
                        similar_words = similar_words[:5]
                    error_details.append(f"  Possible corrections for '{word}': {', '.join(similar_words)}")
        
        if invalid_words:
            error_details.append(f"Invalid Words: {len(invalid_words)} words not in BIP39 wordlist")
            for invalid in invalid_words:
                error_details.append(f"  {invalid}")
        else:
            error_details.append(f"All words are valid BIP39 words, but phrase validation failed (possibly incorrect checksum)")
            
    except Exception as e:
        error_details.append(f"Couldn't analyze words: {str(e)}")
    
    # Log specific suggestions based on word count
    if word_count < min(valid_counts):
        error_details.append(f"Suggestion: Seed phrase is too short. BIP39 requires at least {min(valid_counts)} words.")
    elif word_count > max(valid_counts):
        error_details.append(f"Suggestion: Seed phrase is too long. BIP39 requires at most {max(valid_counts)} words.")
    elif word_count not in valid_counts:
        closest_valid = min(valid_counts, key=lambda x: abs(x - word_count))
        error_details.append(f"Suggestion: Try using {closest_valid} words instead of {word_count}.")
    
    # Log the detailed error info using the logger's error method so it goes to both logs
    logger.error(f"SEED PHRASE ERROR DETAILS:\n" + "\n".join(error_details))
