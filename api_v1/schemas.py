# api_v1/schemas.py
"""
API Schemas - Wave 3 Upgrade

New schemas for:
- Portfolio Dashboard (shows user positions + USD values)
- Security Report (visual badges from GoPlus)
- Quick Actions (pre-built intent templates)
- Enhanced Plan Output (estimated returns)
- Price Information
"""
from ninja import Schema
from pydantic import field_validator
from typing import Optional, List
import uuid
import re
from typing import Optional, List, Dict, Any


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
    signature: str 
    nonce: int 
    expiry: int 

class SubmitIntentOutput(Schema):
    execution_id: uuid.UUID
    status: str

class ExecutionStatusOutput(Schema):
    execution_id: uuid.UUID
    status: str
    tx_hash: Optional[str] = None
    logs: List[str] = []
    
    
# === Signature Schemas (NEW) ===

class PrepareSignatureInput(Schema):
    plan_id: uuid.UUID

class PrepareSignatureOutput(Schema):
    typed_data: Dict[str, Any] # The EIP-712 JSON object
    plan_hash: str
    nonce: int
    expiry: int


# ==========================================================
# WAVE 3 NEW SCHEMAS - Dashboard, Portfolio, Quick Actions
# ==========================================================

# === Portfolio Schemas ===

class StakingPositionSchema(Schema):
    """User's staking position in a protocol."""
    protocol_address: str
    protocol_name: str
    staked_amount: str
    staked_amount_usd: str
    pending_rewards: str
    pending_rewards_usd: str
    apy: str
    
class LendingPositionSchema(Schema):
    """User's lending position in a protocol."""
    protocol_address: str
    protocol_name: str
    supplied_amount: str
    supplied_amount_usd: str
    accrued_interest: str
    supply_apy: str

class TokenBalanceSchema(Schema):
    """Token balance for portfolio display."""
    symbol: str
    name: str
    balance: str
    balance_usd: str
    contract_address: str
    decimals: int = 18
    icon: str = "💰"  # Default icon for tokens

class V2AggregatedSchema(Schema):
    """V2 aggregated portfolio data from single RPC call."""
    wallet_balance: str      # USDT balance in wallet
    staked_balance: str      # Amount staked in farm
    pending_rewards: str     # Unclaimed rewards (THIS IS KEY!)
    current_apy: str         # Current farm APY as percentage
    eth_balance: str         # Native token balance

class PortfolioOutput(Schema):
    """Complete portfolio data for dashboard display."""
    wallet_address: str
    chain_id: int
    chain_name: str
    
    # Native currency balance (BDAG, POL, etc.)
    native_balance: str
    native_balance_usd: str
    native_symbol: str = "BDAG"  # The native currency symbol
    
    # Token balances (MockUSDT, etc.) - NEW for Wave 3
    token_balances: List[TokenBalanceSchema] = []
    
    # Positions
    staking_positions: List[StakingPositionSchema]
    lending_positions: List[LendingPositionSchema]
    
    # Totals for headline display
    total_staked_value: str
    total_staked_value_usd: str
    total_lending_value: str
    total_lending_value_usd: str
    total_pending_rewards: str
    total_pending_rewards_usd: str
    
    # The big number at the top of dashboard
    total_portfolio_value_usd: str
    
    # V2 aggregated data (from IntentWalletV2.getPortfolio() or StakingFarmV2)
    v2_aggregated: Optional[V2AggregatedSchema] = None


# === Price Schemas ===

class PriceInfoSchema(Schema):
    """Token price information."""
    symbol: str
    price_usd: str
    price_formatted: str
    change_24h: str
    change_direction: str  # "up", "down", "neutral"

class PricesOutput(Schema):
    """Multiple token prices."""
    prices: List[PriceInfoSchema]


# === Security Report Schemas ===

class SecurityBadgeSchema(Schema):
    """Individual security check badge."""
    name: str
    status: str  # "passed", "warning", "failed"
    description: str
    icon: str  # For frontend: "shield-check", "alert-triangle", etc.

class SecurityReportOutput(Schema):
    """Complete security report for a protocol - visual badges for frontend."""
    protocol_address: str
    chain_id: int
    overall_score: int  # 0-100
    overall_status: str  # "safe", "caution", "danger"
    badges: List[SecurityBadgeSchema]
    scan_timestamp: str
    provider: str  # "GoPlus"


# === Quick Actions Schemas (One-Tap DeFi) ===

class QuickActionSchema(Schema):
    """Pre-built intent for one-tap execution."""
    id: str
    title: str
    description: str
    icon: str
    intent_template: str  # Pre-filled intent text
    category: str  # "staking", "swap", "lending"
    estimated_apy: Optional[str] = None
    recommended: bool = False

class QuickActionsOutput(Schema):
    """Available quick actions for the user."""
    chain_id: int
    chain_name: str
    actions: List[QuickActionSchema]


# === Enhanced Plan Output (with projections) ===

class ProjectionSchema(Schema):
    """Projected earnings for display."""
    period: str  # "daily", "weekly", "monthly", "yearly"
    amount: str
    amount_usd: str

class EnhancedPlanOutput(Schema):
    """Plan output with financial projections for UX."""
    plan_id: uuid.UUID
    candidates: List[CandidateSchema]
    chosen: CandidateSchema
    
    # NEW: Financial projections
    estimated_apy: str
    projected_earnings: List[ProjectionSchema]
    
    # NEW: USD values
    input_amount: str
    input_amount_usd: str
    
    # NEW: Visual summary for frontend
    summary: str  # "Stake 1000 BDAG at 12% APY → Earn $6.00/month"


# === Intent Parsing Enhancement ===

class ParsedIntentDetailSchema(Schema):
    """Detailed breakdown of parsed intent for transparency."""
    raw_input: str
    intent_type: str
    asset: str
    amount: float
    amount_usd: str
    target_protocol: Optional[str] = None
    confidence: float  # 0.0 to 1.0
    
class EnhancedIntentParseOutput(Schema):
    """Enhanced intent parse output showing the 'AI magic'."""
    intent_id: uuid.UUID
    status: str
    intent: IntentSchema
    clarify_questions: Optional[List[str]] = None
    
    # NEW: Show the AI reasoning
    parsed_details: ParsedIntentDetailSchema
    suggested_actions: List[QuickActionSchema]


# === Relayer Status (for monitoring) ===

class RelayerStatusSchema(Schema):
    """Relayer wallet status for monitoring dashboard."""
    address: str
    chain_id: int
    balance: str
    currency: str
    tracked_nonce: Optional[int] = None
    blockchain_nonce: int
    nonce_synced: Optional[bool] = None



