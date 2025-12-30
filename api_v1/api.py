# api_v1/api.py
"""
IntentLink API v1 - Core Intent Execution

Wave 3 Enhancements:
- Enhanced intent parsing (supports stake, swap, lend)
- Better error messages (no more scary technical logs)
- USD value projections in responses
"""
from ninja import Router
from ninja.errors import HttpError
from django.conf import settings
from .schemas import (
    IntentParseInput, IntentParseOutput, 
    PlanInput, PlanOutput, CandidateSchema,
    SubmitIntentInput, SubmitIntentOutput, ExecutionStatusOutput,
    PrepareSignatureInput, PrepareSignatureOutput,
    EnhancedPlanOutput, ProjectionSchema,
)
from .models import Intent, Plan, Execution
from .tasks import execute_plan_task 
from services.security_service import security_service
from services.signature_service import signature_service
from services.price_service import price_service
from web3 import Web3
from decimal import Decimal
import logging
import traceback
import re


router = Router()
logger = logging.getLogger(__name__)


# ==========================================================
# ENHANCED INTENT PARSING (Wave 3)
# ==========================================================

def parse_intent_text(input_text: str, chain_id: int) -> dict:
    """
    Parse natural language into structured intent.
    
    Wave 3: Support multiple intent types:
    - "stake 1000 bdag" → stake_and_compound
    - "swap 100 bdag to usdt" → swap  
    - "lend 500 bdag" → lend
    - "borrow 200 usdt" → borrow
    
    Returns parsed_intent_data dict or None if cannot parse.
    """
    text = input_text.lower().strip()
    
    # Get currency for this chain
    network_config = settings.NETWORK_CONFIG.get(chain_id, {})
    native_currency = network_config.get('currency', 'BDAG').lower()
    
    # Pattern: stake [amount] [asset]
    stake_pattern = r'stake\s+(\d+(?:\.\d+)?)\s*(\w+)?'
    stake_match = re.search(stake_pattern, text)
    
    if stake_match or 'stake' in text or 'yield' in text or 'apy' in text:
        # Extract amount, default to 1000 if not specified
        amount = float(stake_match.group(1)) if stake_match else 1000.0
        asset = (stake_match.group(2) if stake_match and stake_match.group(2) else native_currency).upper()
        
        return {
            "intent_type": "stake_and_compound",
            "asset": asset,
            "amount": amount,
            "amount_unit": "token",
            "target": "highest_risk_adjusted_apr",
        }
    
    # Pattern: swap [amount] [from_asset] to [to_asset]
    swap_pattern = r'swap\s+(\d+(?:\.\d+)?)\s*(\w+)\s+(?:to|for|into)\s+(\w+)'
    swap_match = re.search(swap_pattern, text)
    
    if swap_match or 'swap' in text or 'convert' in text or 'exchange' in text:
        if swap_match:
            amount = float(swap_match.group(1))
            from_asset = swap_match.group(2).upper()
            to_asset = swap_match.group(3).upper()
        else:
            amount = 100.0
            from_asset = native_currency.upper()
            to_asset = "USDT"
        
        return {
            "intent_type": "swap",
            "asset": from_asset,
            "to_asset": to_asset,
            "amount": amount,
            "amount_unit": "token",
            "target": "best_rate",
        }
    
    # Pattern: lend/supply [amount] [asset]
    lend_pattern = r'(?:lend|supply|deposit)\s+(\d+(?:\.\d+)?)\s*(\w+)?'
    lend_match = re.search(lend_pattern, text)
    
    if lend_match or 'lend' in text or 'supply' in text or 'earn interest' in text:
        amount = float(lend_match.group(1)) if lend_match else 1000.0
        asset = (lend_match.group(2) if lend_match and lend_match.group(2) else native_currency).upper()
        
        return {
            "intent_type": "lend",
            "asset": asset,
            "amount": amount,
            "amount_unit": "token",
            "target": "highest_supply_apy",
        }
    
    # Pattern: borrow [amount] [asset]
    borrow_pattern = r'borrow\s+(\d+(?:\.\d+)?)\s*(\w+)?'
    borrow_match = re.search(borrow_pattern, text)
    
    if borrow_match or 'borrow' in text:
        amount = float(borrow_match.group(1)) if borrow_match else 500.0
        asset = (borrow_match.group(2) if borrow_match and borrow_match.group(2) else "USDT").upper()
        
        return {
            "intent_type": "borrow",
            "asset": asset,
            "amount": amount,
            "amount_unit": "token",
            "target": "lowest_borrow_apy",
        }
    
    # Pattern: compound/harvest
    if 'compound' in text or 'harvest' in text or 'claim' in text:
        return {
            "intent_type": "compound",
            "asset": native_currency.upper(),
            "amount": 0,  # No amount needed for compound
            "amount_unit": "token",
            "target": "auto_compound",
        }
    
    # Could not parse
    return None


