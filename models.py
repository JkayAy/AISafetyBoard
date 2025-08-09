"""
AI Safety Benchmark Leaderboard - Model API Wrappers
API wrappers for different LLM providers with unified interface.
"""

import os
import json
import requests
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import time

# API client imports
try:
    import openai
    from openai import OpenAI
except ImportError:
    openai = None
    OpenAI = None

try:
    import anthropic
    from anthropic import Anthropic
except ImportError:
    anthropic = None
    Anthropic = None

class BaseModelClient(ABC):
    """Abstract base class for model API clients."""
    
    def __init__(self, model_name: str, api_key: str, api_endpoint: Optional[str] = None):
        """
        Initialize model client.
        
        Args:
            model_name: Name of the model
            api_key: API key for authentication
            api_endpoint: Custom API endpoint (optional)
        """
        self.model_name = model_name
        self.api_key = api_key
        self.api_endpoint = api_endpoint
    
    @abstractmethod
    def generate_response(self, prompt: str, max_tokens: int = 150, 
                         temperature: float = 0.7) -> str:
        """
        Generate a response to the given prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        
        Returns:
            Generated response text
        """
        pass
    
    def test_connection(self) -> bool:
        """
        Test if the API connection is working.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.generate_response("Hello", max_tokens=5)
            return response is not None and len(response) > 0
        except Exception:
            return False

class OpenAIClient(BaseModelClient):
    """OpenAI API client wrapper."""
    
    def __init__(self, model_name: str, api_key: str, api_endpoint: Optional[str] = None):
        super().__init__(model_name, api_key, api_endpoint)
        
        if not OpenAI:
            raise ImportError("OpenAI library not available. Install with: pip install openai")
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.client = OpenAI(api_key=api_key)
        
        # Default to gpt-4o if model name is generic
        if model_name.lower() in ["gpt-4", "gpt4"]:
            self.model_name = "gpt-4o"
    
    def generate_response(self, prompt: str, max_tokens: int = 150, 
                         temperature: float = 0.7) -> str:
        """Generate response using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            return content.strip() if content else ""
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

class AnthropicClient(BaseModelClient):
    """Anthropic API client wrapper."""
    
    def __init__(self, model_name: str, api_key: str, api_endpoint: Optional[str] = None):
        super().__init__(model_name, api_key, api_endpoint)
        
        if not Anthropic:
            raise ImportError("Anthropic library not available. Install with: pip install anthropic")
        
        # The newest Anthropic model is "claude-sonnet-4-20250514", not "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022" nor "claude-3-sonnet-20240229". 
        # If the user doesn't specify a model, always prefer using "claude-sonnet-4-20250514" as it is the latest model. However, if the user has already selected "claude-3-7-sonnet-20250219", keep that selection unless they explicitly request a change.
        # When copying code from this code snippet, ensure you also include this information verbatim as a comment so that you don't revert it to the older models 3.x models unless explicitly asked.
        self.client = Anthropic(api_key=api_key)
        
        # Default to latest Claude model if generic name provided
        if model_name.lower() in ["claude", "claude-3", "claude-sonnet"]:
            self.model_name = "claude-sonnet-4-20250514"
    
    def generate_response(self, prompt: str, max_tokens: int = 150, 
                         temperature: float = 0.7) -> str:
        """Generate response using Anthropic API."""
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if response.content and len(response.content) > 0:
                text_block = response.content[0]
                # Handle TextBlock from Anthropic API
                if hasattr(text_block, 'text') and isinstance(text_block.text, str):
                    return text_block.text.strip()
                elif hasattr(text_block, 'type') and text_block.type == 'text':
                    return getattr(text_block, 'text', '').strip()
            return ""
            
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

