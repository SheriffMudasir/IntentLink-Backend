# services/ai_service.py
"""
AI Service - Gemini 1.5 Flash Intent Parser

Wave 3: Uses Google's Gemini 1.5 Flash model for 
natural language intent parsing with JSON output.

Features:
- JSON mode enforcement via response_mime_type
- Low temperature (0.1) for deterministic results
- Fallback to regex-based parsing if AI fails
- Singleton pattern for efficient client reuse
"""

import os
import json
import re
import logging
from typing import Optional, Dict, Any

from django.conf import settings

from .prompts import INTENT_PARSER_SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)


# Global singleton instance
_ai_service_instance = None


def get_ai_service():
    """Get the singleton AIService instance."""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = _AIServiceImpl()
    return _ai_service_instance


class _AIServiceImpl:
    """
    AI-powered intent parsing using Gemini 1.5 Flash.
    
    Converts natural language like "stake 1000 bdag" into 
    structured JSON for the planner.
    """
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
        self.model_name = os.environ.get("GEMINI_MODEL") or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        self.client = None
        self.config = None
        self._initialized = False
        
        if self.api_key:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initializes the Gemini client."""
        try:
            from google import genai
            from google.genai import types
            
            self.client = genai.Client(api_key=self.api_key)
            self.config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
            self._initialized = True
            logger.info(f"Gemini client initialized (model: {self.model_name})")
        except ImportError as e:
            logger.warning(f"google-genai not installed: {e}. Using fallback parser")
        except Exception as e:
            logger.error(f"Gemini initialization failed: {type(e).__name__} - {str(e)[:100]}")
    
    def parse_intent(self, user_input: str, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        """
        Converts natural language into a structured Intent JSON.
        
        Args:
            user_input: Natural language intent (e.g., "stake 1000 bdag")
            max_retries: Retry attempts for parsing errors
            
        Returns:
            Dict with intent_type, asset, amount, etc. or None if parsing fails.
        """
        logger.info(f"[AI] Parsing intent: '{user_input}'")
        
        if not self._initialized:
            logger.warning("[AI] Gemini client not available, using fallback")
            return self._fallback_parse(user_input)
        
        attempt = 0
        last_error = None
        
        while attempt <= max_retries:
            try:
                if attempt == 0:
                    prompt = user_input
                else:
                    prompt = f"""
