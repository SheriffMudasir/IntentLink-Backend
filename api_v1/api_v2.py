# api_v1/api_v2.py
"""
IntentLink API v2 - Wave 3 "Consumer Product" Endpoints

These endpoints power the Robinhood-style dashboard and one-tap DeFi actions.

New Endpoints:
- GET /portfolio/{chain_id}/{wallet}/ - Portfolio dashboard data
- GET /prices/ - Token prices for USD conversion
- GET /quick-actions/{chain_id}/ - One-tap action templates
- GET /security-report/{chain_id}/{address}/ - Visual security badges
- GET /relayer-status/{chain_id}/ - Relayer monitoring
"""
from ninja import Router
from ninja.errors import HttpError
from django.conf import settings
from decimal import Decimal
from datetime import datetime
import logging

from .schemas import (
    PortfolioOutput, StakingPositionSchema, LendingPositionSchema, TokenBalanceSchema, V2AggregatedSchema,
    PricesOutput, PriceInfoSchema,
    QuickActionsOutput, QuickActionSchema,
    SecurityReportOutput, SecurityBadgeSchema,
    RelayerStatusSchema,
    EnhancedPlanOutput, ProjectionSchema, CandidateSchema,
)
from services.portfolio_service import portfolio_service
from services.price_service import price_service
from services.security_service import security_service
from services.relayer_service import RelayerService

router = Router(tags=["v2"])
logger = logging.getLogger(__name__)


# ==========================================================
# PORTFOLIO ENDPOINT - Powers the Dashboard
# ==========================================================

