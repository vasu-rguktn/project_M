"""
Configuration for Agent Service

Environment variables and model configuration for LangGraph + LangChain agents.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AgentConfig:
    """Configuration for agent service"""
    
    # Service Configuration
    AGENTS_SERVICE_PORT: int = int(os.getenv("AGENTS_SERVICE_PORT", "8001"))
    BACKEND_BASE_URL: str = os.getenv("BACKEND_BASE_URL", "http://localhost:4000")
    
    # LLM Configuration - Using Mistral (Free)
    MISTRAL_API_KEY: Optional[str] = os.getenv("MISTRAL_API_KEY")
    
    # Model Selection - Mistral only (free tier)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mistral")  # "mistral" only
    LLM_MODEL: str = os.getenv("LLM_MODEL", "mistral-small-latest")  # Free Mistral model
    
    # LangChain Tracing (optional)
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "chronoshift-agents")
    LANGCHAIN_API_KEY: Optional[str] = os.getenv("LANGCHAIN_API_KEY")
    
    # Agent Behavior
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "300"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.BACKEND_BASE_URL:
            raise ValueError("BACKEND_BASE_URL must be set")
        
        if cls.LLM_PROVIDER == "mistral" and not cls.MISTRAL_API_KEY:
            raise ValueError("MISTRAL_API_KEY must be set when using Mistral")
        
        return True
    
    @classmethod
    def get_llm_api_key(cls) -> str:
        """Get the Mistral API key"""
        if cls.LLM_PROVIDER == "mistral":
            if not cls.MISTRAL_API_KEY:
                raise ValueError("MISTRAL_API_KEY not set. Get your free API key from https://console.mistral.ai/")
            return cls.MISTRAL_API_KEY
        else:
            raise ValueError(f"Unknown LLM provider: {cls.LLM_PROVIDER}. Only 'mistral' is supported.")


# Validate configuration on import
try:
    AgentConfig.validate()
except ValueError as e:
    print(f"Warning: Configuration validation failed: {e}")
    print("Some features may not work until configuration is corrected.")
