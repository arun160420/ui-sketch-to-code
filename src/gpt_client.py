"""
GPT-4o-mini API client for UI wireframe code generation.
Includes secure API key management, JSON schema enforcement, robust error handling,
and multi-turn AST error refinement routing (Week 7: COM71123-9).
"""

import os
import json
import base64
import logging
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv
import openai
from openai import OpenAI

from src.schema import UI_COMPONENT_JSON_SCHEMA, validate_ui_payload

logger = logging.getLogger(__name__)

class GPTAPIError(Exception):
    """Custom base exception for GPT API integration errors."""
    pass

class MissingAPIKeyError(GPTAPIError):
    """Raised when OpenAI API key is missing or not configured."""
    pass

class SchemaValidationError(GPTAPIError):
    """Raised when model response fails JSON schema validation."""
    pass

class GPTCodeGenerator:
    """
    Client for generating UI component HTML/CSS from wireframe data using GPT-4o-mini.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 2500,
        env_path: Optional[str] = None
    ):
        # 1. Load environment variables securely from .env if available
        if env_path:
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", model)
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", str(temperature)))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(max_tokens)))

        self._client: Optional[OpenAI] = None

    @property
    def masked_api_key(self) -> str:
        """Returns securely masked API key for logging and diagnostics."""
        if not self.api_key:
            return "<NOT_SET>"
        if len(self.api_key) <= 8:
            return "sk-****"
        return f"{self.api_key[:3]}...{self.api_key[-4:]}"

    def get_client(self) -> OpenAI:
        """Initializes and returns the OpenAI client with validation."""
        if not self.api_key or self.api_key.strip() == "" or "your_openai_api_key_here" in self.api_key:
            raise MissingAPIKeyError(
                "OpenAI API key is missing or set to placeholder value. "
                "Please configure OPENAI_API_KEY in your .env file or environment variable."
            )
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, timeout=45.0, max_retries=2)
        return self._client

    def build_prompt(
        self,
        wireframe_data: Dict[str, Any],
        image_base64: Optional[str] = None
    ) -> list:
        """
        Constructs system and user message payload adhering to schema expectations.
        """
        system_content = (
            "You are an expert Frontend Web Developer and UI Engineer. "
            "Your task is to analyze wireframe bounding boxes and geometric UI component metadata "
            "and generate clean, modern, accessible HTML5 and responsive CSS code. "
            "You MUST strictly adhere to the enforced JSON schema. "
            "Return valid JSON adhering to the specified schema format."
        )

        components_summary = []
        boxes = wireframe_data.get("normalized_boxes", [])
        for b in boxes:
            components_summary.append({
                "id": f"comp-{b.get('id', 'unk')}",
                "norm_box": b.get("norm_box", []),
                "area_ratio": b.get("area_ratio", 0.0)
            })

        user_text = (
            f"Analyze the following pre-processed wireframe geometry:\n"
            f"- Original canvas shape: {wireframe_data.get('original_shape', (800, 800))}\n"
            f"- Total detected components: {wireframe_data.get('total_components', len(boxes))}\n"
            f"- Component bounding boxes: {json.dumps(components_summary, indent=2)}\n\n"
            "Generate semantic HTML5 components and responsive CSS that precisely reflect the detected layout."
        )

        user_content: Union[str, list] = user_text
        if image_base64:
            user_content = [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                }
            ]

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

    def _generate_mock_response(self, wireframe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provides a valid mock response matching JSON schema for offline testing."""
        boxes = wireframe_data.get("normalized_boxes", [])
        components = []

        types_cycle = ["navbar", "header", "input", "button", "card", "footer"]
        tag_map = {
            "navbar": "nav",
            "header": "header",
            "input": "input",
            "button": "button",
            "card": "div",
            "footer": "footer"
        }

        for idx, b in enumerate(boxes[:6]):
            ctype = types_cycle[idx % len(types_cycle)]
            tag = tag_map.get(ctype, "div")
            comp_id = f"comp-{b.get('id', idx + 1)}"
            box_coords = b.get("norm_box", [0.0, 0.0, 1.0, 0.1])

            if tag == "input":
                comp_html = f'<input type="text" class="ui-input" id="{comp_id}" placeholder="Sample Input">'
            elif tag == "button":
                comp_html = f'<button type="button" class="ui-button" id="{comp_id}">Sample Button</button>'
            else:
                comp_html = f'<{tag} class="ui-{ctype}" id="{comp_id}">Sample {ctype.capitalize()}</{tag}>'

            components.append({
                "component_id": comp_id,
                "component_type": ctype,
                "bounding_box": box_coords,
                "html": comp_html,
                "css_classes": f"ui-{ctype} component-{idx+1}"
            })

        mock_payload = {
            "page_title": "Generated UI Wireframe Prototype",
            "layout_type": "flexbox",
            "components": components,
            "full_html": (
                "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
                "  <meta charset=\"UTF-8\">\n  <title>Wireframe Prototype</title>\n"
                "  <link rel=\"stylesheet\" href=\"styles.css\">\n</head>\n<body>\n"
                "  <div class=\"container\">\n" +
                "".join([f"    {c['html']}\n" for c in components]) +
                "  </div>\n</body>\n</html>"
            ),
            "full_css": (
                "body { font-family: sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }\n"
                ".container { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }\n"
                ".ui-navbar { background: #333; color: #fff; padding: 12px; border-radius: 6px; }\n"
                ".ui-button { background: #007bff; color: white; padding: 8px 16px; border: none; border-radius: 4px; }\n"
                ".ui-input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }\n"
                ".ui-card { background: white; padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px; }\n"
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
        Executes API call to GPT-4o-mini with enforced JSON schema output and error handling.
        """
        if mock:
            logger.info("Generating mock response (mock=True).")
            return self._generate_mock_response(wireframe_data)

        # Ensure API key is present
        client = self.get_client()
        messages = self.build_prompt(wireframe_data, image_base64)

        try:
            # Call OpenAI Chat Completion with Structured Outputs
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": UI_COMPONENT_JSON_SCHEMA
                }
            )

            response_content = response.choices[0].message.content
            if not response_content:
                raise GPTAPIError("Received empty response content from GPT-4o-mini.")

            # Parse JSON
            raw_data = json.loads(response_content)

            # Enforce schema validation
            validated_payload = validate_ui_payload(raw_data)
            return validated_payload

        except openai.AuthenticationError as e:
            raise GPTAPIError(f"Authentication failed with OpenAI API: {e}. Check your OPENAI_API_KEY.") from e
        except openai.RateLimitError as e:
            raise GPTAPIError(f"OpenAI rate limit exceeded or quota exhausted: {e}") from e
        except openai.APIConnectionError as e:
            raise GPTAPIError(f"Failed to connect to OpenAI API server: {e}") from e
        except openai.APITimeoutError as e:
            raise GPTAPIError(f"Request to OpenAI API timed out: {e}") from e
        except json.JSONDecodeError as e:
            raise SchemaValidationError(f"Response from GPT-4o-mini was not valid JSON: {e}") from e
        except Exception as e:
            raise GPTAPIError(f"Unexpected error during GPT-4o-mini code generation: {e}") from e

    def refine_code(
        self,
        erroneous_payload: Dict[str, Any],
        extracted_errors: list,
        mock: bool = False
    ) -> Dict[str, Any]:
        """
        Submits AST validation error logs and the erroneous code back to GPT-4o-mini
        to receive corrected code conforming to UI_COMPONENT_JSON_SCHEMA (Week 7: COM71123-9).
        """
        if mock:
            logger.info("Refining code via deterministic mock repair (mock=True).")
            from src.refinement_loop import AgenticRefinementLoop
            repairer = AgenticRefinementLoop(validator_engine=None)
            return repairer._default_mock_repair_generator(erroneous_payload, extracted_errors)

        from src.refinement_loop import ErrorPromptFormatter
        client = self.get_client()
        messages = ErrorPromptFormatter.build_multiturn_refinement_messages(
            extracted_errors=extracted_errors,
            erroneous_payload=erroneous_payload
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": UI_COMPONENT_JSON_SCHEMA
                }
            )

            response_content = response.choices[0].message.content
            if not response_content:
                raise GPTAPIError("Received empty response from GPT-4o-mini during error refinement.")

            raw_data = json.loads(response_content)
            return validate_ui_payload(raw_data)

        except openai.AuthenticationError as e:
            raise GPTAPIError(f"Authentication failed during refinement: {e}") from e
        except openai.RateLimitError as e:
            raise GPTAPIError(f"OpenAI rate limit exceeded during refinement: {e}") from e
        except Exception as e:
            raise GPTAPIError(f"Error during GPT-4o-mini code refinement: {e}") from e
