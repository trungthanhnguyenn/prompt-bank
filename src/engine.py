"""
Main Prompt Engine for the Multi-Model Prompt Engine.

Main orchestration of prompt generation, request validation and routing,
response formatting, and error handling.
"""

import logging
import time
from typing import Dict, Optional
from datetime import datetime

from .models import PromptRequest, PromptResponse, PromptType
from .loader import TemplateLoader
from .composer import TemplateComposer
from .utils import estimate_tokens, format_timestamp


class PromptEngine:
    """Main prompt generation engine with multi-model support."""
    
    def __init__(self, templates_dir: str = "templates"):
        self.logger = logging.getLogger(__name__)
        self.templates_dir = templates_dir
        
        # Initialize components
        self.loader = TemplateLoader(templates_dir)
        self.composer = TemplateComposer(self.loader)
        
        self.logger.info("Prompt Engine initialized successfully")
    
    def generate_prompt(self, request: PromptRequest) -> PromptResponse:
        """Generate formatted prompt for the request."""
        
        start_time = time.time()
        self.logger.info(f"Generating prompt for model {request.model_id}, type {request.prompt_type.value}")
        
        try:
            # Validate request
            self._validate_request(request)
            
            # Get model configuration
            model_config = self.loader.get_model_config(request.model_id)
            if not model_config:
                raise ValueError(f"Unsupported model: {request.model_id}")
            
            # Compose system prompt from templates
            system_prompt = self.composer.compose_system_prompt(request, model_config.family)
            
            # Format prompt using model-specific Jinja2 template
            formatted_prompt = self._format_prompt(
                model_config=model_config,
                system_prompt=system_prompt,
                request=request
            )
            
            # Estimate tokens
            token_estimate = estimate_tokens(formatted_prompt, model_config.family)
            
            # Prepare response
            response = PromptResponse(
                formatted_prompt=formatted_prompt,
                model_id=request.model_id,
                token_estimate=token_estimate,
                inference_config=model_config.inference,
                metadata={
                    "prompt_type": request.prompt_type.value,
                    "model_family": model_config.family,
                    "tenant_id": request.tenant_id,
                    "has_conversation": len(request.conversation_history) > 0,
                    "system_prompt_length": len(system_prompt),
                    "context_variables": list(request.context.keys()),
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    "timestamp": format_timestamp()
                }
            )
            
            self.logger.info(f"Prompt generated successfully: {token_estimate} tokens, {len(formatted_prompt)} chars")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to generate prompt: {e}")
            raise
    
    def _validate_request(self, request: PromptRequest):
        """Validate prompt request."""
        if not request.user_input or not request.user_input.strip():
            raise ValueError("User input cannot be empty")
        
        if len(request.user_input) > 10000:  # 10k character limit
            raise ValueError("User input too long (max 10,000 characters)")
        
        # Validate conversation history
        for i, turn in enumerate(request.conversation_history):
            if not isinstance(turn, dict):
                raise ValueError(f"Conversation history turn {i} must be a dictionary")
            if 'user' not in turn or 'assistant' not in turn:
                raise ValueError(f"Conversation history turn {i} must have 'user' and 'assistant' keys")
            if len(str(turn.get('user', ''))) > 5000 or len(str(turn.get('assistant', ''))) > 5000:
                raise ValueError(f"Conversation history turn {i} content too long")
    
    def _format_prompt(self, model_config, system_prompt: str, request: PromptRequest) -> str:
        """Format prompt using model-specific Jinja2 template."""
        
        # Get appropriate template based on prompt type
        template_name = request.prompt_type.value
        
        try:
            jinja_template = self.loader.get_jinja_template(model_config.family, template_name)
        except FileNotFoundError:
            # Fallback to chat template if specific template not found
            self.logger.warning(f"Template {template_name} not found for {model_config.family}, falling back to chat")
            jinja_template = self.loader.get_jinja_template(model_config.family, "chat")
        
        # Prepare template variables
        template_vars = {
            "tokens": model_config.tokens,
            "system_prompt": system_prompt,
            "user_input": request.user_input,
            "conversation_history": request.conversation_history,
            **request.context
        }
        
        # Render template
        try:
            rendered = jinja_template.render(**template_vars)
        except Exception as e:
            self.logger.error(f"Failed to render template: {e}")
            raise RuntimeError(f"Template rendering failed: {e}")
        
        # Clean up formatting
        return rendered.strip()
    
    def get_supported_models(self) -> Dict[str, str]:
        """Get list of supported models."""
        return self.loader.get_supported_models()
    
    def reload_templates(self):
        """Reload all templates (useful for development)."""
        self.logger.info("Reloading templates...")
        self.loader.reload()
        self.logger.info("Templates reloaded successfully")
    
    def get_engine_stats(self) -> Dict:
        """Get engine statistics and health information."""
        try:
            template_stats = self.loader.get_template_stats()
            
            return {
                "status": "healthy",
                "version": "1.0.0",
                "templates_loaded": template_stats["global_templates"],
                "models_supported": len(self.get_supported_models()),
                "tenants_configured": template_stats["tenant_configs"],
                "cache_hash": template_stats["cache_hash"],
                "timestamp": format_timestamp()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": format_timestamp()
            }
    
    def validate_template_composition(self, request: PromptRequest) -> Dict:
        """Validate template composition for a request."""
        model_config = self.loader.get_model_config(request.model_id)
        if not model_config:
            raise ValueError(f"Unsupported model: {request.model_id}")
        
        return self.composer.validate_template_composition(request, model_config.family)
    
    def get_template_hierarchy(self, request: PromptRequest) -> Dict:
        """Get template hierarchy information for debugging."""
        model_config = self.loader.get_model_config(request.model_id)
        if not model_config:
            raise ValueError(f"Unsupported model: {request.model_id}")
        
        return self.composer.get_template_hierarchy(request, model_config.family)
    
    def backup_templates(self, backup_dir: str = "backups"):
        """Create backup of all templates."""
        return self.loader.backup_templates(backup_dir)
    
    def test_prompt_generation(self, model_id: str, user_input: str, 
                              prompt_type: PromptType = PromptType.CHAT,
                              tenant_id: Optional[str] = None) -> Dict:
        """Test prompt generation with given parameters."""
        
        try:
            request = PromptRequest(
                model_id=model_id,
                user_input=user_input,
                prompt_type=prompt_type,
                tenant_id=tenant_id
            )
            
            response = self.generate_prompt(request)
            
            return {
                "success": True,
                "model_id": response.model_id,
                "token_estimate": response.token_estimate,
                "prompt_length": len(response.formatted_prompt),
                "metadata": response.metadata
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
