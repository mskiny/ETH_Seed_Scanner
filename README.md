# 🔍 ETH_Seed_Scanner

A specialized tool for Ethereum wallet discovery and analysis from seed phrases.

## 📋 Overview

ETH_Seed_Scanner automates the process of scanning BIP39 seed phrases to discover active Ethereum wallets. The tool derives addresses using multiple derivation paths, checks balances and transaction history via Etherscan API, and exports the results in a structured format.

## ✨ Features

- **🔷 Ethereum-Focused**: Exclusively supports Ethereum wallet discovery and analysis
- **🔀 Multiple Derivation Paths**: Supports various derivation paths including MetaMask standard path (m/44'/60'/0'/0/x)
- **🧠 Smart Scanning**: Uses gap limit implementation to efficiently discover active wallets
- **💰 Balance & Transaction Checking**: Verifies wallet balances and transaction history via Etherscan API
- **📅 Transaction Dating**: Tracks first and last transaction dates for wallet age analysis
- **⚡ Asynchronous Processing**: Optimized with async API calls for faster processing
- **📊 Data Export**: Exports results to CSV and Excel with timestamp-based filenames
- **🔍 Detailed Error Handling**: Provides comprehensive error logging for invalid seed phrases
- **⚙️ Output Filtering**: Option to show only used addresses in the final output
- **🔒 Security-First**: Securely handles sensitive seed phrases and private keys
- **⚙️ Configurable**: Easy to customize gap limits, derivation paths, and output column ordering

## 📋 Requirements

- Python 3.9+
- Required packages:
  - web3>=6.0.0
  - eth-account>=0.8.0
  - bip32utils>=0.3.post4
  - mnemonic>=0.20.0
  - aiohttp>=3.8.0
  - click>=8.0.0
- Etherscan API key

## 🚀 Installation

1. Clone the repository:
```
git clone https://github.com/mskiny/ETH_Seed_Scanner.git
cd ETH_Seed_Scanner
```

2. Create and activate a virtual environment:
```
python -m venv venv
.\venv\Scripts\Activate  # On Windows
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:
```
ETHERSCAN_API_KEY=your_etherscan_api_key
```

## 🏃‍♂️ Quick Start

1. Configure the scan parameters in `config/config.json`
2. Run the scanner using the provided PowerShell script:
```
.\run_scanner.ps1 --seed-file seeds.env --format excel
```

## 🔧 Configuration

The `config/config.json` file allows customization of:

```json
{
  "api_keys": {
    "etherscan": ""
  },
  "scan_settings": {
    "derivation_paths": ["m/44'/60'/0'/0/x"],
    "gap_limit": 10,
    "batch_size": 5,
    "threads": 4,
    "check_balance": true,
    "check_transactions": true,
    "include_private_keys": true
  },
  "output_settings": {
    "fields": [
      "path",
      "index",
      "used",
      "balance",
      "transaction_count",
      "first_tx_date",
      "last_tx_date",
      "etherscan_url",
      "address",
      "private_key",
      "seed_phrase"
    ],
    "mask_private_keys": false,
    "show_only_used_addresses": true,
    "output_dir": "results"
  }
}
```

### Key Settings:

- **derivation_paths**: Which paths to check for wallet addresses
- **gap_limit**: Number of consecutive unused addresses to scan before stopping (default: 10)
- **include_private_keys**: Whether to include private keys in the output
- **fields**: Order of columns in the output files
- **mask_private_keys**: Whether to mask private keys for security (default: false)
- **show_only_used_addresses**: Filter results to only show addresses with activity (default: false)

## 🖥️ Usage Examples

```powershell
# Scan with a single seed phrase
.\run_scanner.ps1 --seed "your seed phrase here" --format excel

# Scan with multiple seed phrases from a file
.\run_scanner.ps1 --seed-file seeds.env --format excel

# Export as CSV instead of Excel
.\run_scanner.ps1 --seed-file seeds.env --format csv

# Enable debug logging
.\run_scanner.ps1 --seed-file seeds.env --debug

# Custom output location
.\run_scanner.ps1 --seed-file seeds.env --output custom/path/results.xlsx

# Scan with multiple seed phrases from a file, showing only used addresses
.\run_scanner.ps1 --seed-file seeds.env --format excel

# Enable detailed logging for invalid seed phrases
.\run_scanner.ps1 --seed-file seeds.env --debug
```

## 🔍 Gap Limit Explanation

The scanner implements a "gap limit" algorithm, similar to how wallets like MetaMask discover accounts:

1. For each derivation path, it sequentially checks addresses (index 0, 1, 2...)
2. It continues scanning until it finds a specified number (gap_limit) of consecutive unused addresses
3. This ensures all active wallets are found without checking an unnecessary number of addresses

Example with gap_limit=10:
- If addresses at indices 0, 3, and 5 are active
- The scanner continues until 10 consecutive unused addresses are found after index 5
- This means it will scan addresses 0-15 before stopping

## 🗂️ Output Format

The scanner produces either CSV or Excel files with the following columns (customizable in config.json):

1. **path**: The derivation path used to generate this address
2. **index**: Index position within the derivation path
3. **used**: Whether the address has been used (has balance or transactions)
4. **balance**: Current wallet balance in wei
5. **transaction_count**: Number of transactions for this address
6. **first_tx_date**: When the wallet was first used (date of first transaction)
7. **last_tx_date**: When the wallet was last active (date of most recent transaction)
8. **etherscan_url**: Link to view the address on Etherscan
9. **address**: The Ethereum wallet address
10. **private_key**: The private key for this address (if include_private_keys=true)
11. **seed_phrase**: The source seed phrase

## 🔐 Security Considerations

- Never share output files containing private keys or seed phrases
- Use `include_private_keys: false` when generating reports for sharing
- Store seed phrases securely and avoid transmitting them over insecure channels
- Consider running in a secure, offline environment for handling high-value wallets

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.
