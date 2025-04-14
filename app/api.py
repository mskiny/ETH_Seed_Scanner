"""
ETH_Seed_Scanner - API Module

Provides integration with Etherscan API for checking Ethereum wallet balances and transactions.
"""
import os
import logging
import time
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class EtherscanAPI:
    """Wrapper for the Etherscan API with rate limiting and error handling."""
    
    BASE_URL = "https://api.etherscan.io/api"
    
    def __init__(self, api_key: str = None, rate_limit: float = 0.2):
        """
        Initialize the Etherscan API client.
        
        Args:
            api_key: Etherscan API key (defaults to ETHERSCAN_API_KEY environment variable)
            rate_limit: Minimum time between API calls in seconds (default: 0.2s = 5 req/sec)
        """
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY", "")
        self.rate_limit = rate_limit
        self.last_request_time = 0
        
        if not self.api_key:
            logger.warning("No Etherscan API key provided. API calls may be rate limited.")
    
    async def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the Etherscan API with rate limiting.
        
        Args:
            params: Parameters for the API request
            
        Returns:
            JSON response from the API
            
        Raises:
            Exception: If the API request fails
        """
        # Add API key to parameters
        params["apikey"] = self.api_key
        
        # Apply rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last)
        
        # Make API request
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Check for API errors
                    if data.get("status") == "0" and data.get("message") != "No transactions found":
                        error = data.get("result", "Unknown error")
                        logger.error(f"Etherscan API error: {error}")
                        raise Exception(f"Etherscan API error: {error}")
                    
                    self.last_request_time = time.time()
                    return data
        
        except aiohttp.ClientError as e:
            logger.error(f"Etherscan API request failed: {str(e)}")
            raise
    
    async def get_balance(self, address: str) -> float:
        """
        Get the balance of an Ethereum address in Ether.
        
        Args:
            address: Ethereum address to check
            
        Returns:
            Balance in Ether (float)
        """
        params = {
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest"
        }
        
        response = await self._make_request(params)
        
        # Convert balance from wei to ether (1 ether = 10^18 wei)
        balance_wei = int(response.get("result", "0"))
        balance_eth = balance_wei / 10**18
        
        return balance_eth
    
    async def get_transaction_count(self, address: str) -> int:
        """
        Get the number of transactions for an Ethereum address.
        
        Args:
            address: Ethereum address to check
            
        Returns:
            Number of transactions
        """
        params = {
            "module": "proxy",
            "action": "eth_getTransactionCount",
            "address": address,
            "tag": "latest"
        }
        
        response = await self._make_request(params)
        
        # Convert hex transaction count to integer
        tx_count_hex = response.get("result", "0x0")
        tx_count = int(tx_count_hex, 16)
        
        return tx_count
    
    async def get_first_transaction(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get the first transaction for an Ethereum address.
        
        Args:
            address: Ethereum address to check
            
        Returns:
            First transaction details or None if no transactions
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": "0",
            "endblock": "99999999",
            "page": "1",
            "offset": "1",
            "sort": "asc"
        }
        
        response = await self._make_request(params)
        
        # Check if any transactions were found
        result = response.get("result", [])
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        
        return None
    
    async def get_last_transaction(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent transaction for an Ethereum address.
        
        Args:
            address: Ethereum address to check
            
        Returns:
            Latest transaction details or None if no transactions
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": "0",
            "endblock": "99999999",
            "page": "1",
            "offset": "1",
            "sort": "desc"  # Sort in descending order to get the most recent first
        }
        
        response = await self._make_request(params)
        
        # Check if any transactions were found
        result = response.get("result", [])
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        
        return None
    
    async def get_transaction_dates(self, address: str) -> Dict[str, Optional[str]]:
        """
        Get the first and last transaction dates for an Ethereum address.
        
        Args:
            address: Ethereum address to check
            
        Returns:
            Dictionary with 'first_tx_date' and 'last_tx_date' keys (ISO format)
        """
        result = {
            'first_tx_date': None,
            'last_tx_date': None
        }
        
        # Get first transaction
        first_tx = await self.get_first_transaction(address)
        if first_tx and 'timeStamp' in first_tx:
            # Convert Unix timestamp to ISO format date
            timestamp = int(first_tx['timeStamp'])
            result['first_tx_date'] = time.strftime('%Y-%m-%d', time.gmtime(timestamp))
        
        # Get last transaction if there was a first one
        if result['first_tx_date']:
            last_tx = await self.get_last_transaction(address)
            if last_tx and 'timeStamp' in last_tx:
                timestamp = int(last_tx['timeStamp'])
                result['last_tx_date'] = time.strftime('%Y-%m-%d', time.gmtime(timestamp))
        
        return result
    
    async def batch_get_balances(self, addresses: List[str]) -> Dict[str, float]:
        """
        Get balances for multiple Ethereum addresses in parallel.
        
        Args:
            addresses: List of Ethereum addresses to check
            
        Returns:
            Dictionary mapping addresses to their balances in Ether
        """
        tasks = [self.get_balance(address) for address in addresses]
        balances = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for i, address in enumerate(addresses):
            if isinstance(balances[i], Exception):
                logger.error(f"Failed to get balance for {address}: {str(balances[i])}")
                result[address] = 0.0
            else:
                result[address] = balances[i]
        
        return result
