"""
Unit tests for Week 5: Component-Specific Code Generation Logic.
Verifies prompt design and Tailwind CSS code generation for the five deterministic UI components:
1. Navigation Bars
2. Login/Signup Forms
3. Hero Sections
4. Content Cards
5. Form Input Fields
"""

import pytest
import jsonschema

from src.component_prompts import (
    ComponentCodeGenerator,
    UIComponentCategory,
    PROMPT_TEMPLATES
)
from src.schema import validate_ui_payload

@pytest.fixture
def generator():
    return ComponentCodeGenerator()

# ==============================================================================
# Task 1-5: Prompt Design & Template Verification Tests
# ==============================================================================

def test_all_five_component_types_supported(generator):
    supported = generator.get_supported_components()
    expected = ["navbar", "form", "hero", "card", "input"]
    for c_type in expected:
        assert c_type in supported

def test_navbar_prompt_design(generator):
    prompt = generator.build_prompt("navbar", bounding_box=[0.0, 0.0, 1.0, 0.1])
    assert "Navigation Bar" in prompt
    assert "<nav>" in prompt
    assert "Tailwind CSS" in prompt
    assert "Flexbox" in prompt or "flex" in prompt
    # Verify default HTML
    comp = generator.generate_component("navbar")
    assert "<nav" in comp["html"]
    assert "flex" in comp["html"]
    assert "Get Started" in comp["html"]

def test_auth_form_prompt_design(generator):
    prompt = generator.build_prompt("form", bounding_box=[0.5, 0.5, 0.9, 0.9])
    assert "Login/Signup Form" in prompt
    assert "<form>" in prompt
    assert "Email" in prompt or "email" in prompt
    assert "password" in prompt or "Password" in prompt
    # Verify default HTML
    comp = generator.generate_component("form")
    assert "<form" in comp["html"]
    assert 'type="email"' in comp["html"]
    assert 'type="password"' in comp["html"]
    assert "Sign In" in comp["html"]

def test_hero_section_prompt_design(generator):
    prompt = generator.build_prompt("hero", bounding_box=[0.0, 0.1, 1.0, 0.5])
    assert "Hero Section" in prompt
    assert "headline" in prompt.lower() or "heading" in prompt.lower() or "cta" in prompt.lower()
    # Verify default HTML
    comp = generator.generate_component("hero")
    assert "<h1" in comp["html"]
    assert "rounded-xl" in comp["html"] or "rounded-full" in comp["html"]
    assert "Start Converting" in comp["html"]

def test_content_card_prompt_design(generator):
    prompt = generator.build_prompt("card", bounding_box=[0.1, 0.5, 0.4, 0.8])
    assert "Content Card" in prompt
    assert "badge" in prompt.lower() or "thumbnail" in prompt.lower()
    # Verify default HTML
    comp = generator.generate_component("card")
    assert "shadow-md" in comp["html"]
    assert "rounded-" in comp["html"]
    assert "Learn more" in comp["html"]

def test_input_field_prompt_design(generator):
    prompt = generator.build_prompt("input", bounding_box=[0.1, 0.6, 0.4, 0.7])
    assert "Form Input Field" in prompt
    assert "<label>" in prompt
    assert "placeholder" in prompt.lower()
    # Verify default HTML
    comp = generator.generate_component("input")
    assert "<label" in comp["html"]
    assert "<input" in comp["html"]
    assert "focus:ring-2" in comp["html"]

# ==============================================================================
# Tailwind CSS & Schema Compliance Tests
# ==============================================================================

def test_tailwind_classes_present_in_all_components(generator):
    components = generator.generate_all_five_components()
    assert len(components) == 5

    tailwind_utility_indicators = ["flex", "text-", "rounded-", "border", "p-", "bg-"]
    for comp in components:
        html = comp["html"]
        # Check that component contains standard Tailwind utilities
        has_utilities = any(u in html for u in tailwind_utility_indicators)
        assert has_utilities, f"Component {comp['component_type']} lacks Tailwind utility classes"

def test_components_satisfy_json_schema(generator):
    components = generator.generate_all_five_components()
    payload = {
        "page_title": "Week 5 Unit Test Payload",
        "layout_type": "flexbox",
        "components": components,
        "full_html": generator.build_showcase_page(components),
        "full_css": "/* Tailwind CSS CDN */"
    }
    # Must validate cleanly without raising ValidationError
    assert validate_ui_payload(payload) is not None

def test_showcase_page_structure(generator):
    page = generator.build_showcase_page()
    assert "<!DOCTYPE html>" in page
    assert "cdn.tailwindcss.com" in page
    assert "<nav" in page
    assert "Hero" in page or "Sketch" in page
    assert "Sign In" in page