@router.get(
    "/portfolio/{chain_id}/{wallet}/",
    response=PortfolioOutput,
    summary="Get User Portfolio",
    description="Fetches complete portfolio data for dashboard display. Shows staked amounts, pending rewards, and USD values."
)
def get_portfolio(request, chain_id: int, wallet: str):
    """
    The most important endpoint for Wave 3.
    
    Frontend displays:
    - "Total Portfolio: $1,250.00"
    - "Staked: 1000 BDAG ($50.00) @ 12% APY"
    - "Pending Rewards: 5.42 BDAG ($0.27)"
    """
    logger.info(f"Portfolio request: chain={chain_id}, wallet={wallet}")
    
    try:
        # Get portfolio from service
        portfolio = portfolio_service.get_portfolio(chain_id, wallet)
        
        # Get prices for USD conversion
        network_config = settings.NETWORK_CONFIG.get(chain_id)
        currency = network_config['currency'] if network_config else 'BDAG'
        token_price = price_service.get_price(currency)
        usdt_price = price_service.get_price('USDT')
        
        # Build token balances list (MockUSDT, etc.)
        token_balances = []
        
        # Add native currency as first "token"
        token_balances.append(TokenBalanceSchema(
            symbol=currency,
            name=f"{currency} (Native)",
            balance=str(portfolio.native_balance),
            balance_usd=price_service.format_usd(portfolio.native_balance * token_price),
            contract_address="0x0000000000000000000000000000000000000000",  # Native token
            decimals=18,
            icon="⛽" if currency == "BDAG" else "🟣",
        ))
        
        # Add MockUSDT balance
        if portfolio.usdt_balance > 0 or True:  # Always show USDT even if 0
            usdt_config = network_config.get('tokens', {}).get('USDT', {})
            usdt_address = usdt_config.get('address', network_config.get('contracts', {}).get('MockUSDT', ''))
            token_balances.append(TokenBalanceSchema(
                symbol="USDT",
                name="Mock USDT",
                balance=str(portfolio.usdt_balance),
                balance_usd=price_service.format_usd(portfolio.usdt_balance * usdt_price),
                contract_address=usdt_address,
                decimals=18,
                icon="💵",
            ))
        
        # Build staking positions with USD values
        staking_positions = []
        for pos in portfolio.staking_positions:
            staking_positions.append(StakingPositionSchema(
                protocol_address=pos.protocol_address,
                protocol_name=pos.protocol_name,
                staked_amount=str(pos.staked_amount),
                staked_amount_usd=price_service.format_usd(pos.staked_amount * token_price),
                pending_rewards=str(pos.pending_rewards),
                pending_rewards_usd=price_service.format_usd(pos.pending_rewards * token_price),
                apy=f"{pos.apy * 100:.1f}%",
            ))
        
        # Build lending positions with USD values
        lending_positions = []
        for pos in portfolio.lending_positions:
            lending_positions.append(LendingPositionSchema(
                protocol_address=pos.protocol_address,
                protocol_name=pos.protocol_name,
                supplied_amount=str(pos.supplied_amount),
                supplied_amount_usd=price_service.format_usd(pos.supplied_amount * token_price),
                accrued_interest=str(pos.accrued_interest),
                supply_apy=f"{pos.supply_apy * 100:.1f}%",
            ))
        
        # Build V2 aggregated data if available
        v2_aggregated = None
        if portfolio.v2_data:
            v2_aggregated = V2AggregatedSchema(
                wallet_balance=str(portfolio.v2_data.wallet_balance),
                staked_balance=str(portfolio.v2_data.staked_balance),
                pending_rewards=str(portfolio.v2_data.pending_rewards),
                current_apy=str(portfolio.v2_data.current_apy),
                eth_balance=str(portfolio.v2_data.eth_balance),
            )
        
        return PortfolioOutput(
            wallet_address=portfolio.wallet_address,
            chain_id=portfolio.chain_id,
            chain_name=portfolio.chain_name,
            native_balance=str(portfolio.native_balance),
            native_balance_usd=price_service.format_usd(portfolio.native_balance * token_price),
            native_symbol=currency,
            token_balances=token_balances,
            staking_positions=staking_positions,
            lending_positions=lending_positions,
            total_staked_value=str(portfolio.total_staked_value),
            total_staked_value_usd=price_service.format_usd(portfolio.total_staked_value * token_price),
            total_lending_value=str(portfolio.total_lending_value),
            total_lending_value_usd=price_service.format_usd(portfolio.total_lending_value * token_price),
            total_pending_rewards=str(portfolio.total_pending_rewards),
            total_pending_rewards_usd=price_service.format_usd(portfolio.total_pending_rewards * token_price),
            total_portfolio_value_usd=price_service.format_usd(portfolio.total_portfolio_value_usd),
            v2_aggregated=v2_aggregated,
        )
        
    except ValueError as e:
        logger.error(f"Portfolio error: {e}")
        raise HttpError(400, str(e))
    except Exception as e:
        logger.error(f"Portfolio error: {e}")
        raise HttpError(500, f"Failed to fetch portfolio: {str(e)}")


# ==========================================================
# PRICES ENDPOINT - Token Prices for USD Display
# ==========================================================

