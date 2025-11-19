# services/security_service.py
import logging
import time
import traceback
from typing import List, Optional
import json

import redis
import httpx
from django.conf import settings
from ninja import Schema

logger = logging.getLogger(__name__)

# Configure detailed logging for security service
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# --- Schemas ---
class SecurityReport(Schema):
    is_safe: bool
    safety_score: int
    warnings: List[str]


# --- Main service using GoPlus REST API ---
class SecurityService:
    GOPLUS_API_BASE = "https://api.gopluslabs.io/api/v1"
    
    def __init__(self, api_key: str, api_secret: str, rpc_url: str, redis_url: str):
        logger.info("Initializing SecurityService...")
        logger.info(f"API Key present: {bool(api_key)}")
        logger.info(f"API Secret present: {bool(api_secret)}")
        logger.info(f"RPC URL: {rpc_url}")
        logger.info(f"Redis URL: {redis_url}")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.token_cache_key = "goplus:access_token"
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            logger.info("✓ Redis client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}")
            logger.error(traceback.format_exc())
            raise

        # HTTP client for API requests
        self.http_client = httpx.Client(timeout=30.0)
        logger.info("✓ HTTP client initialized")
        logger.info("SecurityService initialization complete")

    def _get_access_token(self) -> str:
        """
        Fetches a GoPlus access token from REST API, caching it in Redis.
        """
        # try cache first
        cached_token = self.redis_client.get(self.token_cache_key)
        if cached_token:
            logger.debug("GoPlus access token found in cache.")
            return cached_token

        if not self.api_key or not self.api_secret:
            raise Exception("GoPlus API credentials not configured")

        # Get token from GoPlus API
        logger.info("Fetching new GoPlus access token via REST API...")
        try:
            # Try multiple possible authentication formats
            auth_payloads = [
                {"app_key": self.api_key, "app_secret": self.api_secret},
                {"appKey": self.api_key, "appSecret": self.api_secret},
                {"api_key": self.api_key, "api_secret": self.api_secret},
            ]
            
            last_error = None
            for idx, payload in enumerate(auth_payloads, 1):
                logger.debug(f"Attempt {idx}: Trying auth payload format: {list(payload.keys())}")
                try:
                    response = self.http_client.post(
                        f"{self.GOPLUS_API_BASE}/token",
                        json=payload
                    )
                    response.raise_for_status()
                    token_data = response.json()
                    logger.debug(f"Token API response (attempt {idx}): {token_data}")
                    
                    # Check if we got an error response
                    if token_data.get("code") and token_data.get("code") != 1:
                        error_msg = token_data.get("message", "Unknown error")
                        logger.warning(f"Attempt {idx} failed with code {token_data.get('code')}: {error_msg}")
                        last_error = Exception(f"GoPlus API error: {error_msg}")
                        continue
                    
                    # Extract access token from response
                    access_token = None
                    if isinstance(token_data, dict):
                        result = token_data.get("result") or token_data.get("data")
                        if isinstance(result, dict):
                            access_token = result.get("access_token") or result.get("token")
                        else:
                            access_token = (
                                token_data.get("access_token") or 
                                token_data.get("token")
                            )
                    
                    if access_token:
                        # Cache the token
                        expires_in = token_data.get("expires_in", 3600)
                        if isinstance(result, dict):
                            expires_in = result.get("expires_in", expires_in)
                        cache_ttl = max(60, int(expires_in) - 60)
                        self.redis_client.set(self.token_cache_key, access_token, ex=cache_ttl)
                        logger.info(f"✓ Access token obtained on attempt {idx} and cached for {cache_ttl}s")
                        return access_token
                    
                    logger.warning(f"Attempt {idx}: No access token in response")
                    last_error = Exception(f"Could not extract access token from response: {token_data}")
                    
                except httpx.HTTPStatusError as e:
                    logger.warning(f"Attempt {idx} HTTP error: {e.response.status_code} - {e.response.text}")
                    last_error = e
                    continue
            
            # All attempts failed
            if last_error:
                raise last_error
            raise Exception("All authentication attempts failed")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting access token: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to get GoPlus access token: {e}")
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def _find_deployer_address(self, chain_id: str, contract_address: str) -> Optional[str]:
        """
        MOCKED for the hackathon. A real implementation is complex.
        """
        logger.warning(f"MOCKING deployer address for {contract_address}.")
        # Using the GoPlus API creator address for testing their malicious address endpoint
        # In a real scenario, this would be looked up (e.g. via RPC tx scans or block explorers).
        return "0xc8b759860149542a98a3eb57c14aadf59d6d89b9"

    def run_security_check(self, chain_id: str, contract_address: str) -> SecurityReport:
        """
        Orchestrates the 2-step security check using GoPlus REST API.
        Note: GoPlus public API may not require authentication for basic checks.
        """
        logger.info("=" * 70)
        logger.info(f"SECURITY CHECK START")
        logger.info(f"Chain ID: {chain_id}")
        logger.info(f"Contract: {contract_address}")
        logger.info("=" * 70)
        
        warnings = []
        is_honeypot = False
        is_malicious_creator = False

        # Try without authentication first (GoPlus public API)
        logger.info("Attempting security checks using public API (no auth required)...")
        access_token = None
        
        # Only try to get token if credentials are provided
        if self.api_key and self.api_secret:
            try:
                logger.debug("Attempting to get access token...")
                access_token = self._get_access_token()
                logger.info("✓ Access token obtained")
            except Exception as e:
                logger.warning(f"Failed to get access token (will try public API): {str(e)}")
                access_token = None

        # --- Check 1: Token Security API ---
        logger.info("Check 1: Running Token Security API check...")
        try:
            logger.debug(f"Calling token security API: chain_id={chain_id}, address={contract_address}")
            
            # Prepare headers
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
                logger.debug("Using authenticated request")
            else:
                logger.debug("Using public API (no authentication)")
            
            response = self.http_client.get(
                f"{self.GOPLUS_API_BASE}/token_security/{chain_id}",
                params={"contract_addresses": contract_address},
                headers=headers
            )
            response.raise_for_status()
            token_report = response.json()
            logger.debug(f"Token security response: {token_report}")
            # SDK often returns results keyed by lowercase address
            result = token_report.get("result", {}) or token_report.get("data", {}).get("result", {})
            logger.debug(f"Extracted result container: {result}")
            
            result = (result or {}).get(contract_address.lower()) or (result or {}).get(contract_address)
            logger.debug(f"Extracted address-specific result: {result}")
            
            if result:
                logger.info("Token security data retrieved successfully")
                honeypot_flag = str(result.get("is_honeypot"))
                open_source_flag = str(result.get("is_open_source"))
                
                logger.debug(f"is_honeypot flag: {honeypot_flag}")
                logger.debug(f"is_open_source flag: {open_source_flag}")
                
                if honeypot_flag in {"1", "true", "True"}:
                    is_honeypot = True
                    warnings.append("Honeypot detected by GoPlus.")
                    logger.warning("⚠ HONEYPOT DETECTED")
                else:
                    logger.info("✓ No honeypot detected")
                    
                if open_source_flag in {"0", "false", "False"}:
                    warnings.append("Contract source code is not verified.")
                    logger.warning("⚠ Contract source not verified")
                else:
                    logger.info("✓ Contract source verified")
            else:
                warnings.append("Could not retrieve a token security report from GoPlus.")
                logger.warning("No token security result data")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling GoPlus Token Security API: {e.response.status_code} - {e.response.text}")
            warnings.append("Failed to perform token security check.")
        except Exception as e:
            logger.error(f"Error calling GoPlus Token Security API: {str(e)}")
            logger.error(traceback.format_exc())
            warnings.append("Failed to perform token security check.")

        # --- Check 2: Malicious Address API (on deployer) ---
        logger.info("Check 2: Running Malicious Address API check on deployer...")
        deployer_address = self._find_deployer_address(chain_id, contract_address)
        logger.info(f"Deployer address: {deployer_address}")
        
        if deployer_address:
            try:
                logger.debug(f"Calling address security API: address={deployer_address}")
                
                # Prepare headers
                headers = {}
                if access_token:
                    headers["Authorization"] = f"Bearer {access_token}"
                
                response = self.http_client.get(
                    f"{self.GOPLUS_API_BASE}/address_security/{deployer_address}",
                    params={"chain_id": chain_id},
                    headers=headers
                )
                response.raise_for_status()
                address_report = response.json()
                logger.debug(f"Address security response: {address_report}")
                result = address_report.get("result", {}) or address_report.get("data", {}).get("result", {})
                logger.debug(f"Address security result: {result}")
                
                if result:
                    honeypot_related = str(result.get("honeypot_related_address"))
                    logger.debug(f"honeypot_related_address flag: {honeypot_related}")
                    
                    if honeypot_related in {"1", "true", "True"}:
                        is_malicious_creator = True
                        warnings.append("Deployer address is related to honeypot activities.")
                        logger.warning("⚠ MALICIOUS DEPLOYER DETECTED")
                    else:
                        logger.info("✓ Deployer address appears clean")
                else:
                    logger.warning("No address security result data")
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling GoPlus Address Security API: {e.response.status_code} - {e.response.text}")
                warnings.append("Failed to perform deployer address security check.")
            except Exception as e:
                logger.error(f"Error calling GoPlus Address Security API: {str(e)}")
                logger.error(traceback.format_exc())
                warnings.append("Failed to perform deployer address security check.")
        else:
            logger.warning("No deployer address found, skipping deployer check")

        # --- Aggregate Results ---
        logger.info("=" * 70)
        logger.info("SECURITY CHECK RESULTS:")
        logger.info(f"Is Honeypot: {is_honeypot}")
        logger.info(f"Is Malicious Creator: {is_malicious_creator}")
        logger.info(f"Warnings count: {len(warnings)}")
        
        is_safe = not is_honeypot and not is_malicious_creator
        safety_score = 100 - (len(warnings) * 10) - (80 if is_honeypot else 0) - (50 if is_malicious_creator else 0)
        
        logger.info(f"Is Safe: {is_safe}")
        logger.info(f"Safety Score: {max(0, safety_score)}")
        logger.info(f"Warnings: {warnings}")
        logger.info("=" * 70)

        return SecurityReport(is_safe=is_safe, safety_score=max(0, safety_score), warnings=warnings)


