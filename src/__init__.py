"""
Multi-Model Prompt Engine

A pure Python prompt generation engine supporting multiple LLM formats.
"""

__version__ = "1.0.0"
__author__ = "Prompt Engine Team"
__email__ = "team@promptengine.com"

from .engine import PromptEngine
from .models import PromptRequest, PromptResponse, PromptType

__all__ = [
    "PromptEngine",
    "PromptRequest", 
    "PromptResponse",
    "PromptType"
]
