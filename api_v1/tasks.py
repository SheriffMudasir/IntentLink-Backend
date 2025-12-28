# api_v1/tasks.py
import time
import logging
from celery import shared_task
from web3 import Web3
from eth_abi import encode
from .models import Execution, Plan
from services.relayer_service import RelayerService

logger = logging.getLogger(__name__)




def generate_stake_for_calldata(user_address: str, amount_wei: int) -> bytes:
    """
    Generates calldata for V3 staking: stakeFor(address onBehalfOf, uint256 amount)
    Selector: 0x2ee40908
    """
    function_selector = bytes.fromhex("2ee40908")
    checksum_address = Web3.to_checksum_address(user_address)
    encoded_params = encode(['address', 'uint256'], [checksum_address, int(amount_wei)])
    return function_selector + encoded_params

def generate_transfer_from_calldata(from_address: str, to_address: str, amount_wei: int) -> bytes:
    """
    Generates calldata for ERC20 transferFrom(address from, address to, uint256 amount)
    Selector: 0x23b872dd
    """
    function_selector = bytes.fromhex("23b872dd")
    checksum_from = Web3.to_checksum_address(from_address)
    checksum_to = Web3.to_checksum_address(to_address)
    encoded_params = encode(['address', 'address', 'uint256'], [checksum_from, checksum_to, int(amount_wei)])
    return function_selector + encoded_params


def generate_approve_calldata(spender_address: str, amount_wei: int) -> bytes:
    """
    Generates calldata for ERC20 approve(address spender, uint256 amount)
    Selector: 0x095ea7b3
    """
    function_selector = bytes.fromhex("095ea7b3")
    checksum_spender = Web3.to_checksum_address(spender_address)
    encoded_params = encode(['address', 'uint256'], [checksum_spender, int(amount_wei)])
    return function_selector + encoded_params

