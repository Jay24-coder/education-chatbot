# LLM/SLM Integration Changes for Multi-Model Support

## Overview

This document outlines the necessary changes to the Phase 1 implementation to support flexible integration of multiple LLM/SLM providers, including Google's Gemini API, while maintaining backward compatibility and extensibility for future model integrations.

## Current LLM Integration Points

Based on the Phase 1 implementation, the following areas currently reference LLM integration:

1. **Configuration** (lines 1002-1005, 1036-1039)
2. **LLM Service** (line 54) - Referenced but not implemented
3. **Orchestrator Agent** (lines 298, 327-330) - Intent classification
4. **Topic Expert Agent** (line 695) - Topic extraction

## Required Changes

### 1. Enhanced Configuration System

#### Current Configuration Issues:
- Hardcoded to OpenAI and Anthropic
- No provider selection mechanism
- Limited model configuration options

#### New Configuration Structure:

```python
# src/core/config.py - Enhanced Configuration
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from enum import Enum
import os

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    CUSTOM = "custom"

class LLMConfig(BaseModel):
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 30
    custom_headers: Dict[str, str] = {}

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/education_chatbot"
    REDIS_URL: str = "redis://localhost:6379"
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # LLM Configuration - Enhanced
    DEFAULT_LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI
    LLM_CONFIGS: Dict[str, LLMConfig] = {
        "openai": LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.7,
            max_tokens=2000
        ),
        "anthropic": LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-3-sonnet-20240229",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.7,
            max_tokens=2000
        ),
        "gemini": LLMConfig(
            provider=LLMProvider.GEMINI,
            model_name="gemini-1.5-pro",
            api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.7,
            max_tokens=2000
        )
    }
    
    # Agent Configuration
    MAX_RESPONSE_TIME: int = 30
    DEFAULT_DIFFICULTY_LEVEL: str = "intermediate"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

### 2. Abstract LLM Service Interface

#### New File: `src/services/llm/__init__.py`

```python
# src/services/llm/__init__.py
from .base import BaseLLMService
from .factory import LLMServiceFactory
from .providers import OpenAIProvider, AnthropicProvider, GeminiProvider

__all__ = ["BaseLLMService", "LLMServiceFactory", "OpenAIProvider", "AnthropicProvider", "GeminiProvider"]
```

#### New File: `src/services/llm/base.py`

```python
# src/services/llm/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from pydantic import BaseModel
from ..config import LLMConfig

class LLMRequest(BaseModel):
    """Standardized request format for all LLM providers"""
    messages: List[Dict[str, str]]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    metadata: Dict[str, Any] = {}

class LLMResponse(BaseModel):
    """Standardized response format from all LLM providers"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = {}
    metadata: Dict[str, Any] = {}

class BaseLLMService(ABC):
    """Abstract base class for all LLM providers"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.model_name = config.model_name
        self.provider = config.provider
        
    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    async def generate_streaming_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM"""
        pass
    
    @abstractmethod
    async def classify_intent(self, message: str, context: Dict[str, Any]) -> str:
        """Classify user intent using the LLM"""
        pass
    
    @abstractmethod
    async def extract_topic(self, message: str, subject_context: Optional[str] = None) -> Optional[str]:
        """Extract topic from user message"""
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate connection to the LLM provider"""
        pass
```

### 3. Gemini Provider Implementation

#### New File: `src/services/llm/providers/gemini.py`

```python
# src/services/llm/providers/gemini.py
import google.generativeai as genai
from typing import Dict, Any, Optional, List, AsyncGenerator
import asyncio
import logging

from ..base import BaseLLMService, LLMRequest, LLMResponse
from ...config import LLMConfig, LLMProvider

logger = logging.getLogger(__name__)

