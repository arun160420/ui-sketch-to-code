"""
tests/test_refinement_routing.py

Unit test suite for Week 7 Deliverable (COM71123-9):
Agentic Refinement Loop - Error Routing.

Tests:
1. Error Identification & Extraction Logic (ASTErrorExtractor)
2. Error Log Formatting for Vision Models (ErrorPromptFormatter)
3. Feedback Loop Mechanism & Telemetry (AgenticRefinementLoop)
4. Syntactically Incorrect Code Routing & Convergence (Unclosed tags, Duplicate IDs, Missing attributes)
"""

import pytest
from typing import Dict, Any, List

from src.ast_validator import ASTValidationEngine, ValidationError, ValidationReport
from src.refinement_loop import (
    ASTErrorExtractor,
    ErrorCategory,
    ExtractedError,
    ErrorPromptFormatter,
    AgenticRefinementLoop,
    RefinementStatus,
    RefinementLoopResult
)
from src.model_router import ModelRouter, RoutingStrategy
from src.gpt_client import GPTCodeGenerator


@pytest.fixture
def ast_engine():
    """Initializes ASTValidationEngine for testing."""
    return ASTValidationEngine()


@pytest.fixture
def refinement_loop(ast_engine):
    """Initializes standard AgenticRefinementLoop with deterministic mock repair."""
    return AgenticRefinementLoop(validator_engine=ast_engine, max_iterations=3)


# ============================================================================
# Task 1: Error Identification and Extraction Tests
# ============================================================================

def test_rule_categorization():
    """Validates that html-validate rules are categorized into correct semantic buckets."""
    assert ASTErrorExtractor.categorize_rule("close-order") == ErrorCategory.STRUCTURAL_CLOSURE
    assert ASTErrorExtractor.categorize_rule("no-implicit-close") == ErrorCategory.STRUCTURAL_CLOSURE
    assert ASTErrorExtractor.categorize_rule("no-dup-id") == ErrorCategory.DUPLICATE_IDENTIFIER
    assert ASTErrorExtractor.categorize_rule("element-required-attributes") == ErrorCategory.MISSING_ATTRIBUTE
    assert ASTErrorExtractor.categorize_rule("wcag/h37") == ErrorCategory.MISSING_ATTRIBUTE
    assert ASTErrorExtractor.categorize_rule("no-unknown-elements") == ErrorCategory.UNKNOWN_ELEMENT
    assert ASTErrorExtractor.categorize_rule("void-content") == ErrorCategory.VOID_ELEMENT_VIOLATION
    assert ASTErrorExtractor.categorize_rule("parser-error") == ErrorCategory.SYNTAX_PARSER_ERROR
    assert ASTErrorExtractor.categorize_rule("random-unknown-rule") == ErrorCategory.GENERAL_ERROR


def test_context_snippet_extraction():
    """Checks that source line, surrounding context, and caret pointer are correctly extracted."""
    html_code = (
        "<div class=\"container\">\n"
        "  <span>Unclosed element\n"
        "</div>"
    )
    # Error at line 2, column 3 (<span>)
    offending, snippet = ASTErrorExtractor.extract_context_snippet(html_code, line_num=2, col_num=3)

    assert offending == "  <span>Unclosed element"
    assert " >    2 |   <span>Unclosed element" in snippet
    assert "^--- [ERROR HERE]" in snippet
    assert "      1 | <div class=\"container\">" in snippet
    assert "      3 | </div>" in snippet


def test_extract_errors_from_validation_report(ast_engine):
    """Extracts and enriches errors directly from an actual ValidationReport."""
    bad_html = "<div><span>Unclosed tag</div>"
    report = ast_engine.validate_snippet(bad_html)

    assert not report.is_valid
    extracted = ASTErrorExtractor.extract_errors(report, source_code=bad_html)

    assert len(extracted) >= 1
    err = extracted[0]
    assert err.rule_id == "close-order"
    assert err.category == ErrorCategory.STRUCTURAL_CLOSURE
    assert err.remediation_hint is not None
    assert err.line >= 1
    assert err.column >= 1
    assert err.offending_line is not None


def test_extract_errors_from_dictionary():
    """Validates error extraction when input is a raw dictionary (e.g. from JSON serialization)."""
    raw_dict = {
        "is_valid": False,
        "error_count": 1,
        "errors": [
            {
                "ruleId": "no-dup-id",
                "severity": "error",
                "message": "Duplicate ID 'hero-btn'",
                "line": 5,
                "column": 12,
                "selector": "#hero-btn"
            }
        ],
        "source_snippet": "<div id=\"hero-btn\">1</div>\n<div id=\"hero-btn\">2</div>"
    }

    extracted = ASTErrorExtractor.extract_errors(raw_dict)
    assert len(extracted) == 1
    assert extracted[0].rule_id == "no-dup-id"
    assert extracted[0].category == ErrorCategory.DUPLICATE_IDENTIFIER
    assert "Rename duplicate IDs" in extracted[0].remediation_hint


