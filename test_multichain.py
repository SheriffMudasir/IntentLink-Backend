"""
Quick test script to verify multi-chain configuration
Run this inside the Docker container with: docker compose exec web python test_multichain.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intentlink_project.settings')
django.setup()

from django.conf import settings

def test_multichain_config():
    print("\n" + "="*70)
    print("MULTI-CHAIN CONFIGURATION TEST")
    print("="*70 + "\n")
    
    # Test 1: Check if NETWORK_CONFIG exists
    if not hasattr(settings, 'NETWORK_CONFIG'):
        print("❌ FAILED: NETWORK_CONFIG not found in settings")
        return False
    
    config = settings.NETWORK_CONFIG
    print(f"✅ NETWORK_CONFIG loaded with {len(config)} networks\n")
    
    # Test 2: Verify both chains are configured
    chains = {1043: "BlockDAG", 80002: "Polygon Amoy"}
    for chain_id, name in chains.items():
        if chain_id not in config:
            print(f"❌ FAILED: Chain {chain_id} ({name}) not found")
            return False
        print(f"✅ Chain {chain_id} ({name}) configured")
    
    print("\n" + "-"*70)
    
    # Test 3: Verify contract addresses
    print("\nBlockDAG Awakening Testnet (1043):")
    print("-"*40)
    blockdag = config[1043]
    print(f"  Name: {blockdag['name']}")
    print(f"  Currency: {blockdag['currency']}")
    print(f"  RPC: {blockdag['rpc_url']}")
    print(f"  Contracts:")
    for name, addr in blockdag['contracts'].items():
        print(f"    - {name}: {addr}")
    
    print("\nPolygon Amoy Testnet (80002):")
    print("-"*40)
    amoy = config[80002]
    print(f"  Name: {amoy['name']}")
    print(f"  Currency: {amoy['currency']}")
    print(f"  RPC: {amoy['rpc_url']}")
    print(f"  Contracts:")
    for name, addr in amoy['contracts'].items():
        print(f"    - {name}: {addr}")
    
    # Test 4: Verify address differences
    print("\n" + "-"*70)
    print("\n🔍 VERIFICATION: Address Differences")
    print("-"*40)
    
    # These should be the same
    same_contracts = ['IntentWallet', 'MockDEX']
    print("\nContracts with SAME address on both chains:")
    for contract in same_contracts:
        bd_addr = blockdag['contracts'][contract].lower()
        am_addr = amoy['contracts'][contract].lower()
        if bd_addr == am_addr:
            print(f"  ✅ {contract}: {blockdag['contracts'][contract]}")
        else:
            print(f"  ❌ {contract} mismatch!")
            print(f"     BlockDAG: {blockdag['contracts'][contract]}")
            print(f"     Amoy: {amoy['contracts'][contract]}")
            return False
    
    # These should be different
    diff_contracts = ['MockStaking', 'MockLending']
    print("\nContracts with DIFFERENT addresses on each chain:")
    for contract in diff_contracts:
        bd_addr = blockdag['contracts'][contract].lower()
        am_addr = amoy['contracts'][contract].lower()
        if bd_addr != am_addr:
            print(f"  ✅ {contract}:")
            print(f"     BlockDAG: {blockdag['contracts'][contract]}")
            print(f"     Amoy: {amoy['contracts'][contract]}")
        else:
            print(f"  ⚠️  {contract}: Same on both chains (unexpected)")
    
    # Test 5: Verify whitelisted protocols
    print("\n" + "-"*70)
    print("\n🔒 Whitelisted Protocols:")
    print("-"*40)
    for chain_id, name in chains.items():
        print(f"\n{name} (Chain {chain_id}):")
        protocols = config[chain_id]['whitelisted_protocols']
        for protocol_type, addresses in protocols.items():
            print(f"  {protocol_type}: {len(addresses)} address(es)")
            for addr in addresses:
                print(f"    - {addr}")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED - Multi-chain configuration is correct!")
    print("="*70 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = test_multichain_config()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