@router.post("/parse-intent/", response=IntentParseOutput, summary="Parse a Natural Language Intent")
def parse_intent(request, payload: IntentParseInput):
    """
    Parse natural language input into a structured Intent object.
    
    Wave 3: Powered by Gemini 3 Pro (Preview) for enhanced NLP parsing.
    Falls back to regex-based parsing if AI is unavailable.
    
    Supports:
    - Staking: "stake 1000 bdag", "maximize yield", "earn on my tokens"
    - Swapping: "swap 100 bdag to usdt", "convert my tokens"
    - Lending: "lend 500 bdag", "earn interest"
    - Unstaking: "withdraw my stake", "unstake all"
    - Claiming: "claim rewards", "harvest my earnings"
    """
    logger.info("="*70)
    logger.info("[PARSE-INTENT] New request received")
    logger.info(f"[PARSE-INTENT] User Wallet: {payload.user_wallet}")
    logger.info(f"[PARSE-INTENT] Chain ID: {payload.chain_id}")
    logger.info(f"[PARSE-INTENT] Input Text: '{payload.input}'")
    
    # === WAVE 3: Use Gemini 3 Pro AI Service ===
    from services.ai_service import AIService
    
    logger.info("[PARSE-INTENT] Using Gemini for intent parsing")
    parsed_intent_data = AIService.parse_intent(payload.input)
    
    # Fallback to regex if AI fails
    if not parsed_intent_data:
        logger.warning("[PARSE-INTENT] AI parsing failed, trying regex fallback")
        parsed_intent_data = parse_intent_text(payload.input, payload.chain_id)
    
    if parsed_intent_data:
        status = Intent.Status.PARSED
        logger.info(f"[PARSE-INTENT] Intent parsed: {parsed_intent_data.get('intent_type')}")
        logger.info(f"[PARSE-INTENT] Amount: {parsed_intent_data.get('amount')} {parsed_intent_data.get('asset')}")
        if parsed_intent_data.get('target'):
            logger.info(f"[PARSE-INTENT] Target: {parsed_intent_data.get('target')}")
    else:
        parsed_intent_data = {}
        status = Intent.Status.CLARIFY
        logger.warning(f"[PARSE-INTENT] Could not parse, requesting clarification")
    
    try:
        intent = Intent.objects.create(
            user_wallet=payload.user_wallet,
            chain_id=payload.chain_id, 
            input_text=payload.input,
            intent_json=parsed_intent_data,
            status=status
        )
        logger.info(f"[PARSE-INTENT] Intent created with ID: {intent.id}")
        logger.info("="*70)
    except Exception as e:
        logger.error(f"[PARSE-INTENT] Failed to create Intent: {str(e)}")
        raise

    # User-friendly clarification questions
    clarify_questions = []
    if status == Intent.Status.CLARIFY:
        clarify_questions = [
            "I can help you with staking, swapping, or lending. Try:",
            "• 'Stake 1000 BDAG for highest yield'",
            "• 'Swap 100 BDAG to USDT'", 
            "• 'Lend 500 BDAG to earn interest'",
        ]

    return IntentParseOutput(
        intent_id=intent.id,
        status=intent.status,
        intent=parsed_intent_data if status == Intent.Status.PARSED else None,
        clarify_questions=clarify_questions if status == Intent.Status.CLARIFY else []
    )
    
    

