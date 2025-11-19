# intentlink_project/api.py
from ninja import NinjaAPI
from api_v1.api import router as v1_router

api = NinjaAPI(
    title="IntentLink API",
    version="1.0.0",
    description="API for parsing, planning, and executing DeFi intents securely.",
)

api.add_router("/v1/", v1_router, tags=["v1"])