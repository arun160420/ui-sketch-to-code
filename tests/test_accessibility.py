"""
tests/test_accessibility.py

Unit test suite for Week 9 Deliverable (COM71123-11):
WCAG Accessibility and Semantic HTML5 Enforcement.

Covers:
1. WCAG 2.1 AA guideline taxonomy and rule definitions.
2. AccessibilityAuditor AST & DOM verification:
   - Image alt text requirements (WCAG 1.1.1)
   - Form input label associations & autocomplete (WCAG 1.3.1 / 1.3.5)
   - Keyboard accessible buttons, links, and ARIA roles (WCAG 2.1.1 / 4.1.2)
   - Heading hierarchy ordering (WCAG 2.4.6)
   - Semantic HTML5 landmarks (WCAG 1.3.1)
   - Table header scopes (WCAG 1.3.1)
3. AccessibilityEnforcer automated remediation & semantic upgrading.
4. Refined component prompt templates for semantic HTML5.
5. Full SketchToCodePipeline integration with accessibility reporting.
"""

import pytest
from src.accessibility import (
    AccessibilityAuditor,
    AccessibilityEnforcer,
    AccessibilityReport,
    AccessibilitySeverity,
    WCAGCriterion
)
from src.component_prompts import ComponentCodeGenerator, UIComponentCategory
from src.pipeline import SketchToCodePipeline
from src.model_router import RoutingStrategy


@pytest.fixture
def auditor():
    return AccessibilityAuditor()


@pytest.fixture
def enforcer(auditor):
    return AccessibilityEnforcer(auditor=auditor)


@pytest.fixture
def prompt_generator():
    return ComponentCodeGenerator()


# ==============================================================================
# Task 1: WCAG Guidelines Review & Taxonomy Tests
# ==============================================================================

def test_wcag_guideline_taxonomy():
    """Verifies that all required WCAG 2.1 AA criteria are present in taxonomy."""
    assert WCAGCriterion.NON_TEXT_CONTENT.value.startswith("1.1.1")
    assert WCAGCriterion.INFO_RELATIONSHIPS.value.startswith("1.3.1")
    assert WCAGCriterion.INPUT_PURPOSE.value.startswith("1.3.5")
    assert WCAGCriterion.KEYBOARD_ACCESSIBLE.value.startswith("2.1.1")
    assert WCAGCriterion.HEADINGS_AND_LABELS.value.startswith("2.4.6")
    assert WCAGCriterion.NAME_ROLE_VALUE.value.startswith("4.1.2")


def test_empty_or_whitespace_html_audit(auditor):
    """Empty HTML should return a 100% compliant baseline report."""
    report = auditor.audit("")
    assert report.is_compliant is True
    assert report.score == 100.0
    assert report.error_count == 0
    assert len(report.violations) == 0


# ==============================================================================
# Task 2: Refined Generation Prompts Prioritizing Semantic HTML5
# ==============================================================================

@pytest.mark.parametrize("category", [
    UIComponentCategory.NAVBAR.value,
    UIComponentCategory.AUTH_FORM.value,
    UIComponentCategory.HERO.value,
    UIComponentCategory.CARD.value,
    UIComponentCategory.INPUT.value
])
def test_component_prompts_enforce_wcag_and_semantics(prompt_generator, category):
    """Verifies generation prompts enforce semantic HTML5 and WCAG guidelines."""
    prompt = prompt_generator.build_prompt(category)
    assert "semantic" in prompt.lower()
    assert "wcag" in prompt.lower() or "accessibility" in prompt.lower()

    comp = prompt_generator.generate_component(category)
    assert len(comp["html"]) > 0


# ==============================================================================
# Task 3: In-Depth Checks for Common Accessibility Pitfalls
# ==============================================================================

def test_missing_image_alt_triggers_error(auditor):
    """WCAG 1.1.1: <img> elements missing alt attribute must trigger an error."""
    broken = '<div><img src="avatar.png"></div>'
    report = auditor.audit(broken)
    assert report.is_compliant is False
    assert report.error_count >= 1
    assert any(v.rule_id == "wcag-img-alt" and v.severity == AccessibilitySeverity.ERROR.value for v in report.violations)


def test_valid_image_alt_passes(auditor):
    """WCAG 1.1.1: <img> elements with alt attribute pass verification."""
    valid = '<div><img src="avatar.png" alt="User avatar thumbnail"></div>'
    report = auditor.audit(valid)
    assert not any(v.rule_id == "wcag-img-alt" for v in report.violations)


def test_unassociated_form_input_triggers_error(auditor):
    """WCAG 1.3.1: Inputs missing associated <label> or aria-label trigger an error."""
    broken = '<form><input type="text" id="username" placeholder="Username"></form>'
    report = auditor.audit(broken)
    assert report.is_compliant is False
    assert any(v.rule_id == "wcag-form-label" for v in report.violations)


def test_associated_form_input_passes(auditor):
    """WCAG 1.3.1: Explicit <label for="id"> satisfies accessibility check."""
    valid = '<form><label for="username">Username</label><input type="text" id="username"></form>'
    report = auditor.audit(valid)
    assert not any(v.rule_id == "wcag-form-label" for v in report.violations)


