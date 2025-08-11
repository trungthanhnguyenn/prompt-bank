"""
Pydantic models for the Multi-Model Prompt Engine.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class PromptType(Enum):
    """Supported prompt types."""
    CHAT = "chat"
    REASONING = "reasoning"
    INSTRUCTION = "instruction"


class TemplateContent(BaseModel):
    """Content structure for templates."""
    instruction: str
    rules: List[str] = []


class Template(BaseModel):
    """Template model for JSON-based prompt templates."""
    model_config = ConfigDict(protected_namespaces=())
    
    id: str
    name: str
    category: str
    priority: int
    content: TemplateContent
    variables: List[str] = []
    model_overrides: Dict[str, Dict] = {}
    immutable: bool = False
    applies_to: List[str] = []

    @field_validator('category')
    def validate_category(cls, v):
        valid_categories = ["system", "safety", "instruction", "constraint", "persona"]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of {valid_categories}")
        return v

    @field_validator('priority')
    def validate_priority(cls, v):
        if not 0 <= v <= 999:
            raise ValueError("Priority must be between 0 and 999")
        return v


class ModelConfig(BaseModel):
    """Model configuration for different LLM families."""
    model_config = ConfigDict(protected_namespaces=())
    
    model_id: str
    family: str
    display_name: str
    tokens: Dict[str, str]
    limits: Dict[str, int]
    inference: Dict[str, Any]
    capabilities: List[str]

    @field_validator('family')
    def validate_family(cls, v):
        valid_families = ["deepseek-r1", "gemma", "llama3"]
        if v not in valid_families:
            raise ValueError(f"Model family must be one of {valid_families}")
        return v


class TenantConfig(BaseModel):
    """Tenant configuration for organization-specific settings."""
    tenant_id: str
    name: str
    domain: str
    compliance: List[str] = []


class PromptRequest(BaseModel):
    """Request model for prompt generation."""
    model_config = ConfigDict(protected_namespaces=())

    model_id: str = Field(..., pattern=r'^[a-z0-9\-]+$')
    user_input: str = Field(...)
    prompt_type: PromptType = PromptType.CHAT
    tenant_id: Optional[str] = Field(None, pattern=r'^[a-z0-9_\-]+$')
    conversation_history: List[Dict] = Field(default=[], max_length=50)
    context: Dict[str, Any] = Field(default={})

    @field_validator('user_input')
    def validate_user_input(cls, v):
        # Remove potentially harmful content
        if re.search(r'<script|javascript:|vbscript:', v, re.IGNORECASE):
            raise ValueError("Potentially harmful content detected")
        return v.strip()

    @field_validator('context')
    def validate_context(cls, v):
        # Limit context size
        if len(str(v)) > 5000:
            raise ValueError("Context too large")
        return v

    @field_validator('conversation_history')
    def validate_conversation_history(cls, v):
        # Validate conversation history format
        for turn in v:
            if not isinstance(turn, dict):
                raise ValueError("Conversation history must contain dictionaries")
            if 'user' not in turn or 'assistant' not in turn:
                raise ValueError("Conversation history turns must have 'user' and 'assistant' keys")
        return v


class PromptResponse(BaseModel):
    """Response model for prompt generation."""
    model_config = ConfigDict(protected_namespaces=())

    formatted_prompt: str
    model_id: str
    token_estimate: int
    inference_config: Dict[str, Any]
    metadata: Dict[str, Any]

    @field_validator('token_estimate')
    def validate_token_estimate(cls, v):
        if v < 0:
            raise ValueError("Token estimate cannot be negative")
        return v


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    models_loaded: int
    templates_loaded: int
    timestamp: Optional[str] = None
    error: Optional[str] = None


class ModelsResponse(BaseModel):
    """Models list response model."""
    models: Dict[str, str]


class ReloadResponse(BaseModel):
    """Template reload response model."""
    status: str
    timestamp: str
    message: Optional[str] = None
