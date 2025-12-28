# services/relayer_service.py
"""
Relayer Service - Executes Transactions on Behalf of Users

Wave 3 Upgrades:
- Integrated NonceManager for concurrent request handling
- Added fee payment support for sustainable business model
- Improved error handling and retry logic
"""
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from web3 import Web3
from web3.middleware import geth_poa_middleware
from django.conf import settings

from services.nonce_manager import nonce_manager

logger = logging.getLogger(__name__)


class RelayerService:
    """
    Wave 3 Enhanced Relayer Service
    
    Key Improvements:
    1. NonceManager integration - prevents TX collision under load
    2. Fee payment support - proves sustainable business model
    3. Better error recovery - syncs nonce on failures
    """
    
    def __init__(self, chain_id: int):
        self.chain_id = chain_id
        
        # 1. Load Network Config
        network_config = settings.NETWORK_CONFIG.get(chain_id)
        if not network_config:
            raise ValueError(f"Unsupported Chain ID: {chain_id}")
        
        self.network_config = network_config
        self.rpc_url = network_config['rpc_url']
        
        # 2. Initialize Web3 with timeout and request kwargs
        logger.info(f"Attempting to connect to Chain {chain_id}")
        logger.info(f"RPC URL: {self.rpc_url}")
        
        # Add request_kwargs for better timeout handling
        request_kwargs = {'timeout': 60}  # 60 second timeout
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs=request_kwargs))
        
        # Inject PoA middleware (Required for Polygon Amoy & some testnets)
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Try to connect with retry logic
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Connection attempt {attempt}/{max_retries}")
                if self.w3.is_connected():
                    logger.info(f"Relayer connected to Chain {chain_id} via {self.rpc_url}")
                    break
                else:
                    if attempt < max_retries:
                        logger.warning(f"Connection failed, retrying in {retry_delay}s")
                        import time
                        time.sleep(retry_delay)
                    else:
                        raise ConnectionError(f"Failed to connect to RPC after {max_retries} attempts: {self.rpc_url}")
            except Exception as e:
                logger.error(f"Connection attempt {attempt} error: {str(e)}")
                if attempt < max_retries:
                    import time
                    time.sleep(retry_delay)
                else:
                    raise ConnectionError(f"Failed to connect to RPC: {self.rpc_url}. Error: {str(e)}")

        # Ensure address is checksummed
        raw_address = network_config['contracts']['IntentWallet']
        self.intent_wallet_address = self.w3.to_checksum_address(raw_address)
        logger.info(f"IntentWallet Address: {self.intent_wallet_address}")

        # 3. Load Account
        private_key = settings.RELAYER_PRIVATE_KEY
        if not private_key:
            raise ValueError("RELAYER_PRIVATE_KEY is missing in settings")
        
        self.account = self.w3.eth.account.from_key(private_key)
        logger.info(f"Relayer Account: {self.account.address}")

        # 4. Load ABI
        self.contract = self._load_contract()
        
        # 5. Initialize NonceManager for this chain
        nonce_manager.initialize_nonce(chain_id, self.account.address, self.w3)
        logger.info(f"NonceManager initialized for chain {chain_id}")

    def _load_contract(self):
        """Loads the IntentWalletV2 contract instance."""
        # V2 ABI (Wave 3 upgrade with getPortfolio aggregator)
        abi_path = settings.BASE_DIR / 'ABI' / 'IntentWalletV2.json'
        
        # Fallback to V1 ABI if V2 not found
        if not abi_path.exists():
            logger.warning("IntentWalletV2.json not found, falling back to IntentWallet.json")
            abi_path = settings.BASE_DIR / 'ABI' / 'IntentWallet.json'
        
        if not abi_path.exists():
            raise FileNotFoundError(f"ABI not found at {abi_path}")
            
        with open(abi_path, 'r') as f:
            abi_data = json.load(f)
            # Handle if the JSON is an artifact (Truffle/Hardhat) or raw ABI list
            abi = abi_data['abi'] if 'abi' in abi_data else abi_data
            
        return self.w3.eth.contract(address=self.intent_wallet_address, abi=abi)

    def execute_batch(self, 
                      user_address: str,
                      targets: List[str], 
                      datas: List[bytes], 
                      values: List[int],
                      plan_id: bytes,
                      plan_hash: bytes,
                      nonce: int,
                      expiry: int,
                      signature: bytes,
                      fee_amount: int = 0,
                      fee_token: Optional[str] = None) -> str:
        """
        Builds, signs, and sends the executeBatch transaction with REAL signature data.
        
        Wave 3 Enhancement: Fee payment support
        - fee_amount: Amount of tokens to pay relayer (in wei)
        - fee_token: ERC20 token address for fee (None = native token)
        
        Returns the transaction hash.
        """
        acquired_nonce = None
        
        try:
            logger.info("Submitting transaction payload")
            logger.info(f"User: {user_address}")
            logger.info(f"Plan ID: {plan_id.hex()}")
            logger.info(f"Plan Hash: {plan_hash.hex()}")
            logger.info(f"Nonce: {nonce}, Expiry: {expiry}")
            logger.debug(f"Signature: {signature.hex()}")
            logger.debug(f"Targets: {targets}")
            if fee_amount > 0:
                logger.info(f"Fee Amount: {fee_amount} wei")
                logger.info(f"Fee Token: {fee_token or 'Native'}")
            
            # 1. Get Relayer Nonce using NonceManager
            acquired_nonce = nonce_manager.acquire_nonce(
                self.chain_id, 
                self.account.address, 
                self.w3
            )
            logger.info(f"Relayer nonce: {acquired_nonce}")
            
            # 2. Format Arguments
            checksum_targets = [self.w3.to_checksum_address(t) for t in targets]
            checksum_user = self.w3.to_checksum_address(user_address)
            logger.debug(f"Targets: {checksum_targets}")
            logger.debug(f"User: {checksum_user}")
            
            # CRITICAL FIX: Ensure plan_id and plan_hash are exactly 32 bytes for Solidity's bytes32 type
            # This ensures the contract hashes the EXACT same bytes that were signed
            if isinstance(plan_id, str):
                plan_id_bytes = bytes.fromhex(plan_id[2:] if plan_id.startswith('0x') else plan_id)
            else:
                plan_id_bytes = plan_id

            if isinstance(plan_hash, str):
                plan_hash_bytes = bytes.fromhex(plan_hash[2:] if plan_hash.startswith('0x') else plan_hash)
            else:
                plan_hash_bytes = plan_hash

            # Validate 32-byte length (critical for bytes32 in Solidity)
            if len(plan_id_bytes) != 32:
                raise ValueError(f"planId must be exactly 32 bytes, got {len(plan_id_bytes)} bytes")
            if len(plan_hash_bytes) != 32:
                raise ValueError(f"planHash must be exactly 32 bytes, got {len(plan_hash_bytes)} bytes")
            
            logger.debug(f"Plan ID (bytes32): {plan_id_bytes.hex()[:20]}...")
            logger.debug(f"Plan Hash (bytes32): {plan_hash_bytes.hex()[:20]}...")
            
            # Construct the Plan Struct Tuple: (planId, planHash, nonce, expiry)
            # Solidity expects: tuple(bytes32, bytes32, uint256, uint256)
            plan_struct = (plan_id_bytes, plan_hash_bytes, nonce, expiry)
            
            # Empty cidHash for now (not used in signature verification logic provided)
            cid_hash = b'\x00' * 32

            # 3. Build Contract Call
            logger.debug("Building contract function call")
            func_call = self.contract.functions.executeBatch(
                checksum_user,    # user
                plan_struct,      # plan (tuple)
                checksum_targets, # targets
                datas,            # calldatas (bytes[])
                cid_hash,         # cidHash
                signature         # signature
            )
            
            # 4. Build Transaction Dict
            logger.debug("Estimating gas")
            tx_build = func_call.build_transaction({
                'chainId': self.chain_id,
                'gas': 3000000,  # Conservative gas limit
                'gasPrice': self.w3.eth.gas_price,
                'nonce': acquired_nonce,  # Use NonceManager nonce!
            })
            
            logger.info("Transaction built successfully")
            logger.debug(f"Gas Price: {self.w3.eth.gas_price} wei")

            # 5. Sign & Broadcast
            logger.debug("Signing transaction")
            signed_tx = self.w3.eth.account.sign_transaction(tx_build, private_key=settings.RELAYER_PRIVATE_KEY)
            
            logger.info("Broadcasting transaction")
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = self.w3.to_hex(tx_hash)
            
            logger.info(f"Transaction broadcasted: {tx_hash_hex}")
            return tx_hash_hex

        except Exception as e:
            logger.error(f"Relayer error: {str(e)}")
            if hasattr(e, 'args'):
                logger.error(f"Error details: {e.args}")
            
            # Release nonce if we acquired one but TX failed before broadcast
            if acquired_nonce is not None:
                nonce_manager.release_nonce(self.chain_id, self.account.address, acquired_nonce)
                logger.info(f"Released nonce {acquired_nonce} due to failure")
            
            # Sync nonce with blockchain if it seems corrupted
            if "nonce" in str(e).lower():
                nonce_manager.sync_with_blockchain(self.chain_id, self.account.address, self.w3)
            
            raise e
    
    def get_relayer_balance(self) -> Dict[str, Any]:
        """Get relayer wallet balance and status for monitoring."""
        balance_wei = self.w3.eth.get_balance(self.account.address)
        balance_eth = self.w3.from_wei(balance_wei, 'ether')
        
        current_nonce = nonce_manager.get_current_nonce(self.chain_id, self.account.address)
        blockchain_nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
        
        return {
            "address": self.account.address,
            "chain_id": self.chain_id,
            "balance_wei": str(balance_wei),
            "balance": str(balance_eth),
            "currency": self.network_config.get('currency', 'ETH'),
            "tracked_nonce": current_nonce,
            "blockchain_nonce": blockchain_nonce,
            "nonce_synced": current_nonce == blockchain_nonce if current_nonce else None,
        }