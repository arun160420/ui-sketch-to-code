"""
tests/test_performance.py

Unit test suite for Week 11 Deliverable (COM71123-13):
Performance Evaluation, Benchmarking, and Optimization.

Covers:
1. Latency Measurement Engine:
   - Validates sub-2.5s end-to-end processing across pipeline iterations.
   - Evaluates p50, p95, min, and max latency bounds.
2. AST Structural Integrity:
   - Evaluates compliance across standard layout archetypes.
   - Asserts integrity score exceeds the >95.0% target requirement.
3. Tailwind CSS Compliance:
   - Validates 100% utility class compliance across all generated components.
   - Tests detection and rejection of malformed or non-standard class tokens.
   - Verifies responsive prefixes, arbitrary values, and state modifiers.
4. Bottleneck Profiler & Optimization:
   - Tests phase bottleneck diagnosis and recommendations.
   - Verifies AST and sanitization memoization in OptimizedPipeline.
5. Performance Reporting:
   - Tests JSON serialization and Markdown audit generation.
"""

from pathlib import Path
import pytest

from src.performance import (
    TailwindComplianceValidator,
    ASTIntegrityBenchmark,
    LatencyBenchmark,
    PerformanceBottleneckAnalyzer,
    OptimizedPipeline,
    PerformanceReport
)
from src.component_prompts import PROMPT_TEMPLATES
from src.model_router import RoutingStrategy
from src.pipeline import SketchToCodePipeline


@pytest.fixture
def tailwind_validator():
    return TailwindComplianceValidator()


@pytest.fixture
def ast_benchmark():
    return ASTIntegrityBenchmark()


@pytest.fixture
def sample_wireframe():
    return {
        "original_shape": (800, 800),
        "target_shape": (800, 800),
        "total_components": 3,
        "normalized_boxes": [
            {"id": 1, "norm_box": [0.0, 0.0, 1.0, 0.1], "area_ratio": 0.1},
            {"id": 2, "norm_box": [0.1, 0.15, 0.9, 0.55], "area_ratio": 0.35},
            {"id": 3, "norm_box": [0.1, 0.6, 0.9, 0.95], "area_ratio": 0.3}
        ]
    }


# ==============================================================================
# Task 1: Sub-2.5s Latency Measurement Tests
# ==============================================================================

def test_latency_measurement_sub_2_5s(sample_wireframe):
    """Verifies that average pipeline latency is strictly under the 2.5-second SLA."""
    benchmark = LatencyBenchmark()
    result = benchmark.run_benchmark(sample_wireframe, iterations=3, warmup_runs=1)

    assert result.mean_latency_ms < 2500.0
    assert result.meets_target is True
    assert result.p50_latency_ms < 2500.0
    assert result.p95_latency_ms < 2500.0
    assert "preprocess" in result.phase_breakdown_ms
    assert "ast_validation" in result.phase_breakdown_ms
    assert "security" in result.phase_breakdown_ms


def test_latency_benchmark_with_image_input():
    """Verifies latency benchmark on physical wireframe image asset."""
    sample_path = Path("tests/sample_wireframe.png")
    if not sample_path.exists():
        pytest.skip("tests/sample_wireframe.png not found")

    benchmark = LatencyBenchmark()
    result = benchmark.run_benchmark(str(sample_path), iterations=2, warmup_runs=1)
    assert result.mean_latency_ms < 2500.0
    assert result.meets_target is True


# ==============================================================================
# Task 2: AST Structural Integrity (> 95% Target) Tests
# ==============================================================================

def test_ast_structural_integrity_threshold(ast_benchmark):
    """Verifies that AST structural integrity score across UI corpus exceeds 95%."""
    corpus = [
        {"name": "Navbar", "html": PROMPT_TEMPLATES["navbar"]["default_html"]},
        {"name": "Form", "html": PROMPT_TEMPLATES["form"]["default_html"]},
        {"name": "Hero", "html": PROMPT_TEMPLATES["hero"]["default_html"]},
        {"name": "Card", "html": PROMPT_TEMPLATES["card"]["default_html"]},
        {"name": "Input", "html": PROMPT_TEMPLATES["input"]["default_html"]},
    ]

    result = ast_benchmark.evaluate_test_corpus(corpus)
    assert result["meets_target"] is True
    assert result["integrity_score"] >= 95.0
    assert result["total_errors"] == 0
    assert result["total_passed"] == len(corpus)