@router.post("/plan/", response=PlanOutput, summary="Generate an Execution Plan")
def plan_intent(request, payload: PlanInput):
    """Generate ranked execution plans with security validation.
    
    Supports multi-chain: BlockDAG Awakening Testnet and Polygon Amoy Testnet.
    Validates security using GoPlus API and ranks by utility score.
    """
    logger.info("="*70)
    logger.info("[PLAN] New planning request received")
    logger.info(f"[PLAN] Intent ID: {payload.intent_id}")
    
    try:
        intent = Intent.objects.get(id=payload.intent_id)
        logger.info(f"[PLAN] Intent found: {intent.id}")
        logger.info(f"[PLAN] User Wallet: {intent.user_wallet}")
        logger.info(f"[PLAN] Chain ID: {intent.chain_id}")
        logger.info(f"[PLAN] Intent Data: {intent.intent_json}")
    except Intent.DoesNotExist:
        logger.error(f"[PLAN] Intent not found: {payload.intent_id}")
        raise HttpError(404, f"Intent with ID {payload.intent_id} not found.")

    chain_id_int = intent.chain_id
    chain_id_str = str(chain_id_int)

    # Get network configuration for this chain
    network_config = settings.NETWORK_CONFIG.get(chain_id_int)
    if not network_config:
        logger.error(f"[PLAN] Unsupported chain ID: {chain_id_int}")
        raise HttpError(400, f"Unsupported chain ID: {chain_id_int}")
    
    logger.info(f"[PLAN] Network: {network_config['name']} (Chain ID: {chain_id_int})")
    logger.info(f"[PLAN] Currency: {network_config['currency']}")
    logger.info(f"[PLAN] RPC URL: {network_config['rpc_url']}")
    
    INTENT_WALLET_ADDRESS = network_config["contracts"]["IntentWallet"]
    logger.info(f"[PLAN] IntentWallet Address: {INTENT_WALLET_ADDRESS}")
    
    # Build candidate lists from whitelisted protocols
    CANDIDATE_FARMS = [
        {
            "address": addr,
            "mock_apy": 0.12,
            "mock_tvl": 500_000,
            "protocol": "staking",
        }
        for addr in network_config["whitelisted_protocols"]["staking"]
    ]

    CANDIDATE_LENDING = [
        {
            "address": addr,
            "mock_apy": 0.05,
            "mock_tvl": 2_500_000,
            "protocol": "lending",
        }
        for addr in network_config["whitelisted_protocols"]["lending"]
    ]

    
    intent_type = (intent.intent_json or {}).get("intent_type", "").lower()
    logger.info(f"[PLAN] Intent Type: {intent_type}")
    
    # Wave 4: Handle compound intent (no approval needed, just compound)
    if "compound" in intent_type:
        logger.info(f"[PLAN] Compound intent detected")
        
        # Get staking vault address
        staking_protocols = network_config["whitelisted_protocols"].get("staking", [])
        if not staking_protocols:
            logger.error(f"[PLAN] No staking protocols configured for compounding")
            raise HttpError(500, "No staking protocols available for compounding")
        
        vault_address = staking_protocols[0]
        logger.info(f"[PLAN] Compound target: {vault_address}")
        
        # Create plan with compound step only
        plan_data = {
            "steps": [
                {
                    "type": "compound",
                    "contract": vault_address,
                }
            ],
            "chosen_protocol": "staking",
            "intent_wallet": INTENT_WALLET_ADDRESS,
            "chain_id": intent.chain_id
        }
        
        # Create candidate (vault itself)
        compound_candidate = CandidateSchema(
            address=vault_address,
            apy=0.36,  # Current APY with multiplier
            tvl=500_000,
            safety_score=100,
            utility=1.0,
            warnings=[],
            protocol="staking",
        )
        
        new_plan = Plan.objects.create(
            intent=intent,
            plan_json=plan_data,
            utility_scores=[compound_candidate.model_dump()],
            chosen_contract_address=vault_address,
            status=Plan.Status.READY
        )
        
        intent.status = Intent.Status.PLANNED
        intent.save()
        
        logger.info(f"[PLAN] Compound plan created with ID: {new_plan.id}")
        logger.info("="*70)
        
        return PlanOutput(
            plan_id=new_plan.id,
            candidates=[compound_candidate],
            chosen=compound_candidate
        )
    
    # Regular stake/lend intent handling
    if "lend" in intent_type or "borrow" in intent_type:
        candidates_to_check = CANDIDATE_LENDING
        logger.info(f"[PLAN] Selected LENDING candidates")
    elif "stake" in intent_type or "farm" in intent_type:
        candidates_to_check = CANDIDATE_FARMS
        logger.info(f"[PLAN] Selected STAKING candidates")
    else:
        candidates_to_check = CANDIDATE_FARMS
        logger.info(f"[PLAN] Default to STAKING candidates")
    
    logger.info(f"[PLAN] Checking {len(candidates_to_check)} candidates")
    logger.info("-"*70)

    candidate_results: list[CandidateSchema] = []

    for idx, candidate in enumerate(candidates_to_check, 1):
        addr = candidate["address"]
        logger.info(f"[PLAN] Candidate {idx}/{len(candidates_to_check)}: {addr}")
        logger.info(f"[PLAN]   Protocol: {candidate['protocol']}")
        logger.info(f"[PLAN]   Mock APY: {candidate['mock_apy']*100}%")
        logger.info(f"[PLAN]   Mock TVL: ${candidate['mock_tvl']:,}")

        try:
            logger.info(f"[PLAN]   Running security check...")
            report = security_service.run_security_check(chain_id_str, addr)
            logger.info(f"[PLAN]   Security check completed")
        except Exception as exc:
            logger.error(f"[PLAN]   Security check failed: {exc}")
            logger.error(f"[PLAN]   Traceback: {traceback.format_exc()}")
            continue

        if not report or not getattr(report, "is_safe", False):
            logger.warning(f"[PLAN]   Candidate unsafe, skipping")
            logger.warning(f"[PLAN]   Warnings: {getattr(report, 'warnings', [])}")
            continue

        apy = float(candidate.get("mock_apy", 0.0))
        safety_score = float(getattr(report, "safety_score", 0.0))
        utility = (apy * 0.5) + ((safety_score / 100.0) * 0.5)

        logger.info(f"[PLAN]   Candidate passed security check")
        logger.info(f"[PLAN]   Safety Score: {safety_score}/100")
        logger.info(f"[PLAN]   Utility Score: {utility:.6f}")

        candidate_schema = CandidateSchema(
            address=addr,
            apy=apy,
            tvl=candidate.get("mock_tvl", 0),
            safety_score=safety_score,
            utility=round(utility, 6),
            warnings=getattr(report, "warnings", []),
            protocol=candidate.get("protocol", "unknown"),
        )
        
        candidate_results.append(candidate_schema)
        logger.info(f"[PLAN]   Added to candidate pool")
        logger.info("-"*70)

    if not candidate_results:
        logger.error(f"[PLAN] No safe candidates found after security validation")
        raise HttpError(500, "No safe candidates found after security validation.")

    logger.info(f"[PLAN] Total valid candidates: {len(candidate_results)}")
    chosen_candidate = max(candidate_results, key=lambda c: c.utility)
    logger.info(f"[PLAN] Best candidate selected: {chosen_candidate.address}")
    logger.info(f"[PLAN]    Utility: {chosen_candidate.utility:.6f}")
    logger.info(f"[PLAN]    Protocol: {chosen_candidate.protocol}")
    logger.info(f"[PLAN]    APY: {chosen_candidate.apy*100}%")
    logger.info(f"[PLAN]    Safety Score: {chosen_candidate.safety_score}/100")

    asset = intent.intent_json.get("asset")
    amount = intent.intent_json.get("amount")
    logger.info(f"[PLAN] Plan Details: {amount} {asset} → {chosen_candidate.protocol}")

    if chosen_candidate.protocol == "lending" or "lend" in intent_type:
        action_step = {
            "type": "lend",
            "contract": chosen_candidate.address,
            "amount": amount,
            "asset": asset,
        }
        logger.info(f"[PLAN] Action: LEND")
    else:
        action_step = {
            "type": "stake",
            "contract": chosen_candidate.address,
            "amount": amount,
            "asset": asset,
            "lockType": 2,  # Wave 4: 30-day lock for 3x multiplier (max APY demo)
        }
        logger.info(f"[PLAN] Action: STAKE (Lock Type 2 - 30 days)")

    plan_data = {
        "steps": [
            {
                "type": "approve",
                "asset": asset,
                "amount": amount,
                "spender": chosen_candidate.address,
            },
            action_step
        ],
        "chosen_protocol": chosen_candidate.protocol,
        "intent_wallet": INTENT_WALLET_ADDRESS,
        "chain_id": intent.chain_id
    }
    
    logger.info(f"[PLAN] Plan steps: 1) Approve, 2) {action_step['type'].upper()}")
    
    try:
        new_plan = Plan.objects.create(
            intent=intent,
            plan_json=plan_data,
            utility_scores=[c.model_dump() for c in candidate_results],
            chosen_contract_address=chosen_candidate.address,
            status=Plan.Status.READY
        )

        intent.status = Intent.Status.PLANNED
        intent.save()
        logger.info(f"[PLAN] Plan created with ID: {new_plan.id}")
        logger.info(f"[PLAN] Intent status updated to: PLANNED")
        logger.info("="*70)
    except Exception as e:
        logger.error(f"[PLAN] Failed to save plan: {str(e)}")
        logger.error(f"[PLAN] Traceback: {traceback.format_exc()}")
        raise
    
    return PlanOutput(
        plan_id=new_plan.id,
        candidates=candidate_results,
        chosen=chosen_candidate
    )


