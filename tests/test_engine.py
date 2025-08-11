"""
Unit tests for the Prompt Engine component.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.engine import PromptEngine
from src.models import PromptRequest, PromptType


class TestPromptEngine:
    
    @pytest.fixture
    def engine(self):
        """Create engine instance with test templates."""
        return PromptEngine("tests/fixtures/test_templates")
    
    def test_generate_deepseek_chat_prompt(self, engine):
        """Test DeepSeek-R1 chat prompt generation."""
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="Hello world",
            prompt_type=PromptType.CHAT
        )
        
        response = engine.generate_prompt(request)
        
        assert response.formatted_prompt
        assert "<|im_start|>" in response.formatted_prompt
        assert "<|im_start|>user\nHello world<|im_end|>" in response.formatted_prompt
        assert response.model_id == "deepseek-r1-0528-qwen3-8b"
        assert response.token_estimate > 0
        assert "metadata" in response.model_dump()
    
    def test_generate_gemma_reasoning_prompt(self, engine):
        """Test Gemma reasoning prompt generation."""
        request = PromptRequest(
            model_id="gemma-2-9b-it",
            user_input="Solve: 2x + 5 = 15",
            prompt_type=PromptType.REASONING
        )
        
        response = engine.generate_prompt(request)
        
        assert response.formatted_prompt
        assert "<start_of_turn>user" in response.formatted_prompt
        assert "<start_of_turn>model" in response.formatted_prompt
        assert "step by step" in response.formatted_prompt
    
    def test_generate_llama3_chat_prompt(self, engine):
        """Test Llama3 chat prompt generation."""
        request = PromptRequest(
            model_id="llama3-8b-instruct",
            user_input="What is AI?",
            prompt_type=PromptType.CHAT
        )
        
        response = engine.generate_prompt(request)
        
        assert response.formatted_prompt
        assert "<|start_header_id|>" in response.formatted_prompt
        assert "<|eot_id|>" in response.formatted_prompt
    
    def test_invalid_model(self, engine):
        """Test error handling for invalid model."""
        request = PromptRequest(
            model_id="invalid-model",
            user_input="Test"
        )
        
        with pytest.raises(ValueError, match="Unsupported model"):
            engine.generate_prompt(request)
    
    def test_empty_user_input(self, engine):
        """Test error handling for empty user input."""
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input=""
        )
        
        with pytest.raises(ValueError, match="User input cannot be empty"):
            engine.generate_prompt(request)
    
    def test_long_user_input(self, engine):
        """Test error handling for overly long user input."""
        long_input = "x" * 10001
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input=long_input
        )
        
        with pytest.raises(ValueError, match="User input too long"):
            engine.generate_prompt(request)
    
    def test_conversation_history(self, engine):
        """Test prompt generation with conversation history."""
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="Can you elaborate?",
            prompt_type=PromptType.CHAT,
            conversation_history=[
                {
                    "user": "What is machine learning?",
                    "assistant": "Machine learning is a subset of AI..."
                }
            ]
        )
        
        response = engine.generate_prompt(request)
        
        assert response.formatted_prompt
        assert "What is machine learning?" in response.formatted_prompt
        assert "Machine learning is a subset of AI" in response.formatted_prompt
        assert response.metadata["has_conversation"] is True
    
    def test_tenant_customization(self, engine):
        """Test tenant-specific template customization."""
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="Health question",
            prompt_type=PromptType.CHAT,
            tenant_id="healthcare"
        )
        
        response = engine.generate_prompt(request)
        
        assert response.formatted_prompt
        assert response.metadata["tenant_id"] == "healthcare"
    
    def test_context_variables(self, engine):
        """Test context variable substitution."""
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="Hello",
            prompt_type=PromptType.CHAT,
            context={
                "user_language": "Vietnamese",
                "expertise_level": "beginner"
            }
        )
        
        response = engine.generate_prompt(request)
        
        assert response.formatted_prompt
        assert "Vietnamese" in response.formatted_prompt or "beginner" in response.formatted_prompt
    
    def test_get_supported_models(self, engine):
        """Test getting supported models list."""
        models = engine.get_supported_models()
        
        assert isinstance(models, dict)
        assert len(models) > 0
        assert "deepseek-r1-0528-qwen3-8b" in models
        assert "gemma-2-9b-it" in models
        assert "llama3-8b-instruct" in models
    
    def test_engine_stats(self, engine):
        """Test engine statistics."""
        stats = engine.get_engine_stats()
        
        assert "status" in stats
        assert "version" in stats
        assert "templates_loaded" in stats
        assert "models_supported" in stats
        assert stats["status"] == "healthy"
    
    def test_template_validation(self, engine):
        """Test template composition validation."""
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="Test",
            prompt_type=PromptType.CHAT
        )
        
        validation = engine.validate_template_composition(request)
        
        assert "valid" in validation
        assert "template_count" in validation
        assert "categories" in validation
    
    def test_template_hierarchy(self, engine):
        """Test template hierarchy information."""
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="Test",
            prompt_type=PromptType.CHAT
        )
        
        hierarchy = engine.get_template_hierarchy(request)
        
        assert "prompt_type" in hierarchy
        assert "model_family" in hierarchy
        assert "templates" in hierarchy
        assert len(hierarchy["templates"]) > 0
    
    def test_test_prompt_generation(self, engine):
        """Test the test prompt generation method."""
        result = engine.test_prompt_generation(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="Test message",
            prompt_type=PromptType.CHAT
        )
        
        assert "success" in result
        assert result["success"] is True
        assert "model_id" in result
        assert "token_estimate" in result
