# Phase 1 Implementation: Foundation Framework

## Overview

Phase 1 establishes the foundational multi-agent system with basic LangGraph framework, core orchestration capabilities, and three essential Information Agents. This phase focuses on creating a scalable, extensible architecture that can accommodate future subject additions and advanced features.

## Table of Contents

1. [Framework Architecture](#framework-architecture)
2. [Database Design](#database-design)
3. [Core Components](#core-components)
4. [Agent Implementations](#agent-implementations)
5. [API Layer](#api-layer)
6. [Configuration & Environment](#configuration--environment)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Setup](#deployment-setup)

## Framework Architecture

### 1. Project Structure

```
education-chatbot/
├── src/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration management
│   │   ├── database.py            # Database connection and SQLModel setup
│   │   ├── exceptions.py          # Custom exceptions
│   │   └── middleware.py          # Request/response middleware
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py           # Base agent class
│   │   │   ├── orchestrator.py    # Main orchestrator agent
│   │   │   └── context_manager.py # Context management
│   │   ├── information/
│   │   │   ├── __init__.py
│   │   │   ├── syllabus_agent.py
│   │   │   ├── administration_agent.py
│   │   │   └── topic_expert_agent.py
│   │   └── registry.py            # Agent registration system
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py            # SQLModel models
│   │   ├── schemas.py             # Pydantic schemas
│   │   └── enums.py               # Enums and constants
│   ├── services/
│   │   ├── __init__.py
│   │   ├── knowledge_base.py      # Knowledge retrieval service
│   │   ├── llm_service.py         # Main LLM service manager
│   │   ├── subject_manager.py     # Subject management service
│   │   └── llm/
│   │       ├── __init__.py
│   │       ├── base.py            # Base LLM service interface
│   │       ├── factory.py         # LLM service factory
│   │       └── providers/
│   │           ├── __init__.py
│   │           ├── openai.py      # OpenAI provider
│   │           ├── anthropic.py   # Anthropic provider
│   │           └── gemini.py      # Google Gemini provider
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py            # Chat endpoints
│   │   │   ├── agents.py          # Agent management endpoints
│   │   │   └── subjects.py        # Subject management endpoints
│   │   └── dependencies.py        # API dependencies
│   └── utils/
│       ├── __init__.py
│       ├── logging.py             # Logging configuration
│       ├── validators.py          # Input validation utilities
│       └── helpers.py             # General helper functions
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Test configuration
│   ├── test_agents/
│   ├── test_api/
│   └── test_services/
├── data/
│   ├── knowledge_base/           # Subject-specific knowledge files
│   │   ├── mathematics/
│   │   ├── physics/
│   │   └── templates/            # Template for new subjects
│   └── sample_data/              # Sample data for testing
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
│   ├── api/                      # API documentation
│   └── deployment/               # Deployment guides
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

### 2. Technology Stack

#### Core Framework
- **LangGraph 1.0+**: Multi-agent orchestration and workflow management
- **FastAPI**: High-performance web framework for API endpoints
- **Pydantic**: Data validation and serialization
- **SQLModel**: Type-safe ORM combining SQLAlchemy and Pydantic
- **Alembic**: Database migration management

#### Database & Storage
- **PostgreSQL**: Primary database for structured data
- **Redis**: Session management and caching
- **SQLite**: Development and testing database

#### AI/ML Integration
- **Multi-Provider LLM Support**: OpenAI, Anthropic, Google Gemini, Ollama
- **LangChain**: LLM integration and prompt management
- **Sentence Transformers**: Embedding generation for semantic search
- **Google Generative AI**: Gemini API integration

#### Additional Tools
- **Uvicorn**: ASGI server for FastAPI
- **Pytest**: Testing framework
- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking

## Database Design

### 1. Core Tables

#### Students Table
```python
# src/models/database.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid

class Student(SQLModel, table=True):
    __tablename__ = "students"
    
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: str = Field(unique=True, index=True, max_length=50)
    name: str = Field(max_length=255)
    email: str = Field(unique=True, index=True, max_length=255)
    department: Optional[str] = Field(default=None, max_length=100)
    year: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
```

#### Subjects Table
```python
# src/models/database.py
from sqlmodel import SQLModel, Field, JSON, Column
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class Subject(SQLModel, table=True):
    __tablename__ = "subjects"
    
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    display_name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None, max_length=50)  # 'mathematics', 'physics', 'chemistry', etc.
    difficulty_levels: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))  # ['beginner', 'intermediate', 'advanced']
    prerequisites: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))  # Array of prerequisite subject IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
```

#### Knowledge Base Table
```python
# src/models/database.py
from sqlmodel import SQLModel, Field, JSON, Column, ForeignKey
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class KnowledgeBase(SQLModel, table=True):
    __tablename__ = "knowledge_base"
    
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    subject_id: Optional[uuid.UUID] = Field(default=None, foreign_key="subjects.id")
    topic: str = Field(max_length=255)
    subtopic: Optional[str] = Field(default=None, max_length=255)
    content_type: Optional[str] = Field(default=None, max_length=50)  # 'syllabus', 'concept', 'example', 'formula'
    title: str = Field(max_length=500)
    content: str = Field()
    metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # Additional structured data
    difficulty_level: Optional[str] = Field(default=None, max_length=20)
    tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))  # Array of tags for search
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
```

#### Conversations Table
```python
# src/models/database.py
from sqlmodel import SQLModel, Field, JSON, Column, ForeignKey
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: Optional[uuid.UUID] = Field(default=None, foreign_key="students.id")
    session_id: str = Field(max_length=100)
    agent_type: str = Field(max_length=50)  # 'syllabus', 'administration', 'topic_expert'
    subject_id: Optional[uuid.UUID] = Field(default=None, foreign_key="subjects.id")
    user_message: str = Field()
    agent_response: str = Field()
    intent_classification: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # Classified intent and confidence
    response_time_ms: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