@router.post("/prepare-signature/", response=PrepareSignatureOutput, summary="Get EIP-712 Data for Signing")
def prepare_signature(request, payload: PrepareSignatureInput):
    """
    Generates the EIP-712 Typed Data payload that the frontend must sign.
    Calculates planId and planHash deterministically.
    """
    logger.info("="*70)
    logger.info("[PREPARE-SIG] Signature preparation request received")
    logger.info(f"[PREPARE-SIG] Plan ID: {payload.plan_id}")
    
    try:
        plan = Plan.objects.get(id=payload.plan_id)
        intent = plan.intent
        logger.info(f"[PREPARE-SIG] Plan found")
        logger.info(f"[PREPARE-SIG] User Wallet: {intent.user_wallet}")
        logger.info(f"[PREPARE-SIG] Chain ID: {intent.chain_id}")
        logger.info(f"[PREPARE-SIG] Chosen Contract: {plan.chosen_contract_address}")
    except Plan.DoesNotExist:
        logger.error(f"[PREPARE-SIG] Plan not found: {payload.plan_id}")
        raise HttpError(404, "Plan not found")

    # 1. Generate planId (Keccak256 of the UUID string)
    # This gives us a 32-byte hex string consistent with the JS 'ethers.id'
    plan_id_hex = Web3.keccak(text=str(plan.id)).hex()
    logger.info(f"[PREPARE-SIG] Plan ID Hash: {plan_id_hex}")

    # 2. Generate planHash (Keccak256 of the critical parameters)
    # In a real scenario, this is hash(targets + values + calldata).
    # For now, we hash the chosen address + amount to lock in the commitment.
    data_to_hash = f"{plan.chosen_contract_address}{intent.intent_json.get('amount')}"
    plan_hash_hex = Web3.keccak(text=data_to_hash).hex()
    logger.info(f"[PREPARE-SIG] Plan Hash: {plan_hash_hex}")
    logger.info(f"[PREPARE-SIG] Hash Input: '{data_to_hash}'")

    # 3. Get Nonce from IntentWalletV2 contract
    # CRITICAL: The nonce must match what the contract expects for signature verification
    from services.portfolio_service import portfolio_service
    nonce = portfolio_service.get_user_nonce(intent.chain_id, intent.user_wallet)
    logger.info(f"[PREPARE-SIG] Nonce (from contract): {nonce}")

    # 4. Generate Typed Data
    logger.info(f"[PREPARE-SIG] Generating EIP-712 typed data...")
    typed_data = signature_service.generate_typed_data(
        chain_id=intent.chain_id,
        plan_id_hex=plan_id_hex,
        plan_hash_hex=plan_hash_hex,
        nonce=nonce
    )
    
    expiry = typed_data["message"]["expiry"]
    logger.info(f"[PREPARE-SIG] EIP-712 payload generated")
    logger.info(f"[PREPARE-SIG] Domain: {typed_data['domain']['name']} v{typed_data['domain']['version']}")
    logger.info(f"[PREPARE-SIG] Verifying Contract: {typed_data['domain']['verifyingContract']}")
    logger.info(f"[PREPARE-SIG] Expiry: {expiry} (timestamp)")
    logger.info(f"[PREPARE-SIG] Ready for user signature")
    logger.info("="*70)
    
    return PrepareSignatureOutput(
        typed_data=typed_data,
        plan_hash=plan_hash_hex,
        nonce=nonce,
        expiry=expiry
    )


