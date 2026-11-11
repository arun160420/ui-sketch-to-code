"""
tests/test_security.py

Unit test suite for Week 10 Deliverable (COM71123-12):
Security Sanitization and Sandboxed Preview.

Covers:
1. DOMPurify sanitization engine with JSDOM and Python regex fallback.
2. Neutralization of common XSS attack vectors:
   - Direct <script> injection
   - Inline onerror event handlers on images
   - SVG onload payloads
   - javascript: pseudo-protocol URIs in anchors and forms
   - Dangerous <object>, <embed>, and nested <iframe> elements
   - Autofocus event triggers
   - Body onload attributes
3. Sandboxed iframe policy and CSP header generation:
   - Verification of sandbox directive: allow-scripts allow-same-origin allow-forms
   - Absence of dangerous flags (allow-top-navigation, allow-popups)
   - CSP header construction and strict object-src 'none'
4. Full SketchToCodePipeline integration with security report generation.
"""

import pytest
from src.security import (
    SecuritySanitizer,
    SandboxedIframePolicy,
    ThreatSeverity,
    DetectedThreat,
    SanitizationReport
)
from src.pipeline import SketchToCodePipeline
from src.model_router import RoutingStrategy


@pytest.fixture
def sanitizer():
    return SecuritySanitizer(enable_node_dompurify=True)


@pytest.fixture
def python_fallback_sanitizer():
    # Force pure-python fallback for defense-in-depth testing
    return SecuritySanitizer(enable_node_dompurify=False)


@pytest.fixture
def iframe_policy():
    return SandboxedIframePolicy()


# ==============================================================================
# Task 1 & 4: DOMPurify and Common XSS Attack Vector Tests
# ==============================================================================

def test_xss_direct_script_tag(sanitizer):
    """Test defanging of direct <script> execution tags."""
    dirty = "<div><h1>Title</h1><script>alert('XSS-1')</script><p>Clean body</p></div>"
    report = sanitizer.sanitize(dirty)
    assert "<script" not in report.sanitized_html.lower()
    assert "alert(" not in report.sanitized_html
    assert "<h1>Title</h1>" in report.sanitized_html
    assert "<p>Clean body</p>" in report.sanitized_html
    assert report.is_sanitized is True


def test_xss_image_onerror_handler(sanitizer):
    """Test removal of inline event handlers like onerror on images."""
    dirty = '<img src="invalid.jpg" onerror="alert(\'XSS-2\')" alt="User photo">'
    report = sanitizer.sanitize(dirty)
    assert "onerror" not in report.sanitized_html.lower()
    assert "alert" not in report.sanitized_html
    assert 'alt="User photo"' in report.sanitized_html


def test_xss_svg_onload(sanitizer):
    """Test blocking of SVG elements with inline onload handlers."""
    dirty = '<svg><g onload="alert(\'XSS-3\')"><circle cx="10" cy="10" r="5"></circle></g></svg>'
    report = sanitizer.sanitize(dirty)
    assert "onload" not in report.sanitized_html.lower()
    assert "alert" not in report.sanitized_html


def test_xss_javascript_href(sanitizer):
    """Test stripping or neutralizing javascript: URI scheme in anchors."""
    dirty = '<a href="javascript:alert(\'XSS-4\')">Click to win</a>'
    report = sanitizer.sanitize(dirty)
    assert "javascript:" not in report.sanitized_html.lower()
    assert "Click to win" in report.sanitized_html


def test_xss_nested_iframe(sanitizer):
    """Test defense against nested malicious iframe with javascript src."""
    dirty = '<iframe src="javascript:alert(\'XSS-5\')"></iframe>'
    report = sanitizer.sanitize(dirty)
    assert "javascript:" not in report.sanitized_html.lower()


def test_xss_object_and_embed_tags(sanitizer):
    """Test removal of unsafe plugin tags like <object> and <embed>."""
    dirty = (
        '<div>'
        '<object data="malicious.swf" type="application/x-shockwave-flash"></object>'
        '<embed src="exploit.pdf" type="application/pdf">'
        '<span>Safe content</span>'
        '</div>'
    )
    report = sanitizer.sanitize(dirty)
    assert "<object" not in report.sanitized_html.lower()
    assert "<embed" not in report.sanitized_html.lower()
    assert "<span>Safe content</span>" in report.sanitized_html


