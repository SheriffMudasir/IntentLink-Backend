# api_v1/api.py
from ninja import Router
from ninja.errors import HttpError
from .schemas import IntentParseInput, IntentParseOutput, PlanInput, PlanOutput, CandidateSchema
from .models import Intent, Plan
from services.security_service import security_service
import logging
import traceback


router = Router()
logger = logging.getLogger(__name__)

# Configure logging format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

@router.post("/parse-intent/", response=IntentParseOutput, summary="Parse a Natural Language Intent")
def parse_intent(request, payload: IntentParseInput):
    """
    Parses a natural language input into a structured Intent object.

    **Phase 1 Implementation:** This is a stubbed endpoint.
    It does not call an LLM. It returns a hardcoded, deterministic response
    for a specific known input. This allows frontend development to proceed.
    """
    logger.info("=" * 80)
    logger.info("PARSE INTENT ENDPOINT CALLED")
    logger.info(f"Request payload: {payload.model_dump()}")
    logger.info(f"User wallet: {payload.user_wallet}")
    logger.info(f"Chain ID: {payload.chain_id}")
    logger.info(f"Input text: {payload.input}")
    
    # --- LLM Stub Logic ---
    # In the future, this section will be replaced with a real LLM call.
    # We simulate a successful parse for a known phrase.
    if "stake 1000 bdag" in payload.input.lower():
        parsed_intent_data = {
            "intent_type": "stake_and_compound",
            "asset": "BDAG",
            "amount": 1000.0,
            "amount_unit": "token",
            "target": "highest_risk_adjusted_apr",
        }
        status = Intent.Status.PARSED
    else:
        # Simulate a case where the intent is not understood
        parsed_intent_data = {}
        status = Intent.Status.CLARIFY

    # Create the Intent object in the database
    logger.info(f"Creating Intent object with status: {status}")
    logger.debug(f"Parsed intent data: {parsed_intent_data}")
    
    try:
        intent = Intent.objects.create(
            user_wallet=payload.user_wallet,
            chain_id=payload.chain_id, 
            input_text=payload.input,
            intent_json=parsed_intent_data,
            status=status
        )
        logger.info(f"Intent created successfully with ID: {intent.id}")
    except Exception as e:
        logger.error(f"Failed to create Intent: {str(e)}")
        logger.error(traceback.format_exc())
        raise

    # Prepare the response
    logger.info("Preparing response...")
    return IntentParseOutput(
        intent_id=intent.id,
        status=intent.status,
        intent=parsed_intent_data if status == Intent.Status.PARSED else None,
        clarify_questions=["Sorry, I can only understand staking intents right now."] if status == Intent.Status.CLARIFY else []
    )
    
    

