"""
LLM Factory for creating language model instances.

Supports both OpenAI and Ollama (local Llama models).
"""
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

def get_llm(model_name: Optional[str] = None, temperature: float = 0.1, **kwargs):
    """
    Create an LLM instance based on environment configuration.
    
    Args:
        model_name: Model name (optional, uses env vars if not provided)
        temperature: Temperature for generation
        **kwargs: Additional arguments for LLM initialization
        
    Returns:
        LLM instance (ChatOpenAI or ChatOllama)
    """
    # Check which provider to use
    llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if llm_provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError(
                "langchain-ollama is not installed. Install it with: pip install langchain-ollama"
            )
        
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = model_name or os.getenv("OLLAMA_MODEL", "llama3.2")
        
        return ChatOllama(
            model=ollama_model,
            base_url=ollama_base_url,
            temperature=temperature,
            **kwargs
        )
    else:
        # Default to OpenAI
        from langchain_openai import ChatOpenAI
        
        openai_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o")
        
        return ChatOpenAI(
            model=openai_model,
            temperature=temperature,
            **kwargs
        )
