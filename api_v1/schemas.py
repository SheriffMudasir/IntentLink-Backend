# api_v1/schemas.py
from ninja import Schema
from typing import Optional, List
import uuid

# === Input Schemas ===

class IntentParseInput(Schema):
    """
    Schema for the input to the /parse-intent endpoint.
    """
    input: str
    user_wallet: str
    chain_id: int = 1043

# === Output Schemas ===

class IntentSchema(Schema):
    """
    Represents the structured JSON of a parsed intent.
    This schema must be kept strict to prevent LLM hallucinations.
    """
    intent_type: str
    asset: str
    amount: float
    amount_unit: str
    target: str

class IntentParseOutput(Schema):
    """
    Schema for the output of the /parse-intent endpoint.
    """
    intent_id: uuid.UUID
    status: str
    intent: IntentSchema
    clarify_questions: Optional[List[str]] = None
    
# === Plan Schemas ===

class PlanInput(Schema):
    intent_id: uuid.UUID

class CandidateSchema(Schema):
    address: str
    apy: float
    tvl: float
    safety_score: int
    utility: float
    warnings: List[str]
    protocol: str  

class PlanOutput(Schema):
    plan_id: uuid.UUID
    candidates: List[CandidateSchema]
    chosen: CandidateSchema