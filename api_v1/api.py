# api_v1/api.py
from ninja import Router
from ninja.errors import HttpError
from .schemas import (
    IntentParseInput, IntentParseOutput, 
    PlanInput, PlanOutput, CandidateSchema,
    SubmitIntentInput, SubmitIntentOutput, ExecutionStatusOutput 
)
from .models import Intent, Plan, Execution
from .tasks import execute_plan_task 
from services.security_service import security_service
import logging
import traceback


router = Router()
logger = logging.getLogger(__name__)

@router.post("/parse-intent/", response=IntentParseOutput, summary="Parse a Natural Language Intent")
def parse_intent(request, payload: IntentParseInput):
    """Parse natural language input into a structured Intent object.
    
    Currently uses hardcoded parsing logic. Future versions will integrate LLM.
    """
    logger.info(f"Parse intent called for wallet: {payload.user_wallet}")
    
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
        parsed_intent_data = {}
        status = Intent.Status.CLARIFY
    
    try:
        intent = Intent.objects.create(
            user_wallet=payload.user_wallet,
            chain_id=payload.chain_id, 
            input_text=payload.input,
            intent_json=parsed_intent_data,
            status=status
        )
        logger.info(f"Intent created: {intent.id}")
    except Exception as e:
        logger.error(f"Failed to create Intent: {str(e)}")
        raise

    return IntentParseOutput(
        intent_id=intent.id,
        status=intent.status,
        intent=parsed_intent_data if status == Intent.Status.PARSED else None,
        clarify_questions=["Sorry, I can only understand staking intents right now."] if status == Intent.Status.CLARIFY else []
    )
    
    

@router.post("/plan/", response=PlanOutput, summary="Generate an Execution Plan")
def plan_intent(request, payload: PlanInput):
    """Generate ranked execution plans with security validation.
    
    Uses whitelisted protocols for BlockDAG Awakening Testnet.
    Validates security using GoPlus API and ranks by utility score.
    """
    logger.info(f"Plan intent called for: {payload.intent_id}")
    
    try:
        intent = Intent.objects.get(id=payload.intent_id)
    except Intent.DoesNotExist:
        raise HttpError(404, f"Intent with ID {payload.intent_id} not found.")

    chain_id_str = str(intent.chain_id)

    INTENT_WALLET_ADDRESS = "0x718a09981d305c2293d0c85e9d957ad25cb2a1c7"
    
    CANDIDATE_FARMS = [
        {
            "address": "0x1b227DF9c8D34CaB880774737FBf426E66Ba98Ed",
            "mock_apy": 0.12,
            "mock_tvl": 500_000,
            "protocol": "staking",
        },
    ]

    CANDIDATE_LENDING = [
        {
            "address": "0xa23bDd28F9221F275897D8A26A8eb97A341cd257",
            "mock_apy": 0.05,
            "mock_tvl": 2_500_000,
            "protocol": "lending",
        }
    ]

    intent_type = (intent.intent_json or {}).get("intent_type", "").lower()
    
    if "lend" in intent_type or "borrow" in intent_type:
        candidates_to_check = CANDIDATE_LENDING
    elif "stake" in intent_type or "farm" in intent_type:
        candidates_to_check = CANDIDATE_FARMS
    else:
        candidates_to_check = CANDIDATE_FARMS
    
    logger.info(f"Checking {len(candidates_to_check)} candidates for intent type: {intent_type}")

    candidate_results: list[CandidateSchema] = []

    for candidate in candidates_to_check:
        addr = candidate["address"]

        try:
            report = security_service.run_security_check(chain_id_str, addr)
        except Exception as exc:
            logger.error(f"Security check failed for {addr}: {exc}")
            continue

        if not report or not getattr(report, "is_safe", False):
            logger.warning(f"Skipping unsafe candidate: {addr}")
            continue

        apy = float(candidate.get("mock_apy", 0.0))
        safety_score = float(getattr(report, "safety_score", 0.0))
        utility = (apy * 0.5) + ((safety_score / 100.0) * 0.5)

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
        logger.info(f"Added candidate {addr} with utility {utility:.4f}")

    if not candidate_results:
        raise HttpError(500, "No safe candidates found after security validation.")

    chosen_candidate = max(candidate_results, key=lambda c: c.utility)
    logger.info(f"Selected candidate: {chosen_candidate.address} (utility: {chosen_candidate.utility:.4f})")

    asset = intent.intent_json.get("asset")
    amount = intent.intent_json.get("amount")

    if chosen_candidate.protocol == "lending" or "lend" in intent_type:
        action_step = {
            "type": "lend",
            "contract": chosen_candidate.address,
            "amount": amount,
            "asset": asset,
        }
    else:
        action_step = {
            "type": "stake",
            "contract": chosen_candidate.address,
            "amount": amount,
            "asset": asset,
        }

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
        logger.info(f"Plan created: {new_plan.id}")
    except Exception as e:
        logger.error(f"Failed to save plan: {str(e)}")
        raise
    
    return PlanOutput(
        plan_id=new_plan.id,
        candidates=candidate_results,
        chosen=chosen_candidate
    )




@router.post("/submit-intent/", response=SubmitIntentOutput, summary="Submit a Plan for Execution")
def submit_intent(request, payload: SubmitIntentInput):
    """Create execution record and queue async task."""
    try:
        plan = Plan.objects.get(id=payload.plan_id)
    except Plan.DoesNotExist:
        raise HttpError(404, "Plan not found")

    if hasattr(plan, 'execution'):
        return SubmitIntentOutput(
            execution_id=plan.execution.id,
            status=plan.execution.status
        )

    execution = Execution.objects.create(
        plan=plan,
        status=Execution.Status.PENDING,
        relayer_address="0xRelayerBot"
    )
    
    execute_plan_task.delay(execution.id)
    logger.info(f"Execution queued: {execution.id}")

    return SubmitIntentOutput(
        execution_id=execution.id,
        status=execution.status
    )

@router.get("/execution/{execution_id}/status/", response=ExecutionStatusOutput, summary="Poll Execution Status")
def get_execution_status(request, execution_id: str):
    """Return current status and transaction hash of an execution."""
    try:
        execution = Execution.objects.get(id=execution_id)
    except Execution.DoesNotExist:
        raise HttpError(404, "Execution not found")

    return ExecutionStatusOutput(
        execution_id=execution.id,
        status=execution.status,
        tx_hash=execution.tx_hash,
        logs=execution.receipt.get("logs", []) if execution.receipt else []
    )