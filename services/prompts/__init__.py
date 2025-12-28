# services/prompts/__init__.py
"""
Prompt templates for AI services.
"""

from .intent_parser_prompt import (
    INTENT_PARSER_SYSTEM_INSTRUCTION,
    INTENT_SCHEMA,
)

__all__ = [
    'INTENT_PARSER_SYSTEM_INSTRUCTION',
    'INTENT_SCHEMA',
]
