# test_bytes32_encoding.py
"""
Quick test to verify how eth_account handles bytes32 fields
"""
from eth_account import Account
from eth_account.messages import encode_typed_data

# Test 1: Using hex strings (my current fix)
print("="*70)
print("TEST 1: Using HEX STRINGS for bytes32 fields")
print("="*70)

domain = {
    "name": "IntentLink",
    "version": "1",
    "chainId": 1043,
    "verifyingContract": "0x718a09981d305c2293d0c85e9d957ad25cb2a1c7"
}

message_types = {
    "Plan": [
        {"name": "planId", "type": "bytes32"},
        {"name": "planHash", "type": "bytes32"},
        {"name": "nonce", "type": "uint256"},
        {"name": "expiry", "type": "uint256"}
    ]
}

# Using HEX STRINGS
message_hex = {
    "planId": "0xb26a67a8cefecd835304be8c22df4bdb2d940c523a04421eb7a7075363cf09c6",
    "planHash": "0x556249e498c2d568d6de60693a3849e4e68ed5234e975b4c3c1694d5f6ead961",
    "nonce": 0,
    "expiry": 1764693969
}

try:
    signable_hex = encode_typed_data(domain, message_types, message_hex)
    print(f"[OK] HEX STRING encoding SUCCESS")
    print(f"   Hash: {signable_hex.body.hex()[:66]}...")
except Exception as e:
    print(f"[ERROR] HEX STRING encoding FAILED: {e}")

print()

# Test 2: Using raw bytes (original code)
print("="*70)
print("TEST 2: Using RAW BYTES for bytes32 fields")
print("="*70)

message_bytes = {
    "planId": bytes.fromhex("b26a67a8cefecd835304be8c22df4bdb2d940c523a04421eb7a7075363cf09c6"),
    "planHash": bytes.fromhex("556249e498c2d568d6de60693a3849e4e68ed5234e975b4c3c1694d5f6ead961"),
    "nonce": 0,
    "expiry": 1764693969
}

try:
    signable_bytes = encode_typed_data(domain, message_types, message_bytes)
    print(f"[OK] RAW BYTES encoding SUCCESS")
    print(f"   Hash: {signable_bytes.body.hex()[:66]}...")
except Exception as e:
    print(f"[ERROR] RAW BYTES encoding FAILED: {e}")

print()
print("="*70)
print("COMPARISON")
print("="*70)
if 'signable_hex' in locals() and 'signable_bytes' in locals():
    if signable_hex.body == signable_bytes.body:
        print("[OK] Both methods produce IDENTICAL hashes!")
    else:
        print("[ERROR] Methods produce DIFFERENT hashes!")
        print(f"   HEX:   {signable_hex.body.hex()}")
        print(f"   BYTES: {signable_bytes.body.hex()}")
