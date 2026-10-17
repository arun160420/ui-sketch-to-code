"""
JSON Schema definitions and validation for UI component code generation.
Enforces structured output from GPT-4o-mini.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import jsonschema

# Strict JSON Schema definition compatible with OpenAI Structured Outputs
UI_COMPONENT_JSON_SCHEMA: Dict[str, Any] = {
    "name": "ui_component_generation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "page_title": {
                "type": "string",
                "description": "Descriptive title for the generated web page."
            },
            "layout_type": {
                "type": "string",
                "enum": ["flexbox", "grid", "single-column"],
                "description": "Primary layout structure used for the UI."
            },
            "components": {
                "type": "array",
                "description": "List of individual extracted UI components.",
                "items": {
                    "type": "object",
                    "properties": {
                        "component_id": {
                            "type": "string",
                            "description": "Unique identifier matching preprocessed component ID."
                        },
                        "component_type": {
                            "type": "string",
                            "enum": ["header", "navbar", "button", "input", "card", "footer", "text", "image", "form", "hero"],
                            "description": "Semantic UI component classification."
                        },
                        "bounding_box": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Normalized coordinates [xmin, ymin, xmax, ymax] in [0.0, 1.0]."
                        },
                        "html": {
                            "type": "string",
                            "description": "Clean semantic HTML snippet for this component."
                        },
                        "css_classes": {
                            "type": "string",
                            "description": "CSS classes applied to this component."
                        }
                    },
                    "required": ["component_id", "component_type", "bounding_box", "html", "css_classes"],
                    "additionalProperties": False
                }
            },
            "full_html": {
                "type": "string",
                "description": "Complete HTML5 document combining all components."
            },
            "full_css": {
                "type": "string",
                "description": "Complete stylesheet providing responsive modern CSS styling."
            }
        },
        "required": ["page_title", "layout_type", "components", "full_html", "full_css"],
        "additionalProperties": False
    }
}

# Pydantic Models for programmatic type enforcement
class ComponentItem(BaseModel):
    component_id: str
    component_type: str
    bounding_box: List[float] = Field(default_factory=list)
    html: str
    css_classes: str

class UIPageGeneration(BaseModel):
    page_title: str
    layout_type: str
    components: List[ComponentItem]
    full_html: str
    full_css: str

def validate_ui_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates payload against the strict JSON schema.
    Raises jsonschema.ValidationError if invalid.
    Returns validated payload dictionary.
    """
    validator = jsonschema.Draft202012Validator(UI_COMPONENT_JSON_SCHEMA["schema"])
    validator.validate(payload)
    return payload
