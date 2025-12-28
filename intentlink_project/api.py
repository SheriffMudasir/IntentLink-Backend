# intentlink_project/api.py
"""
Main API configuration using Django Ninja.

Wave 3: Added v2 router for dashboard/portfolio endpoints.
"""
from ninja import NinjaAPI
from api_v1.api import router as v1_router
from api_v1.api_v2 import router as v2_router

api = NinjaAPI(
    title="IntentLink API",
    version="2.0.0",
    description="""
    IntentLink - The Gasless AI Trading Wallet
    
    Turn your words into profitable DeFi transactions.
    No friction, no gas management, no complexity.
    
    API Versions:
    - v1: Core intent parsing, planning, and execution
    - v2: Dashboard, portfolio, quick actions, and prices
    """,
)

# Core intent execution endpoints
api.add_router("/v1/", v1_router, tags=["v1 - Intent Execution"])

# Wave 3: Dashboard and UX endpoints
api.add_router("/v2/", v2_router, tags=["v2 - Dashboard & UX"])