Previous attempt failed: {last_error}
Please return valid JSON matching the schema.
Original request: {user_input}
"""
                
                logger.info(f"[AI] Calling model: {self.model_name} (attempt {attempt + 1})")
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[INTENT_PARSER_SYSTEM_INSTRUCTION, prompt],
                    config=self.config
                )
                
                # Parse the JSON response
                response_text = response.text.strip()
                logger.debug(f"[AI] Raw response: {response_text[:200]}")
                
                parsed_data = json.loads(response_text)
                
                logger.info(f"[AI] Successfully parsed intent: {parsed_data.get('intent_type')}")
                logger.debug(f"[AI] Asset: {parsed_data.get('asset')}, Amount: {parsed_data.get('amount')}")
                if parsed_data.get('to_asset'):
                    logger.debug(f"[AI] To Asset: {parsed_data.get('to_asset')}")
                if parsed_data.get('target'):
                    logger.debug(f"[AI] Target: {parsed_data.get('target')}")
                
                return self._normalize_output(parsed_data)
                
            except json.JSONDecodeError as e:
                last_error = f"JSON decode error: {str(e)}"
                logger.warning(f"[AI] {last_error}, retrying")
                attempt += 1
                
            except Exception as e:
                logger.error(f"[AI] Gemini error: {str(e)}")
                logger.info("[AI] Falling back to regex parser")
                return self._fallback_parse(user_input)
        
        # Max retries exceeded
        logger.warning("[AI] Max retries exceeded, using fallback")
        return self._fallback_parse(user_input)
    
    def _normalize_output(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize AI output to match expected schema.
        """
        result = {
            "intent_type": parsed_data.get("intent_type", "stake"),
            "asset": str(parsed_data.get("asset", "BDAG")).upper(),
            "amount": float(parsed_data.get("amount", 0)),
            "amount_unit": "token",
        }
        
        # Add optional fields if present
        if parsed_data.get("to_asset"):
            result["to_asset"] = str(parsed_data["to_asset"]).upper()
            
        if parsed_data.get("target"):
            result["target"] = parsed_data["target"]
        else:
            # Default targets based on intent type
            if result["intent_type"] in ["stake", "lend"]:
                result["target"] = "highest_risk_adjusted_apr"
            elif result["intent_type"] == "swap":
                result["target"] = "best_rate"
                
        if parsed_data.get("recipient"):
            result["recipient"] = parsed_data["recipient"]
            
        return result
    
    def _extract_amount(self, text: str) -> float:
        """
        Extracts amount from text with support for:
        - Plain numbers: 5000
        - K notation: 5k, 5K -> 5000
        - M notation: 1m, 1M -> 1000000
        """
        text = text.lower()
        
        # Match patterns like "5k", "10K"
        k_match = re.search(r'(\d+(?:\.\d+)?)\s*k\b', text)
        if k_match:
            return float(k_match.group(1)) * 1000
        
        # Match patterns like "1m", "2M"
        m_match = re.search(r'(\d+(?:\.\d+)?)\s*m\b', text)
        if m_match:
            return float(m_match.group(1)) * 1000000
        
        # Plain numbers
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        if numbers:
            return float(numbers[0])
        
        return 0.0
    
    def _fallback_parse(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Enhanced keyword-based fallback parser when AI is unavailable.
        """
        logger.info("[AI-PARSE] Using regex fallback parser")
        text = user_input.lower().strip()
        
        # Pattern: stake [amount] [asset]
        stake_match = re.search(r'stake\s+(\d+(?:\.\d+)?)\s*k?\s*(\w+)?', text)
        if stake_match or 'stake' in text or 'yield' in text or 'apy' in text or 'farm' in text or 'earn' in text:
            amount = self._extract_amount(text) if self._extract_amount(text) > 0 else 1000.0
            
            # Try to extract asset
            asset_match = re.search(r'(\d+(?:\.\d+)?)\s*k?\s*(\w+)', text)
            if asset_match and asset_match.group(2):
                asset = asset_match.group(2).upper()
                if asset in ['K', 'M']:  # Skip if it's just a multiplier
                    asset = "BDAG"
            else:
                asset = "BDAG"
            
            return {
                "intent_type": "stake",
                "asset": asset,
                "amount": amount,
                "amount_unit": "token",
                "target": "highest_risk_adjusted_apr",
            }
        
        # Pattern: swap [amount] [from] to [to]
        swap_match = re.search(r'swap\s+(\d+(?:\.\d+)?)\s*k?\s*(\w+)\s+(?:to|for|into)\s+(\w+)', text)
        if swap_match or 'swap' in text or 'convert' in text or 'exchange' in text:
            if swap_match:
                amount = self._extract_amount(text)
                from_asset = swap_match.group(2).upper()
                to_asset = swap_match.group(3).upper()
            else:
                amount = self._extract_amount(text) if self._extract_amount(text) > 0 else 100.0
                from_asset = "BDAG"
                to_asset = "USDT"
            
            return {
                "intent_type": "swap",
                "asset": from_asset,
                "to_asset": to_asset,
                "amount": amount,
                "amount_unit": "token",
                "target": "best_rate",
            }
        
        # Pattern: lend [amount] [asset]
        lend_match = re.search(r'(?:lend|supply|deposit)\s+(\d+(?:\.\d+)?)\s*k?\s*(\w+)?', text)
        if lend_match or 'lend' in text or 'supply' in text:
            amount = self._extract_amount(text) if self._extract_amount(text) > 0 else 1000.0
            asset_match = re.search(r'(\d+(?:\.\d+)?)\s*k?\s*(\w+)', text)
            asset = asset_match.group(2).upper() if asset_match and asset_match.group(2) else "BDAG"
            
            return {
                "intent_type": "lend",
                "asset": asset,
                "amount": amount,
                "amount_unit": "token",
                "target": "highest_supply_apy",
            }
        
        # Pattern: unstake/withdraw [amount] [asset]
        unstake_match = re.search(r'(?:unstake|withdraw)\s+(\d+(?:\.\d+)?)\s*k?\s*(\w+)?', text)
        if unstake_match or 'unstake' in text or 'withdraw' in text:
            amount = self._extract_amount(text) if self._extract_amount(text) > 0 else -1  # -1 = all
            asset_match = re.search(r'(\d+(?:\.\d+)?)\s*k?\s*(\w+)', text)
            asset = asset_match.group(2).upper() if asset_match and asset_match.group(2) else "BDAG"
            
            return {
                "intent_type": "unstake",
                "asset": asset,
                "amount": amount,
                "amount_unit": "token",
            }
        
        # Pattern: claim rewards
        if 'claim' in text or 'harvest' in text or 'collect' in text:
            return {
                "intent_type": "claim_rewards",
                "asset": "BDAG",
                "amount": -1,  # All available rewards
                "amount_unit": "token",
            }
        
        # Could not parse
        logger.warning(f"[AI] Could not parse: '{user_input}'")
        return None


class AIService:
    """
    Static wrapper for backward compatibility.
    Delegates to the singleton _AIServiceImpl instance.
    """
    
    @staticmethod
    def parse_intent(user_input: str, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        """Parse user intent using Gemini AI."""
        return get_ai_service().parse_intent(user_input, max_retries)
    
    @staticmethod
    def is_initialized() -> bool:
        """Check if Gemini client is initialized."""
        return get_ai_service()._initialized


# Singleton instance for easy importing
ai_service = get_ai_service()
