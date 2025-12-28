# services/nonce_manager.py
"""
Nonce Manager Service - Solves Scalability Issues

This service manages relayer transaction nonces using Redis for atomic operations.
Without this, concurrent user requests cause nonce collisions and failed transactions.

Key Features:
- Atomic nonce acquisition using Redis INCR
- Nonce recovery on failed transactions
- Multi-chain support (each chain has its own nonce sequence)
- Fallback to blockchain if Redis is unavailable
"""

import logging
import redis
from typing import Optional
from django.conf import settings
from web3 import Web3

logger = logging.getLogger(__name__)


class NonceManager:
    """
    Thread-safe nonce management for high-frequency transaction submission.
    
    Problem Solved:
    - Single relayer wallet serving multiple users
    - Concurrent execute requests cause nonce collision
    - web3.eth.get_transaction_count doesn't account for pending TXs
    
    Solution:
    - Track nonces in Redis with atomic INCR
    - Each chain_id has its own counter
    - Recover nonces on TX failures
    """
    
    NONCE_KEY_PREFIX = "intentlink:relayer:nonce:"
    LOCK_KEY_PREFIX = "intentlink:relayer:lock:"
    LOCK_TIMEOUT = 30  # seconds
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            redis_url = settings.CELERY_BROKER_URL
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("NonceManager: Redis connection established")
            else:
                logger.warning("NonceManager: REDIS_URL not configured, using fallback mode")
        except Exception as e:
            logger.error(f"NonceManager: Redis connection failed: {e}")
            self.redis_client = None
    
    def _get_nonce_key(self, chain_id: int, relayer_address: str) -> str:
        """Generate unique key for chain + relayer combination."""
        return f"{self.NONCE_KEY_PREFIX}{chain_id}:{relayer_address.lower()}"
    
    def _get_lock_key(self, chain_id: int, relayer_address: str) -> str:
        """Generate lock key for distributed locking."""
        return f"{self.LOCK_KEY_PREFIX}{chain_id}:{relayer_address.lower()}"
    
    def initialize_nonce(self, chain_id: int, relayer_address: str, w3: Web3) -> int:
        """
        Initialize nonce from blockchain if not yet tracked.
        Called once when relayer service starts for a chain.
        """
        key = self._get_nonce_key(chain_id, relayer_address)
        
        if self.redis_client:
            try:
                # Check if already initialized
                current = self.redis_client.get(key)
                if current is not None:
                    logger.info(f"NonceManager: Using cached nonce {current} for chain {chain_id}")
                    return int(current)
                
                # Fetch from blockchain
                blockchain_nonce = w3.eth.get_transaction_count(relayer_address, 'pending')
                
                # Set in Redis (only if not already set by another process)
                self.redis_client.setnx(key, blockchain_nonce)
                
                logger.info(f"NonceManager: Initialized nonce to {blockchain_nonce} for chain {chain_id}")
                return blockchain_nonce
                
            except Exception as e:
                logger.error(f"NonceManager: Initialize failed: {e}")
                return w3.eth.get_transaction_count(relayer_address, 'pending')
        else:
            return w3.eth.get_transaction_count(relayer_address, 'pending')
    
    def acquire_nonce(self, chain_id: int, relayer_address: str, w3: Web3) -> int:
        """
        Atomically acquire the next nonce for a transaction.
        
        Returns the nonce to use, and increments the counter.
        Thread-safe due to Redis INCR atomic operation.
        """
        key = self._get_nonce_key(chain_id, relayer_address)
        
        if self.redis_client:
            try:
                # Ensure initialized
                if self.redis_client.get(key) is None:
                    self.initialize_nonce(chain_id, relayer_address, w3)
                
                # Atomically get current and increment
                # INCR returns the value AFTER incrementing, so we subtract 1
                # Actually, we want: get current, then increment for next caller
                # Use a Lua script for true atomic get-and-increment
                
                lua_script = """
                local current = redis.call('GET', KEYS[1])
                if current == false then
                    return -1
                end
                redis.call('INCR', KEYS[1])
                return tonumber(current)
                """
                
                nonce = self.redis_client.eval(lua_script, 1, key)
                
                if nonce == -1:
                    # Not initialized, fallback
                    nonce = w3.eth.get_transaction_count(relayer_address, 'pending')
                    self.redis_client.set(key, nonce + 1)
                
                logger.info(f"NonceManager: Acquired nonce {nonce} for chain {chain_id}")
                return int(nonce)
                
            except Exception as e:
                logger.error(f"NonceManager: Acquire failed, using blockchain: {e}")
                return w3.eth.get_transaction_count(relayer_address, 'pending')
        else:
            # Fallback: direct blockchain query (not safe for concurrent requests)
            logger.warning("NonceManager: Using unsafe blockchain nonce query")
            return w3.eth.get_transaction_count(relayer_address, 'pending')
    
    def release_nonce(self, chain_id: int, relayer_address: str, nonce: int):
        """
        Release a nonce back if transaction failed before broadcast.
        
        This prevents nonce gaps when transactions fail during building/signing.
        Only call this if the TX was never sent to the network.
        """
        key = self._get_nonce_key(chain_id, relayer_address)
        
        if self.redis_client:
            try:
                # Only decrement if current value is nonce + 1
                # (meaning we're the one who incremented it)
                lua_script = """
                local current = tonumber(redis.call('GET', KEYS[1]))
                local target = tonumber(ARGV[1])
                if current == target + 1 then
                    redis.call('DECR', KEYS[1])
                    return 1
                end
                return 0
                """
                
                result = self.redis_client.eval(lua_script, 1, key, nonce)
                
                if result == 1:
                    logger.info(f"NonceManager: Released nonce {nonce} for chain {chain_id}")
                else:
                    logger.warning(f"NonceManager: Could not release nonce {nonce} (already used)")
                    
            except Exception as e:
                logger.error(f"NonceManager: Release failed: {e}")
    
    def sync_with_blockchain(self, chain_id: int, relayer_address: str, w3: Web3):
        """
        Re-sync nonce with blockchain state.
        
        Call this after detecting nonce-related errors or periodically
        to recover from any drift.
        """
        key = self._get_nonce_key(chain_id, relayer_address)
        
        if self.redis_client:
            try:
                blockchain_nonce = w3.eth.get_transaction_count(relayer_address, 'pending')
                self.redis_client.set(key, blockchain_nonce)
                logger.info(f"NonceManager: Synced nonce to {blockchain_nonce} for chain {chain_id}")
                return blockchain_nonce
            except Exception as e:
                logger.error(f"NonceManager: Sync failed: {e}")
                return None
        return None
    
    def get_current_nonce(self, chain_id: int, relayer_address: str) -> Optional[int]:
        """Get current nonce value without incrementing (for debugging)."""
        key = self._get_nonce_key(chain_id, relayer_address)
        
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                return int(value) if value else None
            except Exception as e:
                logger.error(f"NonceManager: Get failed: {e}")
                return None
        return None


# Singleton instance
nonce_manager = NonceManager()