#### Student Context Table
```python
# src/models/database.py
from sqlmodel import SQLModel, Field, JSON, Column, ForeignKey
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class StudentContext(SQLModel, table=True):
    __tablename__ = "student_context"
    
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: Optional[uuid.UUID] = Field(default=None, foreign_key="students.id")
    subject_id: Optional[uuid.UUID] = Field(default=None, foreign_key="subjects.id")
    current_topic: Optional[str] = Field(default=None, max_length=255)
    difficulty_level: Optional[str] = Field(default=None, max_length=20)
    learning_progress: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # Progress tracking data
    preferences: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # User preferences and settings
    last_interaction: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2. Indexes for Performance

```python
# src/models/database.py
from sqlmodel import SQLModel, Field, Index
from sqlalchemy import Index as SQLIndex

# Add indexes to models for better performance
class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    
    # ... existing fields ...
    
    __table_args__ = (
        SQLIndex("idx_conversations_student_session", "student_id", "session_id"),
        SQLIndex("idx_conversations_created_at", "created_at"),
    )

class KnowledgeBase(SQLModel, table=True):
    __tablename__ = "knowledge_base"
    
    # ... existing fields ...
    
    __table_args__ = (
        SQLIndex("idx_knowledge_base_subject_topic", "subject_id", "topic"),
        SQLIndex("idx_knowledge_base_tags", "tags", postgresql_using="gin"),
    )

class StudentContext(SQLModel, table=True):
    __tablename__ = "student_context"
    
    # ... existing fields ...
    
    __table_args__ = (
        SQLIndex("idx_student_context_student_subject", "student_id", "subject_id"),
    )
```

## Database Connection Setup

### 1. SQLModel Database Configuration

```python
# src/core/database.py
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import logging

from .config import get_settings

logger = logging.getLogger(__name__)

# Create database engine
def create_database_engine():
    """Create database engine with SQLModel"""
    settings = get_settings()
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.LOG_LEVEL == "DEBUG",
        pool_pre_ping=True,
        pool_recycle=300,
    )
    return engine

# Global engine instance
engine = create_database_engine()

