# api_v1/schemas.py
from ninja import Schema
from pydantic import field_validator
from typing import Optional, List
import uuid
import re

# === Input Schemas ===

class IntentParseInput(Schema):
    """Input schema for intent parsing endpoint."""
    input: str
    user_wallet: str
    chain_id: int = 1043

    @field_validator('user_wallet')
    def validate_eth_address(cls, v):
        if not re.match(r"^0x[a-fA-F0-9]{40}$", v):
            raise ValueError('Invalid EVM wallet address format. Must be 0x followed by 40 hex characters.')
        return v

# === Output Schemas ===

class IntentSchema(Schema):
    """Structured representation of a parsed intent."""
    intent_type: str
    asset: str
    amount: float
    amount_unit: str
    target: str

class IntentParseOutput(Schema):
    """Output schema for parsed intent with status."""
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
    
    
    
# === Execution Schemas ===

class SubmitIntentInput(Schema):
    plan_id: uuid.UUID

class SubmitIntentOutput(Schema):
    execution_id: uuid.UUID
    status: str

class ExecutionStatusOutput(Schema):
    execution_id: uuid.UUID
    status: str
    tx_hash: Optional[str] = None
    logs: List[str] = []