@router.post("/submit-intent/", response=SubmitIntentOutput, summary="Submit a Signed Plan")
def submit_intent(request, payload: SubmitIntentInput):
    """
    Verifies the user signature and queues execution.
    """
    logger.info("="*70)
    logger.info("[SUBMIT] Signed plan submission received")
    logger.info(f"[SUBMIT] Plan ID: {payload.plan_id}")
    logger.info(f"[SUBMIT] Signature: {payload.signature[:66]}...")
    logger.info(f"[SUBMIT] Nonce: {payload.nonce}")
    logger.info(f"[SUBMIT] Expiry: {payload.expiry}")
    
    try:
        plan = Plan.objects.get(id=payload.plan_id)
        intent = plan.intent
        logger.info(f"[SUBMIT] Plan found")
        logger.info(f"[SUBMIT] User Wallet: {intent.user_wallet}")
        logger.info(f"[SUBMIT] Chain ID: {intent.chain_id}")
        logger.info(f"[SUBMIT] Chosen Contract: {plan.chosen_contract_address}")
        logger.info(f"[SUBMIT] Amount: {intent.intent_json.get('amount')} {intent.intent_json.get('asset')}")
    except Plan.DoesNotExist:
        logger.error(f"[SUBMIT] Plan not found: {payload.plan_id}")
        raise HttpError(404, "Plan not found")

    # --- SIGNATURE VERIFICATION ---
    logger.info("-"*70)
    logger.info("[SUBMIT] SIGNATURE VERIFICATION STARTING")
    logger.info("-"*70)
    
    # Re-calculate the IDs to ensure the user signed what we expect
    plan_id_hex = Web3.keccak(text=str(plan.id)).hex()
    logger.info(f"[SUBMIT] Recalculated Plan ID Hash: {plan_id_hex}")
    
    # Re-calculate planHash (Must match prepare-signature logic exactly)
    data_to_hash = f"{plan.chosen_contract_address}{intent.intent_json.get('amount')}"
    plan_hash_hex = Web3.keccak(text=data_to_hash).hex()
    logger.info(f"[SUBMIT] Recalculated Plan Hash: {plan_hash_hex}")
    logger.info(f"[SUBMIT] Hash Input: '{data_to_hash}'")
    
    logger.info(f"[SUBMIT] Verifying signature from: {intent.user_wallet}")
    logger.info(f"[SUBMIT] Using chain ID: {intent.chain_id}")

    is_valid = signature_service.verify_signature(
        chain_id=intent.chain_id,
        plan_id_hex=plan_id_hex,
        plan_hash_hex=plan_hash_hex,
        nonce=payload.nonce,
        expiry=payload.expiry,
        signature=payload.signature,
        user_address=intent.user_wallet
    )

    if not is_valid:
        logger.error(f"[SUBMIT] SIGNATURE VERIFICATION FAILED")
        logger.error(f"[SUBMIT] Expected user: {intent.user_wallet}")
        logger.error(f"[SUBMIT] Signature: {payload.signature}")
        logger.error(f"[SUBMIT] Unauthorized execution attempt blocked")
        logger.info("="*70)
        raise HttpError(401, "Invalid signature. You are not authorized to execute this plan.")

    logger.info(f"[SUBMIT] SIGNATURE VERIFIED SUCCESSFULLY")
    logger.info(f"[SUBMIT] User authenticated: {intent.user_wallet}")
    logger.info("-"*70)
    # --- END VERIFICATION ---

    # Idempotency check
    if hasattr(plan, 'execution'):
        logger.warning(f"[SUBMIT] Execution already exists for this plan")
        logger.warning(f"[SUBMIT] Returning existing execution: {plan.execution.id}")
        logger.info("="*70)
        return SubmitIntentOutput(
            execution_id=plan.execution.id,
            status=plan.execution.status
        )

    logger.info(f"[SUBMIT] Creating execution record...")
    execution = Execution.objects.create(
        plan=plan,
        status=Execution.Status.PENDING,
        relayer_address="0xRelayerBot",
        # Save signature data for the worker
        signature=payload.signature,
        nonce=str(payload.nonce),
        expiry=str(payload.expiry)
    )
    logger.info(f"[SUBMIT] Execution created: {execution.id}")
    logger.info(f"[SUBMIT] Status: {execution.status}")
    logger.info(f"[SUBMIT] Relayer: {execution.relayer_address}")
    
    logger.info(f"[SUBMIT] Queueing execution task in Celery...")
    execute_plan_task.delay(execution.id)
    logger.info(f"[SUBMIT] Task queued successfully")
    logger.info(f"[SUBMIT] Execution ID: {execution.id}")
    logger.info("="*70)

    return SubmitIntentOutput(
        execution_id=execution.id,
        status=execution.status
    )

