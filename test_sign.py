# intentlink-backend\test_sign.py
import time
from eth_account import Account
from eth_account.messages import encode_typed_data
from hexbytes import HexBytes

# 1. SETUP
# Matches the wallet we used in Step 1
PRIVATE_KEY = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
CONTRACT_ADDRESS = "0x718a09981d305c2293d0c85e9d957ad25cb2a1c7" # IntentWallet
CHAIN_ID = 1043

# 2. INPUTS (COPY FROM STEP 2 & 3 RESPONSES)
PLAN_ID_HEX = "0xb50fbbdc0386207106edfcc69658076430df4b972a0e89d7dacce9c2a166078e" 

PLAN_HASH_HEX = "0x556249e498c2d568d6de60693a3849e4e68ed5234e975b4c3c1694d5f6ead961" # Copy 'planHash' from Step 3 response
NONCE = 0                # Copy 'nonce' from Step 3 response
EXPIRY = 1764351464      # Copy 'expiry' from Step 3 response

def sign():
    domain_data = {
        "name": "IntentLink",
        "version": "1",
        "chainId": CHAIN_ID,
        "verifyingContract": CONTRACT_ADDRESS
    }

    message_types = {
        "Plan": [
            {"name": "planId", "type": "bytes32"},
            {"name": "planHash", "type": "bytes32"},
            {"name": "nonce", "type": "uint256"},
            {"name": "expiry", "type": "uint256"}
        ]
    }

    message_data = {
        "planId": HexBytes(PLAN_ID_HEX),
        "planHash": HexBytes(PLAN_HASH_HEX),
        "nonce": int(NONCE),
        "expiry": int(EXPIRY)
    }

    signable_message = encode_typed_data(domain_data, message_types, message_data)
    signed_message = Account.sign_message(signable_message, PRIVATE_KEY)
    
    print("\n--- COPY THIS TO SWAGGER ---")
    print(f"Signature: {signed_message.signature.hex()}")

if __name__ == "__main__":
    sign()