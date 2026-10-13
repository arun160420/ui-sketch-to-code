"""
Local LLaVA-v1.6-7B client via Ollama for UI wireframe code generation fallback.
Handles local REST endpoints, prompt construction, JSON formatting, and schema validation.
"""

import os
import json
import base64
import logging
from typing import Dict, Any, Optional, List, Union
import requests
from dotenv import load_dotenv

from src.schema import UI_COMPONENT_JSON_SCHEMA, validate_ui_payload

logger = logging.getLogger(__name__)

class OllamaError(Exception):
    """Base exception for Ollama client errors."""
    pass

class OllamaConnectionError(OllamaError):
    """Raised when the local Ollama server is unreachable."""
    pass

class OllamaModelNotFoundError(OllamaError):
    """Raised when the requested LLaVA model is not installed locally."""
    pass

class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an invalid or non-schema conforming response."""
    pass

class LLaVAClient:
    """
    Client for interacting with local LLaVA-v1.6-7B model served via Ollama.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0
    ):
        load_dotenv()
        self.base_url = (base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llava:7b")
        self.timeout = timeout

    def is_server_running(self) -> bool:
        """Checks if local Ollama daemon is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def list_local_models(self) -> List[str]:
        """Returns list of models available in local Ollama instance."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name", "") for m in data.get("models", [])]
            return []
        except Exception as e:
            logger.warning(f"Failed to query Ollama models: {e}")
            return []

    def check_model_availability(self) -> bool:
        """Verifies if the configured LLaVA model is present locally."""
        models = self.list_local_models()
        model_base = self.model.split(":")[0]
        return any(self.model in m or model_base in m for m in models)

    def build_prompt(self, wireframe_data: Dict[str, Any]) -> str:
        """
        Builds a comprehensive prompt instructing LLaVA to generate semantic UI code
        and adhere to the strict JSON schema.
        """
        boxes = wireframe_data.get("normalized_boxes", [])
        components_summary = []
        for b in boxes:
            components_summary.append({
                "id": f"comp-{b.get('id', 'unk')}",
                "norm_box": b.get("norm_box", []),
                "area_ratio": b.get("area_ratio", 0.0)
            })

        schema_props = list(UI_COMPONENT_JSON_SCHEMA["schema"]["properties"].keys())

        prompt = (
            "You are an expert Frontend Web Developer. Analyze the wireframe layout and detected UI component bounding boxes:\n"
            f"- Canvas Dimensions: {wireframe_data.get('original_shape', (800, 800))}\n"
            f"- Component Boxes: {json.dumps(components_summary, indent=2)}\n\n"
            "Requirements:\n"
            "1. Generate modern, accessible HTML5 components and responsive CSS (Flexbox/Grid).\n"
            "2. Output MUST be strictly valid JSON without any markdown code fences or conversational text.\n"
            f"3. Include these exact required JSON keys: {schema_props}.\n"
            "4. Each item in 'components' must have: 'component_id', 'component_type', 'bounding_box', 'html', 'css_classes'.\n"
        )
        return prompt

    def _generate_mock_llava_response(self, wireframe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic mock response for offline and automated test environments."""
        boxes = wireframe_data.get("normalized_boxes", [])
        components = []

        types_cycle = ["navbar", "header", "input", "button", "card", "footer"]
        for idx, b in enumerate(boxes[:6]):
            ctype = types_cycle[idx % len(types_cycle)]
            comp_id = f"comp-{b.get('id', idx + 1)}"
            box_coords = b.get("norm_box", [0.0, 0.0, 1.0, 0.1])

            components.append({
                "component_id": comp_id,
                "component_type": ctype,
                "bounding_box": box_coords,
                "html": f"<{ctype} class=\"llava-ui-{ctype}\" id=\"{comp_id}\">LLaVA Generated {ctype.capitalize()}</{ctype}>",
                "css_classes": f"llava-ui-{ctype} local-component-{idx+1}"
            })

        mock_payload = {
            "page_title": "LLaVA-v1.6-7B Wireframe Prototype",
            "layout_type": "flexbox",
            "components": components,
            "full_html": (
                "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
                "  <meta charset=\"UTF-8\">\n  <title>LLaVA Wireframe Prototype</title>\n"
                "  <link rel=\"stylesheet\" href=\"styles.css\">\n</head>\n<body>\n"
                "  <div class=\"llava-container\">\n" +
                "".join([f"    {c['html']}\n" for c in components]) +
                "  </div>\n</body>\n</html>"
            ),
            "full_css": (
                ":root { --primary: #2563eb; --bg: #f1f5f9; }\n"
                "body { font-family: system-ui, sans-serif; margin: 0; padding: 24px; background: var(--bg); }\n"
                ".llava-container { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }\n"
                ".llava-ui-navbar { background: #1e293b; color: #fff; padding: 14px; border-radius: 8px; }\n"
                ".llava-ui-button { background: var(--primary); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; }\n"
                ".llava-ui-input { padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; }\n"
                ".llava-ui-card { background: white; padding: 20px; border: 1px solid #e2e8f0; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }\n"
            )
        }
        return validate_ui_payload(mock_payload)

    def generate_code(
        self,
        wireframe_data: Dict[str, Any],
        image_base64: Optional[str] = None,
        mock: bool = False
    ) -> Dict[str, Any]:
        """
        Calls local Ollama endpoint with LLaVA model and returns validated JSON output.
        """
        if mock:
            logger.info("Using LLaVA mock generation mode (mock=True).")
            return self._generate_mock_llava_response(wireframe_data)

        # Check server availability
        if not self.is_server_running():
            raise OllamaConnectionError(
                f"Cannot connect to local Ollama server at {self.base_url}. "
                "Ensure 'ollama serve' is running or use mock mode."
            )

        prompt = self.build_prompt(wireframe_data)

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 2500
            }
        }

        # If base64 image provided, pass in Ollama multimodal images list
        if image_base64:
            clean_b64 = image_base64.split(",")[-1]
            payload["images"] = [clean_b64]

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            if resp.status_code != 200:
                raise OllamaResponseError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

            result_json = resp.json()
            raw_text = result_json.get("response", "").strip()

            if not raw_text:
                raise OllamaResponseError("Received empty response string from Ollama LLaVA.")

            # Parse JSON
            parsed = json.loads(raw_text)

            # Enforce schema validation
            validated = validate_ui_payload(parsed)
            return validated

        except requests.exceptions.Timeout as e:
            raise OllamaResponseError(f"Ollama request timed out after {self.timeout}s: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise OllamaConnectionError(f"Connection failed to Ollama server at {self.base_url}: {e}") from e
        except json.JSONDecodeError as e:
            raise OllamaResponseError(f"Ollama response was not valid JSON: {e}\nRaw output: {raw_text[:200]}") from e
        except Exception as e:
            raise OllamaResponseError(f"Unexpected error calling Ollama LLaVA: {e}") from e