def test_xss_autofocus_onfocus(sanitizer):
    """Test stripping of autofocus + onfocus vector on inputs."""
    dirty = '<input type="text" autofocus onfocus="alert(\'XSS-8\')" name="username">'
    report = sanitizer.sanitize(dirty)
    assert "onfocus" not in report.sanitized_html.lower()
    assert "alert" not in report.sanitized_html
    assert 'name="username"' in report.sanitized_html


def test_xss_body_onload(sanitizer):
    """Test stripping of onload on body tags."""
    dirty = '<body onload="alert(\'XSS-9\')"><h1>Dashboard</h1></body>'
    report = sanitizer.sanitize(dirty)
    assert "onload" not in report.sanitized_html.lower()
    assert "<h1>Dashboard</h1>" in report.sanitized_html


def test_xss_form_action_javascript(sanitizer):
    """Test neutralization of javascript: URI in form actions."""
    dirty = '<form action="javascript:stealCookie()"><button type="submit">Submit</button></form>'
    report = sanitizer.sanitize(dirty)
    assert "javascript:" not in report.sanitized_html.lower()
    assert "<button" in report.sanitized_html


# ==============================================================================
# Pure Python Fallback Engine Tests (Defense-in-Depth)
# ==============================================================================

def test_pure_python_fallback_defense(python_fallback_sanitizer):
    """Verify regex/DOM fallback sanitizer neutralizes threats without Node."""
    dirty = (
        '<div>'
        '<script>alert("fallback")</script>'
        '<img src="x" onerror="evil()">'
        '<a href="javascript:exploit()">Link</a>'
        '<object data="plugin.swf"></object>'
        '<p>Valid Paragraph</p>'
        '</div>'
    )
    report = python_fallback_sanitizer.sanitize(dirty)
    assert "<script" not in report.sanitized_html.lower()
    assert "onerror" not in report.sanitized_html.lower()
    assert "javascript:" not in report.sanitized_html.lower()
    assert "<object" not in report.sanitized_html.lower()
    assert "Valid Paragraph" in report.sanitized_html
    assert len(report.threats) > 0


# ==============================================================================
# Task 2: Sandboxed Iframe Component & Policy Tests
# ==============================================================================

def test_sandboxed_iframe_attributes(iframe_policy):
    """Ensure sandbox directive includes necessary capabilities and blocks harmful ones."""
    sandbox_attr = iframe_policy.sandbox_attribute
    assert "allow-scripts" in sandbox_attr
    assert "allow-same-origin" in sandbox_attr
    assert "allow-forms" in sandbox_attr
    # Security: MUST NOT allow top navigation or popups
    assert "allow-top-navigation" not in sandbox_attr
    assert "allow-popups" not in sandbox_attr


def test_sandboxed_iframe_csp_directives(iframe_policy):
    """Ensure Content Security Policy disables object execution and limits scripts."""
    csp = iframe_policy.generate_csp()
    assert "object-src 'none'" in csp
    assert "default-src" in csp
    assert "script-src" in csp
    assert "style-src" in csp


def test_sandboxed_iframe_tag_generation(iframe_policy):
    """Verify HTML iframe element generation with sandbox and security attributes."""
    iframe_tag = iframe_policy.render_iframe_tag(
        srcdoc="<h1>Safe Preview</h1>",
        element_id="preview-frame",
        css_classes="w-full h-full border-0"
    )
    assert '<iframe' in iframe_tag
    assert 'sandbox="allow-forms allow-same-origin allow-scripts"' in iframe_tag
    assert 'id="preview-frame"' in iframe_tag
    assert 'referrerpolicy="no-referrer"' in iframe_tag
    assert '&lt;h1&gt;Safe Preview&lt;/h1&gt;' in iframe_tag or '<h1>Safe Preview</h1>' in iframe_tag


# ==============================================================================
# Full Pipeline Integration Tests with Security Sanitization
# ==============================================================================

def test_pipeline_integration_with_security():
    """Verify that SketchToCodePipeline runs SecuritySanitizer and returns security telemetry."""
    pipeline = SketchToCodePipeline(strategy=RoutingStrategy.MOCK)
    result = pipeline.process(
        input_source="tests/sample_wireframe.png",
        force_mock=True
    )
    assert result.success is True
    assert result.ast_valid_initially is True
    assert result.security_sanitized is True
    assert result.security_report is not None
    assert "threats_detected" in result.security_report
    assert "<script" not in result.full_html.lower()
