#!/usr/bin/env python3
"""
Demo script for Multi-Model Prompt Engine.

This script demonstrates the core functionality of the prompt engine
with various models and prompt types.
"""

import json
from src.engine import PromptEngine
from src.models import PromptRequest, PromptType


def demo_basic_prompt_generation():
    """Demo basic prompt generation for different models."""
    
    print("🚀 Multi-Model Prompt Engine Demo")
    print("=" * 50)
    
    # Initialize engine
    engine = PromptEngine()
    
    # Test cases
    test_cases = [
        {
            "name": "DeepSeek-R1 Chat",
            "model_id": "deepseek-r1-0528-qwen3-8b",
            "user_input": "Hello, how are you?",
            "prompt_type": PromptType.CHAT
        },
        {
            "name": "Gemma Reasoning",
            "model_id": "gemma-2-9b-it",
            "user_input": "Solve: 2x + 5 = 15",
            "prompt_type": PromptType.REASONING
        },
        {
            "name": "Llama3 Chat",
            "model_id": "llama3-8b-instruct",
            "user_input": "What is artificial intelligence?",
            "prompt_type": PromptType.CHAT
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📝 {test_case['name']}")
        print("-" * 30)
        
        try:
            request = PromptRequest(
                model_id=test_case["model_id"],
                user_input=test_case["user_input"],
                prompt_type=test_case["prompt_type"]
            )
            
            response = engine.generate_prompt(request)
            
            print(f"✅ Success!")
            print(f"📊 Tokens: {response.token_estimate}")
            print(f"📏 Length: {len(response.formatted_prompt)} chars")
            print(f"🔧 Model: {response.model_id}")
            print(f"📋 Prompt Type: {response.metadata['prompt_type']}")
            
            # Show first 200 characters of prompt
            preview = response.formatted_prompt[:200]
            if len(response.formatted_prompt) > 200:
                preview += "..."
            print(f"📄 Preview: {preview}")
            
        except Exception as e:
            print(f"❌ Error: {e}")


def demo_tenant_customization():
    """Demo tenant-specific template customization."""
    
    print("\n🏢 Tenant Customization Demo")
    print("=" * 50)
    
    engine = PromptEngine()
    
    # Test with healthcare tenant
    print("\n🏥 Healthcare Tenant")
    print("-" * 20)
    
    try:
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="What are the symptoms of diabetes?",
            prompt_type=PromptType.CHAT,
            tenant_id="healthcare"
        )
        
        response = engine.generate_prompt(request)
        
        print(f"✅ Success!")
        print(f"📊 Tokens: {response.token_estimate}")
        print(f"🏢 Tenant: {response.metadata['tenant_id']}")
        
        # Show system prompt to see healthcare-specific content
        if "system_prompt_length" in response.metadata:
            print(f"📋 System prompt length: {response.metadata['system_prompt_length']} chars")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test with finance tenant
    print("\n💰 Finance Tenant")
    print("-" * 20)
    
    try:
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="What is compound interest?",
            prompt_type=PromptType.CHAT,
            tenant_id="finance"
        )
        
        response = engine.generate_prompt(request)
        
        print(f"✅ Success!")
        print(f"📊 Tokens: {response.token_estimate}")
        print(f"🏢 Tenant: {response.metadata['tenant_id']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_conversation_history():
    """Demo conversation history handling."""
    
    print("\n💬 Conversation History Demo")
    print("=" * 50)
    
    engine = PromptEngine()
    
    try:
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="Can you elaborate on that?",
            prompt_type=PromptType.CHAT,
            conversation_history=[
                {
                    "user": "What is machine learning?",
                    "assistant": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed."
                },
                {
                    "user": "How does it work?",
                    "assistant": "Machine learning works by training algorithms on large datasets to identify patterns and make predictions or decisions based on new data."
                }
            ]
        )
        
        response = engine.generate_prompt(request)
        
        print(f"✅ Success!")
        print(f"📊 Tokens: {response.token_estimate}")
        print(f"💬 Has conversation: {response.metadata['has_conversation']}")
        print(f"📏 Total length: {len(response.formatted_prompt)} chars")
        
        # Show conversation context in prompt
        if "machine learning" in response.formatted_prompt.lower():
            print("✅ Conversation history properly included in prompt")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_context_variables():
    """Demo context variable substitution."""
    
    print("\n🔧 Context Variables Demo")
    print("=" * 50)
    
    engine = PromptEngine()
    
    try:
        request = PromptRequest(
            model_id="deepseek-r1-0528-qwen3-8b",
            user_input="Hello",
            prompt_type=PromptType.CHAT,
            context={
                "user_language": "Vietnamese",
                "expertise_level": "beginner",
                "user_name": "Alice"
            }
        )
        
        response = engine.generate_prompt(request)
        
        print(f"✅ Success!")
        print(f"📊 Tokens: {response.token_estimate}")
        print(f"🔧 Context variables: {response.metadata['context_variables']}")
        
        # Check if context variables were substituted
        if "Vietnamese" in response.formatted_prompt or "beginner" in response.formatted_prompt:
            print("✅ Context variables properly substituted")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_engine_stats():
    """Demo engine statistics and health information."""
    
    print("\n📊 Engine Statistics Demo")
    print("=" * 50)
    
    engine = PromptEngine()
    
    try:
        # Get supported models
        models = engine.get_supported_models()
        print(f"🤖 Supported Models: {len(models)}")
        for model_id, display_name in models.items():
            print(f"  - {model_id}: {display_name}")
        
        # Get engine stats
        stats = engine.get_engine_stats()
        print(f"\n📈 Engine Stats:")
        print(f"  - Status: {stats['status']}")
        print(f"  - Version: {stats['version']}")
        print(f"  - Templates loaded: {stats['templates_loaded']}")
        print(f"  - Models supported: {stats['models_supported']}")
        print(f"  - Tenants configured: {stats['tenants_configured']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all demos."""
    
    try:
        # Run all demos
        demo_basic_prompt_generation()
        demo_tenant_customization()
        demo_conversation_history()
        demo_context_variables()
        demo_engine_stats()
        
        print("\n🎉 Demo completed successfully!")
        print("\n💡 To test the API, start the server with:")
        print("   python main.py")
        print("\n📚 API Documentation will be available at:")
        print("   http://localhost:8800/docs")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