# ============================================================================
# Task 2: Error Log Formatting for Vision Model Tests
# ============================================================================

def test_format_diagnostic_prompt_structure():
    """Ensures formatted diagnostic prompt includes all essential LLM repair guidance."""
    errors = [
        ExtractedError(
            rule_id="close-order",
            category=ErrorCategory.STRUCTURAL_CLOSURE,
            severity="error",
            message="Unclosed element '<span>'",
            line=1,
            column=7,
            selector="div > span",
            offending_line="<div><span>broken</div>",
            context_snippet=" >    1 | <div><span>broken</div>\n             ^--- [ERROR HERE]",
            remediation_hint="Ensure every opening tag has a corresponding closing tag."
        )
    ]
    raw_html = "<div><span>broken</div>"
    prompt = ErrorPromptFormatter.format_diagnostic_prompt(
        extracted_errors=errors,
        original_code=raw_html,
        component_type="Navbar",
        include_schema_rules=True
    )

    assert "### Automated AST Validation Error Report for Component 'Navbar'" in prompt
    assert "[close-order]" in prompt
    assert "Unclosed element '<span>'" in prompt
    assert "`div > span`" in prompt
    assert "^--- [ERROR HERE]" in prompt
    assert "#### Erroneous HTML to Repair:" in prompt
    assert "#### Repair Requirements:" in prompt
    assert "Return valid JSON adhering to the enforced schema" in prompt


def test_build_multiturn_refinement_messages():
    """Verifies construction of 3-turn chat completion history (System -> Assistant -> User)."""
    errors = [
        ExtractedError(
            rule_id="no-dup-id",
            category=ErrorCategory.DUPLICATE_IDENTIFIER,
            severity="error",
            message="Duplicate ID 'nav-item'",
            line=1,
            column=10,
            selector="#nav-item",
            remediation_hint="Ensure unique IDs"
        )
    ]
    payload = {
        "layout_type": "navbar",
        "full_html": '<nav><a id="nav-item">1</a><a id="nav-item">2</a></nav>'
    }

    messages = ErrorPromptFormatter.build_multiturn_refinement_messages(
        extracted_errors=errors,
        erroneous_payload=payload
    )

    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert "Agentic Refinement Loop" in messages[0]["content"]

    assert messages[1]["role"] == "assistant"
    assert "nav-item" in messages[1]["content"]

    assert messages[2]["role"] == "user"
    assert "### Automated AST Validation Error Report" in messages[2]["content"]
    assert "[no-dup-id]" in messages[2]["content"]


# ============================================================================
# Task 3 & 4: Feedback Loop Mechanism & Error Routing Tests
# ============================================================================

def test_refinement_loop_valid_code_bypasses(refinement_loop):
    """Clean, valid HTML snippet immediately bypasses refinement with 0 iterations."""
    valid_html = '<div class="p-4 bg-white"><h2 class="text-lg">Clean UI</h2></div>'
    repaired, result = refinement_loop.run_snippet_loop(valid_html, component_type="Card")

    assert result.status == RefinementStatus.VALIDATION_BYPASS
    assert result.is_valid is True
    assert result.total_iterations == 0
    assert result.initial_error_count == 0
    assert result.final_error_count == 0
    assert repaired == valid_html


def test_refinement_loop_routes_and_repairs_unclosed_tag(refinement_loop, ast_engine):
    """Routes an unclosed tag error back through the loop and verifies AST passes."""
    broken_html = "<div><span>Unclosed Tag in Component</div>"

    # Verify initially invalid
    initial_check = ast_engine.validate_snippet(broken_html)
    assert not initial_check.is_valid
    assert any(e.rule_id == "close-order" for e in initial_check.errors)

    # Run refinement loop
    repaired, result = refinement_loop.run_snippet_loop(broken_html, component_type="Navbar")

    assert result.status == RefinementStatus.SUCCESS
    assert result.is_valid is True
    assert result.total_iterations >= 1
    assert result.initial_error_count >= 1
    assert result.final_error_count == 0
    assert "</span>" in repaired

    # Re-validate repaired snippet with AST engine
    post_check = ast_engine.validate_snippet(repaired)
    assert post_check.is_valid is True
    assert post_check.error_count == 0


def test_refinement_loop_routes_and_repairs_duplicate_id(refinement_loop, ast_engine):
    """Routes duplicate ID violations back through the loop and verifies uniqueness."""
    broken_html = '<div id="card"><button type="button" id="card">Click</button></div>'

    repaired, result = refinement_loop.run_snippet_loop(broken_html, component_type="Card")

    assert result.status == RefinementStatus.SUCCESS
    assert result.is_valid is True
    assert result.final_error_count == 0

    post_check = ast_engine.validate_snippet(repaired)
    assert post_check.is_valid is True
    assert not any(e.rule_id == "no-dup-id" for e in post_check.errors)