def test_aria_label_on_input_passes(auditor):
    """WCAG 1.3.1: aria-label directly on input satisfies accessible name check."""
    valid = '<form><input type="search" id="site-search" aria-label="Search articles"></form>'
    report = auditor.audit(valid)
    assert not any(v.rule_id == "wcag-form-label" for v in report.violations)


def test_missing_input_autocomplete_triggers_warning(auditor):
    """WCAG 1.3.5: Credential inputs missing autocomplete trigger warning."""
    broken = '<form><label for="email">Email</label><input type="email" id="email"></form>'
    report = auditor.audit(broken)
    assert any(v.rule_id == "wcag-input-autocomplete" for v in report.violations)


def test_button_missing_type_triggers_warning(auditor):
    """WCAG 4.1.2: <button> missing type attribute triggers warning."""
    broken = '<button>Click Me</button>'
    report = auditor.audit(broken)
    assert any(v.rule_id == "wcag-button-type" for v in report.violations)


def test_button_without_accessible_name_triggers_error(auditor):
    """WCAG 4.1.2: <button> with empty text and no aria-label triggers error."""
    broken = '<button type="button"></button>'
    report = auditor.audit(broken)
    assert report.is_compliant is False
    assert any(v.rule_id == "wcag-button-name" for v in report.violations)


def test_heading_hierarchy_skips_trigger_warning(auditor):
    """WCAG 2.4.6: Heading skips (e.g. h1 directly to h3) trigger warning."""
    broken = '<main><h1>Title</h1><h3>Sub-sub heading</h3></main>'
    report = auditor.audit(broken)
    assert any(v.rule_id == "wcag-heading-order" for v in report.violations)
    assert "h1" in report.heading_hierarchy
    assert "h3" in report.heading_hierarchy


def test_generic_clickable_div_triggers_warning(auditor):
    """WCAG 2.1.1: Clickable <div> without role='button' and tabindex triggers warning."""
    broken = '<div onclick="doSomething()" class="btn">Click</div>'
    report = auditor.audit(broken)
    assert any(v.rule_id == "wcag-clickable-role" for v in report.violations)


def test_table_header_missing_scope_triggers_warning(auditor):
    """WCAG 1.3.1: <th> missing scope attribute triggers warning."""
    broken = '<table><tr><th>Name</th></tr></table>'
    report = auditor.audit(broken)
    assert any(v.rule_id == "wcag-table-scope" for v in report.violations)


# ==============================================================================
# Task 4: Automated Remediation & Enforcement Tests
# ==============================================================================

def test_enforcer_remediates_img_alt(enforcer):
    """Enforcer automatically injects alt attribute into bare <img> tags."""
    broken = '<img src="photo.jpg">'
    remediated, report = enforcer.enforce_accessibility(broken)
    assert 'alt="' in remediated
    assert not any(v.rule_id == "wcag-img-alt" for v in report.violations)


def test_enforcer_remediates_missing_labels(enforcer):
    """Enforcer automatically injects aria-label into orphan form inputs."""
    broken = '<input type="email" placeholder="you@domain.com">'
    remediated, report = enforcer.enforce_accessibility(broken)
    assert 'aria-label=' in remediated
    assert 'autocomplete="email"' in remediated
    assert not any(v.rule_id == "wcag-form-label" for v in report.violations)


def test_enforcer_remediates_buttons(enforcer):
    """Enforcer automatically injects type and accessible name into buttons."""
    broken = '<button></button>'
    remediated, report = enforcer.enforce_accessibility(broken)
    assert 'type="button"' in remediated
    assert 'aria-label=' in remediated or len(remediated) > 17
    assert report.is_compliant is True


def test_enforcer_upgrades_full_document(enforcer):
    """Enforcer adds lang='en', <title>, and wraps body in <main role='main'>."""
    broken_doc = """
    <html>
      <head></head>
      <body>
        <h1>Synthesized Page</h1>
        <p>Content without semantic landmarks.</p>
      </body>
    </html>
    """
    remediated, report = enforcer.enforce_accessibility(broken_doc)
    assert 'lang="en"' in remediated
    assert "<title>" in remediated
    assert "<main" in remediated or 'role="main"' in remediated
    assert report.is_compliant is True


# ==============================================================================
# Task 5: End-to-End Pipeline Integration Tests
# ==============================================================================

def test_pipeline_accessibility_integration():
    """Full pipeline automatically enforces accessibility and reports WCAG score."""
    pipeline = SketchToCodePipeline(strategy=RoutingStrategy.MOCK)
    wireframe_input = {
        "original_shape": (800, 800),
        "total_components": 2,
        "normalized_boxes": [
            {"id": 1, "norm_box": [0.0, 0.0, 1.0, 0.1], "area_ratio": 0.1},
            {"id": 2, "norm_box": [0.1, 0.2, 0.9, 0.8], "area_ratio": 0.5}
        ]
    }
    result = pipeline.process(wireframe_input, force_mock=True)

    assert result.success is True
    assert result.accessibility_compliant is True
    assert result.accessibility_score >= 90.0
    assert result.accessibility_report is not None
    assert "violations" in result.accessibility_report
    assert "<!DOCTYPE html>" in result.full_html
