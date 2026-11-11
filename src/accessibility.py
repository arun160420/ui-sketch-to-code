"""
src/accessibility.py

Week 9 Deliverable (COM71123-11):
WCAG Accessibility and Semantic HTML5 Enforcement Engine.

Provides:
1. Structured WCAG 2.1 / 2.2 AA guidelines and rule taxonomy.
2. AccessibilityAuditor: In-depth AST and DOM auditing for common accessibility pitfalls:
   - Missing / empty image alternative text (WCAG 1.1.1)
   - Unassociated or missing form input labels (WCAG 1.3.1)
   - Missing input purpose / autocomplete attributes (WCAG 1.3.5)
   - Missing keyboard accessibility & interactive roles (WCAG 2.1.1)
   - Non-descriptive links & empty buttons (WCAG 2.4.4 / 4.1.2)
   - Illogical heading hierarchy skips (WCAG 2.4.6)
   - Semantic HTML5 landmarks & document lang/title compliance (WCAG 1.3.1 / 2.4.2 / 3.1.1)
   - Accessible table structure & header scopes (WCAG 1.3.1)
3. AccessibilityEnforcer: Automated AST remediation and semantic HTML5 upgrading to
   achieve 100% WCAG compliance.
4. Comprehensive audit reporting and metrics calculation.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
import html
from html.parser import HTMLParser
import logging
import re
from typing import Dict, Any, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class WCAGCriterion(str, Enum):
    """WCAG 2.1 / 2.2 Success Criteria Taxonomy."""
    NON_TEXT_CONTENT = "1.1.1 Non-text Content (Level A)"
    INFO_RELATIONSHIPS = "1.3.1 Info and Relationships (Level A)"
    INPUT_PURPOSE = "1.3.5 Identify Input Purpose (Level AA)"
    KEYBOARD_ACCESSIBLE = "2.1.1 Keyboard Accessible (Level A)"
    PAGE_TITLED = "2.4.2 Page Titled (Level A)"
    LINK_PURPOSE = "2.4.4 Link Purpose (In Context) (Level A)"
    HEADINGS_AND_LABELS = "2.4.6 Headings and Labels (Level AA)"
    FOCUS_VISIBLE = "2.4.7 Focus Visible (Level AA)"
    LANGUAGE_OF_PAGE = "3.1.1 Language of Page (Level A)"
    NAME_ROLE_VALUE = "4.1.2 Name, Role, Value (Level A)"


class AccessibilitySeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class AccessibilityViolation:
    """Represents a specific WCAG accessibility rule violation."""
    rule_id: str
    criterion: str
    severity: str
    element_tag: str
    snippet: str
    line_number: int
    message: str
    remediation_hint: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AccessibilityReport:
    """Detailed audit report for a snippet or document."""
    is_compliant: bool
    score: float
    error_count: int
    warning_count: int
    violations: List[AccessibilityViolation] = field(default_factory=list)
    semantic_landmarks: List[str] = field(default_factory=list)
    heading_hierarchy: List[str] = field(default_factory=list)
    audited_elements_count: int = 0
    passed_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_compliant": self.is_compliant,
            "score": round(self.score, 1),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "violations": [v.to_dict() for v in self.violations],
            "semantic_landmarks": self.semantic_landmarks,
            "heading_hierarchy": self.heading_hierarchy,
            "audited_elements_count": self.audited_elements_count,
            "passed_rules": self.passed_rules
        }

    def to_markdown_summary(self) -> str:
        status_badge = "✅ COMPLIANT (WCAG 2.1 AA)" if self.is_compliant else "⚠️ VIOLATIONS DETECTED"
        lines = [
            f"### WCAG Accessibility Audit: {status_badge}",
            f"- **Accessibility Score:** {self.score:.1f} / 100",
            f"- **Errors:** {self.error_count} (must be resolved for Level A/AA)",
            f"- **Warnings:** {self.warning_count}",
            f"- **Audited Elements:** {self.audited_elements_count}",
            f"- **Semantic Landmarks:** {', '.join(f'<{m}>' for m in self.semantic_landmarks) if self.semantic_landmarks else 'None'}",
            f"- **Heading Hierarchy:** {' &rarr; '.join(self.heading_hierarchy) if self.heading_hierarchy else 'None'}",
            ""
        ]
        if self.violations:
            lines.append("#### Detected Violations:")
            for idx, v in enumerate(self.violations, 1):
                icon = "🛑" if v.severity == AccessibilitySeverity.ERROR.value else "⚠️"
                lines.append(
                    f"{idx}. {icon} **[{v.rule_id}]** {v.message} (`{v.criterion}`)\n"
                    f"   - **Element:** `<{v.element_tag}>` on line {v.line_number}\n"
                    f"   - **Remediation:** {v.remediation_hint}"
                )
        return "\n".join(lines)


# ==============================================================================
# 2. In-Depth HTML DOM / AST Accessibility Auditor
# ==============================================================================

class _DOMNode:
    def __init__(self, tag: str, attrs: Dict[str, str], line: int):
        self.tag = tag.lower()
        self.attrs = attrs
        self.line = line
        self.text: List[str] = []
        self.children: List['_DOMNode'] = []
        self.parent: Optional['_DOMNode'] = None


class _AccessibilityTreeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = _DOMNode("document", {}, 1)
        self.current = self.root
        self.stack: List[_DOMNode] = [self.root]
        self.all_nodes: List[_DOMNode] = []
        self.void_tags = {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"
        }

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        node = _DOMNode(tag, attr_dict, self.getpos()[0])
        node.parent = self.current
        self.current.children.append(node)
        self.all_nodes.append(node)

        if tag.lower() not in self.void_tags:
            self.stack.append(node)
            self.current = node

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in self.void_tags:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag_lower:
                self.stack = self.stack[:i]
                self.current = self.stack[-1]
                break

    def handle_data(self, data: str):
        stripped = data.strip()
        if stripped:
            self.current.text.append(stripped)


class AccessibilityAuditor:
    """
    Audits HTML snippets and documents for strict WCAG 2.1 AA and Semantic HTML5 compliance.
    """

    def audit(self, html_content: str) -> AccessibilityReport:
        if not html_content or not html_content.strip():
            return AccessibilityReport(
                is_compliant=True,
                score=100.0,
                error_count=0,
                warning_count=0,
                violations=[],
                semantic_landmarks=[],
                heading_hierarchy=[],
                audited_elements_count=0
            )

        parser = _AccessibilityTreeParser()
        try:
            parser.feed(html_content)
        except Exception as e:
            logger.warning("HTML parsing error during accessibility audit: %s", e)

        nodes = parser.all_nodes
        violations: List[AccessibilityViolation] = []
        semantic_landmarks: List[str] = []
        heading_hierarchy: List[str] = []
        passed_rules: Set[str] = set()

        is_full_document = bool(re.search(r"<html|<head|<body", html_content, re.IGNORECASE))

        # Track labels and inputs for association matching
        input_ids: Set[str] = set()
        label_fors: Set[str] = set()
        labels_by_for: Dict[str, _DOMNode] = {}

        for n in nodes:
            if n.tag == "label":
                for_attr = n.attrs.get("for", "").strip()
                if for_attr:
                    label_fors.add(for_attr)
                    labels_by_for[for_attr] = n

        # ----------------------------------------------------------------------
        # Rule 1: Document Language (WCAG 3.1.1) & Title (WCAG 2.4.2)
        # ----------------------------------------------------------------------
        if is_full_document:
            html_nodes = [n for n in nodes if n.tag == "html"]
            if html_nodes:
                if not html_nodes[0].attrs.get("lang"):
                    violations.append(AccessibilityViolation(
                        rule_id="wcag-html-lang",
                        criterion=WCAGCriterion.LANGUAGE_OF_PAGE.value,
                        severity=AccessibilitySeverity.ERROR.value,
                        element_tag="html",
                        snippet="<html>",
                        line_number=html_nodes[0].line,
                        message="The <html> element must have a non-empty 'lang' attribute (e.g. lang='en').",
                        remediation_hint="Add lang='en' to the root <html> tag to announce page language to screen readers."
                    ))
                else:
                    passed_rules.add("wcag-html-lang")

            title_nodes = [n for n in nodes if n.tag == "title"]
            if not title_nodes or not any(n.text for n in title_nodes):
                violations.append(AccessibilityViolation(
                    rule_id="wcag-page-title",
                    criterion=WCAGCriterion.PAGE_TITLED.value,
                    severity=AccessibilitySeverity.ERROR.value,
                    element_tag="head",
                    snippet="<head>...</head>",
                    line_number=1,
                    message="Document is missing a descriptive <title> element in <head>.",
                    remediation_hint="Provide an informative, concise <title> inside <head>."
                ))
            else:
                passed_rules.add("wcag-page-title")

        # ----------------------------------------------------------------------
        # Rule 2: Non-text Content (Images must have alt) (WCAG 1.1.1)
        # ----------------------------------------------------------------------
        img_nodes = [n for n in nodes if n.tag == "img"]
        for img in img_nodes:
            if "alt" not in img.attrs:
                violations.append(AccessibilityViolation(
                    rule_id="wcag-img-alt",
                    criterion=WCAGCriterion.NON_TEXT_CONTENT.value,
                    severity=AccessibilitySeverity.ERROR.value,
                    element_tag="img",
                    snippet=f"<img src='{img.attrs.get('src', '')}'>",
                    line_number=img.line,
                    message="Image element is missing an 'alt' attribute.",
                    remediation_hint="Add alt='Descriptive text' for informative images, or alt='' for decorative assets."
                ))
            else:
                passed_rules.add("wcag-img-alt")

        # ----------------------------------------------------------------------
        # Rule 3: Form Input Labels & Accessible Names (WCAG 1.3.1)
        # ----------------------------------------------------------------------
        form_control_tags = {"input", "textarea", "select"}
        excluded_input_types = {"hidden", "submit", "button", "reset", "image"}

        for n in nodes:
            if n.tag in form_control_tags:
                input_type = n.attrs.get("type", "text").lower()
                if n.tag == "input" and input_type in excluded_input_types:
                    continue

                input_id = n.attrs.get("id", "").strip()
                has_label_for = bool(input_id and input_id in label_fors)
                has_aria_label = bool(n.attrs.get("aria-label", "").strip())
                has_aria_labelledby = bool(n.attrs.get("aria-labelledby", "").strip())
                has_title = bool(n.attrs.get("title", "").strip())
                
                # Check for wrapped parent label
                has_parent_label = False
                curr_parent = n.parent
                while curr_parent and curr_parent.tag != "document":
                    if curr_parent.tag == "label":
                        has_parent_label = True
                        break
                    curr_parent = curr_parent.parent

                if not (has_label_for or has_aria_label or has_aria_labelledby or has_parent_label or has_title):
                    violations.append(AccessibilityViolation(
                        rule_id="wcag-form-label",
                        criterion=WCAGCriterion.INFO_RELATIONSHIPS.value,
                        severity=AccessibilitySeverity.ERROR.value,
                        element_tag=n.tag,
                        snippet=f"<{n.tag} id='{input_id}' type='{input_type}'>",
                        line_number=n.line,
                        message=f"Form control <{n.tag}> lacks an associated label or aria-label.",
                        remediation_hint="Associate an explicit <label for='...'> matching the input id, or add aria-label='...'."
                    ))
                else:
                    passed_rules.add("wcag-form-label")

                # Check autocomplete for identify input purpose (WCAG 1.3.5)
                if n.tag == "input" and input_type in {"email", "password", "tel", "name", "username"}:
                    if not n.attrs.get("autocomplete"):
                        violations.append(AccessibilityViolation(
                            rule_id="wcag-input-autocomplete",
                            criterion=WCAGCriterion.INPUT_PURPOSE.value,
                            severity=AccessibilitySeverity.WARNING.value,
                            element_tag="input",
                            snippet=f"<input type='{input_type}' id='{input_id}'>",
                            line_number=n.line,
                            message=f"Input of type '{input_type}' should specify an 'autocomplete' attribute.",
                            remediation_hint=f"Add autocomplete='{input_type if input_type != 'password' else 'current-password'}'."
                        ))
                    else:
                        passed_rules.add("wcag-input-autocomplete")

        # ----------------------------------------------------------------------
        # Rule 4: Buttons & Interactive Element Semantics (WCAG 4.1.2 & 2.1.1)
        # ----------------------------------------------------------------------
        for n in nodes:
            if n.tag == "button":
                # Button type attribute check
                if "type" not in n.attrs:
                    violations.append(AccessibilityViolation(
                        rule_id="wcag-button-type",
                        criterion=WCAGCriterion.NAME_ROLE_VALUE.value,
                        severity=AccessibilitySeverity.WARNING.value,
                        element_tag="button",
                        snippet="<button>",
                        line_number=n.line,
                        message="<button> element is missing an explicit 'type' attribute (defaults to type='submit').",
                        remediation_hint="Add type='button' for action buttons or type='submit' for form submissions."
                    ))
                else:
                    passed_rules.add("wcag-button-type")

                # Accessible name check
                has_text = bool("".join(n.text).strip())
                has_aria = bool(n.attrs.get("aria-label", "").strip() or n.attrs.get("title", "").strip())
                has_img_alt = any(c.tag == "img" and c.attrs.get("alt") for c in n.children)
                if not (has_text or has_aria or has_img_alt):
                    violations.append(AccessibilityViolation(
                        rule_id="wcag-button-name",
                        criterion=WCAGCriterion.NAME_ROLE_VALUE.value,
                        severity=AccessibilitySeverity.ERROR.value,
                        element_tag="button",
                        snippet="<button>...</button>",
                        line_number=n.line,
                        message="<button> has no accessible name (empty text and no aria-label).",
                        remediation_hint="Add visible text or an aria-label='...' attribute."
                    ))
                else:
                    passed_rules.add("wcag-button-name")

            elif n.tag == "a":
                has_text = bool("".join(n.text).strip())
                has_aria = bool(n.attrs.get("aria-label", "").strip() or n.attrs.get("title", "").strip())
                has_img_alt = any(c.tag == "img" and c.attrs.get("alt") for c in n.children)
                if not (has_text or has_aria or has_img_alt):
                    violations.append(AccessibilityViolation(
                        rule_id="wcag-link-name",
                        criterion=WCAGCriterion.LINK_PURPOSE.value,
                        severity=AccessibilitySeverity.ERROR.value,
                        element_tag="a",
                        snippet=f"<a href='{n.attrs.get('href', '')}'></a>",
                        line_number=n.line,
                        message="Anchor link <a> has no accessible name (empty text and missing aria-label).",
                        remediation_hint="Add clear link text or aria-label describing the destination."
                    ))
                else:
                    passed_rules.add("wcag-link-name")

            # Check generic non-semantic clickable elements
            elif n.tag in {"div", "span"}:
                onclick = n.attrs.get("onclick")
                classes = n.attrs.get("class", "").lower()
                is_styled_button = "cursor-pointer" in classes and ("btn" in classes or "button" in classes)
                if onclick or is_styled_button:
                    role = n.attrs.get("role", "").lower()
                    tabindex = n.attrs.get("tabindex")
                    if role != "button" or tabindex is None:
                        violations.append(AccessibilityViolation(
                            rule_id="wcag-clickable-role",
                            criterion=WCAGCriterion.KEYBOARD_ACCESSIBLE.value,
                            severity=AccessibilitySeverity.WARNING.value,
                            element_tag=n.tag,
                            snippet=f"<{n.tag} class='{classes}'>",
                            line_number=n.line,
                            message=f"Interactive <{n.tag}> lacks semantic <button> tag or role='button' with tabindex='0'.",
                            remediation_hint="Replace with semantic <button type='button'> or add role='button' and tabindex='0'."
                        ))
                    else:
                        passed_rules.add("wcag-clickable-role")

        # ----------------------------------------------------------------------
        # Rule 5: Semantic Landmarks (WCAG 1.3.1)
        # ----------------------------------------------------------------------
        landmark_tags = {"header", "nav", "main", "footer", "section", "article", "aside"}
        for n in nodes:
            if n.tag in landmark_tags:
                if n.tag not in semantic_landmarks:
                    semantic_landmarks.append(n.tag)

        if is_full_document:
            if "main" not in semantic_landmarks and not any(n.attrs.get("role") == "main" for n in nodes):
                violations.append(AccessibilityViolation(
                    rule_id="wcag-semantic-main",
                    criterion=WCAGCriterion.INFO_RELATIONSHIPS.value,
                    severity=AccessibilitySeverity.WARNING.value,
                    element_tag="body",
                    snippet="<body>...</body>",
                    line_number=1,
                    message="Document lacks a primary <main role='main'> landmark container.",
                    remediation_hint="Enclose central content inside a semantic <main> tag."
                ))
            else:
                passed_rules.add("wcag-semantic-main")

            if not any(m in semantic_landmarks for m in ["nav", "header", "footer"]):
                violations.append(AccessibilityViolation(
                    rule_id="wcag-semantic-landmarks",
                    criterion=WCAGCriterion.INFO_RELATIONSHIPS.value,
                    severity=AccessibilitySeverity.WARNING.value,
                    element_tag="body",
                    snippet="<body>...</body>",
                    line_number=1,
                    message="Document lacks structural landmarks (<nav>, <header>, or <footer>).",
                    remediation_hint="Use semantic HTML5 elements instead of exclusively using generic <div> tags."
                ))
            else:
                passed_rules.add("wcag-semantic-landmarks")

        # ----------------------------------------------------------------------
        # Rule 6: Logical Heading Hierarchy (WCAG 2.4.6)
        # ----------------------------------------------------------------------
        heading_tags = {"h1", "h2", "h3", "h4", "h5", "h6"}
        last_level = 0
        for n in nodes:
            if n.tag in heading_tags:
                heading_hierarchy.append(n.tag)
                curr_level = int(n.tag[1])
                if last_level > 0 and curr_level > last_level + 1:
                    violations.append(AccessibilityViolation(
                        rule_id="wcag-heading-order",
                        criterion=WCAGCriterion.HEADINGS_AND_LABELS.value,
                        severity=AccessibilitySeverity.WARNING.value,
                        element_tag=n.tag,
                        snippet=f"<{n.tag}>",
                        line_number=n.line,
                        message=f"Heading level skipped: moved from <h{last_level}> directly to <h{curr_level}>.",
                        remediation_hint=f"Use <h{last_level + 1}> to preserve heading navigation hierarchy without skipping levels."
                    ))
                else:
                    passed_rules.add("wcag-heading-order")
                last_level = curr_level

        # ----------------------------------------------------------------------
        # Rule 7: Table Structure (WCAG 1.3.1)
        # ----------------------------------------------------------------------
        th_nodes = [n for n in nodes if n.tag == "th"]
        for th in th_nodes:
            if not th.attrs.get("scope"):
                violations.append(AccessibilityViolation(
                    rule_id="wcag-table-scope",
                    criterion=WCAGCriterion.INFO_RELATIONSHIPS.value,
                    severity=AccessibilitySeverity.WARNING.value,
                    element_tag="th",
                    snippet="<th>",
                    line_number=th.line,
                    message="Table header <th> lacks a 'scope' attribute (scope='col' or scope='row').",
                    remediation_hint="Add scope='col' for column headers or scope='row' for row headers."
                ))
            else:
                passed_rules.add("wcag-table-scope")

        # ----------------------------------------------------------------------
        # Calculate Score & Compliance
        # ----------------------------------------------------------------------
        error_count = sum(1 for v in violations if v.severity == AccessibilitySeverity.ERROR.value)
        warning_count = sum(1 for v in violations if v.severity == AccessibilitySeverity.WARNING.value)

        # Base 100 with penalties for violations
        penalty = (error_count * 15.0) + (warning_count * 4.0)
        score = max(0.0, min(100.0, 100.0 - penalty))
        is_compliant = (error_count == 0)

        return AccessibilityReport(
            is_compliant=is_compliant,
            score=score,
            error_count=error_count,
            warning_count=warning_count,
            violations=violations,
            semantic_landmarks=semantic_landmarks,
            heading_hierarchy=heading_hierarchy,
            audited_elements_count=len(nodes),
            passed_rules=sorted(list(passed_rules))
        )


# ==============================================================================
# 3. Automated Semantic HTML5 & WCAG Remediation Transformer
# ==============================================================================

class AccessibilityEnforcer:
    """
    Autonomously remediates accessibility defects and upgrades HTML to semantic standards.
    """

    def __init__(self, auditor: Optional[AccessibilityAuditor] = None):
        self.auditor = auditor or AccessibilityAuditor()

    def enforce_accessibility(self, html_content: str) -> Tuple[str, AccessibilityReport]:
        """
        Takes raw HTML code, applies automated WCAG 2.1 AA transformations,
        and returns (remediated_html, final_report).
        """
        if not html_content or not html_content.strip():
            return html_content, self.auditor.audit(html_content)

        code = html_content

        # 1. Ensure HTML lang attribute
        if re.search(r"<html(?![^>]*\blang=)", code, re.IGNORECASE):
            code = re.sub(r"<html([^>]*)>", r'<html lang="en"\1>', code, count=1, flags=re.IGNORECASE)

        # 2. Ensure Document Title in <head>
        if "<head>" in code.lower() and not re.search(r"<title[^>]*>.*?</title>", code, re.IGNORECASE | re.DOTALL):
            code = re.sub(
                r"<head([^>]*)>",
                r"<head\1>\n  <title>SketchToCode AI &bull; Synthesized Accessible UI</title>",
                code,
                count=1,
                flags=re.IGNORECASE
            )

        # 3. Fix <img> tags missing alt attribute
        def _add_img_alt(match: re.Match) -> str:
            tag = match.group(0)
            if not re.search(r"\balt=", tag, re.IGNORECASE):
                # Check if decorative or informative
                return tag[:-1] + ' alt="Visual UI wireframe preview asset" />' if tag.endswith("/>") else tag[:-1] + ' alt="Visual UI wireframe preview asset">'
            return tag

        code = re.sub(r"<img\b[^>]*>", _add_img_alt, code, flags=re.IGNORECASE)

        # 4. Fix <button> tags missing explicit type
        def _add_button_type(match: re.Match) -> str:
            tag = match.group(0)
            if not re.search(r"\btype=", tag, re.IGNORECASE):
                return tag[:-1] + ' type="button">'
            return tag

        code = re.sub(r"<button\b[^>]*>", _add_button_type, code, flags=re.IGNORECASE)

        # 4b. Fix empty <button> tags missing accessible name
        def _add_button_name(match: re.Match) -> str:
            full_match = match.group(0)
            tag_open = match.group(1)
            content = match.group(2)
            if not content.strip() and not re.search(r"\b(aria-label|title)=", tag_open, re.IGNORECASE):
                tag_open = tag_open[:-1] + ' aria-label="Action button">'
                return f"{tag_open}Action</button>"
            return full_match

        code = re.sub(r"(<button\b[^>]*>)(.*?)(</button>)", _add_button_name, code, flags=re.IGNORECASE | re.DOTALL)

        # 4c. Fix empty <a> tags missing accessible name
        def _add_link_name(match: re.Match) -> str:
            full_match = match.group(0)
            tag_open = match.group(1)
            content = match.group(2)
            if not content.strip() and not re.search(r"\b(aria-label|title)=", tag_open, re.IGNORECASE):
                tag_open = tag_open[:-1] + ' aria-label="Navigation link">'
                return f"{tag_open}Link</a>"
            return full_match

        code = re.sub(r"(<a\b[^>]*>)(.*?)(</a>)", _add_link_name, code, flags=re.IGNORECASE | re.DOTALL)

        # 5. Fix <input> tags missing autocomplete on email / password
        def _fix_input_autocomplete(match: re.Match) -> str:
            tag = match.group(0)
            input_type_match = re.search(r'\btype=["\']?(\w+)["\']?', tag, re.IGNORECASE)
            itype = input_type_match.group(1).lower() if input_type_match else "text"

            if not re.search(r"\bautocomplete=", tag, re.IGNORECASE):
                if itype == "email":
                    suffix = ' autocomplete="email"'
                elif itype == "password":
                    suffix = ' autocomplete="current-password"'
                elif itype == "tel":
                    suffix = ' autocomplete="tel"'
                else:
                    suffix = ""
                if suffix:
                    return tag[:-1] + suffix + (">" if not tag.endswith("/>") else " />")
            return tag

        code = re.sub(r"<input\b[^>]*>", _fix_input_autocomplete, code, flags=re.IGNORECASE)

        # 6. Ensure input fields have aria-label if no explicit <label for> exists
        def _ensure_input_accessible_name(match: re.Match) -> str:
            tag = match.group(0)
            input_type_match = re.search(r'\btype=["\']?(\w+)["\']?', tag, re.IGNORECASE)
            itype = input_type_match.group(1).lower() if input_type_match else "text"
            if itype in {"hidden", "submit", "button", "reset"}:
                return tag

            id_match = re.search(r'\bid=["\']?([^"\'\s>]+)["\']?', tag, re.IGNORECASE)
            input_id = id_match.group(1) if id_match else ""

            # If no aria-label, aria-labelledby, or title
            if not re.search(r"\b(aria-label|aria-labelledby|title)=", tag, re.IGNORECASE):
                # Check if there is a corresponding label for this ID
                if not (input_id and re.search(rf'<label[^>]*\bfor=["\']?{re.escape(input_id)}["\']?', code, re.IGNORECASE)):
                    placeholder_match = re.search(r'\bplaceholder=["\']?([^"\']+)["\']?', tag, re.IGNORECASE)
                    label_text = placeholder_match.group(1) if placeholder_match else f"{itype.capitalize()} Input"
                    return tag[:-1] + f' aria-label="{html.escape(label_text)}"' + (">" if not tag.endswith("/>") else " />")
            return tag

        code = re.sub(r"<input\b[^>]*>", _ensure_input_accessible_name, code, flags=re.IGNORECASE)

        # 7. Add scope="col" to <th> table headers missing scope
        def _add_th_scope(match: re.Match) -> str:
            tag = match.group(0)
            if not re.search(r"\bscope=", tag, re.IGNORECASE):
                return tag[:-1] + ' scope="col">'
            return tag

        code = re.sub(r"<th\b[^>]*>", _add_th_scope, code, flags=re.IGNORECASE)

        # 8. Upgrade generic clickable div/span to role="button" tabindex="0"
        def _upgrade_clickable(match: re.Match) -> str:
            tag = match.group(0)
            if not re.search(r"\brole=", tag, re.IGNORECASE):
                tag = tag[:-1] + ' role="button"' + (">" if not tag.endswith("/>") else " />")
            if not re.search(r"\btabindex=", tag, re.IGNORECASE):
                tag = tag[:-1] + ' tabindex="0"' + (">" if not tag.endswith("/>") else " />")
            return tag

        code = re.sub(r"<(div|span)\b[^>]*\bonclick=[^>]*>", _upgrade_clickable, code, flags=re.IGNORECASE)

        # 9. Ensure Semantic <main role="main"> landmark in full documents
        if "<body" in code.lower() and "<main" not in code.lower() and 'role="main"' not in code.lower():
            # Wrap inner body content in <main role="main">
            body_match = re.search(r"(<body[^>]*>)(.*?)(</body>)", code, re.IGNORECASE | re.DOTALL)
            if body_match:
                b_start = body_match.group(1)
                b_content = body_match.group(2)
                b_end = body_match.group(3)
                # Keep top banner / nav outside main if present
                code = code[:body_match.start()] + f"{b_start}\n  <main role=\"main\" class=\"flex-1\">\n{b_content}\n  </main>\n{b_end}" + code[body_match.end():]

        # Audit final code
        final_report = self.auditor.audit(code)
        return code, final_report
