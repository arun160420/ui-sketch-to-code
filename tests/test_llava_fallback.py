"""
Unit tests for Week 4: LLaVA-v1.6-7B Fallback Integration and Intelligent Model Routing.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
import requests

from src.ollama_client import (
    LLaVAClient,
    OllamaError,
    OllamaConnectionError,
    OllamaResponseError
)
from src.model_router import ModelRouter, RoutingStrategy
from src.gpt_client import GPTCodeGenerator, GPTAPIError
from src.schema import validate_ui_payload

@pytest.fixture
def sample_wireframe_data():
    return {
        "original_shape": (600, 800),
        "target_shape": (800, 800),
        "total_components": 3,
        "normalized_boxes": [
            {
                "id": 1,
                "box_pixels": [50, 50, 700, 80],
                "norm_box": [0.0625, 0.0625, 0.9375, 0.1625],
                "norm_wh": [0.875, 0.1],
                "area_ratio": 0.0875
            },
            {
                "id": 2,
                "box_pixels": [100, 200, 300, 50],
                "norm_box": [0.125, 0.25, 0.5, 0.3125],
                "norm_wh": [0.375, 0.0625],
                "area_ratio": 0.0234
            },
            {
                "id": 3,
                "box_pixels": [100, 300, 150, 45],
                "norm_box": [0.125, 0.375, 0.3125, 0.4312],
                "norm_wh": [0.1875, 0.0562],
                "area_ratio": 0.0105
            }
        ]
    }

# ============================================================================
# Task 1 & 2: LLaVA Client & API Tests
# ============================================================================

def test_llava_client_initialization():
    client = LLaVAClient(base_url="http://localhost:11434", model="llava:7b")
    assert client.base_url == "http://localhost:11434"
    assert client.model == "llava:7b"
    assert client.timeout == 60.0

def test_llava_prompt_construction(sample_wireframe_data):
    client = LLaVAClient()
    prompt = client.build_prompt(sample_wireframe_data)
    assert "Canvas Dimensions: (600, 800)" in prompt
    assert "comp-1" in prompt
    assert "page_title" in prompt
    assert "components" in prompt

def test_llava_mock_response_schema_compliance(sample_wireframe_data):
    client = LLaVAClient()
    result = client.generate_code(sample_wireframe_data, mock=True)
    # Validate against strict schema
    assert validate_ui_payload(result) is not None
    assert result["page_title"] == "LLaVA-v1.6-7B Wireframe Prototype"
    assert len(result["components"]) > 0
    assert "llava-container" in result["full_html"]
    assert "llava-ui-navbar" in result["full_css"]

def test_llava_server_connection_error(sample_wireframe_data):
    client = LLaVAClient(base_url="http://127.0.0.1:99999")
    with patch.object(client, "is_server_running", return_value=False):
        with pytest.raises(OllamaConnectionError):
            client.generate_code(sample_wireframe_data, mock=False)

def test_llava_live_call_parsing(sample_wireframe_data):
    client = LLaVAClient()
    mock_payload = {
        "page_title": "Local Wireframe",
        "layout_type": "flexbox",
        "components": [
            {
                "component_id": "comp-1",
                "component_type": "button",
                "bounding_box": [0.1, 0.2, 0.3, 0.4],
                "html": "<button class=\"btn\">Click</button>",
                "css_classes": "btn"
            }
        ],
        "full_html": "<!DOCTYPE html><html><body><button class=\"btn\">Click</button></body></html>",
        "full_css": ".btn { color: blue; }"
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": json.dumps(mock_payload)}

    with patch.object(client, "is_server_running", return_value=True):
        with patch("requests.post", return_value=mock_resp):
            result = client.generate_code(sample_wireframe_data, mock=False)
            assert result["page_title"] == "Local Wireframe"
            assert result["components"][0]["component_type"] == "button"

def test_llava_malformed_json_response(sample_wireframe_data):
    client = LLaVAClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "This is raw text, not valid JSON."}

    with patch.object(client, "is_server_running", return_value=True):
        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(OllamaResponseError):
                client.generate_code(sample_wireframe_data, mock=False)

# ============================================================================
# Task 3: Switching / Fallback Router Tests
# ============================================================================

def test_router_health_check():
    router = ModelRouter()
    health = router.get_system_health()
    assert "routing_strategy" in health
    assert "gpt_4o_mini" in health
    assert "llava_local" in health

def test_router_fallback_when_gpt_key_missing(sample_wireframe_data):
    mock_gpt = GPTCodeGenerator(api_key=None)
    mock_gpt.api_key = ""
    router = ModelRouter(strategy=RoutingStrategy.AUTO, gpt_client=mock_gpt)

    result = router.generate(sample_wireframe_data)
    metadata = result["metadata"]

    assert metadata["fallback_triggered"] is True
    assert "OpenAI unavailable" in metadata["fallback_reason"]
    assert "llava" in metadata["model_used"].lower()
    assert validate_ui_payload(result["data"]) is not None

def test_router_fallback_when_gpt_call_fails(sample_wireframe_data):
    mock_gpt = MagicMock()
    mock_gpt.api_key = "sk-validkey123"
    mock_gpt.model = "gpt-4o-mini"
    mock_gpt.generate_code.side_effect = GPTAPIError("Rate limit reached 429")

    router = ModelRouter(strategy=RoutingStrategy.AUTO, gpt_client=mock_gpt)
    with patch.object(router, "check_gpt_availability", return_value=(True, "OK")):
        result = router.generate(sample_wireframe_data)
        metadata = result["metadata"]

        assert metadata["fallback_triggered"] is True
        assert "Rate limit" in metadata["fallback_reason"]
        assert "llava" in metadata["model_used"].lower()
        assert validate_ui_payload(result["data"]) is not None

def test_router_llava_only_mode(sample_wireframe_data):
    router = ModelRouter(strategy=RoutingStrategy.LLAVA_ONLY)
    result = router.generate(sample_wireframe_data)
    assert result["metadata"]["strategy"] == "LLAVA_ONLY"
    assert "llava" in result["metadata"]["model_used"].lower()
    assert validate_ui_payload(result["data"]) is not None

def test_router_latency_tracking(sample_wireframe_data):
    router = ModelRouter(strategy=RoutingStrategy.MOCK)
    result = router.generate(sample_wireframe_data)
    assert result["metadata"]["execution_time_seconds"] >= 0.0