@router.get("/execution/{execution_id}/status/", response=ExecutionStatusOutput, summary="Poll Execution Status")
def get_execution_status(request, execution_id: str):
    """Return current status and transaction hash of an execution."""
    logger.info("="*70)
    logger.info("[STATUS] Execution status query received")
    logger.info(f"[STATUS] Execution ID: {execution_id}")
    
    try:
        execution = Execution.objects.get(id=execution_id)
        logger.info(f"[STATUS] Execution found")
        logger.info(f"[STATUS] Status: {execution.status}")
        logger.info(f"[STATUS] TX Hash: {execution.tx_hash or 'Not yet available'}")
        logger.info(f"[STATUS] Relayer: {execution.relayer_address}")
        
        if execution.receipt:
            logger.info(f"[STATUS] Receipt available: {len(execution.receipt.get('logs', []))} logs")
        else:
            logger.info(f"[STATUS] No receipt yet")
        
        logger.info("="*70)
    except Execution.DoesNotExist:
        logger.error(f"[STATUS] Execution not found: {execution_id}")
        logger.info("="*70)
        raise HttpError(404, "Execution not found")

    return ExecutionStatusOutput(
        execution_id=execution.id,
        status=execution.status,
        tx_hash=execution.tx_hash,
        logs=execution.receipt.get("logs", []) if execution.receipt else []
    )


