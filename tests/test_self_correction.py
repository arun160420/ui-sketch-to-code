"""
tests/test_self_correction.py

Unit test suite for Week 8 Deliverable (COM71123-10):
Agentic Refinement Loop - Self-Correction.

Tests:
1. Self-Correction Prompt Engineering (Reflection, Repair Plan, Few-Shot guidance)
2. Generation Pipeline Integration (Preprocessing -> Router -> Validator -> Self-Correction)
3. Iterative Code Generation and Validation Cycles (Snippet & Multi-component payload)
4. Convergence Monitoring (States: CONVERGED, PROGRESSING, STAGNATING, REGRESSING, Early Stopping)
"""

import pytest
from typing import Dict, Any, List

from src.ast_validator import ASTValidationEngine
from src.refinement_loop import ASTErrorExtractor, ExtractedError, ErrorCategory
from src.self_correction import (
    SelfCorrectionPromptEngine,
    ConvergenceState,
    CycleTelemetry,
    ConvergenceMonitor,
    SelfCorrectionEngine,
    SelfCorrectionResult
)
from src.pipeline import SketchToCodePipeline, PipelineResult
from src.model_router import ModelRouter, RoutingStrategy


@pytest.fixture
def ast_engine():
    """Initializes ASTValidationEngine for testing."""
    return ASTValidationEngine()


@pytest.fixture
def self_correction_engine(ast_engine):
    """Initializes standard SelfCorrectionEngine with default reflection repair."""
    return SelfCorrectionEngine(validator_engine=ast_engine, max_cycles=3)


# ============================================================================
# Task 1: Prompt Design for Code Repair Based on Error Logs Tests
# ============================================================================

def test_reflection_prompt_design():
    """Ensures self-correction prompts enforce reflection, repair plan, and repaired code sections."""
    errors = [
        ExtractedError(
            rule_id="close-order",
            category=ErrorCategory.STRUCTURAL_CLOSURE,
            severity="error",
            message="Unclosed element '<span>'",
            line=1,
            column=6,
            selector="nav > span",
            remediation_hint="Close the opening <span> tag before parent closes."
        )
    ]
    code = "<nav><span>Unclosed Brand</nav>"
    prompt = SelfCorrectionPromptEngine.build_reflection_prompt(
        extracted_errors=errors,
        original_code=code,
        component_type="Navbar",
        include_few_shot=True
    )

    assert "Agentic Self-Correction cycle for Navbar" in prompt
    assert "[close-order]" in prompt
    assert "Unclosed element '<span>'" in prompt
    assert "<reflection>" in prompt
    assert "<repair_plan>" in prompt
    assert "<repaired_code>" in prompt
    assert "Reference Self-Correction Pattern:" in prompt


def test_localized_component_repair_prompt():
    """Verifies that targeted component repair prompts isolate the specific failing component."""
    errors = [
        ExtractedError(
            rule_id="no-dup-id",
            category=ErrorCategory.DUPLICATE_IDENTIFIER,
            severity="error",
            message="Duplicate ID 'submit-btn'",
            line=2,
            column=10,
            remediation_hint="Rename duplicate IDs."
        )
    ]
    failing_code = '<button id="submit-btn">A</button>\n<button id="submit-btn">B</button>'
    prompt = SelfCorrectionPromptEngine.build_component_localized_repair_prompt(
        component_id="comp-btn-01",
        component_type="button",
        failing_html=failing_code,
        errors=errors
    )

    assert "Localized Component Self-Correction: [BUTTON] (ID: comp-btn-01)" in prompt
    assert "[no-dup-id]" in prompt
    assert "submit-btn" in prompt


# ============================================================================
# Task 2: Convergence Monitoring & Telemetry Tests
# ============================================================================

def test_convergence_monitor_converged():
    """Validates that achieving 0 errors transitions state to CONVERGED and terminates loop."""
    monitor = ConvergenceMonitor(max_cycles=3)
    state, should_continue = monitor.evaluate_cycle(
        cycle_num=1,
        error_count_before=4,
        error_count_after=0,
        duration_seconds=0.15
    )

    assert state == ConvergenceState.CONVERGED
    assert should_continue is False  # Loop stops immediately upon convergence
    assert len(monitor.history) == 1
    assert monitor.history[0].delta_errors == 4
    assert monitor.history[0].velocity == 1.0


def test_convergence_monitor_progressing():
    """Validates that error reduction transitions to PROGRESSING and permits next cycle."""
    monitor = ConvergenceMonitor(max_cycles=3)
    state, should_continue = monitor.evaluate_cycle(
        cycle_num=1,
        error_count_before=5,
        error_count_after=2,
        duration_seconds=0.20
    )

    assert state == ConvergenceState.PROGRESSING
    assert should_continue is True
    assert monitor.history[0].delta_errors == 3


def test_convergence_monitor_stagnation_detection():
    """Validates that repeated identical error counts trigger STAGNATING and early stops."""
    monitor = ConvergenceMonitor(max_cycles=4, max_stagnation_cycles=2)

    # Cycle 1: Stagnating
    state1, cont1 = monitor.evaluate_cycle(cycle_num=1, error_count_before=3, error_count_after=3, duration_seconds=0.1)
    assert state1 == ConvergenceState.STAGNATING
    assert cont1 is True  # First stagnation allowed

    # Cycle 2: Second consecutive stagnation triggers early stopping
    state2, cont2 = monitor.evaluate_cycle(cycle_num=2, error_count_before=3, error_count_after=3, duration_seconds=0.1)
    assert state2 == ConvergenceState.STAGNATING
    assert cont2 is False  # Max stagnation cycles reached, aborts loop!


