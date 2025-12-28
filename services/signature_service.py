# services/signature_service.py
import logging
import time
from typing import Dict, Any
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3
from django.conf import settings

logger = logging.getLogger(__name__)

class SignatureService:
    def __init__(self):
        # IntentWalletV2 - Updated for Wave 3
        self.contract_address = "0xe3dad1813a5c75fba505780a386a81fd3b8777e4"
        # Legacy V1 address for reference: 0x718a09981d305c2293d0c85e9d957ad25cb2a1c7
    
    def _get_domain_data(self, chain_id: int) -> Dict[str, Any]:
        """Returns the EIP-712 Domain Separator."""
        return {
            "name": "IntentLink",
            "version": "1",
            "chainId": chain_id,
            "verifyingContract": self.contract_address
        }

    def _get_message_types(self) -> Dict[str, Any]:
        """Returns the EIP-712 Type Definition."""
        return {
            "Plan": [
                {"name": "planId", "type": "bytes32"},
                {"name": "planHash", "type": "bytes32"},
                {"name": "nonce", "type": "uint256"},
                {"name": "expiry", "type": "uint256"}
            ]
        }

    def generate_typed_data(self, chain_id: int, plan_id_hex: str, plan_hash_hex: str, nonce: int = 0) -> Dict[str, Any]:
        """
        Generates the payload the Frontend needs to sign.
        """
        logger.info("-"*70)
        logger.info("[SIG-GEN] Generating EIP-712 typed data")
        logger.info(f"[SIG-GEN] Chain ID: {chain_id}")
        logger.info(f"[SIG-GEN] Plan ID Hash: {plan_id_hex}")
        logger.info(f"[SIG-GEN] Plan Hash: {plan_hash_hex}")
        logger.info(f"[SIG-GEN] Nonce: {nonce}")
        
        # Validate that planId and planHash are exactly 32 bytes (66 chars with 0x prefix)
        if not plan_id_hex.startswith('0x') or len(plan_id_hex) != 66:
            raise ValueError(f"planId must be a 32-byte hex string (66 chars), got: {plan_id_hex} (length: {len(plan_id_hex)})")
        if not plan_hash_hex.startswith('0x') or len(plan_hash_hex) != 66:
            raise ValueError(f"planHash must be a 32-byte hex string (66 chars), got: {plan_hash_hex} (length: {len(plan_hash_hex)})")
        
        # Set expiry to 1 hour from now
        expiry = int(time.time()) + 3600
        logger.info(f"[SIG-GEN] Expiry set to: {expiry} (1 hour from now)")
        
        message = {
            "planId": plan_id_hex,     # Keep as hex string - ethers.js will handle bytes32 conversion
            "planHash": plan_hash_hex, # Keep as hex string - ethers.js will handle bytes32 conversion
            "nonce": nonce,
            "expiry": expiry
        }

        domain_data = self._get_domain_data(chain_id)
        logger.info(f"[SIG-GEN] Domain: {domain_data['name']} v{domain_data['version']}")
        logger.info(f"[SIG-GEN] Verifying Contract: {domain_data['verifyingContract']}")

        # Construct the standard EIP-712 dictionary
        typed_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"}
                ],
                **self._get_message_types()
            },
            "primaryType": "Plan",
            "domain": domain_data,
            "message": message
        }
        
        logger.info(f"[SIG] Typed data generated successfully")
        logger.info("-"*70)
        return typed_data

    def verify_signature(self, chain_id: int, plan_id_hex: str, plan_hash_hex: str, nonce: int, expiry: int, signature: str, user_address: str) -> bool:
        """
        Recovers the signer address from the signature and compares it to user_address.
        """
        logger.info("-"*70)
        logger.info("[SIG-VERIFY] Starting signature verification")
        logger.info(f"[SIG-VERIFY] Chain ID: {chain_id}")
        logger.info(f"[SIG-VERIFY] Plan ID Hash: {plan_id_hex}")
        logger.info(f"[SIG-VERIFY] Plan Hash: {plan_hash_hex}")
        logger.info(f"[SIG-VERIFY] Nonce: {nonce}")
        logger.info(f"[SIG-VERIFY] Expiry: {expiry}")
        logger.info(f"[SIG-VERIFY] Expected User: {user_address}")
        logger.info(f"[SIG-VERIFY] Signature: {signature[:66]}...")
        
        try:
            domain_data = self._get_domain_data(chain_id)
            logger.info(f"[SIG-VERIFY] Domain: {domain_data['name']} v{domain_data['version']}")
            logger.info(f"[SIG-VERIFY] Verifying Contract: {domain_data['verifyingContract']}")
            
            message_types = self._get_message_types()
            
            # CRITICAL FIX: Use hex strings to match frontend signing format
            # The frontend signs over hex strings, not raw bytes
            # encode_typed_data will handle the conversion to bytes32 internally
            message_data = {
                "planId": plan_id_hex,     # Keep as hex string to match frontend
                "planHash": plan_hash_hex, # Keep as hex string to match frontend
                "nonce": int(nonce),
                "expiry": int(expiry)
            }
            
            logger.info(f"[SIG-VERIFY] Encoding EIP-712 message...")
            logger.info(f"[SIG-VERIFY] Message data: planId={plan_id_hex[:18]}..., planHash={plan_hash_hex[:18]}...")
            # Encode the data exactly as the wallet did
            signable_message = encode_typed_data(domain_data, message_types, message_data)
            
            logger.info(f"[SIG-VERIFY] Recovering signer address from signature...")
            # Recover the address
            recovered_address = Account.recover_message(signable_message, signature=signature)
            
            logger.info(f"[SIG-VERIFY] Recovered Address: {recovered_address}")
            logger.info(f"[SIG-VERIFY] Expected Address: {user_address}")
            
            is_match = recovered_address.lower() == user_address.lower()
            
            if is_match:
                logger.info(f"[SIG] Signature valid - addresses match")
            else:
                logger.error(f"[SIG] Signature invalid - address mismatch")
                logger.error(f"[SIG] Recovered: {recovered_address}")
                logger.error(f"[SIG] Expected: {user_address}"))
            
            logger.info("-"*70)
            return is_match

        except Exception as e:
            logger.error(f"[SIG] Signature verification exception: {e}")
            logger.error(f"[SIG] Exception type: {type(e).__name__}"))
            import traceback
            logger.error(f"[SIG-VERIFY] Traceback: {traceback.format_exc()}")
            logger.info("-"*70)
            return False

# Singleton
signature_service = SignatureService()