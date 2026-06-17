"""
Abstract Agent Service - Modular LLM interface with prompt caching.
Allows swapping between different LLM providers (Gemini, OpenAI, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AgentResponse:
    """Wrapper for agent responses."""
    def __init__(self, text: str, raw_response: Optional[Any] = None):
        self.text = text
        self.raw_response = raw_response


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


class GeminiAgentService(BaseAgentService):
    """Gemini-based implementation of the agent service with prompt caching."""
    
    def __init__(self, api_key: str, parser_model: str, critic_model: str, editor_model: str):
        self.api_key = api_key
        self.parser_model = parser_model
        self.critic_model = critic_model
        self.editor_model = editor_model
        self.client = None
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
                    model=self.parser_model
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
                    model=self.critic_model
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
                    model=self.editor_model
                )
            )
        )
    
    def _get_cached_content(self, system_instruction: str, model: str):
        """
        Create a cached content reference for the system instruction.
        Returns a CachedContent resource that references the system instruction.
        """
        from google.genai import types
        
        try:
            # Create cached content for the system instruction
            cached_content = self.client.cached_content.create(
                model=model,
                display_name=f"system-instruction-{model}",
                system_instruction=system_instruction,
                cache_expiration_duration=types.Duration(seconds=3600),  # 1 hour cache
            )
            return cached_content
        except Exception as e:
            # If caching fails, return None (chats will work without cache)
            print(f"Warning: Prompt caching initialization failed: {e}")
            return None
    
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