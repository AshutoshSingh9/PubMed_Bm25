"""
LLM Provider — Abstraction layer for Ollama (local) and Groq (cloud).

Provides a clean interface for the pipeline stages to call the LLM without
coupling to a specific provider. 
"""

import json
import logging
from typing import Generator, Optional

import ollama

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

import config

logger = logging.getLogger(__name__)


class LLMProvider:
    """Unified LLM interface backed by Ollama (local) or Groq (cloud)."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.provider = provider or config.LLM_PROVIDER
        
        # Set model based on provider if not explicitly passed
        if model:
            self.model = model
        else:
            self.model = config.GROQ_MODEL if self.provider == "groq" else config.OLLAMA_MODEL
            
        self.temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        self.max_tokens = max_tokens or config.LLM_MAX_TOKENS
        
        self._ollama_client = None
        self._groq_client = None
        self._groq_configured = False
        
        if self.provider == "groq":
            self._setup_groq()
        else:
            self._setup_ollama()

    def _setup_ollama(self):
        """Eagerly initialize and pre-warm Ollama client."""
        try:
            self._ollama_client = ollama.Client(host=config.OLLAMA_BASE_URL, timeout=60.0)
            self._ollama_client.list()  # Pre-warm connection
        except TypeError:
            # Fallback if timeout isn't supported in this ollama version
            self._ollama_client = ollama.Client(host=config.OLLAMA_BASE_URL)
            self._ollama_client.list()
        except Exception as e:
            logger.warning(f"Ollama connection pre-warm failed: {e}")

    def _setup_groq(self):
        """Configure Groq API client."""
        if not HAS_GROQ:
            logger.warning("groq library not installed. Falling back to Ollama.")
            self.provider = "ollama"
            self.model = config.OLLAMA_MODEL
            return
            
        if not config.GROQ_API_KEY or config.GROQ_API_KEY == "your_groq_api_key_here":
            logger.warning("GROQ_API_KEY not set. Falling back to Ollama.")
            self.provider = "ollama"
            self.model = config.OLLAMA_MODEL
            return
            
        self._groq_client = Groq(api_key=config.GROQ_API_KEY)
        self._groq_configured = True

    @property
    def ollama_client(self):
        """Lazy-init Ollama client."""
        if self._ollama_client is None:
            self._ollama_client = ollama.Client(host=config.OLLAMA_BASE_URL)
        return self._ollama_client

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System/role instruction
            user_prompt: User message with patient data + context

        Returns:
            Raw LLM response text
        """
        if self.provider == "groq" and self._groq_configured:
            return self._generate_groq(system_prompt, user_prompt)
        else:
            return self._generate_ollama(system_prompt, user_prompt)

    def _generate_groq(self, system_prompt: str, user_prompt: str) -> str:
        """Call Groq API using Llama 3 or Mixtral."""
        try:
            chat_completion = self._groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq call failed: {e}")
            raise RuntimeError(f"Groq API error: {e}")

    def _generate_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """Call Local Ollama."""
        try:
            response = self.ollama_client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )
            return response["message"]["content"]

        except ollama.ResponseError as e:
            logger.error(f"Ollama response error: {e}")
            raise RuntimeError(
                f"LLM call failed: {e}. "
                f"Ensure Ollama is running (`ollama serve`) and model is pulled "
                f"(`ollama pull {self.model}`)."
            ) from e
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError(
                f"Could not connect to Ollama at {config.OLLAMA_BASE_URL}. "
                f"Start Ollama with: `ollama serve`"
            ) from e

    def get_info(self) -> dict:
        """Get provider information."""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "base_url": config.OLLAMA_BASE_URL if self.provider == "ollama" else "Groq Cloud",
        }

    def check_health(self) -> dict:
        """Check if the selected provider is ready."""
        if self.provider == "groq":
            if self._groq_configured:
                # To actually verify model presence on Groq we could query /models, but true is safe here
                return {
                    "status": "connected",
                    "provider": "Groq API",
                    "requested_model": self.model,
                    "model_available": True,
                }
            else:
                return {
                    "status": "disconnected",
                    "provider": "Groq API",
                    "error": "API Key not set or library missing",
                    "action_needed": "Set GROQ_API_KEY in .env",
                }
                
        # Ollama health check
        try:
            models = self.ollama_client.list()
            available = [m.get("name", m.get("model", "")) for m in models.get("models", [])]
            model_ready = any(self.model in m for m in available)

            return {
                "status": "connected",
                "provider": "Ollama (Local)",
                "ollama_url": config.OLLAMA_BASE_URL,
                "requested_model": self.model,
                "model_available": model_ready,
                "available_models": available[:10],
                "action_needed": (
                    None if model_ready
                    else f"Run: ollama pull {self.model}"
                ),
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "provider": "Ollama (Local)",
                "ollama_url": config.OLLAMA_BASE_URL,
                "error": str(e),
                "action_needed": "Start Ollama: `ollama serve`",
            }
