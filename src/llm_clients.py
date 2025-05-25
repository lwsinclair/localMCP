"""
LLM Clients - Multi-provider LLM integration
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, AsyncGenerator

import openai
import anthropic
import json

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    OLLAMA = "ollama"

@dataclass
class LLMMessage:
    role: str  # "user", "assistant", "system"
    content: str

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, Any]] = None

class BaseLLMClient(ABC):
    """Base class for all LLM clients"""
    
    def __init__(self, model: str):
        self.model = model
    
    @abstractmethod
    async def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        pass
    
    @abstractmethod
    async def stream_chat(self, messages: List[LLMMessage], **kwargs) -> AsyncGenerator[str, None]:
        pass

class OpenAIClient(BaseLLMClient):
    """OpenAI API client"""
    
    def __init__(self, model: str = "gpt-4", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model)
        self.client = openai.AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )
    
    async def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Send chat messages to OpenAI"""
        try:
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                **kwargs
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.model,
                provider="openai",
                usage=response.usage.dict() if response.usage else None
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def stream_chat(self, messages: List[LLMMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat response from OpenAI"""
        try:
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise

class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API client"""
    
    def __init__(self, model: str = "claude-3-sonnet-20240229", api_key: Optional[str] = None):
        super().__init__(model)
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
    
    async def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Send chat messages to Claude"""
        try:
            # Convert messages format for Claude
            system_message = None
            claude_messages = []
            
            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    claude_messages.append({"role": msg.role, "content": msg.content})
            
            response = await self.client.messages.create(
                model=self.model,
                messages=claude_messages,
                system=system_message,
                max_tokens=kwargs.get("max_tokens", 4096),
                **{k: v for k, v in kwargs.items() if k != "max_tokens"}
            )
            
            return LLMResponse(
                content=response.content[0].text,
                model=self.model,
                provider="claude",
                usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
            )
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
    
    async def stream_chat(self, messages: List[LLMMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat response from Claude"""
        try:
            # Convert messages format for Claude
            system_message = None
            claude_messages = []
            
            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    claude_messages.append({"role": msg.role, "content": msg.content})
            
            stream = await self.client.messages.create(
                model=self.model,
                messages=claude_messages,
                system=system_message,
                max_tokens=kwargs.get("max_tokens", 4096),
                stream=True,
                **{k: v for k, v in kwargs.items() if k not in ["max_tokens"]}
            )
            
            async for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.text:
                    yield chunk.delta.text
                    
        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
            raise

class OllamaClient(BaseLLMClient):
    """Ollama API client"""
    
    def __init__(self, model: str = "llama2", base_url: Optional[str] = None):
        super().__init__(model)
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    async def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Send chat messages to Ollama"""
        try:
            import aiohttp
            
            ollama_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": ollama_messages,
                        "stream": False,
                        **kwargs
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return LLMResponse(
                            content=result["message"]["content"],
                            model=self.model,
                            provider="ollama"
                        )
                    else:
                        raise Exception(f"Ollama API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise
    
    async def stream_chat(self, messages: List[LLMMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat response from Ollama"""
        try:
            import aiohttp
            
            ollama_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": ollama_messages,
                        "stream": True,
                        **kwargs
                    }
                ) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                try:
                                    data = json.loads(line.decode())
                                    if "message" in data and "content" in data["message"]:
                                        yield data["message"]["content"]
                                except json.JSONDecodeError:
                                    continue
                    else:
                        raise Exception(f"Ollama streaming error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise

def create_llm_client(provider: str, model: str, **kwargs) -> BaseLLMClient:
    """Factory function to create LLM clients"""
    if provider == "openai":
        return OpenAIClient(model, **kwargs)
    elif provider == "claude":
        return ClaudeClient(model, **kwargs)
    elif provider == "ollama":
        return OllamaClient(model, **kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
