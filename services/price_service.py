# services/price_service.py
"""
Price Oracle Service - Makes USD Values Possible

This service provides token prices to convert raw token amounts
to USD values for the frontend dashboard.

Example: "1000 BDAG" → "$50.00"

For the hackathon, we use mock prices. In production, this would
integrate with Chainlink or other price oracles.
"""

import logging
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PriceService:
    """
    Token price service for USD conversions.
    
    This transforms the UI from showing "1000 BDAG" (meaningless)
    to showing "$50.00" (value the user understands).
    
    Mock Prices (for hackathon demo):
    - BDAG: $0.05
    - POL: $0.35
    - ETH: $2,500
    - USDT: $1.00
    """
    
    # Mock price feed (in production, fetch from oracle)
    MOCK_PRICES: Dict[str, Decimal] = {
        "BDAG": Decimal("0.05"),      # BlockDAG testnet token
        "POL": Decimal("0.35"),       # Polygon native token
        "MATIC": Decimal("0.35"),     # Polygon (old name)
        "ETH": Decimal("2500.00"),    # Ethereum
        "WETH": Decimal("2500.00"),   # Wrapped ETH
        "USDT": Decimal("1.00"),      # Tether
        "USDC": Decimal("1.00"),      # USD Coin
        "DAI": Decimal("1.00"),       # DAI
        "WBTC": Decimal("95000.00"),  # Wrapped BTC
    }
    
    # Price change simulation (for realistic dashboard)
    MOCK_24H_CHANGE: Dict[str, Decimal] = {
        "BDAG": Decimal("5.2"),   # +5.2%
        "POL": Decimal("-2.1"),  # -2.1%
        "ETH": Decimal("1.8"),
        "USDT": Decimal("0.01"),
        "USDC": Decimal("-0.02"),
    }
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # symbol -> (price, timestamp)
        self._cache_ttl = timedelta(minutes=5)
    
    def get_price(self, symbol: str) -> Decimal:
        """
        Get current price for a token symbol.
        
        Args:
            symbol: Token symbol (e.g., "BDAG", "ETH", "USDT")
            
        Returns:
            Price in USD as Decimal
        """
        symbol = symbol.upper()
        
        # Check cache
        if symbol in self._cache:
            price, timestamp = self._cache[symbol]
            if datetime.now() - timestamp < self._cache_ttl:
                return price
        
        # Get from mock prices (in production, call oracle API)
        price = self.MOCK_PRICES.get(symbol, Decimal("0"))
        
        # Cache it
        self._cache[symbol] = (price, datetime.now())
        
        if price == 0:
            logger.warning(f"No price data for {symbol}, returning 0")
        
        return price
    
    def get_prices(self, symbols: list) -> Dict[str, Decimal]:
        """
        Get prices for multiple tokens at once.
        """
        return {symbol: self.get_price(symbol) for symbol in symbols}
    
    def convert_to_usd(self, amount: Decimal, symbol: str) -> Decimal:
        """
        Convert token amount to USD value.
        
        Example:
            convert_to_usd(Decimal("1000"), "BDAG") -> Decimal("50.00")
        """
        price = self.get_price(symbol)
        return amount * price
    
    def format_usd(self, amount: Decimal) -> str:
        """
        Format USD value for display.
        
        Example:
            format_usd(Decimal("50.00")) -> "$50.00"
            format_usd(Decimal("1234.567")) -> "$1,234.57"
        """
        return f"${amount:,.2f}"
    
    def get_price_change_24h(self, symbol: str) -> Decimal:
        """
        Get 24-hour price change percentage.
        
        Used for dashboard display: "BDAG +5.2%"
        """
        symbol = symbol.upper()
        return self.MOCK_24H_CHANGE.get(symbol, Decimal("0"))
    
    def get_price_info(self, symbol: str) -> Dict:
        """
        Get complete price information for a token.
        
        Returns dict suitable for frontend display:
        {
            "symbol": "BDAG",
            "price_usd": "0.05",
            "price_formatted": "$0.05",
            "change_24h": "5.2",
            "change_direction": "up"
        }
        """
        price = self.get_price(symbol)
        change = self.get_price_change_24h(symbol)
        
        return {
            "symbol": symbol.upper(),
            "price_usd": str(price),
            "price_formatted": self.format_usd(price),
            "change_24h": str(change),
            "change_direction": "up" if change > 0 else "down" if change < 0 else "neutral",
        }
    
    def estimate_value_after_period(
        self, 
        amount: Decimal, 
        symbol: str, 
        apy: Decimal, 
        days: int
    ) -> Dict:
        """
        Calculate projected value after a time period with APY.
        
        Used for dashboard projections:
        "Your 1000 BDAG staked at 12% APY will be worth $56.16 in 30 days"
        
        Args:
            amount: Token amount
            symbol: Token symbol
            apy: Annual percentage yield (e.g., 0.12 for 12%)
            days: Number of days to project
            
        Returns:
            Dict with current and projected values
        """
        price = self.get_price(symbol)
        current_value = amount * price
        
        # Calculate projected amount with APY
        daily_rate = apy / Decimal(365)
        projected_amount = amount * (1 + daily_rate * days)
        projected_value = projected_amount * price
        
        earnings = projected_value - current_value
        
        return {
            "current_amount": str(amount),
            "current_value_usd": str(current_value),
            "current_value_formatted": self.format_usd(current_value),
            "projected_amount": str(projected_amount.quantize(Decimal("0.0001"))),
            "projected_value_usd": str(projected_value.quantize(Decimal("0.01"))),
            "projected_value_formatted": self.format_usd(projected_value),
            "projected_earnings_usd": str(earnings.quantize(Decimal("0.01"))),
            "projected_earnings_formatted": self.format_usd(earnings),
            "apy": str(apy * 100) + "%",
            "period_days": days,
        }


# Singleton instance
price_service = PriceService()