# --- Dev-friendly fallback singleton creation ---
def _create_security_service():
    logger.info("=" * 70)
    logger.info("Creating SecurityService singleton...")
    
    # If GOPLUS credentials are missing in env, create service with empty creds (dev fallback)
    api_key = getattr(settings, "GOPLUS_API_KEY", "") or ""
    api_secret = getattr(settings, "GOPLUS_API_SECRET", "") or ""
    rpc_url = getattr(settings, "BLOCKDAG_RPC_URL", "")
    redis_url = getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0")
    
    logger.info(f"Configuration loaded from Django settings:")
    logger.info(f"  API Key: {api_key[:8] + '...' if api_key else '(NOT SET)'}")
    logger.info(f"  API Key length: {len(api_key)}")
    logger.info(f"  API Secret present: {bool(api_secret)}")
    logger.info(f"  API Secret length: {len(api_secret)}")
    logger.info(f"  RPC URL: {rpc_url if rpc_url else '(not set)'}")
    logger.info(f"  Redis URL: {redis_url}")
    logger.info("=" * 70)
    
    return SecurityService(api_key=api_key, api_secret=api_secret, rpc_url=rpc_url, redis_url=redis_url)


logger.info("Initializing security_service singleton...")
security_service = _create_security_service()
logger.info("✓ security_service singleton created")