@router.post("/plan/", response=PlanOutput, summary="Generate an Execution Plan")
def plan_intent(request, payload: PlanInput):
    """
    Takes an intent_id and generates a ranked list of candidate execution plans
    using GoPlus for security validation.

    Phase 1 Implementation (updated):
    - Uses an explicit whitelist of protocol contracts (staking + lending) provided
      by the blockchain team for BlockDAG Awakening Testnet.
    - Calls SecurityService (GoPlus) for safety_score + warnings.
    - Uses mock APY/TVL values for ranking/utility computation.
    - Supports selecting either staking or lending candidates based on parsed intent.
    """
    logger.info("=" * 80)
    logger.info("PLAN ENDPOINT CALLED")
    logger.info(f"Request payload: {payload.model_dump()}")
    logger.info(f"Intent ID: {payload.intent_id}")
    
    # -----------------------------------------------------
    # 0. Load Intent
    # -----------------------------------------------------
    logger.info("Step 0: Loading Intent from database...")
    try:
        intent = Intent.objects.get(id=payload.intent_id)
        logger.info(f"Intent loaded successfully: {intent.id}")
        logger.debug(f"Intent status: {intent.status}")
        logger.debug(f"Intent JSON: {intent.intent_json}")
        logger.debug(f"Chain ID: {intent.chain_id}")
    except Intent.DoesNotExist:
        logger.error(f"Intent with ID {payload.intent_id} not found")
        raise HttpError(404, f"Intent with ID {payload.intent_id} not found.")
    except Exception as e:
        logger.error(f"Unexpected error loading Intent: {str(e)}")
        logger.error(traceback.format_exc())
        raise

    chain_id_str = str(intent.chain_id)
    logger.info(f"Chain ID (string): {chain_id_str}")

    # -----------------------------------------------------
    # Official addresses (BlockDAG Awakening Testnet - Chain ID: 1043)
    # Provided by the blockchain team:
    #   IntentWallet: 0x718a09981d305c2293d0c85e9d957ad25cb2a1c7
    #   MockDEX:      0xbC47d9625e7c102C6E9C08D29BbD3A76514eCB56
    #   MockStakingFarm: 0x1b227DF9c8D34CaB880774737FBf426E66Ba98Ed
    #   MockLending:     0xa23bDd28F9221F275897D8A26A8eb97A341cd257
    # -----------------------------------------------------

    INTENT_WALLET_ADDRESS = "0x718a09981d305c2293d0c85e9d957ad25cb2a1c7"
    CANDIDATE_DEX = [
        {"address": "0xbC47d9625e7c102C6E9C08D29BbD3A76514eCB56", "note": "MockDEX (not used for stake/lend selection)"}
    ]

    # Whitelisted staking farms (official)
    CANDIDATE_FARMS = [
        {
            "address": "0x1b227DF9c8D34CaB880774737FBf426E66Ba98Ed",  # MockStakingFarm
            "mock_apy": 0.12,  # 12% APY (placeholder)
            "mock_tvl": 500_000,
            "protocol": "staking",
        },
        # Additional production farms can be added here as they are deployed
    ]

    # Whitelisted lending protocols (official)
    CANDIDATE_LENDING = [
        {
            "address": "0xa23bDd28F9221F275897D8A26A8eb97A341cd257",  # MockLending
            "mock_apy": 0.05,  # 5% APY (placeholder)
            "mock_tvl": 2_500_000,
            "protocol": "lending",
        }
    ]

    # -----------------------------------------------------
    # Decide which candidate list to evaluate based on parsed intent
    # -----------------------------------------------------
    logger.info("Step 1: Determining candidate list based on intent type...")
    intent_type = (intent.intent_json or {}).get("intent_type", "").lower()
    logger.info(f"Intent type detected: '{intent_type}'")
    
    if "lend" in intent_type or "borrow" in intent_type:
        candidates_to_check = CANDIDATE_LENDING
        logger.info(f"Using LENDING candidates ({len(candidates_to_check)} protocols)")
    elif "stake" in intent_type or "farm" in intent_type:
        candidates_to_check = CANDIDATE_FARMS
        logger.info(f"Using STAKING candidates ({len(candidates_to_check)} protocols)")
    else:
        # default to staking if unclear
        candidates_to_check = CANDIDATE_FARMS
        logger.warning(f"Intent type unclear, defaulting to STAKING candidates ({len(candidates_to_check)} protocols)")
    
    logger.debug(f"Candidates to check: {candidates_to_check}")

    # -----------------------------------------------------
    # 2. Run SecurityService (GoPlus) for each candidate
    # -----------------------------------------------------
    logger.info("=" * 60)
    logger.info("Step 2: Running security checks on candidates...")
    candidate_results: list[CandidateSchema] = []

    for idx, candidate in enumerate(candidates_to_check, 1):
        addr = candidate["address"]
        logger.info(f"Checking candidate {idx}/{len(candidates_to_check)}: {addr}")
        logger.debug(f"Candidate details: {candidate}")

        # run the security check (wrap in try/except to be resilient)
        try:
            logger.info(f"Calling security_service.run_security_check(chain_id={chain_id_str}, address={addr})")
            report = security_service.run_security_check(chain_id_str, addr)
            logger.info(f"Security check completed for {addr}")
            logger.debug(f"Security report: {report}")
        except Exception as exc:
            # If security service fails for this address, skip and continue
            logger.error(f"SecurityService error for {addr} on chain {chain_id_str}")
            logger.exception("Full exception details:", exc_info=exc)
            continue

        # If the report isn't present or flagged unsafe, skip
        if not report:
            logger.warning(f"No report returned for {addr}, skipping")
            continue
            
        is_safe = getattr(report, "is_safe", False)
        logger.info(f"Candidate {addr} safety status: {is_safe}")
        
        if not is_safe:
            logger.warning(f"Skipping candidate {addr} because it's not safe according to GoPlus.")
            logger.debug(f"Report details: is_safe={is_safe}, warnings={getattr(report, 'warnings', [])}")
            continue

        # -----------------------------------------------------
        # 3. Compute utility
        # Utility formula (same as before):
        #   utility = (APY * 0.5) + (safety_score/100 * 0.5)
        # APY should be in fractional form (e.g. 0.12 for 12%).
        # -----------------------------------------------------
        apy = float(candidate.get("mock_apy", 0.0))
        safety_score = float(getattr(report, "safety_score", 0.0))
        utility = (apy * 0.5) + ((safety_score / 100.0) * 0.5)
        
        logger.info(f"Utility calculation for {addr}:")
        logger.info(f"  APY: {apy} ({apy*100}%)")
        logger.info(f"  Safety Score: {safety_score}")
        logger.info(f"  Utility: {utility:.6f}")

        candidate_schema = CandidateSchema(
            address=addr,
            apy=apy,
            tvl=candidate.get("mock_tvl", 0),
            safety_score=safety_score,
            utility=round(utility, 6),
            warnings=getattr(report, "warnings", []),
            protocol=candidate.get("protocol", "unknown"),
        )
        
        logger.debug(f"Candidate schema created: {candidate_schema.model_dump()}")
        candidate_results.append(candidate_schema)
        logger.info(f"✓ Candidate {addr} added to results (total: {len(candidate_results)})")

    # -----------------------------------------------------
    # If no safe candidates found, return an error
    # -----------------------------------------------------
    logger.info("=" * 60)
    logger.info(f"Step 3: Evaluating results - Total safe candidates: {len(candidate_results)}")
    
    if not candidate_results:
        logger.error("No safe candidates found after security checks!")
        raise HttpError(
            500,
            "Could not generate a plan. No safe and valid candidates were found after GoPlus security check."
        )

    # -----------------------------------------------------
    # 4. Choose the best candidate (highest utility)
    # -----------------------------------------------------
    logger.info("Step 4: Selecting best candidate...")
    for idx, cand in enumerate(candidate_results, 1):
        logger.info(f"  Candidate {idx}: {cand.address[:10]}... - Utility: {cand.utility:.6f}")
    
    chosen_candidate = max(candidate_results, key=lambda c: c.utility)
    logger.info(f"✓ Best candidate chosen: {chosen_candidate.address}")
    logger.info(f"  Utility: {chosen_candidate.utility:.6f}")
    logger.info(f"  Protocol: {chosen_candidate.protocol}")
    logger.info(f"  APY: {chosen_candidate.apy*100}%")
    logger.info(f"  Safety Score: {chosen_candidate.safety_score}")

    # -----------------------------------------------------
    # 5. Construct plan steps (approve -> action)
    # Action differs by protocol type
    # -----------------------------------------------------
    logger.info("=" * 60)
    logger.info("Step 5: Constructing execution plan...")
    
    asset = intent.intent_json.get("asset")
    amount = intent.intent_json.get("amount")
    logger.info(f"Asset: {asset}")
    logger.info(f"Amount: {amount}")

    if chosen_candidate.protocol == "lending" or "lend" in intent_type:
        action_step = {
            "type": "lend",  # or "supply" depending on on-chain naming
            "contract": chosen_candidate.address,
            "amount": amount,
            "asset": asset,
        }
        logger.info(f"Action type: LEND")
    else:
        action_step = {
            "type": "stake",
            "contract": chosen_candidate.address,
            "amount": amount,
            "asset": asset,
        }
        logger.info(f"Action type: STAKE")
    
    logger.debug(f"Action step: {action_step}")

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

    # -----------------------------------------------------
    # 6. Save Plan + Update Intent
    # -----------------------------------------------------
    logger.info("=" * 60)
    logger.info("Step 6: Saving plan to database...")
    logger.debug(f"Plan data: {plan_data}")
    
    try:
        new_plan = Plan.objects.create(
            intent=intent,
            plan_json=plan_data,
            utility_scores=[c.model_dump() for c in candidate_results],
            chosen_contract_address=chosen_candidate.address,
            status=Plan.Status.READY
        )
        logger.info(f"✓ Plan created successfully with ID: {new_plan.id}")

        intent.status = Intent.Status.PLANNED
        intent.save()
        logger.info(f"✓ Intent status updated to PLANNED")
    except Exception as e:
        logger.error(f"Failed to save plan or update intent: {str(e)}")
        logger.error(traceback.format_exc())
        raise

    # -----------------------------------------------------
    # 7. Return response
    # -----------------------------------------------------
    logger.info("Step 7: Preparing response...")
    logger.info(f"Returning {len(candidate_results)} candidates with chosen: {chosen_candidate.address}")
    logger.info("=" * 80)
    
    return PlanOutput(
        plan_id=new_plan.id,
        candidates=candidate_results,
        chosen=chosen_candidate
    )