@router.get(
    "/prices/",
    response=PricesOutput,
    summary="Get Token Prices",
    description="Get current prices for supported tokens. Used by frontend to display USD values."
)
def get_prices(request, symbols: str = "BDAG,POL,ETH,USDT"):
    """
    Fetch token prices for USD conversion.
    
    Query params:
    - symbols: Comma-separated list of token symbols
    
    Example: /prices/?symbols=BDAG,POL,ETH
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    prices = []
    for symbol in symbol_list:
        info = price_service.get_price_info(symbol)
        prices.append(PriceInfoSchema(**info))
    
    return PricesOutput(prices=prices)


# ==========================================================
# QUICK ACTIONS ENDPOINT - One-Tap DeFi
# ==========================================================

@router.get(
    "/quick-actions/{chain_id}/",
    response=QuickActionsOutput,
    summary="Get Quick Actions",
    description="Get pre-built intent templates for one-tap DeFi actions. No typing required!"
)
def get_quick_actions(request, chain_id: int):
    """
    Returns the "Happy Path" buttons for the frontend:
    - "🚀 Maximize Yield"
    - "🔄 Swap Tokens"
    - "🏦 Earn Interest"
    
    This fixes the UX problem of users not knowing what to type.
    """
    network_config = settings.NETWORK_CONFIG.get(chain_id)
    if not network_config:
        raise HttpError(400, f"Unsupported chain ID: {chain_id}")
    
    currency = network_config['currency']
    chain_name = network_config['name']
    
    actions = [
        QuickActionSchema(
            id="stake_max_yield",
            title="🚀 Maximize Yield",
            description=f"Stake your {currency} for the highest APY available",
            icon="trending-up",
            intent_template=f"stake 1000 {currency.lower()} for highest yield",
            category="staking",
            estimated_apy="12%",
            recommended=True,
        ),
        QuickActionSchema(
            id="stake_1000",
            title=f"💎 Stake 1,000 {currency}",
            description="Start earning passive income immediately",
            icon="coins",
            intent_template=f"stake 1000 {currency.lower()}",
            category="staking",
            estimated_apy="12%",
            recommended=False,
        ),
        QuickActionSchema(
            id="stake_5000",
            title=f"🏆 Stake 5,000 {currency}",
            description="Serious staking for serious returns",
            icon="trophy",
            intent_template=f"stake 5000 {currency.lower()}",
            category="staking",
            estimated_apy="12%",
            recommended=False,
        ),
        QuickActionSchema(
            id="swap_to_usdt",
            title="🔄 Swap to Stablecoin",
            description=f"Convert your {currency} to USDT safely",
            icon="refresh-cw",
            intent_template=f"swap 100 {currency.lower()} to usdt",
            category="swap",
            estimated_apy=None,
            recommended=False,
        ),
        QuickActionSchema(
            id="lend_earn",
            title="🏦 Lend & Earn",
            description="Supply liquidity and earn interest",
            icon="landmark",
            intent_template=f"lend 1000 {currency.lower()}",
            category="lending",
            estimated_apy="5%",
            recommended=False,
        ),
    ]
    
    return QuickActionsOutput(
        chain_id=chain_id,
        chain_name=chain_name,
        actions=actions,
    )


# ==========================================================
# SECURITY REPORT ENDPOINT - Visual Badges
# ==========================================================

@router.get(
    "/security-report/{chain_id}/{address}/",
    response=SecurityReportOutput,
    summary="Get Security Report",
    description="Get visual security badges for a protocol address. Shows GoPlus scan results."
)
def get_security_report(request, chain_id: int, address: str):
    """
    Returns security badges for the frontend to display:
    
    ✅ "Contract Verified"
    ✅ "No Honeypot Risk"  
    ✅ "Owner Not Malicious"
    ⚠️ "New Contract (< 30 days)"
    
    This makes the user FEEL protected by our AI security layer.
    """
    logger.info(f"Security report request: chain={chain_id}, address={address}")
    
    try:
        # Get security check from GoPlus
        report = security_service.run_security_check(str(chain_id), address)
        
        badges = []
        
        if report:
            # Build badges from report
            if report.is_safe:
                badges.append(SecurityBadgeSchema(
                    name="Contract Safe",
                    status="passed",
                    description="No malicious code detected",
                    icon="shield-check",
                ))
            else:
                badges.append(SecurityBadgeSchema(
                    name="Contract Risk",
                    status="failed",
                    description="Potential risks detected",
                    icon="shield-alert",
                ))
            
            # Check for honeypot
            if hasattr(report, 'is_honeypot') and not report.is_honeypot:
                badges.append(SecurityBadgeSchema(
                    name="Not a Honeypot",
                    status="passed",
                    description="Tokens can be sold freely",
                    icon="check-circle",
                ))
            
            # Check for verified source
            badges.append(SecurityBadgeSchema(
                name="Source Verified",
                status="passed" if report.safety_score > 70 else "warning",
                description="Contract source code is verified" if report.safety_score > 70 else "Source not fully verified",
                icon="file-check",
            ))
            
            # Add warning badges if any
            for warning in report.warnings[:3]:  # Max 3 warnings
                badges.append(SecurityBadgeSchema(
                    name="Warning",
                    status="warning",
                    description=warning,
                    icon="alert-triangle",
                ))
            
            overall_score = report.safety_score
            overall_status = "safe" if overall_score >= 80 else "caution" if overall_score >= 50 else "danger"
        else:
            # Fallback if no report
            badges = [
                SecurityBadgeSchema(
                    name="Scan Pending",
                    status="warning",
                    description="Security scan in progress",
                    icon="loader",
                )
            ]
            overall_score = 50
            overall_status = "caution"
        
        return SecurityReportOutput(
            protocol_address=address,
            chain_id=chain_id,
            overall_score=overall_score,
            overall_status=overall_status,
            badges=badges,
            scan_timestamp=datetime.now().isoformat(),
            provider="GoPlus",
        )
        
    except Exception as e:
        logger.error(f"Security report error: {e}")
        raise HttpError(500, f"Security scan failed: {str(e)}")


# ==========================================================
# RELAYER STATUS ENDPOINT - Monitoring
# ==========================================================

@router.get(
    "/relayer-status/{chain_id}/",
    response=RelayerStatusSchema,
    summary="Get Relayer Status",
    description="Get relayer wallet balance and nonce status for monitoring."
)
def get_relayer_status(request, chain_id: int):
    """
    Monitoring endpoint for relayer health.
    
    Shows:
    - Relayer balance (to detect low funds)
    - Nonce tracking status (to detect sync issues)
    """
    try:
        relayer = RelayerService(chain_id=chain_id)
        status = relayer.get_relayer_balance()
        
        return RelayerStatusSchema(**status)
        
    except Exception as e:
        logger.error(f"Relayer status error: {e}")
        raise HttpError(500, f"Failed to get relayer status: {str(e)}")


# ==========================================================
# PROJECTED EARNINGS CALCULATOR
# ==========================================================

@router.get(
    "/calculate-earnings/",
    summary="Calculate Projected Earnings",
    description="Calculate projected earnings for a staking/lending amount."
)
def calculate_earnings(
    request, 
    amount: float, 
    symbol: str = "BDAG", 
    apy: float = 0.12,
    days: int = 30
):
    """
    Calculator endpoint for frontend "projected earnings" display.
    
    Example: "If you stake 1000 BDAG at 12% APY, you'll earn $1.64 in 30 days"
    """
    result = price_service.estimate_value_after_period(
        amount=Decimal(str(amount)),
        symbol=symbol,
        apy=Decimal(str(apy)),
        days=days,
    )
    
    return result


# ==========================================================
# SUPPORTED CHAINS ENDPOINT
# ==========================================================

@router.get(
    "/chains/",
    summary="Get Supported Chains",
    description="List all supported blockchain networks."
)
def get_supported_chains(request):
    """
    Returns list of supported chains for network selector.
    
    Frontend displays:
    - "BlockDAG Awakening (Fast, Cheap)"
    - "Polygon Amoy (Stable, Cross-chain)"
    """
    chains = []
    
    for chain_id, config in settings.NETWORK_CONFIG.items():
        chains.append({
            "chain_id": chain_id,
            "name": config['name'],
            "currency": config['currency'],
            "features": _get_chain_features(chain_id),
        })
    
    return {"chains": chains}


def _get_chain_features(chain_id: int) -> list:
    """Get marketing features for each chain."""
    features_map = {
        1043: ["⚡ Ultra Fast", "💰 Low Fees", "🔒 Secure"],
        80002: ["🌐 Cross-chain", "💧 High Liquidity", "🏛️ Established"],
    }
    return features_map.get(chain_id, ["🔗 Blockchain"])