@shared_task
def execute_plan_task(execution_id):
    """
    Executes the plan on-chain using the RelayerService with real signature data.
    
    V3 Update: Now uses stakeFor(user, amount) instead of stake(amount)
    to properly attribute stakes to the user, not the relayer wallet.
    
    Fix: Iterates through plan steps (TransferFrom + Approve + Stake) to ensure
    IntentWallet has funds before approving/staking.
    """
    logger.info(f"[Task] Starting execution for ID: {execution_id}")
    
    try:
        execution = Execution.objects.get(id=execution_id)
        plan = execution.plan
        intent = plan.intent
        
        # Update status
        execution.status = Execution.Status.SUBMITTED
        execution.save()
        
        chain_id = intent.chain_id
        logger.info(f"[Task] Chain ID: {chain_id}")
        logger.info(f"[Task] User Wallet: {intent.user_wallet}")
        logger.info(f"[Task] Chosen Contract: {plan.chosen_contract_address}")
        logger.info(f"[Task] Plan JSON: {plan.plan_json}") 
        
        # Initialize Relayer
        relayer = RelayerService(chain_id=chain_id)
        
        # --- PREPARE DATA FOR RELAYER ---
        
        targets = []
        values = []
        datas = []
        
        # Parse steps from plan
        steps = plan.plan_json.get('steps', [])
        intent_wallet_address = plan.plan_json.get('intent_wallet') 
        if not intent_wallet_address:
             # Fallback to config if missing in plan
             intent_wallet_address = relayer.network_config['contracts']['IntentWallet']

        logger.info(f"[Task] Processing {len(steps)} steps...")
        
        for step in steps:
            step_type = step.get('type')
            amount_val = float(step.get('amount', 0))
            # Convert to wei (assuming 18 decimals for now, ideally fetch from config)
            amount_wei = int(amount_val * (10 ** 18))
            
            if step_type == 'approve':
                # Approve step: Target is the ASSET (e.g. MockUSDT)
                # Spender is the contract (e.g. MockStaking)
                
                # Lookup token address
                token_symbol = step.get('asset')
                network_config = relayer.network_config 
                token_address = None
                
                tokens_config = network_config.get('tokens', {})
                if token_symbol in tokens_config:
                     token_address = tokens_config[token_symbol]['address']
                elif f"Mock{token_symbol}" in network_config['contracts']:
                     token_address = network_config['contracts'][f"Mock{token_symbol}"]
                elif "MockUSDT" in network_config['contracts'] and (token_symbol == 'USDT' or token_symbol == 'MOCKUSDT'):
                     token_address = network_config['contracts']["MockUSDT"]
                
                if not token_address:
                    if Web3.is_address(token_symbol):
                        token_address = token_symbol
                    else:
                        logger.error(f"[Task] Could not resolve token address for {token_symbol}")
                        raise ValueError(f"Unknown token: {token_symbol}")

                spender = step.get('spender')
                
                # Inject TRANSFER_FROM (User -> IntentWallet)
                # We must pull funds before we can approve/spend them.
                logger.info(f"[Task] Injecting TRANSFER_FROM (User -> IntentWallet)")
                logger.info(f"[Task]    From: {intent.user_wallet}")
                logger.info(f"[Task]    To: {intent_wallet_address}")
                logger.info(f"[Task]    Amount: {amount_wei}")
                
                tf_calldata = generate_transfer_from_calldata(intent.user_wallet, intent_wallet_address, amount_wei)
                targets.append(token_address)
                values.append(0)
                datas.append(tf_calldata)

                # Now the Approve Step
                logger.info(f"[Task] Generating APPROVE for {token_symbol} ({token_address})")
                logger.info(f"[Task]    Spender: {spender}")
                logger.info(f"[Task]    Amount: {amount_wei}")
                
                calldata = generate_approve_calldata(spender, amount_wei)
                
                targets.append(token_address)
                values.append(0)
                datas.append(calldata)
                
            elif step_type in ['stake', 'staking', 'lend', 'supply']:
                # Stake step: Target is the CONTRACT
                contract_address = step.get('contract')
                
                logger.info(f"[Task] Generating {step_type.upper()} for {contract_address}")
                logger.info(f"[Task]    User: {intent.user_wallet}")
                logger.info(f"[Task]    Amount: {amount_wei}")
                
                # Use stakeFor for V3
                calldata = generate_stake_for_calldata(intent.user_wallet, amount_wei)
                
                targets.append(contract_address)
                values.append(0)
                datas.append(calldata)
        
        logger.info(f"[Task] Generated {len(targets)} commands for batch execution")
        for i, t in enumerate(targets):
            logger.info(f"[Task]    CMD {i+1}: Target={t} DataLen={len(datas[i])}")

        
        # 2. Plan Data (Must match what was signed)
        # Re-derive planId
        plan_id_bytes = Web3.keccak(text=str(plan.id))
        logger.info(f"[Task] Plan ID (bytes32): {plan_id_bytes.hex()}")
        
        # Re-derive planHash (Must match prepare-signature logic)
        data_to_hash = f"{plan.chosen_contract_address}{intent.intent_json.get('amount')}"
        plan_hash_bytes = Web3.keccak(text=data_to_hash)
        logger.info(f"[Task] Plan Hash (bytes32): {plan_hash_bytes.hex()}")
        logger.info(f"[Task] Hash Input: '{data_to_hash}'")
        
        # 3. Signature & Meta from Database
        nonce = int(execution.nonce)
        expiry = int(execution.expiry)
        signature_bytes = bytes.fromhex(execution.signature.replace('0x', ''))
        
        logger.info(f"[Task] Nonce: {nonce}")
        logger.info(f"[Task] Expiry: {expiry}")
        logger.info(f"[Task] Signature: {execution.signature[:66]}...")

        logger.info(f"[Task] Relaying transaction to Chain {chain_id}...")
        
        # 4. Execute with Real Signature Data
        tx_hash = relayer.execute_batch(
            user_address=intent.user_wallet,
            targets=targets,
            datas=datas,
            values=values,
            plan_id=plan_id_bytes,
            plan_hash=plan_hash_bytes,
            nonce=nonce,
            expiry=expiry,
            signature=signature_bytes
        )
        
        # 5. Wait for Receipt to confirm status (Fixes "False Success" bug)
        logger.info(f"[Task] ⏳ Transaction broadcasted: {tx_hash}")
        logger.info(f"[Task] ⏳ Waiting for receipt (timeout=60s)...")
        
        try:
            # wait_for_transaction_receipt returns the receipt (dict-like)
            receipt = relayer.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            # Check status: 1 = Success, 0 = Revert
            status = receipt.get('status')
            
            if status == 1:
                logger.info(f"[Task] Transaction mined successfully")
                execution.status = Execution.Status.CONFIRMED
                plan.status = Plan.Status.EXECUTED
            else:
                logger.error(f"[Task] Transaction reverted on-chain")
                execution.status = Execution.Status.FAILED
                # We can't easily get the revert reason without re-simulating, 
                # but the status=0 confirms it failed.
                
            # Log gas used
            gas_used = receipt.get('gasUsed')
            logger.info(f"[Task] Gas Used: {gas_used}")
            logger.info(f"[Task] TX Hash: {execution.tx_hash}")

        except Exception as e:
            logger.error(f"[Task] Error waiting for receipt (may be pending): {e}")
            # If timeout, we leave it as SUBMITTED (or we could mark PENDING_CONFIRMATION)
            # For now, let's assume if it times out it's just slow, not necessarily failed.
            # But strictly speaking, we haven't confirmed it yet.
            pass

        # Save updates
        execution.tx_hash = tx_hash
        execution.save() # Save status and tx_hash
        
        if execution.status == Execution.Status.CONFIRMED:
            plan.save() # Save plan status

        logger.info(f"[Task] Final Status: {execution.status}")
        
    except Execution.DoesNotExist:
        logger.error(f"[Task] Execution {execution_id} not found")
    except Exception as e:
        logger.error(f"[Task] Execution failed: {e}")
        if 'execution' in locals():
            execution.status = Execution.Status.FAILED
            execution.save()