def init_db():
    """Initialize database tables"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise

def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()
```

### 2. Alembic Configuration for SQLModel

```python
# alembic/env.py
import sqlmodel
from sqlmodel import SQLModel
from alembic import context

# Import all your models to ensure they're registered
from src.models.database import Student, Subject, KnowledgeBase, Conversation, StudentContext

# Use SQLModel metadata for migrations
target_metadata = SQLModel.metadata

# Rest of your Alembic configuration...
```

## Core Components

### 1. Base LLM Service Interface

```python
# src/services/llm/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from pydantic import BaseModel
from ...core.config import LLMConfig

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

### 2. LLM Service Factory

```python
# src/services/llm/factory.py
from typing import Dict, Optional
from ...core.config import LLMConfig, LLMProvider
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

### 3. Gemini Provider Implementation

```python
# src/services/llm/providers/gemini.py
import google.generativeai as genai
from typing import Dict, Any, Optional, List, AsyncGenerator
import asyncio
import logging

from ..base import BaseLLMService, LLMRequest, LLMResponse
from ...core.config import LLMConfig, LLMProvider

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

### 4. LLM Service Manager (SRP-Compliant)

```python
# src/services/llm_service.py
from typing import Dict, Any, Optional, List, AsyncGenerator
from ..core.config import Settings, LLMConfig
from .llm.base import BaseLLMService, LLMRequest, LLMResponse
from .llm.factory import LLMServiceFactory
import logging

logger = logging.getLogger(__name__)

class LLMServiceManager:
    """Manages LLM service instances and provider selection"""
    
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
    
    def get_service(self, provider: Optional[str] = None) -> BaseLLMService:
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

class LLMResponseGenerator:
    """Handles LLM response generation operations"""
    
    def __init__(self, service_manager: LLMServiceManager):
        self.service_manager = service_manager
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        provider: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using specified or default provider"""
        service = self.service_manager.get_service(provider)
        request = LLMRequest(messages=messages, **kwargs)
        return await service.generate_response(request)
    
    async def generate_streaming_response(
        self, 
        messages: List[Dict[str, str]], 
        provider: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using specified or default provider"""
        service = self.service_manager.get_service(provider)
        request = LLMRequest(messages=messages, stream=True, **kwargs)
        async for chunk in service.generate_streaming_response(request):
            yield chunk

class LLMIntentClassifier:
    """Handles intent classification using LLM services"""
    
    def __init__(self, service_manager: LLMServiceManager):
        self.service_manager = service_manager
    
    async def classify_intent(
        self, 
        message: str, 
        context: Dict[str, Any], 
        provider: Optional[str] = None
    ) -> str:
        """Classify user intent using specified or default provider"""
        service = self.service_manager.get_service(provider)
        return await service.classify_intent(message, context)

class LLMTopicExtractor:
    """Handles topic extraction using LLM services"""
    
    def __init__(self, service_manager: LLMServiceManager):
        self.service_manager = service_manager
    
    async def extract_topic(
        self, 
        message: str, 
        subject_context: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Optional[str]:
        """Extract topic from message using specified or default provider"""
        service = self.service_manager.get_service(provider)
        return await service.extract_topic(message, subject_context)
```

### 5. Base Agent Class

```python
# src/agents/base/agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
import logging

logger = logging.getLogger(__name__)

class AgentState(BaseModel):
    """Base state for all agents"""
    user_id: str
    session_id: str
    message: str
    context: Dict[str, Any] = {}
    response: Optional[str] = None
    metadata: Dict[str, Any] = {}
    next_agent: Optional[str] = None

class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"agent.{name}")
        
    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        """Process the current state and return updated state"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this agent can handle"""
        pass
    
    def should_handle(self, intent: str, context: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the given intent"""
        return intent in self.get_capabilities()
    
    async def validate_input(self, state: AgentState) -> bool:
        """Validate input state before processing"""
        if not state.user_id or not state.message:
            self.logger.error("Invalid input: missing user_id or message")
            return False
        return True
    
    def create_response(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Create standardized response format"""
        response = {
            "content": content,
            "agent": self.name,
            "metadata": metadata or {}
        }
        return response
```

### 6. Orchestrator Components (SRP-Compliant)

```python
# src/agents/base/intent_classifier.py
from typing import Dict, Any
from ...services.llm_service import LLMIntentClassifier
import logging

logger = logging.getLogger(__name__)

class IntentClassifier:
    """Handles user intent classification"""
    
    def __init__(self, intent_classifier: LLMIntentClassifier):
        self.intent_classifier = intent_classifier
        
    async def classify_intent(self, message: str, context: Dict[str, Any]) -> str:
        """Classify user intent using LLM service"""
        try:
            return await self.intent_classifier.classify_intent(message, context)
        except Exception as e:
            logger.error(f"Intent classification error: {str(e)}")
            return "unclear"

# src/agents/base/agent_selector.py
from typing import Dict, List, Optional
from .agent import BaseAgent
from ..registry import AgentRegistry

class AgentSelector:
    """Handles agent selection based on intent and context"""
    
    def __init__(self, agent_registry: AgentRegistry):
        self.agent_registry = agent_registry
    
    async def select_agent(self, intent: str, context: Dict[str, Any]) -> Optional[BaseAgent]:
        """Select the most appropriate agent for the intent"""
        available_agents = self.agent_registry.get_agents()
        
        for agent in available_agents:
            if agent.should_handle(intent, context):
                return agent
                
        return None

# src/agents/base/response_generator.py
class ResponseGenerator:
    """Handles response generation for different scenarios"""
    
    @staticmethod
    def create_fallback_response(intent: str) -> str:
        """Create fallback response when no agent can handle the intent"""
        return f"I understand you're asking about {intent}, but I need more information to help you effectively. Could you please provide more details?"
    
    @staticmethod
    def create_error_response() -> str:
        """Create error response for technical difficulties"""
        return "I'm experiencing some technical difficulties. Please try again in a moment."

# src/agents/base/orchestrator.py
from typing import Dict, List, Optional
from langgraph.graph import StateGraph, END
from .agent import BaseAgent, AgentState
from .intent_classifier import IntentClassifier
from .agent_selector import AgentSelector
from .response_generator import ResponseGenerator
import logging

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """Central orchestrator that coordinates request processing"""
    
    def __init__(self, intent_classifier: IntentClassifier, agent_selector: AgentSelector):
        super().__init__("orchestrator", "Coordinates request processing")
        self.intent_classifier = intent_classifier
        self.agent_selector = agent_selector
        self.response_generator = ResponseGenerator()
        
    async def process(self, state: AgentState) -> AgentState:
        """Main orchestration logic"""
        try:
            # 1. Classify user intent
            intent = await self.intent_classifier.classify_intent(state.message, state.context)
            state.metadata["intent"] = intent
            
            # 2. Select appropriate agent
            selected_agent = await self.agent_selector.select_agent(intent, state.context)
            state.metadata["selected_agent"] = selected_agent.name if selected_agent else None
            
            # 3. Route to selected agent
            if selected_agent:
                state.next_agent = selected_agent.name
                self.logger.info(f"Routed to {selected_agent.name} for intent: {intent}")
            else:
                state.response = self.response_generator.create_fallback_response(intent)
                state.next_agent = END
                
        except Exception as e:
            self.logger.error(f"Orchestration error: {str(e)}")
            state.response = self.response_generator.create_error_response()
            state.next_agent = END
            
        return state
    
    def get_capabilities(self) -> List[str]:
        return ["intent_classification", "agent_routing", "fallback_handling"]
```

### 7. Context Management Components (SRP-Compliant)

```python
# src/agents/base/student_context_manager.py
from typing import Dict, Any, Optional
from sqlmodel import Session, select
from ...models.database import StudentContext

class StudentContextManager:
    """Manages student context data"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    async def get_student_context(self, student_id: str, subject_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve student's current context"""
        statement = select(StudentContext).where(StudentContext.student_id == student_id)
        
        if subject_id:
            statement = statement.where(StudentContext.subject_id == subject_id)
            
        contexts = self.db.exec(statement).all()
        
        return {
            "current_topics": [ctx.current_topic for ctx in contexts if ctx.current_topic],
            "difficulty_levels": {ctx.subject_id: ctx.difficulty_level for ctx in contexts},
            "learning_progress": {ctx.subject_id: ctx.learning_progress for ctx in contexts},
            "preferences": {ctx.subject_id: ctx.preferences for ctx in contexts}
        }
    
    async def update_context(self, student_id: str, subject_id: str, updates: Dict[str, Any]):
        """Update student context"""
        statement = select(StudentContext).where(
            StudentContext.student_id == student_id,
            StudentContext.subject_id == subject_id
        )
        context = self.db.exec(statement).first()
        
        if not context:
            context = StudentContext(
                student_id=student_id,
                subject_id=subject_id
            )
            self.db.add(context)
        
        # Update fields
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
                
        self.db.commit()

# src/agents/base/conversation_manager.py
from typing import Dict, Any, List
from sqlmodel import Session, select
from ...models.database import Conversation

class ConversationManager:
    """Manages conversation data and history"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def save_conversation(self, conversation_data: Dict[str, Any]):
        """Save conversation to database"""
        conversation = Conversation(**conversation_data)
        self.db.add(conversation)
        self.db.commit()
    
    async def get_recent_conversations(self, student_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        statement = select(Conversation).where(
            Conversation.student_id == student_id
        ).order_by(Conversation.created_at.desc()).limit(limit)
        conversations = self.db.exec(statement).all()
        
        return [
            {
                "message": conv.user_message,
                "response": conv.agent_response,
                "agent": conv.agent_type,
                "timestamp": conv.created_at.isoformat()
            }
            for conv in conversations
        ]

# src/agents/base/context_manager.py
from typing import Dict, Any, Optional
from .student_context_manager import StudentContextManager
from .conversation_manager import ConversationManager

class ContextManager:
    """Facade for context management operations"""
    
    def __init__(self, student_context_manager: StudentContextManager, conversation_manager: ConversationManager):
        self.student_context_manager = student_context_manager
        self.conversation_manager = conversation_manager
        
    async def get_student_context(self, student_id: str, subject_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve student's current context"""
        return await self.student_context_manager.get_student_context(student_id, subject_id)
    
    async def update_context(self, student_id: str, subject_id: str, updates: Dict[str, Any]):
        """Update student context"""
        await self.student_context_manager.update_context(student_id, subject_id, updates)
    
    async def save_conversation(self, conversation_data: Dict[str, Any]):
        """Save conversation to database"""
        await self.conversation_manager.save_conversation(conversation_data)
    
    async def get_recent_conversations(self, student_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        return await self.conversation_manager.get_recent_conversations(student_id, limit)
```

## Agent Implementations

### 1. Syllabus Agent

```python
# src/agents/information/syllabus_agent.py
from typing import Dict, List, Any
from ..base.agent import BaseAgent, AgentState
from ...services.knowledge_base import KnowledgeBaseService
from ...services.subject_manager import SubjectManager
import logging

logger = logging.getLogger(__name__)

class SyllabusAgent(BaseAgent):
    """Handles curriculum queries, course structure, and prerequisites"""
    
    def __init__(self, knowledge_service: KnowledgeBaseService, subject_manager: SubjectManager):
        super().__init__("syllabus", "Handles curriculum and course structure queries")
        self.knowledge_service = knowledge_service
        self.subject_manager = subject_manager
        
    async def process(self, state: AgentState) -> AgentState:
        """Process syllabus-related queries"""
        try:
            if not await self.validate_input(state):
                state.response = self._create_error_response("Invalid input provided")
                return state
            
            # Extract query details
            query_type = await self._classify_syllabus_query(state.message)
            subject_id = state.context.get("subject_id")
            
            if query_type == "course_structure":
                response = await self._get_course_structure(subject_id)
            elif query_type == "prerequisites":
                response = await self._get_prerequisites(subject_id)
            elif query_type == "learning_objectives":
                response = await self._get_learning_objectives(subject_id)
            elif query_type == "assessment_methods":
                response = await self._get_assessment_methods(subject_id)
            else:
                response = await self._get_general_syllabus_info(subject_id)
            
            state.response = self.create_response(response, {
                "query_type": query_type,
                "subject_id": subject_id
            })
            
        except Exception as e:
            logger.error(f"Syllabus agent error: {str(e)}")
            state.response = self._create_error_response("Unable to retrieve syllabus information")
            
        return state
    
    async def _classify_syllabus_query(self, message: str) -> str:
        """Classify the type of syllabus query"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["structure", "outline", "topics", "chapters"]):
            return "course_structure"
        elif any(word in message_lower for word in ["prerequisite", "required", "before", "prior"]):
            return "prerequisites"
        elif any(word in message_lower for word in ["objective", "goal", "learn", "outcome"]):
            return "learning_objectives"
        elif any(word in message_lower for word in ["exam", "assessment", "test", "evaluation"]):
            return "assessment_methods"
        else:
            return "general_info"
    
    async def _get_course_structure(self, subject_id: str) -> str:
        """Get course structure and topics"""
        topics = await self.knowledge_service.get_topics_by_subject(subject_id, content_type="syllabus")
        
        if not topics:
            return f"I don't have detailed course structure information for this subject yet."
        
        response = "Here's the course structure:\n\n"
        for i, topic in enumerate(topics, 1):
            response += f"{i}. {topic['title']}\n"
            if topic.get('description'):
                response += f"   {topic['description']}\n"
        
        return response
    
    async def _get_prerequisites(self, subject_id: str) -> str:
        """Get course prerequisites"""
        subject_info = await self.subject_manager.get_subject_info(subject_id)
        
        if not subject_info or not subject_info.get('prerequisites'):
            return "No specific prerequisites are listed for this course."
        
        prereqs = subject_info['prerequisites']
        response = "Prerequisites for this course:\n\n"
        
        for prereq in prereqs:
            prereq_info = await self.subject_manager.get_subject_info(prereq)
            if prereq_info:
                response += f"• {prereq_info['display_name']}\n"
        
        return response
    
    def get_capabilities(self) -> List[str]:
        return [
            "syllabus_query",
            "course_structure",
            "prerequisites",
            "learning_objectives",
            "assessment_methods"
        ]
```

### 2. Administration Agent

```python
# src/agents/information/administration_agent.py
from typing import Dict, List, Any
from ..base.agent import BaseAgent, AgentState
from ...services.knowledge_base import KnowledgeBaseService
import logging

logger = logging.getLogger(__name__)

class AdministrationAgent(BaseAgent):
    """Manages institutional policies, procedures, and deadlines"""
    
    def __init__(self, knowledge_service: KnowledgeBaseService):
        super().__init__("administration", "Handles institutional policies and procedures")
        self.knowledge_service = knowledge_service
        
    async def process(self, state: AgentState) -> AgentState:
        """Process administration-related queries"""
        try:
            if not await self.validate_input(state):
                state.response = self._create_error_response("Invalid input provided")
                return state
            
            query_type = await self._classify_admin_query(state.message)
            
            if query_type == "deadlines":
                response = await self._get_deadlines(state.message)
            elif query_type == "policies":
                response = await self._get_policies(state.message)
            elif query_type == "procedures":
                response = await self._get_procedures(state.message)
            elif query_type == "contact_info":
                response = await self._get_contact_info(state.message)
            else:
                response = await self._get_general_admin_info(state.message)
            
            state.response = self.create_response(response, {
                "query_type": query_type
            })
            
        except Exception as e:
            logger.error(f"Administration agent error: {str(e)}")
            state.response = self._create_error_response("Unable to retrieve administrative information")
            
        return state
    
    async def _classify_admin_query(self, message: str) -> str:
        """Classify the type of administration query"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["deadline", "due", "date", "when"]):
            return "deadlines"
        elif any(word in message_lower for word in ["policy", "rule", "regulation"]):
            return "policies"
        elif any(word in message_lower for word in ["procedure", "process", "how to", "steps"]):
            return "procedures"
        elif any(word in message_lower for word in ["contact", "email", "phone", "office"]):
            return "contact_info"
        else:
            return "general_info"
    
    async def _get_deadlines(self, message: str) -> str:
        """Get relevant deadlines"""
        # Query knowledge base for deadline information
        deadlines = await self.knowledge_service.search_content(
            query=message,
            content_type="deadline",
            limit=5
        )
        
        if not deadlines:
            return "I don't have specific deadline information for your query. Please contact the administration office for the most current information."
        
        response = "Here are the relevant deadlines:\n\n"
        for deadline in deadlines:
            response += f"• {deadline['title']}\n"
            if deadline.get('content'):
                response += f"  {deadline['content']}\n"
        
        return response
    
    def get_capabilities(self) -> List[str]:
        return [
            "admin_query",
            "deadlines",
            "policies",
            "procedures",
            "contact_info"
        ]
```

### 3. Topic Expert Agent Components (SRP-Compliant)

```python
# src/agents/information/topic_extractor.py
from typing import Optional
from ...services.llm_service import LLMTopicExtractor
import logging

logger = logging.getLogger(__name__)

class TopicExtractor:
    """Handles topic extraction from user messages"""
    
    def __init__(self, topic_extractor: LLMTopicExtractor):
        self.topic_extractor = topic_extractor
    
    async def extract_topic(self, message: str) -> Optional[str]:
        """Extract the specific topic from the user message using LLM"""
        try:
            return await self.topic_extractor.extract_topic(message)
        except Exception as e:
            logger.error(f"Topic extraction error: {str(e)}")
            # Fallback to simple extraction
            return self._simple_topic_extraction(message)
    
    def _simple_topic_extraction(self, message: str) -> Optional[str]:
        """Fallback simple topic extraction"""
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

# src/agents/information/subject_inferencer.py
from typing import Optional, List, Dict, Any
from ...services.subject_manager import SubjectManager

class SubjectInferencer:
    """Handles subject inference from user messages"""
    
    def __init__(self, subject_manager: SubjectManager):
        self.subject_manager = subject_manager
    
    async def infer_subject(self, message: str) -> Optional[str]:
        """Infer the subject from the message content"""
        # Get all available subjects
        subjects = await self.subject_manager.get_all_subjects()
        
        message_lower = message.lower()
        
        # Check for subject keywords
        for subject in subjects:
            subject_keywords = subject.get('keywords', [])
            if any(keyword.lower() in message_lower for keyword in subject_keywords):
                return subject['id']
        
        return None

# src/agents/information/explanation_generator.py
from typing import Dict, List, Any
from ...services.knowledge_base import KnowledgeBaseService

class ExplanationGenerator:
    """Handles topic explanation generation"""
    
    def __init__(self, knowledge_service: KnowledgeBaseService):
        self.knowledge_service = knowledge_service
    
    async def generate_explanation(self, subject_id: str, topic: str, difficulty_level: str, context: Dict) -> str:
        """Get comprehensive topic explanation"""
        # Search for relevant knowledge base entries
        knowledge_entries = await self.knowledge_service.search_content(
            query=topic,
            subject_id=subject_id,
            difficulty_level=difficulty_level,
            limit=5
        )
        
        if not knowledge_entries:
            return f"I don't have detailed information about '{topic}' in the {subject_id} subject yet. Please try rephrasing your question or contact your instructor."
        
        # Build comprehensive explanation
        explanation = f"Here's an explanation of {topic}:\n\n"
        
        for entry in knowledge_entries:
            explanation += f"**{entry['title']}**\n"
            explanation += f"{entry['content']}\n\n"
            
            # Add examples if available
            if entry.get('metadata', {}).get('examples'):
                explanation += "Examples:\n"
                for example in entry['metadata']['examples']:
                    explanation += f"• {example}\n"
                explanation += "\n"
        
        # Add related topics
        related_topics = await self._get_related_topics(subject_id, topic)
        if related_topics:
            explanation += "Related topics you might find helpful:\n"
            for related in related_topics:
                explanation += f"• {related}\n"
        
        return explanation
    
    async def _get_related_topics(self, subject_id: str, topic: str) -> List[str]:
        """Get related topics for the current subject"""
        # This would use semantic search or predefined relationships
        related = await self.knowledge_service.get_related_topics(subject_id, topic, limit=3)
        return [r['title'] for r in related]

# src/agents/information/topic_expert_agent.py
from typing import Dict, List, Any, Optional
from ..base.agent import BaseAgent, AgentState
from .topic_extractor import TopicExtractor
from .subject_inferencer import SubjectInferencer
from .explanation_generator import ExplanationGenerator
import logging

logger = logging.getLogger(__name__)

class TopicExpertAgent(BaseAgent):
    """Provides detailed explanations of specific subjects - extensible for any subject"""
    
    def __init__(self, topic_extractor: TopicExtractor, subject_inferencer: SubjectInferencer, explanation_generator: ExplanationGenerator):
        super().__init__("topic_expert", "Provides detailed subject explanations")
        self.topic_extractor = topic_extractor
        self.subject_inferencer = subject_inferencer
        self.explanation_generator = explanation_generator
        
    async def process(self, state: AgentState) -> AgentState:
        """Process topic explanation queries"""
        try:
            if not await self.validate_input(state):
                state.response = self._create_error_response("Invalid input provided")
                return state
            
            # Extract subject and topic information
            subject_id = state.context.get("subject_id")
            topic = await self.topic_extractor.extract_topic(state.message)
            difficulty_level = state.context.get("difficulty_level", "intermediate")
            
            if not subject_id:
                # Try to infer subject from message
                subject_id = await self.subject_inferencer.infer_subject(state.message)
            
            if not subject_id:
                state.response = self._create_error_response("Please specify which subject you're asking about")
                return state
            
            # Get topic explanation
            explanation = await self.explanation_generator.generate_explanation(
                subject_id, topic, difficulty_level, state.context
            )
            
            state.response = self.create_response(explanation, {
                "subject_id": subject_id,
                "topic": topic,
                "difficulty_level": difficulty_level
            })
            
        except Exception as e:
            logger.error(f"Topic expert agent error: {str(e)}")
            state.response = self._create_error_response("Unable to provide topic explanation")
            
        return state
    
    def get_capabilities(self) -> List[str]:
        return [
            "topic_explanation",
            "concept_definition",
            "subject_help",
            "learning_support"
        ]
```

## API Layer

### 1. FastAPI Application Setup (SRP-Compliant)

```python
# src/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .core.config import get_settings
from .core.database import get_db, init_db
from .api.v1 import chat, agents, subjects
from .agents.registry import AgentRegistry
from .services.knowledge_base import KnowledgeBaseService
from .services.subject_manager import SubjectManager
from .services.subject_creator import SubjectCreator
from .services.subject_retriever import SubjectRetriever
from .services.llm_service import LLMServiceManager, LLMResponseGenerator, LLMIntentClassifier, LLMTopicExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Education Chatbot API")
    
    # Initialize database
    await init_db()
    
    # Initialize services with SRP-compliant structure
    db_session = next(get_db())
    
    # Initialize subject management components
    subject_creator = SubjectCreator(db_session)
    subject_retriever = SubjectRetriever(db_session)
    app.state.subject_manager = SubjectManager(subject_creator, subject_retriever)
    
    # Initialize knowledge service
    app.state.knowledge_service = KnowledgeBaseService(db_session)
    
    # Initialize LLM service components
    settings = get_settings()
    app.state.llm_service_manager = LLMServiceManager(settings)
    await app.state.llm_service_manager.initialize()
    
    app.state.llm_response_generator = LLMResponseGenerator(app.state.llm_service_manager)
    app.state.llm_intent_classifier = LLMIntentClassifier(app.state.llm_service_manager)
    app.state.llm_topic_extractor = LLMTopicExtractor(app.state.llm_service_manager)
    
    # Initialize agent registry with LLM service components
    app.state.agent_registry = AgentRegistry()
    await app.state.agent_registry.initialize(
        app.state.llm_response_generator,
        app.state.llm_intent_classifier,
        app.state.llm_topic_extractor
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down Education Chatbot API")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="Education Chatbot API",
        description="Multi-agent educational support system",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(subjects.router, prefix="/api/v1/subjects", tags=["subjects"])
    
    return app

app = create_app()

@app.get("/")
async def root():
    return {"message": "Education Chatbot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

### 2. Chat API Endpoints

```python
# src/api/v1/chat.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid

from ...core.database import get_db
from ...agents.registry import AgentRegistry
from ...agents.base.context_manager import ContextManager
from ...services.knowledge_base import KnowledgeBaseService

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None
    subject_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = {}

class ChatResponse(BaseModel):
    response: str
    agent: str
    session_id: str
    metadata: Dict[str, Any]

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db=Depends(get_db),
    agent_registry: AgentRegistry = Depends(lambda: app.state.agent_registry),
    knowledge_service: KnowledgeBaseService = Depends(lambda: app.state.knowledge_service)
):
    """Main chat endpoint"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Initialize context manager
        context_manager = ContextManager(db, knowledge_service)
        
        # Get or create user context
        user_context = await context_manager.get_student_context(
            request.user_id, request.subject_id
        )
        
        # Merge with request context
        full_context = {**user_context, **request.context}
        full_context["subject_id"] = request.subject_id
        
        # Process through orchestrator
        orchestrator = agent_registry.get_agent("orchestrator")
        
        from ...agents.base.agent import AgentState
        state = AgentState(
            user_id=request.user_id,
            session_id=session_id,
            message=request.message,
            context=full_context
        )
        
        # Process the request
        result_state = await orchestrator.process(state)
        
        # Save conversation
        await context_manager.save_conversation({
            "student_id": request.user_id,
            "session_id": session_id,
            "agent_type": result_state.metadata.get("selected_agent", "orchestrator"),
            "subject_id": request.subject_id,
            "user_message": request.message,
            "agent_response": result_state.response,
            "intent_classification": result_state.metadata.get("intent", {}),
            "response_time_ms": result_state.metadata.get("response_time_ms", 0)
        })
        
        return ChatResponse(
            response=result_state.response,
            agent=result_state.metadata.get("selected_agent", "orchestrator"),
            session_id=session_id,
            metadata=result_state.metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")

@router.get("/history/{user_id}")
async def get_chat_history(
    user_id: str,
    limit: int = 20,
    db=Depends(get_db),
    knowledge_service: KnowledgeBaseService = Depends(lambda: app.state.knowledge_service)
):
    """Get chat history for a user"""
    context_manager = ContextManager(db, knowledge_service)
    history = await context_manager.get_recent_conversations(user_id, limit)
    return {"history": history}
```

## Configuration & Environment

### 1. Environment Configuration

```python
# src/core/config.py
from pydantic_settings import BaseSettings
from pydantic import BaseModel
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
    MAX_RESPONSE_TIME: int = 30  # seconds
    DEFAULT_DIFFICULTY_LEVEL: str = "intermediate"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

def get_settings() -> Settings:
    return Settings()
```

### 2. Environment File Template

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
DEFAULT_LLM_PROVIDER=openai

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

## Testing Strategy

### 1. Unit Tests

```python
# tests/test_agents/test_syllabus_agent.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.agents.information.syllabus_agent import SyllabusAgent
from src.agents.base.agent import AgentState

@pytest.fixture
def syllabus_agent():
    knowledge_service = AsyncMock()
    subject_manager = AsyncMock()
    return SyllabusAgent(knowledge_service, subject_manager)

@pytest.mark.asyncio
async def test_syllabus_agent_course_structure(syllabus_agent):
    """Test syllabus agent handling course structure queries"""
    # Mock knowledge service response
    syllabus_agent.knowledge_service.get_topics_by_subject.return_value = [
        {"title": "Introduction to Calculus", "description": "Basic concepts"},
        {"title": "Derivatives", "description": "Rate of change"}
    ]
    
    state = AgentState(
        user_id="test_user",
        session_id="test_session",
        message="What is the course structure for mathematics?",
        context={"subject_id": "math_101"}
    )
    
    result = await syllabus_agent.process(state)
    
    assert result.response is not None
    assert "course structure" in result.response.lower()
    assert "Introduction to Calculus" in result.response
```

### 2. Integration Tests

```python
# tests/test_integration/test_chat_flow.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_chat_endpoint():
    """Test complete chat flow"""
    response = client.post("/api/v1/chat/", json={
        "message": "What is the syllabus for mathematics?",
        "user_id": "test_user",
        "subject_id": "math_101"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "agent" in data
    assert "session_id" in data
```

## Dependencies

### 1. Project Dependencies

```toml
# pyproject.toml
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
    "sqlmodel>=0.0.14",
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

## Deployment Setup

### 1. Docker Configuration

```dockerfile
# docker/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY pyproject.toml .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/education_chatbot
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=education_chatbot
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## Subject Extensibility Design

### 1. Subject Management Components (SRP-Compliant)

```python
# src/services/subject_creator.py
from typing import Dict, Any
from sqlmodel import Session
from ..models.database import Subject
import json

class SubjectCreator:
    """Handles subject creation operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    async def create_subject(self, subject_data: Dict[str, Any]) -> str:
        """Create a new subject with full configuration"""
        subject = Subject(
            name=subject_data["name"],
            display_name=subject_data["display_name"],
            description=subject_data.get("description", ""),
            category=subject_data.get("category", "general"),
            difficulty_levels=subject_data.get("difficulty_levels", ["beginner", "intermediate", "advanced"]),
            prerequisites=subject_data.get("prerequisites", []),
            metadata=subject_data.get("metadata", {})
        )
        
        self.db.add(subject)
        self.db.commit()
        self.db.refresh(subject)
        
        return str(subject.id)

# src/services/subject_retriever.py
from typing import Dict, List, Any, Optional
from sqlmodel import Session, select
from ..models.database import Subject
import json

class SubjectRetriever:
    """Handles subject retrieval operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def get_subject_info(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """Get subject information"""
        statement = select(Subject).where(Subject.id == subject_id)
        subject = self.db.exec(statement).first()
        
        if not subject:
            return None
            
        return {
            "id": str(subject.id),
            "name": subject.name,
            "display_name": subject.display_name,
            "description": subject.description,
            "category": subject.category,
            "difficulty_levels": subject.difficulty_levels,
            "prerequisites": subject.prerequisites,
            "metadata": subject.metadata
        }
    
    async def get_all_subjects(self) -> List[Dict[str, Any]]:
        """Get all active subjects"""
        statement = select(Subject).where(Subject.is_active == True)
        subjects = self.db.exec(statement).all()
        
        return [
            {
                "id": str(subject.id),
                "name": subject.name,
                "display_name": subject.display_name,
                "category": subject.category,
                "keywords": subject.metadata.get("keywords", []) if subject.metadata else []
            }
            for subject in subjects
        ]

# src/services/subject_manager.py
from typing import Dict, List, Any, Optional
from .subject_creator import SubjectCreator
from .subject_retriever import SubjectRetriever

class SubjectManager:
    """Facade for subject management operations"""
    
    def __init__(self, subject_creator: SubjectCreator, subject_retriever: SubjectRetriever):
        self.subject_creator = subject_creator
        self.subject_retriever = subject_retriever
        
    async def create_subject(self, subject_data: Dict[str, Any]) -> str:
        """Create a new subject with full configuration"""
        return await self.subject_creator.create_subject(subject_data)
    
    async def get_subject_info(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """Get subject information"""
        return await self.subject_retriever.get_subject_info(subject_id)
    
    async def get_all_subjects(self) -> List[Dict[str, Any]]:
        """Get all active subjects"""
        return await self.subject_retriever.get_all_subjects()
```

### 2. Knowledge Base Initialization

```python
# src/services/knowledge_base.py
from typing import Dict, List, Any, Optional
from sqlmodel import Session, select
from ..models.database import KnowledgeBase
from ..core.database import get_db
import json
import os

class KnowledgeBaseService:
    """Manages knowledge base operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    async def initialize_subject_knowledge(self, subject_id: str):
        """Initialize knowledge base for a new subject"""
        # Load template knowledge structure
        template_path = "data/knowledge_base/templates/subject_template.json"
        
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                template = json.load(f)
            
            # Create knowledge entries from template
            for entry in template["knowledge_entries"]:
                knowledge_entry = KnowledgeBase(
                    subject_id=subject_id,
                    topic=entry["topic"],
                    subtopic=entry.get("subtopic"),
                    content_type=entry["content_type"],
                    title=entry["title"],
                    content=entry["content"],
                    metadata=entry.get("metadata", {}),
                    difficulty_level=entry.get("difficulty_level", "intermediate"),
                    tags=entry.get("tags", [])
                )
                self.db.add(knowledge_entry)
            
            self.db.commit()
    
    async def add_knowledge_entry(self, entry_data: Dict[str, Any]) -> str:
        """Add a new knowledge entry"""
        entry = KnowledgeBase(
            subject_id=entry_data["subject_id"],
            topic=entry_data["topic"],
            subtopic=entry_data.get("subtopic"),
            content_type=entry_data["content_type"],
            title=entry_data["title"],
            content=entry_data["content"],
            metadata=entry_data.get("metadata", {}),
            difficulty_level=entry_data.get("difficulty_level", "intermediate"),
            tags=entry_data.get("tags", [])
        )
        
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        
        return str(entry.id)
```

## Expected Agent Outputs

### 1. Syllabus Agent Output Example

```json
{
  "response": "Here's the course structure for Mathematics 101:\n\n1. Introduction to Calculus\n   Basic concepts of limits and continuity\n\n2. Derivatives\n   Rate of change and applications\n\n3. Integration\n   Antiderivatives and definite integrals\n\n4. Applications\n   Optimization and related rates\n\nPrerequisites: Basic algebra and trigonometry",
  "agent": "syllabus",
  "metadata": {
    "query_type": "course_structure",
    "subject_id": "math_101",
    "response_time_ms": 1200
  }
}
```

### 2. Administration Agent Output Example

```json
{
  "response": "Here are the relevant deadlines:\n\n• Midterm Exam: March 15, 2024\n• Assignment 3 Due: March 20, 2024\n• Final Project Submission: April 30, 2024\n\nFor more specific information about any deadline, please contact the mathematics department office.",
  "agent": "administration",
  "metadata": {
    "query_type": "deadlines",
    "response_time_ms": 800
  }
}
```

### 3. Topic Expert Agent Output Example

```json
{
  "response": "Here's an explanation of derivatives:\n\n**What are Derivatives?**\nA derivative represents the rate of change of a function at any given point. It tells us how fast a quantity is changing.\n\n**Mathematical Definition**\nThe derivative of f(x) is: f'(x) = lim(h→0) [f(x+h) - f(x)]/h\n\n**Examples:**\n• If f(x) = x², then f'(x) = 2x\n• If f(x) = 3x + 5, then f'(x) = 3\n\n**Applications:**\n• Finding maximum and minimum values\n• Analyzing motion and velocity\n• Optimization problems\n\nRelated topics you might find helpful:\n• Limits and continuity\n• Integration\n• Applications of derivatives",
  "agent": "topic_expert",
  "metadata": {
    "subject_id": "math_101",
    "topic": "derivatives",
    "difficulty_level": "intermediate",
    "response_time_ms": 2100
  }
}
```

## LLM Integration Benefits

### 1. **Flexibility**
- Easy switching between LLM providers (OpenAI, Anthropic, Google Gemini, Ollama)
- Support for multiple providers simultaneously
- Simple addition of new providers through the factory pattern

### 2. **Scalability**
- Provider-specific optimizations
- Load balancing across providers
- Fallback mechanisms for reliability

### 3. **Maintainability**
- Clean separation of concerns with abstract base classes
- Standardized interfaces across all providers
- Easy testing and mocking capabilities

### 4. **Cost Optimization**
- Use different providers for different tasks
- Provider-specific rate limiting
- Cost monitoring per provider

### 5. **Future-Proofing**
- Easy integration of new models and providers
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

## Single Responsibility Principle (SRP) Compliance

This implementation has been refactored to strictly follow the Single Responsibility Principle, ensuring each class has only one reason to change. Here are the key improvements:

### 1. LLM Service Decomposition
**Before**: `LLMService` handled service management, response generation, intent classification, topic extraction, and connection validation.

**After**: 
- `LLMServiceManager`: Manages LLM service instances and provider selection
- `LLMResponseGenerator`: Handles response generation operations
- `LLMIntentClassifier`: Handles intent classification using LLM services
- `LLMTopicExtractor`: Handles topic extraction using LLM services

### 2. Orchestrator Agent Decomposition
**Before**: `OrchestratorAgent` handled intent classification, agent selection, routing, and fallback responses.

**After**:
- `IntentClassifier`: Handles user intent classification
- `AgentSelector`: Handles agent selection based on intent and context
- `ResponseGenerator`: Handles response generation for different scenarios
- `OrchestratorAgent`: Coordinates request processing (orchestration only)

### 3. Context Management Decomposition
**Before**: `ContextManager` handled context retrieval, updates, conversation saving, and history management.

**After**:
- `StudentContextManager`: Manages student context data
- `ConversationManager`: Manages conversation data and history
- `ContextManager`: Facade for context management operations

### 4. Topic Expert Agent Decomposition
**Before**: `TopicExpertAgent` handled topic extraction, subject inference, explanation generation, and subject management.

**After**:
- `TopicExtractor`: Handles topic extraction from user messages
- `SubjectInferencer`: Handles subject inference from user messages
- `ExplanationGenerator`: Handles topic explanation generation
- `TopicExpertAgent`: Coordinates topic explanation processing

### 5. Subject Management Decomposition
**Before**: `SubjectManager` handled subject creation, retrieval, and metadata management.

**After**:
- `SubjectCreator`: Handles subject creation operations
- `SubjectRetriever`: Handles subject retrieval operations
- `SubjectManager`: Facade for subject management operations

### Benefits of SRP Compliance

1. **Maintainability**: Each class has a single, well-defined responsibility, making it easier to understand and modify
2. **Testability**: Smaller, focused classes are easier to unit test
3. **Reusability**: Individual components can be reused in different contexts
4. **Extensibility**: New functionality can be added without modifying existing classes
5. **Debugging**: Issues can be isolated to specific components more easily
6. **Code Organization**: Clear separation of concerns improves code readability

### Design Patterns Used

- **Facade Pattern**: `ContextManager`, `SubjectManager` act as facades for related operations
- **Strategy Pattern**: Different LLM providers can be swapped without changing client code
- **Factory Pattern**: `LLMServiceFactory` creates appropriate LLM service instances
- **Dependency Injection**: Services are injected into classes that need them, promoting loose coupling

This comprehensive Phase 1 implementation provides a solid foundation for the multi-agent educational chatbot system, with particular emphasis on extensibility for adding new subjects, flexible LLM provider integration, and maintaining clean, modular architecture that strictly adheres to SOLID principles.
