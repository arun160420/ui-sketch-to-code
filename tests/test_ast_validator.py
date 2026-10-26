"""
tests/test_ast_validator.py

Unit test suite for Week 6 Deliverable (COM71123-8):
Abstract Syntax Tree (AST) Validation Engine.

Tests:
- html-validate integration & configuration
- HTML snippet AST validation
- Error capture, log parsing & location pinpointing
- Status reporting mechanisms & UI payload validation
"""

import json
from pathlib import Path
import pytest

from src.ast_validator import (
    ASTValidationEngine,
    ValidationError,
    ValidationReport
)
from src.component_prompts import ComponentCodeGenerator


@pytest.fixture
def validator_engine():
    """Initializes standard ASTValidationEngine using project root configuration."""
    return ASTValidationEngine()


# ============================================================================
# Task 1: Configuration & Engine Initialization Tests
# ============================================================================

def test_engine_initialization(validator_engine):
    """Engine should initialize with resolved paths to config and bridge script."""
    assert validator_engine.bridge_script.exists()
    assert validator_engine.bridge_script.name == "validate_html_ast.js"
    if validator_engine.config_path:
        assert validator_engine.config_path.exists()
        assert validator_engine.config_path.name == ".htmlvalidate.json"


def test_custom_config_loading(tmp_path):
    """Engine should respect custom .htmlvalidate.json configurations."""
    custom_cfg = tmp_path / "custom.htmlvalidate.json"
    custom_cfg.write_text(json.dumps({
        "extends": ["html-validate:recommended"],
        "rules": {
            "no-inline-style": "error"
        }
    }), encoding="utf-8")

    engine = ASTValidationEngine(config_path=custom_cfg)
    assert engine.config_path == custom_cfg

    # Code with inline style should now trigger an error under custom config
    html_with_style = '<div style="color: red;"><p>Styled</p></div>'
    report = engine.validate_snippet(html_with_style)
    assert not report.is_valid
    rule_ids = [e.rule_id for e in report.errors]
    assert "no-inline-style" in rule_ids


# ============================================================================
# Task 2: AST Validation for Generated HTML Snippets Tests
# ============================================================================

def test_valid_html_snippet(validator_engine):
    """Valid HTML snippet should pass validation with 0 errors."""
    valid_snippet = '<div class="container mx-auto p-4"><h1 class="text-xl">Title</h1><p>Body</p></div>'
    report = validator_engine.validate_snippet(valid_snippet)
    assert report.is_valid is True
    assert report.error_count == 0
    assert len(report.errors) == 0


def test_empty_html_snippet_fails(validator_engine):
    """Empty or whitespace snippet should fail gracefully with descriptive error."""
    report = validator_engine.validate_snippet("   ")
    assert report.is_valid is False
    assert report.error_count >= 1
    assert report.errors[0].rule_id == "empty-input"


@pytest.mark.parametrize("category", [
    "navbar",
    "hero",
    "form",
    "card",
    "input"
])
def test_week5_components_pass_ast_validation(validator_engine, category):
    """All 5 deterministic UI components generated from Week 5 must pass AST validation."""
    generator = ComponentCodeGenerator()
    component = generator.generate_component(category)
    html_code = component["html"]
    report = validator_engine.validate_snippet(html_code)

    assert report.is_valid is True, (
        f"Component {category} failed AST validation: "
        f"{[e.message for e in report.errors]}"
    )
    assert report.error_count == 0


# ============================================================================
# Task 3: Error Capture & Parsing Tests
# ============================================================================

def test_capture_unclosed_tag_error(validator_engine):
    """Unclosed element in AST must be captured with 'close-order' rule and line/column."""
    invalid_html = '<div><span>Open text</div>'
    report = validator_engine.validate_snippet(invalid_html)

    assert report.is_valid is False
    assert report.error_count >= 1

    rule_ids = [e.rule_id for e in report.errors]
    assert "close-order" in rule_ids

    # Verify line and column tracking
    close_order_err = next(e for e in report.errors if e.rule_id == "close-order")
    assert close_order_err.line >= 1
    assert close_order_err.column >= 1
    assert "<span>" in close_order_err.message or "open elements" in close_order_err.message


