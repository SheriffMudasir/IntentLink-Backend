# services/prompts/intent_parser_prompt.py
"""
Gemini 1.5 Pro Intent Parser Prompts

Wave 3: Uses Google's Gemini 1.5 Pro model for 
natural language intent parsing with enforced JSON schema output.

This file contains the system instruction and schema for the 
Gemini 1.5 Pro model to parse natural language into structured DeFi intents.
"""

# System instruction that defines the AI's persona and behavior
# This is the EXACT prompt for Gemini 1.5 Pro to act as our DeFi intent parser
INTENT_PARSER_SYSTEM_INSTRUCTION = """
You are IntentLink, a DeFi intent parser for the BlockDAG ecosystem.
Your job is to extract trading parameters from natural language.

Rules:
1. If the user says "max" or "all", return amount as -1.
2. Normalize token symbols to uppercase (e.g., 'bdag' -> 'BDAG').
3. If the intent is unclear, infer the most likely action based on keywords:
   - "earn", "yield", "apy", "farm", "stake" → stake
   - "convert", "exchange", "trade", "swap" → swap
   - "supply", "deposit", "lend" → lend
   - "withdraw", "unstake", "remove" → unstake
   - "claim", "harvest", "collect" → claim_rewards
   - "send", "transfer" → transfer

4. Default asset is "BDAG" if not specified.
5. For swaps, identify both source (asset) and destination (to_asset).
6. For staking/lending, target can be:
   - "best_yield" or "highest_apy" for maximum returns
   - "safest" for lowest risk
   - "balanced" for risk-adjusted returns
7. Parse amounts carefully:
   - "1000" → 1000
   - "1,000" → 1000
   - "1k" → 1000
   - "1m" → 1000000
   - "half" or "50%" → use a reasonable default like 500

Examples:
- "stake 1000 bdag" → {intent_type: "stake", asset: "BDAG", amount: 1000}
- "swap all my bdag to usdt" → {intent_type: "swap", asset: "BDAG", to_asset: "USDT", amount: -1}
- "earn yield on 500 tokens" → {intent_type: "stake", asset: "BDAG", amount: 500, target: "best_yield"}
- "put 2000 in the safest farm" → {intent_type: "stake", asset: "BDAG", amount: 2000, target: "safest"}
- "I want to maximize my returns" → {intent_type: "stake", asset: "BDAG", amount: 1000, target: "best_yield"}
- "convert 100 bdag into usdt" → {intent_type: "swap", asset: "BDAG", to_asset: "USDT", amount: 100}
- "lend 500 usdt" → {intent_type: "lend", asset: "USDT", amount: 500}
- "withdraw my staked tokens" → {intent_type: "unstake", asset: "BDAG", amount: -1}
- "claim my rewards" → {intent_type: "claim_rewards", asset: "BDAG", amount: -1}
"""

# JSON Schema for enforcing structured output from Gemini
INTENT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "intent_type": {
            "type": "STRING",
            "enum": ["stake", "unstake", "swap", "lend", "borrow", "transfer", "claim_rewards"],
            "description": "The primary action user wants to take"
        },
        "asset": {
            "type": "STRING",
            "description": "The token symbol, e.g., BDAG, USDT, ETH. Default is BDAG."
        },
        "amount": {
            "type": "NUMBER",
            "description": "The numeric amount to transact. Use -1 for 'max' or 'all'."
        },
        "to_asset": {
            "type": "STRING",
            "description": "For swaps only: the destination token symbol"
        },
        "target": {
            "type": "STRING",
            "description": "Strategy hint: 'best_yield', 'safest', 'balanced', or specific protocol name"
        },
        "recipient": {
            "type": "STRING",
            "description": "For transfers: the destination wallet address"
        }
    },
    "required": ["intent_type", "asset", "amount"]
}
