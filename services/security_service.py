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


class SecurityReport(Schema):
    """Security validation report from GoPlus API."""
    is_safe: bool
    safety_score: int
    warnings: List[str]


class SecurityService:
    """Security validation service using GoPlus API."""
    GOPLUS_API_BASE = "https://api.gopluslabs.io/api/v1"
    
    def __init__(self, api_key: str, api_secret: str, rpc_url: str, redis_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.token_cache_key = "goplus:access_token"
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}")
            raise

        self.http_client = httpx.Client(timeout=30.0)

    def _get_access_token(self) -> str:
        """Fetch GoPlus access token from REST API, caching in Redis."""
        cached_token = self.redis_client.get(self.token_cache_key)
        if cached_token:
            return cached_token

        if not self.api_key or not self.api_secret:
            raise Exception("GoPlus API credentials not configured")

        logger.info("Fetching new GoPlus access token...")
        try:
            auth_payloads = [
                {"app_key": self.api_key, "app_secret": self.api_secret},
                {"appKey": self.api_key, "appSecret": self.api_secret},
                {"api_key": self.api_key, "api_secret": self.api_secret},
            ]
            
            last_error = None
            for payload in auth_payloads:
                try:
                    response = self.http_client.post(
                        f"{self.GOPLUS_API_BASE}/token",
                        json=payload
                    )
                    response.raise_for_status()
                    token_data = response.json()
                    
                    if token_data.get("code") and token_data.get("code") != 1:
                        error_msg = token_data.get("message", "Unknown error")
                        last_error = Exception(f"GoPlus API error: {error_msg}")
                        continue
                    
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
                        expires_in = token_data.get("expires_in", 3600)
                        if isinstance(result, dict):
                            expires_in = result.get("expires_in", expires_in)
                        cache_ttl = max(60, int(expires_in) - 60)
                        self.redis_client.set(self.token_cache_key, access_token, ex=cache_ttl)
                        logger.info(f"Access token obtained and cached for {cache_ttl}s")
                        return access_token
                    
                    last_error = Exception(f"Could not extract access token from response: {token_data}")
                    
                except httpx.HTTPStatusError as e:
                    last_error = e
                    continue
            
            if last_error:
                raise last_error
            raise Exception("All authentication attempts failed")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting access token: {e.response.status_code}")
            raise Exception(f"Failed to get GoPlus access token: {e}")
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            raise

    def _find_deployer_address(self, chain_id: str, contract_address: str) -> Optional[str]:
        """Mock deployer address lookup for hackathon demo."""
        return "0xc8b759860149542a98a3eb57c14aadf59d6d89b9"

    def run_security_check(self, chain_id: str, contract_address: str) -> SecurityReport:
        """Execute two-step security check using GoPlus REST API."""
        logger.info(f"Security check for {contract_address} on chain {chain_id}")
        
        warnings = []
        is_honeypot = False
        is_malicious_creator = False

        access_token = None
        
        if self.api_key and self.api_secret:
            try:
                access_token = self._get_access_token()
            except Exception as e:
                logger.warning(f"Failed to get access token (will try public API): {str(e)}")
                access_token = None

        logger.info("Running Token Security API check...")
        try:
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            response = self.http_client.get(
                f"{self.GOPLUS_API_BASE}/token_security/{chain_id}",
                params={"contract_addresses": contract_address},
                headers=headers
            )
            response.raise_for_status()
            token_report = response.json()
            result = token_report.get("result", {}) or token_report.get("data", {}).get("result", {})
            
            result = (result or {}).get(contract_address.lower()) or (result or {}).get(contract_address)
            
            if result:
                honeypot_flag = str(result.get("is_honeypot"))
                open_source_flag = str(result.get("is_open_source"))
                
                if honeypot_flag in {"1", "true", "True"}:
                    is_honeypot = True
                    warnings.append("Honeypot detected by GoPlus.")
                    logger.warning("Honeypot detected")
                    
                if open_source_flag in {"0", "false", "False"}:
                    warnings.append("Contract source code is not verified.")
            else:
                warnings.append("Could not retrieve a token security report from GoPlus.")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling GoPlus Token Security API: {e.response.status_code}")
            warnings.append("Failed to perform token security check.")
        except Exception as e:
            logger.error(f"Error calling GoPlus Token Security API: {str(e)}")
            warnings.append("Failed to perform token security check.")

        logger.info("Running Malicious Address API check on deployer...")
        deployer_address = self._find_deployer_address(chain_id, contract_address)
        
        if deployer_address:
            try:
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
                result = address_report.get("result", {}) or address_report.get("data", {}).get("result", {})
                
                if result:
                    honeypot_related = str(result.get("honeypot_related_address"))
                    
                    if honeypot_related in {"1", "true", "True"}:
                        is_malicious_creator = True
                        warnings.append("Deployer address is related to honeypot activities.")
                        logger.warning("Malicious deployer detected")
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling GoPlus Address Security API: {e.response.status_code}")
                warnings.append("Failed to perform deployer address security check.")
            except Exception as e:
                logger.error(f"Error calling GoPlus Address Security API: {str(e)}")
                warnings.append("Failed to perform deployer address security check.")

        is_safe = not is_honeypot and not is_malicious_creator
        safety_score = 100 - (len(warnings) * 10) - (80 if is_honeypot else 0) - (50 if is_malicious_creator else 0)
        
        logger.info(f"Security check complete: safe={is_safe}, score={max(0, safety_score)}, warnings={len(warnings)}")

        return SecurityReport(is_safe=is_safe, safety_score=max(0, safety_score), warnings=warnings)


def _create_security_service():
    """Create SecurityService singleton instance."""
    api_key = getattr(settings, "GOPLUS_API_KEY", "") or ""
    api_secret = getattr(settings, "GOPLUS_API_SECRET", "") or ""
    rpc_url = getattr(settings, "BLOCKDAG_RPC_URL", "")
    redis_url = getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0")
    
    return SecurityService(api_key=api_key, api_secret=api_secret, rpc_url=rpc_url, redis_url=redis_url)


security_service = _create_security_service()