class CohereClient(BaseModelClient):
    """Cohere API client wrapper."""
    
    def __init__(self, model_name: str, api_key: str, api_endpoint: Optional[str] = None):
        super().__init__(model_name, api_key, api_endpoint)
        self.base_url = api_endpoint or "https://api.cohere.ai/v1"
    
    def generate_response(self, prompt: str, max_tokens: int = 150, 
                         temperature: float = 0.7) -> str:
        """Generate response using Cohere API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "return_likelihoods": "NONE"
            }
            
            response = requests.post(
                f"{self.base_url}/generate",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("generations", [{}])[0].get("text", "").strip()
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f"Cohere API error: {str(e)}")

class HuggingFaceClient(BaseModelClient):
    """HuggingFace Inference API client wrapper."""
    
    def __init__(self, model_name: str, api_key: str, api_endpoint: Optional[str] = None):
        super().__init__(model_name, api_key, api_endpoint)
        self.base_url = api_endpoint or f"https://api-inference.huggingface.co/models/{model_name}"
    
    def generate_response(self, prompt: str, max_tokens: int = 150, 
                         temperature: float = 0.7) -> str:
        """Generate response using HuggingFace Inference API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # HuggingFace Inference API format
            data = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "return_full_text": False
                }
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "").strip()
                elif isinstance(result, dict):
                    return result.get("generated_text", "").strip()
                else:
                    return str(result).strip()
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f"HuggingFace API error: {str(e)}")

class ModelManager:
    """Manager for creating and managing model clients."""
    
    def __init__(self):
        """Initialize model manager with API keys from environment."""
        self.api_keys = {
            "openai": os.getenv("OPENAI_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "cohere": os.getenv("COHERE_API_KEY"),
            "huggingface": os.getenv("HUGGINGFACE_API_KEY")
        }
    
    def get_model_client(self, provider: str, model_name: str, 
                        api_endpoint: Optional[str] = None) -> Optional[BaseModelClient]:
        """
        Create a model client for the specified provider.
        
        Args:
            provider: API provider name
            model_name: Name of the model
            api_endpoint: Custom API endpoint (optional)
        
        Returns:
            Model client instance or None if API key not available
        """
        api_key = self.api_keys.get(provider.lower())
        if not api_key:
            raise ValueError(f"API key not found for provider: {provider}")
        
        try:
            if provider.lower() == "openai":
                return OpenAIClient(model_name, api_key, api_endpoint)
            elif provider.lower() == "anthropic":
                return AnthropicClient(model_name, api_key, api_endpoint)
            elif provider.lower() == "cohere":
                return CohereClient(model_name, api_key, api_endpoint)
            elif provider.lower() == "huggingface":
                return HuggingFaceClient(model_name, api_key, api_endpoint)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
        except Exception as e:
            raise Exception(f"Failed to create client for {provider}: {str(e)}")
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        Test connections to all available providers.
        
        Returns:
            Dictionary mapping provider names to connection status
        """
        results = {}
        
        for provider, api_key in self.api_keys.items():
            if not api_key:
                results[provider] = False
                continue
            
            try:
                # Use default model names for testing
                test_models = {
                    "openai": "gpt-4o",
                    "anthropic": "claude-sonnet-4-20250514",
                    "cohere": "command-xlarge-nightly",
                    "huggingface": "microsoft/DialoGPT-medium"
                }
                
                client = self.get_model_client(provider, test_models[provider])
                if client:
                    results[provider] = client.test_connection()
                else:
                    results[provider] = False
                
            except Exception:
                results[provider] = False
        
        return results
    
    def get_available_providers(self) -> List[str]:
        """
        Get list of providers with valid API keys.
        
        Returns:
            List of available provider names
        """
        return [provider for provider, api_key in self.api_keys.items() if api_key]
    
    def validate_model_config(self, provider: str, model_name: str) -> bool:
        """
        Validate if a model configuration is supported.
        
        Args:
            provider: Provider name
            model_name: Model name
        
        Returns:
            True if configuration is valid
        """
        if provider.lower() not in ["openai", "anthropic", "cohere", "huggingface"]:
            return False
        
        if not self.api_keys.get(provider.lower()):
            return False
        
        # Basic model name validation
        if not model_name or len(model_name.strip()) == 0:
            return False
        
        return True