class GeminiProvider(BaseLLMService):
    """Google Gemini API provider implementation"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if not config.api_key:
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=config.api_key)
        self.model = genai.GenerativeModel(config.model_name)
        
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Gemini API"""
        try:
            # Convert messages to Gemini format
            prompt = self._convert_messages_to_prompt(request.messages)
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=request.temperature or self.config.temperature,
                max_output_tokens=request.max_tokens or self.config.max_tokens,
            )
            
            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config
            )
            
            return LLMResponse(
                content=response.text,
                model=self.model_name,
                provider=LLMProvider.GEMINI,
                usage={
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(response.text.split()),
                    "total_tokens": len(prompt.split()) + len(response.text.split())
                },
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise
    
    async def generate_streaming_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate streaming response using Gemini API"""
        try:
            prompt = self._convert_messages_to_prompt(request.messages)
            
            generation_config = genai.types.GenerationConfig(
                temperature=request.temperature or self.config.temperature,
                max_output_tokens=request.max_tokens or self.config.max_tokens,
            )
            
            # Note: Gemini doesn't support true streaming yet, so we simulate it
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config
            )
            
            # Simulate streaming by yielding chunks
            text = response.text
            chunk_size = 50
            for i in range(0, len(text), chunk_size):
                yield text[i:i + chunk_size]
                await asyncio.sleep(0.05)  # Small delay to simulate streaming
                
        except Exception as e:
            logger.error(f"Gemini streaming error: {str(e)}")
            raise
    
    async def classify_intent(self, message: str, context: Dict[str, Any]) -> str:
        """Classify user intent using Gemini"""
        prompt = f"""
        Analyze the following user message and classify the intent. 
        Context: {context}
        Message: "{message}"
        
        Classify as one of: syllabus_query, admin_query, topic_explanation, general_help, unclear
        
        Respond with only the classification:
        """
        
        request = LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50
        )
        
        response = await self.generate_response(request)
        return response.content.strip().lower()
    
    async def extract_topic(self, message: str, subject_context: Optional[str] = None) -> Optional[str]:
        """Extract topic from user message using Gemini"""
        prompt = f"""
        Extract the main topic or concept from this message.
        Subject context: {subject_context or "Not specified"}
        Message: "{message}"
        
        Extract only the main topic/concept, or respond "NONE" if no clear topic:
        """
        
        request = LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100
        )
        
        response = await self.generate_response(request)
        topic = response.content.strip()
        
        return None if topic.upper() == "NONE" else topic
    
    async def validate_connection(self) -> bool:
        """Validate connection to Gemini API"""
        try:
            test_request = LLMRequest(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            await self.generate_response(test_request)
            return True
        except Exception as e:
            logger.error(f"Gemini connection validation failed: {str(e)}")
            return False
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to Gemini prompt format"""
        prompt_parts = []
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n\n".join(prompt_parts)
```

### 4. LLM Service Factory

#### New File: `src/services/llm/factory.py`

```python
# src/services/llm/factory.py
from typing import Dict, Optional
from ..config import LLMConfig, LLMProvider
from .base import BaseLLMService
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider
from .providers.gemini import GeminiProvider
import logging

logger = logging.getLogger(__name__)

class LLMServiceFactory:
    """Factory for creating LLM service instances"""
    
    _providers: Dict[LLMProvider, type] = {
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.ANTHROPIC: AnthropicProvider,
        LLMProvider.GEMINI: GeminiProvider,
    }
    
    @classmethod
    def create_service(cls, config: LLMConfig) -> BaseLLMService:
        """Create an LLM service instance based on configuration"""
        provider_class = cls._providers.get(config.provider)
        
        if not provider_class:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
        
        try:
            return provider_class(config)
        except Exception as e:
            logger.error(f"Failed to create {config.provider} service: {str(e)}")
            raise
    
    @classmethod
    def register_provider(cls, provider: LLMProvider, provider_class: type):
        """Register a new LLM provider"""
        cls._providers[provider] = provider_class
        logger.info(f"Registered new LLM provider: {provider}")
    
    @classmethod
    def get_available_providers(cls) -> list[LLMProvider]:
        """Get list of available providers"""
        return list(cls._providers.keys())
```

### 5. Enhanced LLM Service

#### Updated File: `src/services/llm_service.py` (replaces the placeholder)

```python
# src/services/llm_service.py
from typing import Dict, Any, Optional, List, AsyncGenerator
from ..core.config import Settings, LLMConfig
from .llm.base import BaseLLMService, LLMRequest, LLMResponse
from .llm.factory import LLMServiceFactory
import logging

logger = logging.getLogger(__name__)

class LLMService:
    """Main LLM service that manages multiple providers"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._services: Dict[str, BaseLLMService] = {}
        self._default_service: Optional[BaseLLMService] = None
        
    async def initialize(self):
        """Initialize LLM services"""
        try:
            # Initialize default service
            default_config = self.settings.LLM_CONFIGS.get(
                self.settings.DEFAULT_LLM_PROVIDER.value
            )
            if default_config:
                self._default_service = LLMServiceFactory.create_service(default_config)
                self._services["default"] = self._default_service
                logger.info(f"Initialized default LLM service: {default_config.provider}")
            
            # Initialize other configured services
            for name, config in self.settings.LLM_CONFIGS.items():
                if name != self.settings.DEFAULT_LLM_PROVIDER.value:
                    try:
                        service = LLMServiceFactory.create_service(config)
                        self._services[name] = service
                        logger.info(f"Initialized LLM service '{name}': {config.provider}")
                    except Exception as e:
                        logger.warning(f"Failed to initialize {name} service: {str(e)}")
            
            # Validate connections
            await self._validate_connections()
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM services: {str(e)}")
            raise
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        provider: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using specified or default provider"""
        service = self._get_service(provider)
        request = LLMRequest(messages=messages, **kwargs)
        return await service.generate_response(request)
    
    async def generate_streaming_response(
        self, 
        messages: List[Dict[str, str]], 
        provider: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using specified or default provider"""
        service = self._get_service(provider)
        request = LLMRequest(messages=messages, stream=True, **kwargs)
        async for chunk in service.generate_streaming_response(request):
            yield chunk
    
    async def classify_intent(
        self, 
        message: str, 
        context: Dict[str, Any], 
        provider: Optional[str] = None
    ) -> str:
        """Classify user intent using specified or default provider"""
        service = self._get_service(provider)
        return await service.classify_intent(message, context)
    
    async def extract_topic(
        self, 
        message: str, 
        subject_context: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Optional[str]:
        """Extract topic from message using specified or default provider"""
        service = self._get_service(provider)
        return await service.extract_topic(message, subject_context)
    
    def _get_service(self, provider: Optional[str] = None) -> BaseLLMService:
        """Get LLM service by name or default"""
        if provider and provider in self._services:
            return self._services[provider]
        
        if self._default_service:
            return self._default_service
        
        raise ValueError("No LLM service available")
    
    async def _validate_connections(self):
        """Validate all service connections"""
        for name, service in self._services.items():
            try:
                is_valid = await service.validate_connection()
                if is_valid:
                    logger.info(f"LLM service '{name}' connection validated")
                else:
                    logger.warning(f"LLM service '{name}' connection validation failed")
            except Exception as e:
                logger.error(f"LLM service '{name}' validation error: {str(e)}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self._services.keys())
    
    def get_provider_info(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific provider"""
        if provider in self._services:
            service = self._services[provider]
            return {
                "provider": service.provider,
                "model": service.model_name,
                "available": True
            }
        return None
```

### 6. Updated Orchestrator Agent

#### Changes to `src/agents/base/orchestrator.py`:

```python
# Updated imports and initialization
from ...services.llm_service import LLMService

class OrchestratorAgent(BaseAgent):
    """Central orchestrator that routes requests to appropriate agents"""
    
    def __init__(self, agent_registry: AgentRegistry, llm_service: LLMService):
        super().__init__("orchestrator", "Routes requests to appropriate agents")
        self.agent_registry = agent_registry
        self.llm_service = llm_service  # Updated from None
        
    async def _classify_intent(self, message: str, context: Dict) -> str:
        """Classify user intent using LLM service"""
        try:
            return await self.llm_service.classify_intent(message, context)
        except Exception as e:
            self.logger.error(f"Intent classification error: {str(e)}")
            return "unclear"
```

### 7. Updated Topic Expert Agent

#### Changes to `src/agents/information/topic_expert_agent.py`:

```python
# Updated imports and initialization
from ...services.llm_service import LLMService

class TopicExpertAgent(BaseAgent):
    """Provides detailed explanations of specific subjects - extensible for any subject"""
    
    def __init__(self, knowledge_service: KnowledgeBaseService, subject_manager: SubjectManager, llm_service: LLMService):
        super().__init__("topic_expert", "Provides detailed subject explanations")
        self.knowledge_service = knowledge_service
        self.subject_manager = subject_manager
        self.llm_service = llm_service  # Added LLM service
        
    async def _extract_topic(self, message: str) -> Optional[str]:
        """Extract the specific topic from the user message using LLM"""
        try:
            return await self.llm_service.extract_topic(message)
        except Exception as e:
            self.logger.error(f"Topic extraction error: {str(e)}")
            # Fallback to simple extraction
            return self._simple_topic_extraction(message)
    
    def _simple_topic_extraction(self, message: str) -> Optional[str]:
        """Fallback simple topic extraction"""
        # Original simple extraction logic as fallback
        message_lower = message.lower()
        topic_indicators = ["about", "explain", "what is", "how does", "tell me about"]
        
        for indicator in topic_indicators:
            if indicator in message_lower:
                parts = message_lower.split(indicator, 1)
                if len(parts) > 1:
                    topic = parts[1].strip()
                    topic = topic.replace("?", "").strip()
                    return topic
        return None
```

### 8. Updated Environment Configuration

#### Updated `.env.example`:

```bash
# .env.example
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/education_chatbot
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# LLM Configuration - Enhanced
DEFAULT_LLM_PROVIDER=gemini

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Anthropic Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-pro

# Agent Configuration
MAX_RESPONSE_TIME=30
DEFAULT_DIFFICULTY_LEVEL=intermediate

# Logging
LOG_LEVEL=INFO
```

### 9. Updated Dependencies

#### Updated `pyproject.toml`:

```toml
[project]
name = "education-chatbot"
version = "0.1.0"
description = "Multi-agent educational support system"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "langgraph>=1.0.0",
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.0",
    "redis>=5.0.0",
    "openai>=1.3.0",
    "anthropic>=0.7.0",
    "google-generativeai>=0.3.0",
    "sentence-transformers>=2.2.0",
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",
]

[project.optional-dependencies]
dev = [
    "black>=23.0.0",
    "isort>=5.12.0",
    "mypy>=1.7.0",
    "pre-commit>=3.5.0",
]
```

### 10. Updated Main Application

#### Changes to `src/main.py`:

```python
# Updated imports and initialization
from .services.llm_service import LLMService

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Education Chatbot API")
    
    # Initialize database
    await init_db()
    
    # Initialize services
    app.state.knowledge_service = KnowledgeBaseService()
    app.state.subject_manager = SubjectManager()
    
    # Initialize LLM service
    settings = get_settings()
    app.state.llm_service = LLMService(settings)
    await app.state.llm_service.initialize()
    
    # Initialize agent registry with LLM service
    app.state.agent_registry = AgentRegistry()
    await app.state.agent_registry.initialize(app.state.llm_service)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Education Chatbot API")
```

## Benefits of These Changes

### 1. **Flexibility**
- Easy switching between LLM providers
- Support for multiple providers simultaneously
- Simple addition of new providers

### 2. **Scalability**
- Provider-specific optimizations
- Load balancing across providers
- Fallback mechanisms

### 3. **Maintainability**
- Clean separation of concerns
- Standardized interfaces
- Easy testing and mocking

### 4. **Cost Optimization**
- Use different providers for different tasks
- Provider-specific rate limiting
- Cost monitoring per provider

### 5. **Future-Proofing**
- Easy integration of new models
- Support for local models (Ollama, etc.)
- Custom provider implementations

## Migration Guide

### For Existing Implementations:

1. **Update Configuration**: Replace hardcoded LLM configs with the new structure
2. **Update Service Initialization**: Use the new LLMService instead of direct provider calls
3. **Update Agent Constructors**: Pass LLMService to agents that need it
4. **Update Environment Variables**: Add new provider configurations

### For New Implementations:

1. **Choose Default Provider**: Set `DEFAULT_LLM_PROVIDER` in environment
2. **Configure API Keys**: Add provider-specific API keys
3. **Test Connections**: Use the validation endpoints to ensure connectivity
4. **Monitor Usage**: Implement logging and monitoring for each provider

## Testing Strategy

### Unit Tests:
- Test each provider independently
- Mock external API calls
- Test fallback mechanisms

### Integration Tests:
- Test provider switching
- Test error handling
- Test performance under load

### End-to-End Tests:
- Test complete chat flows with different providers
- Test intent classification accuracy
- Test topic extraction quality

This enhanced architecture provides a robust, flexible foundation for integrating any LLM/SLM provider while maintaining clean code organization and easy extensibility.