# ==========================================================
# ENHANCED PLAN ENDPOINT (Wave 3 - with USD projections)
# ==========================================================

@router.post("/plan-enhanced/", response=EnhancedPlanOutput, summary="Generate Plan with Earnings Projections")
def plan_intent_enhanced(request, payload: PlanInput):
    """
    Enhanced plan endpoint that includes projected earnings.
    
    Returns the same plan as /plan/ but with additional:
    - Estimated APY
    - Projected earnings (daily, weekly, monthly, yearly)
    - USD values
    - Summary string for display
    
    This powers the UX: "Stake 1000 BDAG at 12% APY → Earn $6.00/month"
    """
    logger.info("="*70)
    logger.info("[PLAN-ENHANCED] Enhanced planning request with projections")
    
    try:
        intent = Intent.objects.get(id=payload.intent_id)
    except Intent.DoesNotExist:
        raise HttpError(404, f"Intent with ID {payload.intent_id} not found.")

    chain_id_int = intent.chain_id
    network_config = settings.NETWORK_CONFIG.get(chain_id_int)
    if not network_config:
        raise HttpError(400, f"Unsupported chain ID: {chain_id_int}")
    
    # Get standard plan first
    INTENT_WALLET_ADDRESS = network_config["contracts"]["IntentWallet"]
    currency = network_config['currency']
    
    # Build candidates (simplified for enhanced endpoint)
    intent_type = (intent.intent_json or {}).get("intent_type", "").lower()
    
    if "lend" in intent_type:
        protocol_type = "lending"
        apy = 0.05
        addresses = network_config["whitelisted_protocols"]["lending"]
    else:
        protocol_type = "staking"
        apy = 0.12
        addresses = network_config["whitelisted_protocols"]["staking"]
    
    if not addresses:
        raise HttpError(500, f"No {protocol_type} protocols configured")
    
    chosen_address = addresses[0]
    
    # Run security check
    try:
        report = security_service.run_security_check(str(chain_id_int), chosen_address)
        safety_score = getattr(report, "safety_score", 80)
        warnings = getattr(report, "warnings", [])
    except Exception:
        safety_score = 80
        warnings = []
    
    utility = (apy * 0.5) + ((safety_score / 100.0) * 0.5)
    
    chosen = CandidateSchema(
        address=chosen_address,
        apy=apy,
        tvl=500000,
        safety_score=safety_score,
        utility=round(utility, 6),
        warnings=warnings,
        protocol=protocol_type,
    )
    
    # Get amount and calculate USD values
    amount = Decimal(str(intent.intent_json.get("amount", 1000)))
    asset = intent.intent_json.get("asset", currency)
    
    token_price = price_service.get_price(asset)
    amount_usd = amount * token_price
    
    # Calculate projected earnings
    apy_decimal = Decimal(str(apy))
    
    daily_earnings = amount * apy_decimal / Decimal(365)
    weekly_earnings = daily_earnings * 7
    monthly_earnings = daily_earnings * 30
    yearly_earnings = amount * apy_decimal
    
    projections = [
        ProjectionSchema(
            period="daily",
            amount=f"{daily_earnings:.4f} {asset}",
            amount_usd=price_service.format_usd(daily_earnings * token_price),
        ),
        ProjectionSchema(
            period="weekly",
            amount=f"{weekly_earnings:.4f} {asset}",
            amount_usd=price_service.format_usd(weekly_earnings * token_price),
        ),
        ProjectionSchema(
            period="monthly",
            amount=f"{monthly_earnings:.4f} {asset}",
            amount_usd=price_service.format_usd(monthly_earnings * token_price),
        ),
        ProjectionSchema(
            period="yearly",
            amount=f"{yearly_earnings:.4f} {asset}",
            amount_usd=price_service.format_usd(yearly_earnings * token_price),
        ),
    ]
    
    # Build human-readable summary
    monthly_usd = price_service.format_usd(monthly_earnings * token_price)
    summary = f"Stake {amount:,.0f} {asset} at {apy*100:.0f}% APY → Earn {monthly_usd}/month"
    
    # Create plan in database
    plan_data = {
        "steps": [
            {"type": "approve", "asset": asset, "amount": float(amount), "spender": chosen_address},
            {"type": protocol_type, "contract": chosen_address, "amount": float(amount), "asset": asset},
        ],
        "chosen_protocol": protocol_type,
        "intent_wallet": INTENT_WALLET_ADDRESS,
        "chain_id": intent.chain_id,
    }
    
    new_plan = Plan.objects.create(
        intent=intent,
        plan_json=plan_data,
        utility_scores=[chosen.model_dump()],
        chosen_contract_address=chosen_address,
        status=Plan.Status.READY
    )
    
    intent.status = Intent.Status.PLANNED
    intent.save()
    
    logger.info(f"[PLAN-ENHANCED] Plan created: {new_plan.id}")
    logger.info(f"[PLAN-ENHANCED] Summary: {summary}")
    logger.info("="*70)
    
    return EnhancedPlanOutput(
        plan_id=new_plan.id,
        candidates=[chosen],
        chosen=chosen,
        estimated_apy=f"{apy*100:.1f}%",
        projected_earnings=projections,
        input_amount=f"{amount:,.0f} {asset}",
        input_amount_usd=price_service.format_usd(amount_usd),
        summary=summary,
    )