def test_refinement_loop_routes_and_repairs_missing_attributes(refinement_loop, ast_engine):
    """Routes missing <img> required attributes (src, alt) back and verifies compliance."""
    broken_html = '<div class="profile"><img class="avatar"></div>'

    repaired, result = refinement_loop.run_snippet_loop(broken_html, component_type="Profile")

    assert result.status == RefinementStatus.SUCCESS
    assert result.is_valid is True
    assert 'src="' in repaired
    assert 'alt="' in repaired

    post_check = ast_engine.validate_snippet(repaired)
    assert post_check.is_valid is True


def test_refinement_loop_telemetry_and_history(refinement_loop):
    """Verifies that iteration history captures error progression and timings."""
    broken_html = "<div><span>Broken 1</div>"
    _, result = refinement_loop.run_snippet_loop(broken_html)

    assert len(result.history) >= 1
    record = result.history[0]
    assert record.iteration == 1
    assert record.initial_error_count >= 1
    assert record.execution_time_seconds >= 0.0
    assert len(record.errors_diagnosed) >= 1

    summary = result.format_summary()
    assert "Agentic Refinement Loop Summary: [SUCCESS]" in summary
    assert "Total Iterations:" in summary


def test_refinement_loop_max_retries_exceeded(ast_engine):
    """Verifies graceful termination when generator repeatedly fails to resolve error."""
    broken_html = "<div><span>Never Fixed</div>"

    # Mock generator that refuses to fix the code
    def stubborn_generator(payload, errors):
        return payload  # Returns exact same broken code

    stubborn_loop = AgenticRefinementLoop(
        validator_engine=ast_engine,
        generator_fn=stubborn_generator,
        max_iterations=2
    )

    _, result = stubborn_loop.run_snippet_loop(broken_html)

    assert result.status == RefinementStatus.MAX_RETRIES_EXCEEDED
    assert result.is_valid is False
    assert result.total_iterations == 2
    assert result.final_error_count >= 1


def test_refinement_loop_full_payload_routing(refinement_loop, ast_engine):
    """Routes errors for an entire multi-component UI payload dictionary."""
    broken_payload = {
        "page_title": "Multi-Component Prototype",
        "layout_type": "flexbox",
        "components": [
            {
                "component_id": "comp-1",
                "component_type": "navbar",
                "bounding_box": [0.0, 0.0, 1.0, 0.1],
                "html": "<nav><span>Broken Nav</nav>",
                "css_classes": "ui-navbar"
            },
            {
                "component_id": "comp-2",
                "component_type": "card",
                "bounding_box": [0.0, 0.2, 0.5, 0.6],
                "html": '<div id="card-dup">1</div><div id="card-dup">2</div>',
                "css_classes": "ui-card"
            }
        ],
        "full_html": '<!DOCTYPE html><html lang="en"><head><title>Test</title></head><body><div><span>Broken Body</div></body></html>',
        "full_css": "body { margin: 0; }"
    }

    repaired_payload, result = refinement_loop.run_payload_loop(broken_payload)

    assert result.status == RefinementStatus.SUCCESS
    assert result.is_valid is True
    assert result.final_error_count == 0

    # Components should be fixed
    comp1_html = repaired_payload["components"][0]["html"]
    assert "</span>" in comp1_html
    assert ast_engine.validate_snippet(comp1_html).is_valid is True


def test_model_router_refine_integration():
    """Verifies that ModelRouter.refine integrates seamlessly with error feedback."""
    router = ModelRouter(strategy=RoutingStrategy.MOCK)
    erroneous_payload = {
        "page_title": "Test Router Refine",
        "layout_type": "flexbox",
        "components": [
            {
                "component_id": "comp-1",
                "component_type": "navbar",
                "bounding_box": [0.0, 0.0, 1.0, 0.1],
                "html": "<div><span>Broken</div>",
                "css_classes": "ui-navbar"
            }
        ],
        "full_html": '<!DOCTYPE html><html lang="en"><head><title>Test</title></head><body><div><span>Broken</div></body></html>',
        "full_css": "body { margin: 0; }"
    }
    mock_errors = [
        ExtractedError(
            rule_id="close-order",
            category=ErrorCategory.STRUCTURAL_CLOSURE,
            severity="error",
            message="Unclosed element '<span>'",
            line=1,
            column=6
        )
    ]

    repaired = router.refine(erroneous_payload, mock_errors, force_mock=True)

    assert "components" in repaired
    assert "</span></div>" in repaired["components"][0]["html"]