def test_ast_integrity_detects_malformed_input(ast_benchmark):
    """Verifies that corrupted AST trees are appropriately flagged."""
    corrupted_corpus = [
        {"name": "Valid Card", "html": PROMPT_TEMPLATES["card"]["default_html"]},
        {"name": "Unclosed Divs", "html": "<div><div><p>Unclosed"},
    ]
    result = ast_benchmark.evaluate_test_corpus(corrupted_corpus)
    assert result["total_errors"] > 0
    assert result["integrity_score"] < 100.0


# ==============================================================================
# Task 3: Tailwind Compliance (100% Target) Tests
# ==============================================================================

def test_tailwind_compliance_100_percent(tailwind_validator):
    """Verifies 100% Tailwind CSS utility class compliance across all standard components."""
    for category, tmpl in PROMPT_TEMPLATES.items():
        res = tailwind_validator.validate_html(tmpl["default_html"])
        assert res["is_compliant"] is True, f"Failed for {category}: {res['invalid_classes']}"
        assert res["compliance_score"] == 100.0
        assert len(res["invalid_classes"]) == 0


def test_tailwind_validator_arbitrary_and_responsive(tailwind_validator):
    """Verifies support for arbitrary values ([#123456]) and responsive/state variants."""
    html = (
        '<div class="md:hover:bg-indigo-700 focus:ring-2 p-[15px] w-[320px] '
        'dark:text-slate-200 transition-all duration-300 shadow-md">Hello</div>'
    )
    res = tailwind_validator.validate_html(html)
    assert res["is_compliant"] is True
    assert res["compliance_score"] == 100.0


def test_tailwind_validator_rejects_invalid_tokens(tailwind_validator):
    """Verifies detection of non-standard, fabricated CSS classes."""
    html = '<button class="px-4 py-2 my-bogus-button-class completely-invalid-token">Click</button>'
    res = tailwind_validator.validate_html(html)
    assert res["is_compliant"] is False
    assert res["compliance_score"] < 100.0
    assert "my-bogus-button-class" in res["invalid_classes"]
    assert "completely-invalid-token" in res["invalid_classes"]


# ==============================================================================
# Task 4: Bottleneck Diagnosis & Optimization Tests
# ==============================================================================

def test_bottleneck_analyzer_diagnosis():
    """Verifies that the bottleneck profiler identifies the slowest stage and yields guidance."""
    breakdown = {
        "preprocess": 140.0,
        "synthesis": 2.0,
        "ast_validation": 30.0,
        "accessibility": 5.0,
        "security": 10.0
    }
    diagnosis = PerformanceBottleneckAnalyzer.identify_bottleneck(breakdown)
    assert diagnosis["primary_bottleneck"] == "preprocess"
    assert diagnosis["percentage"] > 70.0
    assert "downsampling" in diagnosis["recommendation"].lower() or "opencv" in diagnosis["recommendation"].lower()


def test_optimized_pipeline_memoization(sample_wireframe):
    """Verifies that OptimizedPipeline caches validation results for repeated calls."""
    pipeline = OptimizedPipeline(strategy=RoutingStrategy.MOCK)
    html_snippet = "<nav class='flex items-center'><span>Logo</span></nav>"

    # First call - populates cache
    rep1 = pipeline.validate_fast(html_snippet)
    # Second call - retrieves from cache
    rep2 = pipeline.validate_fast(html_snippet)

    assert rep1.is_valid == rep2.is_valid
    assert str(hash(html_snippet)) in pipeline.validation_cache


# ==============================================================================
# Task 5: Performance Report Serialization Tests
# ==============================================================================

def test_performance_report_serialization(sample_wireframe):
    """Verifies JSON dictionary and Markdown formatting of performance report."""
    bench = LatencyBenchmark()
    lat_res = bench.run_benchmark(sample_wireframe, iterations=1, warmup_runs=0)
    ast_res = {"meets_target": True, "integrity_score": 100.0, "total_passed": 5, "total_evaluated": 5, "total_errors": 0, "total_warnings": 0}
    tw_res = {"is_compliant": True, "compliance_score": 100.0, "total_classes": 50, "valid_classes": 50, "invalid_classes": []}
    bottleneck = {"primary_bottleneck": "preprocess", "percentage": 85.0, "recommendation": "Downsample image"}

    report = PerformanceReport(
        timestamp="2026-11-11 19:30:00",
        latency=lat_res,
        ast_integrity=ast_res,
        tailwind_compliance=tw_res,
        bottleneck_analysis=bottleneck,
        all_targets_met=True
    )

    data = report.to_dict()
    assert data["all_targets_met"] is True
    assert data["latency"]["mean_latency_ms"] == lat_res.mean_latency_ms

    md = report.to_markdown_summary()
    assert "Week 11 Performance Evaluation" in md
    assert "Sub-2.5s" in md
    assert "100%" in md
