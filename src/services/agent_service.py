"""
Abstract Agent Service - Modular LLM interface with prompt caching.
Allows swapping between different LLM providers (Gemini, OpenAI, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AgentResponse:
    """Wrapper for agent responses with metadata."""
    def __init__(self, text: str, raw_response: Optional[Any] = None, cache_config: Optional[Dict] = None):
        self.text = text
        self.raw_response = raw_response
        self.input_tokens = None
        self.output_tokens = None
        self.cache_hit = False
        self.cache_creation_tokens = None
        
        # Extract token metadata from raw response
        if raw_response and hasattr(raw_response, 'usage_metadata'):
            usage = raw_response.usage_metadata
            self.input_tokens = getattr(usage, 'prompt_token_count', None)
            self.output_tokens = getattr(usage, 'candidates_token_count', None)
            self.cache_hit = getattr(usage, 'cached_content_input_token_count', 0) > 0
            self.cache_creation_tokens = getattr(usage, 'cache_creation_input_token_count', None)


class BaseAgentService(ABC):
    """Abstract base class for LLM-based agents."""
    
    @abstractmethod
    def initialize(self):
        """Initialize the service with API keys and models."""
        pass
    
    @abstractmethod
    def parser_parse(self, prompt: str) -> AgentResponse:
        """Parser agent: structure raw text into JSON."""
        pass
    
    @abstractmethod
    def critic_audit_original(self, prompt: str) -> AgentResponse:
        """Critic agent: audit original resume."""
        pass
    
    @abstractmethod
    def editor_rewrite(self, prompt: str) -> AgentResponse:
        """Editor agent: rewrite resume based on feedback."""
        pass
    
    @abstractmethod
    def critic_audit_edited(self, prompt: str) -> AgentResponse:
        """Critic agent: audit edited resume."""
        pass
    
    @abstractmethod
    def invalidate_cache(self) -> None:
        """Invalidate cached content."""
        pass


class GeminiAgentService(BaseAgentService):
    """Gemini-based implementation of the agent service with prompt caching."""
    
    def __init__(self, api_key: str, parser_model: str, critic_model: str, editor_model: str, cache_duration_seconds: int = 3600):
        self.api_key = api_key
        self.parser_model = parser_model
        self.critic_model = critic_model
        self.editor_model = editor_model
        self.cache_duration_seconds = cache_duration_seconds
        self.client = None
        self._cached_content = {}
        self._init_chats()
    
    def initialize(self):
        """Initialize Gemini client."""
        from google import genai
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing or unconfigured.")
        self.client = genai.Client(api_key=self.api_key)
    
    def _init_chats(self):
        """Initialize persistent chat sessions for each agent with prompt caching."""
        from google import genai
        from google.genai import types
        from src.analysis.analysis_prompts import (
            PARSER_SYSTEM_INSTRUCTION,
            CRITIC_SYSTEM_INSTRUCTION,
            EDITOR_SYSTEM_INSTRUCTION
        )
        
        if not self.client:
            self.initialize()
        
        # Parser Chat - Cached system instruction
        self.parser_chat = self.client.chats.create(
            model=self.parser_model,
            config=types.GenerateContentConfig(
                system_instruction=PARSER_SYSTEM_INSTRUCTION,
                temperature=0.0,
                cached_content=self._get_cached_content(
                    system_instruction=PARSER_SYSTEM_INSTRUCTION,
                    model=self.parser_model,
                    cache_key="parser"
                )
            )
        )
        
        # Critic Chat - Cached system instruction + JSON enforcement
        self.critic_chat = self.client.chats.create(
            model=self.critic_model,
            config=types.GenerateContentConfig(
                system_instruction=CRITIC_SYSTEM_INSTRUCTION,
                temperature=0.0,
                response_mime_type="application/json",
                cached_content=self._get_cached_content(
                    system_instruction=CRITIC_SYSTEM_INSTRUCTION,
                    model=self.critic_model,
                    cache_key="critic"
                )
            )
        )
        
        # Editor Chat - Cached system instruction
        self.editor_chat = self.client.chats.create(
            model=self.editor_model,
            config=types.GenerateContentConfig(
                system_instruction=EDITOR_SYSTEM_INSTRUCTION,
                temperature=0.4,
                cached_content=self._get_cached_content(
                    system_instruction=EDITOR_SYSTEM_INSTRUCTION,
                    model=self.editor_model,
                    cache_key="editor"
                )
            )
        )
    
    def _get_cached_content(self, system_instruction: str, model: str, cache_key: str):
        """
        Create a cached content reference for the system instruction.
        Returns a CachedContent resource that references the system instruction.
        """
        from google.genai import types
        
        try:
            # Check if cache already exists
            if cache_key in self._cached_content:
                return self._cached_content[cache_key]
            
            # Create cached content for the system instruction
            cached_content = self.client.cached_content.create(
                model=model,
                display_name=f"system-instruction-{model}",
                system_instruction=system_instruction,
                cache_expiration_duration=types.Duration(seconds=self.cache_duration_seconds),
            )
            self._cached_content[cache_key] = cached_content
            return cached_content
        except Exception as e:
            # If caching fails, return None (chats will work without cache)
            print(f"Warning: Prompt caching initialization failed: {e}")
            return None
    
    def invalidate_cache(self) -> None:
        """Invalidate all cached content."""
        from google.genai import exceptions
        try:
            for cache_key, cached_content in self._cached_content.items():
                if cached_content:
                    self.client.cached_content.delete(name=cached_content.name)
            self._cached_content.clear()
            self._init_chats()
        except Exception as e:
            print(f"Warning: Cache invalidation failed: {e}")
    
    def parser_parse(self, prompt: str) -> AgentResponse:
        """Parse resume with parser agent."""
        response = self.parser_chat.send_message(prompt)
        return AgentResponse(text=response.text, raw_response=response)
    
    def critic_audit_original(self, prompt: str) -> AgentResponse:
        """Audit original resume with critic agent."""
        response = self.critic_chat.send_message(prompt)
        return AgentResponse(text=response.text, raw_response=response)
    
    def editor_rewrite(self, prompt: str) -> AgentResponse:
        """Rewrite resume with editor agent."""
        response = self.editor_chat.send_message(prompt)
        return AgentResponse(text=response.text, raw_response=response)
    
    def critic_audit_edited(self, prompt: str) -> AgentResponse:
        """Audit edited resume with critic agent."""
        response = self.critic_chat.send_message(prompt)
        return AgentResponse(text=response.text, raw_response=response)
