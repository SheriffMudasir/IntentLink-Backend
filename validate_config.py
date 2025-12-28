#!/usr/bin/env python
"""
Multi-Chain Configuration Validation Script
Tests that NETWORK_CONFIG is properly set up for both chains.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intentlink_project.settings')
django.setup()

from django.conf import settings


def validate_network_config():
    """Validate multi-chain configuration."""
    print("=" * 70)
    print("MULTI-CHAIN CONFIGURATION VALIDATION")
    print("=" * 70)
    
    # Check if NETWORK_CONFIG exists
    if not hasattr(settings, 'NETWORK_CONFIG'):
        print("❌ NETWORK_CONFIG not found in settings!")
        return False
    
    network_config = settings.NETWORK_CONFIG
    print(f"✅ NETWORK_CONFIG loaded with {len(network_config)} networks\n")
    
    # Expected chains
    expected_chains = {
        1043: "BlockDAG Awakening Testnet",
        80002: "Polygon Amoy Testnet"
    }
    
    all_valid = True
    
    for chain_id, expected_name in expected_chains.items():
        print(f"\n{'─' * 70}")
        print(f"🔍 Validating Chain ID: {chain_id}")
        print(f"{'─' * 70}")
        
        if chain_id not in network_config:
            print(f"❌ Chain {chain_id} not found in NETWORK_CONFIG!")
            all_valid = False
            continue
        
        chain = network_config[chain_id]
        
        # Validate basic properties
        print(f"   Name: {chain.get('name', 'MISSING')}")
        print(f"   Currency: {chain.get('currency', 'MISSING')}")
        print(f"   RPC URL: {chain.get('rpc_url', 'MISSING')}")
        
        # Validate contracts
        required_contracts = ['IntentWallet', 'MockDEX', 'MockStaking', 'MockLending']
        contracts = chain.get('contracts', {})
        
        print(f"\n   📋 Contracts:")
        for contract_name in required_contracts:
            if contract_name in contracts:
                address = contracts[contract_name]
                print(f"      ✅ {contract_name}: {address}")
            else:
                print(f"      ❌ {contract_name}: MISSING")
                all_valid = False
        
        # Validate whitelisted protocols
        protocols = chain.get('whitelisted_protocols', {})
        print(f"\n   🔒 Whitelisted Protocols:")
        for protocol_type in ['dex', 'staking', 'lending']:
            if protocol_type in protocols:
                addresses = protocols[protocol_type]
                print(f"      ✅ {protocol_type}: {len(addresses)} address(es)")
                for addr in addresses:
                    print(f"         - {addr}")
            else:
                print(f"      ❌ {protocol_type}: MISSING")
                all_valid = False
    
    # Test unique differences
    print(f"\n{'=' * 70}")
    print("🔄 CROSS-CHAIN COMPARISON")
    print(f"{'=' * 70}")
    
    if 1043 in network_config and 80002 in network_config:
        blockdag = network_config[1043]['contracts']
        amoy = network_config[80002]['contracts']
        
        print("\n📍 Identical Addresses (Should Match):")
        for contract in ['IntentWallet', 'MockDEX']:
            if blockdag.get(contract, '').lower() == amoy.get(contract, '').lower():
                print(f"   ✅ {contract}: {blockdag[contract]}")
            else:
                print(f"   ❌ {contract}: MISMATCH!")
                print(f"      BlockDAG: {blockdag.get(contract, 'MISSING')}")
                print(f"      Amoy: {amoy.get(contract, 'MISSING')}")
                all_valid = False
        
        print("\n📍 Different Addresses (Should Differ):")
        for contract in ['MockStaking', 'MockLending']:
            if blockdag.get(contract, '').lower() != amoy.get(contract, '').lower():
                print(f"   ✅ {contract}:")
                print(f"      BlockDAG: {blockdag[contract]}")
                print(f"      Amoy: {amoy[contract]}")
            else:
                print(f"   ⚠️ {contract}: Same on both chains (unexpected!)")
    
    print(f"\n{'=' * 70}")
    if all_valid:
        print("✅ ALL VALIDATIONS PASSED")
    else:
        print("❌ SOME VALIDATIONS FAILED")
    print(f"{'=' * 70}\n")
    
    return all_valid


if __name__ == "__main__":
    try:
        success = validate_network_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
