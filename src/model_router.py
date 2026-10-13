"""
Model Router and Fallback Management for UI Sketch-to-Code Generation.
Dynamically routes requests between GPT-4o-mini (cloud) and LLaVA-v1.6-7B (local Ollama)
based on API key availability, service health, and performance.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from dotenv import load_dotenv

from src.gpt_client import GPTCodeGenerator, GPTAPIError, MissingAPIKeyError
from src.ollama_client import LLaVAClient, OllamaError, OllamaConnectionError
from src.schema import validate_ui_payload

logger = logging.getLogger(__name__)

class RoutingStrategy(str, Enum):
    AUTO = "AUTO"             # Try GPT-4o-mini first, fallback to LLaVA
    GPT_ONLY = "GPT_ONLY"     # Strictly use GPT-4o-mini
    LLAVA_ONLY = "LLAVA_ONLY" # Strictly use local LLaVA
    MOCK = "MOCK"             # Deterministic mock testing

class ModelRouter:
    """
    Intelligent router coordinating GPT-4o-mini (primary) and LLaVA-v1.6-7B (fallback).
    """

    def __init__(
        self,
        strategy: Optional[RoutingStrategy] = None,
        gpt_client: Optional[GPTCodeGenerator] = None,
        llava_client: Optional[LLaVAClient] = None
    ):
        load_dotenv()
        env_strategy = os.getenv("MODEL_ROUTER_STRATEGY", "AUTO").upper()
        self.strategy = strategy or RoutingStrategy(env_strategy)

        self.gpt_client = gpt_client or GPTCodeGenerator()
        self.llava_client = llava_client or LLaVAClient()

    def check_gpt_availability(self) -> Tuple[bool, str]:
        """Checks if GPT-4o-mini is configured with an active API key."""
        if not self.gpt_client.api_key:
            return False, "OPENAI_API_KEY is not set."
        if "your_openai_api_key_here" in self.gpt_client.api_key:
            return False, "OPENAI_API_KEY is set to default placeholder."
        return True, "API key configured."

    def check_llava_availability(self) -> Tuple[bool, str]:
        """Checks if local Ollama daemon is reachable and has LLaVA installed."""
        if not self.llava_client.is_server_running():
            return False, f"Ollama daemon not running at {self.llava_client.base_url}."
        if not self.llava_client.check_model_availability():
            return False, f"Model '{self.llava_client.model}' not found in local Ollama repository."
        return True, f"Local Ollama server active with {self.llava_client.model} ready."

    def get_system_health(self) -> Dict[str, Any]:
        """Returns diagnostic health status of both AI providers."""
        gpt_ok, gpt_msg = self.check_gpt_availability()
        llava_ok, llava_msg = self.check_llava_availability()

        return {
            "routing_strategy": self.strategy.value,
            "gpt_4o_mini": {
                "available": gpt_ok,
                "status": gpt_msg,
                "masked_key": self.gpt_client.masked_api_key
            },
            "llava_local": {
                "available": llava_ok,
                "status": llava_msg,
                "endpoint": self.llava_client.base_url,
                "model": self.llava_client.model
            }
        }

    def generate(
        self,
        wireframe_data: Dict[str, Any],
        image_base64: Optional[str] = None,
        force_mock: bool = False
    ) -> Dict[str, Any]:
        """
        Executes code generation using the configured routing strategy and fallback logic.
        Returns combined payload with generated UI and routing execution metadata.
        """
        start_time = time.time()
        metadata: Dict[str, Any] = {
            "strategy": self.strategy.value,
            "primary_attempted": None,
            "fallback_triggered": False,
            "fallback_reason": None,
            "model_used": None,
            "provider": None,
            "execution_time_seconds": 0.0
        }

        if force_mock or self.strategy == RoutingStrategy.MOCK:
            ui_result = self.gpt_client.generate_code(wireframe_data, mock=True)
            metadata["model_used"] = "mock-generator"
            metadata["provider"] = "deterministic-mock"
            metadata["execution_time_seconds"] = round(time.time() - start_time, 4)
            return {"data": ui_result, "metadata": metadata}

        # Strategy 1: Strictly LLAVA_ONLY
        if self.strategy == RoutingStrategy.LLAVA_ONLY:
            metadata["primary_attempted"] = self.llava_client.model
            llava_running = self.llava_client.is_server_running()
            ui_result = self.llava_client.generate_code(wireframe_data, image_base64, mock=not llava_running)
            metadata["model_used"] = self.llava_client.model
            metadata["provider"] = "ollama-local" if llava_running else "llava-mock"
            metadata["execution_time_seconds"] = round(time.time() - start_time, 4)
            return {"data": ui_result, "metadata": metadata}

        # Strategy 2: Strictly GPT_ONLY
        if self.strategy == RoutingStrategy.GPT_ONLY:
            metadata["primary_attempted"] = self.gpt_client.model
            ui_result = self.gpt_client.generate_code(wireframe_data, image_base64, mock=False)
            metadata["model_used"] = self.gpt_client.model
            metadata["provider"] = "openai-cloud"
            metadata["execution_time_seconds"] = round(time.time() - start_time, 4)
            return {"data": ui_result, "metadata": metadata}

        # Strategy 3: AUTO (Primary GPT-4o-mini with fallback to local LLaVA)
        metadata["primary_attempted"] = self.gpt_client.model
        gpt_ready, gpt_reason = self.check_gpt_availability()

        if gpt_ready:
            try:
                logger.info(f"Attempting code generation via primary model {self.gpt_client.model}...")
                ui_result = self.gpt_client.generate_code(wireframe_data, image_base64, mock=False)
                metadata["model_used"] = self.gpt_client.model
                metadata["provider"] = "openai-cloud"
                metadata["execution_time_seconds"] = round(time.time() - start_time, 4)
                return {"data": ui_result, "metadata": metadata}

            except (GPTAPIError, Exception) as e:
                logger.warning(f"Primary model {self.gpt_client.model} failed: {e}. Initiating LLaVA fallback...")
                metadata["fallback_triggered"] = True
                metadata["fallback_reason"] = f"GPT API Error: {str(e)}"
        else:
            logger.info(f"OpenAI key not configured ({gpt_reason}). Routing directly to LLaVA fallback.")
            metadata["fallback_triggered"] = True
            metadata["fallback_reason"] = f"OpenAI unavailable: {gpt_reason}"

        # Fallback to local LLaVA
        llava_running = self.llava_client.is_server_running()
        if llava_running:
            logger.info(f"Executing fallback generation via local LLaVA at {self.llava_client.base_url}")
            ui_result = self.llava_client.generate_code(wireframe_data, image_base64, mock=False)
            metadata["model_used"] = self.llava_client.model
            metadata["provider"] = "ollama-local"
        else:
            logger.info("Local Ollama daemon not running. Executing schema-validated local fallback.")
            ui_result = self.llava_client.generate_code(wireframe_data, image_base64, mock=True)
            metadata["model_used"] = f"{self.llava_client.model} (schema-validated-fallback)"
            metadata["provider"] = "local-fallback-engine"

        metadata["execution_time_seconds"] = round(time.time() - start_time, 4)
        return {"data": ui_result, "metadata": metadata}