def test_convergence_monitor_regression_detection():
    """Validates that newly introduced errors trigger REGRESSING."""
    monitor = ConvergenceMonitor(max_cycles=3)
    state, cont = monitor.evaluate_cycle(cycle_num=1, error_count_before=2, error_count_after=4, duration_seconds=0.1)

    assert state == ConvergenceState.REGRESSING
    assert monitor.history[0].delta_errors == -2


def test_convergence_metrics_summary():
    """Checks overall summary metrics computation (total delta, reduction %, duration)."""
    monitor = ConvergenceMonitor(max_cycles=3)
    monitor.evaluate_cycle(cycle_num=1, error_count_before=6, error_count_after=2, duration_seconds=0.1)
    monitor.evaluate_cycle(cycle_num=2, error_count_before=2, error_count_after=0, duration_seconds=0.1)

    metrics = monitor.get_summary_metrics()
    assert metrics["total_cycles"] == 2
    assert metrics["converged"] is True
    assert metrics["initial_error_count"] == 6
    assert metrics["final_error_count"] == 0
    assert metrics["total_errors_resolved"] == 6
    assert metrics["error_reduction_percentage"] == 100.0


# ============================================================================
# Task 3: Iterative Code Generation and Validation Cycles Tests
# ============================================================================

def test_self_correct_snippet_converges(self_correction_engine, ast_engine):
    """Executes self-correction on a broken snippet and verifies 0 errors post-correction."""
    broken_snippet = '<div class="header"><h1><span>Broken Title</h1></div>'

    # Check initially failing
    rep_before = ast_engine.validate_snippet(broken_snippet)
    assert not rep_before.is_valid

    # Run self-correction
    result = self_correction_engine.self_correct_snippet(broken_snippet, component_type="Header")

    assert result.converged is True
    assert result.convergence_state == ConvergenceState.CONVERGED
    assert result.final_errors == 0
    assert result.total_cycles >= 1

    # Verify final HTML validates cleanly
    rep_after = ast_engine.validate_snippet(result.final_code)
    assert rep_after.is_valid is True


def test_self_correct_payload_localized_components(self_correction_engine, ast_engine):
    """Executes localized component-level self-correction across a full UI payload."""
    payload = {
        "page_title": "Multi Component Self Correction",
        "layout_type": "flexbox",
        "components": [
            {
                "component_id": "comp-1",
                "component_type": "navbar",
                "html": '<nav><span>Broken Navbar</nav>'
            },
            {
                "component_id": "comp-2",
                "component_type": "card",
                "html": '<div id="dup-card"><p id="dup-card">Content</p></div>'
            }
        ],
        "full_html": '<!DOCTYPE html><html lang="en"><head><title>Test</title></head><body><main><span>Broken Body</main></body></html>'
    }

    result = self_correction_engine.self_correct_payload(payload)

    assert result.converged is True
    assert result.final_errors == 0

    # Components should be individually valid
    repaired_comp1 = result.final_code["components"][0]["html"]
    repaired_comp2 = result.final_code["components"][1]["html"]
    assert ast_engine.validate_snippet(repaired_comp1).is_valid is True
    assert ast_engine.validate_snippet(repaired_comp2).is_valid is True


# ============================================================================
# Task 4: Pipeline Integration Tests
# ============================================================================

def test_pipeline_integration_with_self_correction(ast_engine):
    """Tests the full end-to-end pipeline with automatic self-correction activation."""
    wireframe_data = {
        "original_shape": (800, 800),
        "target_shape": (800, 800),
        "total_components": 2,
        "normalized_boxes": [
            {"id": 1, "norm_box": [0.0, 0.0, 1.0, 0.1], "area_ratio": 0.1},
            {"id": 2, "norm_box": [0.1, 0.2, 0.9, 0.7], "area_ratio": 0.4}
        ]
    }

    # Pipeline running in mock mode
    pipeline = SketchToCodePipeline(strategy=RoutingStrategy.MOCK)
    result = pipeline.process(wireframe_data, force_mock=True)

    assert result.success is True
    assert len(result.components) > 0
    assert result.final_error_count == 0
    assert result.model_provider == "deterministic-mock"
    assert "<!DOCTYPE html>" in result.full_html


def test_pipeline_recovers_from_injected_syntax_error(ast_engine):
    """Pipeline detects model-generated syntax errors and auto-recovers via SelfCorrectionEngine."""
    # Custom router generator that deliberately produces broken code initially
    class BuggyMockGenerator:
        def generate_code(self, wireframe_data, **kwargs):
            return {
                "page_title": "Buggy Prototype",
                "layout_type": "flexbox",
                "components": [
                    {
                        "component_id": "c-1",
                        "component_type": "navbar",
                        "html": '<nav><span>Broken Tag in Pipeline</nav>',
                        "css_classes": "ui-nav"
                    }
                ],
                "full_html": '<!DOCTYPE html><html lang="en"><head><title>Test</title></head><body><div><span>Unclosed Tag</div></body></html>',
                "full_css": "body { margin: 0; }"
            }

    custom_router = ModelRouter(strategy=RoutingStrategy.MOCK)
    custom_router.gpt_client = BuggyMockGenerator()

    pipeline = SketchToCodePipeline(router=custom_router)
    dummy_input = {"normalized_boxes": [{"id": 1, "norm_box": [0,0,1,0.1]}], "total_components": 1}

    result = pipeline.process(dummy_input, force_mock=False)

    assert result.self_correction_applied is True
    assert result.success is True
    assert result.final_error_count == 0
    assert result.convergence_state == ConvergenceState.CONVERGED.value