def test_capture_duplicate_id_error(validator_engine):
    """Duplicate element IDs must trigger 'no-dup-id' error with selector target."""
    dup_id_html = '<div id="submit-btn"><button>One</button></div><div id="submit-btn"><button>Two</button></div>'
    report = validator_engine.validate_snippet(dup_id_html)

    assert report.is_valid is False
    assert any(e.rule_id == "no-dup-id" for e in report.errors)

    dup_err = next(e for e in report.errors if e.rule_id == "no-dup-id")
    assert "submit-btn" in dup_err.message
    assert dup_err.selector is not None


def test_capture_unknown_element_error(validator_engine):
    """Non-standard unknown HTML tags must trigger 'no-unknown-elements'."""
    unknown_html = '<div><nonexistenttag>Invalid element</nonexistenttag></div>'
    report = validator_engine.validate_snippet(unknown_html)

    assert report.is_valid is False
    assert any(e.rule_id == "no-unknown-elements" for e in report.errors)


def test_capture_void_element_content_error(validator_engine):
    """Void tags containing child elements must trigger 'void-content'."""
    void_content_html = '<img src="photo.jpg" alt="Photo"><p>Child of void</p></img>'
    report = validator_engine.validate_snippet(void_content_html)

    assert report.is_valid is False
    assert any(e.rule_id == "void-content" for e in report.errors)


# ============================================================================
# Task 4: Reporting Mechanism & Payload Integration Tests
# ============================================================================

def test_summary_and_markdown_formatting(validator_engine):
    """Report formatting methods must render human-readable and markdown logs."""
    invalid_html = '<div><span id="x">Test</div>'
    report = validator_engine.validate_snippet(invalid_html)

    summary = report.format_summary()
    assert "=== AST Validation Report: [FAIL] ===" in summary
    assert "Total Errors:" in summary
    assert "[close-order]" in summary

    markdown = report.format_markdown_report()
    assert "### AST Validation Report: **Fail**" in markdown
    assert "| Rule ID | Location | Message |" in markdown
    assert "`close-order`" in markdown


def test_validate_file_on_disk(validator_engine):
    """Validates real HTML file generated in week5 on disk."""
    week5_html = Path("output/week5/index.html")
    if week5_html.exists():
        report = validator_engine.validate_file(week5_html)
        assert report.is_valid is True
        assert report.error_count == 0


def test_validate_missing_file_reports_error(validator_engine):
    """Engine must report file-not-found error when given nonexistent path."""
    report = validator_engine.validate_file("nonexistent/path/doc.html")
    assert report.is_valid is False
    assert report.errors[0].rule_id == "file-not-found"


def test_validate_ui_payload_integration(validator_engine):
    """Engine must validate an entire multi-component UI payload dictionary."""
    payload = {
        "page_title": "Test Page",
        "components": [
            {
                "component_id": "comp_001",
                "component_type": "navbar",
                "html": '<nav class="bg-blue-600 p-4 text-white"><a href="#home">Home</a></nav>'
            },
            {
                "component_id": "comp_002",
                "component_type": "card",
                "html": '<div class="card"><h3>Card Title</h3><p>Content</p></div>'
            },
            {
                "component_id": "comp_003",
                "component_type": "broken",
                "html": '<div><span>Broken tags</div>'
            }
        ],
        "full_html": "<!DOCTYPE html><html lang=\"en\"><head><title>Test</title></head><body><div>Content</div></body></html>"
    }

    result = validator_engine.validate_ui_payload(payload)

    assert result["all_valid"] is False  # Because comp_003 has broken tags
    assert len(result["components"]) == 3
    assert result["components"][0]["is_valid"] is True
    assert result["components"][1]["is_valid"] is True
    assert result["components"][2]["is_valid"] is False
    assert result["components"][2]["error_count"] >= 1
    assert result["document_report"] is not None
    assert result["document_report"]["is_valid"] is True
