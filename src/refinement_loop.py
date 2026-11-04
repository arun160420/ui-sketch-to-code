"""
src/refinement_loop.py

Week 7 Deliverable (COM71123-9):
Agentic Refinement Loop - Error Routing

Implements the first phase of the Agentic Refinement Loop:
1. AST Error Extraction: Identifies, categorizes, and pinpoints structural errors from html-validate.
2. Error Prompt Formatting: Constructs structured, actionable diagnostic prompts for the vision model.
3. Feedback Loop Mechanism: Routes validation errors back to the generation API with iteration tracking,
   telemetry, and convergence verification.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.ast_validator import ASTValidationEngine, ValidationError, ValidationReport
from src.schema import UI_COMPONENT_JSON_SCHEMA, validate_ui_payload

logger = logging.getLogger("RefinementLoop")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ============================================================================
# 1. Error Categories & Extraction Models
# ============================================================================

class ErrorCategory(str, Enum):
    STRUCTURAL_CLOSURE = "structural_closure"     # Unclosed tags, mismatched tags (close-order)
    DUPLICATE_IDENTIFIER = "duplicate_identifier" # Duplicate id attributes (no-dup-id)
    MISSING_ATTRIBUTE = "missing_attribute"       # Required attrs missing (element-required-attributes, wcag/h37)
    UNKNOWN_ELEMENT = "unknown_element"           # Non-standard HTML tags (no-unknown-elements)
    VOID_ELEMENT_VIOLATION = "void_content"       # Child elements inside void tags (void-content)
    SYNTAX_PARSER_ERROR = "parser_error"         # Malformed tokens, invalid quotes
    GENERAL_ERROR = "general_error"               # Other structural errors


@dataclass
class ExtractedError:
    """Detailed metadata for an individual extracted AST error."""
    rule_id: str
    category: ErrorCategory
    severity: str
    message: str
    line: int
    column: int
    selector: Optional[str] = None
    offending_line: Optional[str] = None
    context_snippet: Optional[str] = None
    remediation_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d


class ASTErrorExtractor:
    """
    Analyzes html-validate ValidationReport outputs, extracts relevant
    structural errors, pinpoints code locations, and generates actionable hints.
    """

    RULE_CATEGORY_MAP = {
        "close-order": ErrorCategory.STRUCTURAL_CLOSURE,
        "no-implicit-close": ErrorCategory.STRUCTURAL_CLOSURE,
        "no-dup-id": ErrorCategory.DUPLICATE_IDENTIFIER,
        "element-required-attributes": ErrorCategory.MISSING_ATTRIBUTE,
        "wcag/h37": ErrorCategory.MISSING_ATTRIBUTE,
        "no-unknown-elements": ErrorCategory.UNKNOWN_ELEMENT,
        "void-content": ErrorCategory.VOID_ELEMENT_VIOLATION,
        "parser-error": ErrorCategory.SYNTAX_PARSER_ERROR,
    }

    REMEDIATION_HINTS = {
        ErrorCategory.STRUCTURAL_CLOSURE: (
            "Ensure every opening tag has a corresponding closing tag in the exact nested order. "
            "For example: '<div><span>text</span></div>' instead of '<div><span>text</div>'."
        ),
        ErrorCategory.DUPLICATE_IDENTIFIER: (
            "Each 'id' attribute in the document/component must be globally unique. "
            "Rename duplicate IDs (e.g., append numeric suffixes like '-1', '-2')."
        ),
        ErrorCategory.MISSING_ATTRIBUTE: (
            "Provide all required HTML attributes. For <img> tags, always include valid 'src' and 'alt' attributes. "
            "For <input> elements, specify 'type' and 'name' or 'id'."
        ),
        ErrorCategory.UNKNOWN_ELEMENT: (
            "Use only valid HTML5 elements (e.g., div, section, nav, button, span). "
            "Replace custom or misspelled tags with standard semantic HTML."
        ),
        ErrorCategory.VOID_ELEMENT_VIOLATION: (
            "Void elements (such as <img>, <input>, <hr>, <br>) cannot have closing tags or child content. "
            "Remove any closing tags or child nodes from void elements."
        ),
        ErrorCategory.SYNTAX_PARSER_ERROR: (
            "Fix malformed HTML syntax, unescaped characters, or mismatched quotes in attributes."
        ),
        ErrorCategory.GENERAL_ERROR: (
            "Review and fix HTML compliance according to standard HTML5 specifications."
        )
    }

    @classmethod
    def categorize_rule(cls, rule_id: str) -> ErrorCategory:
        """Maps an html-validate rule ID to an ErrorCategory enum."""
        return cls.RULE_CATEGORY_MAP.get(rule_id, ErrorCategory.GENERAL_ERROR)

    @classmethod
    def extract_context_snippet(
        cls,
        source_code: str,
        line_num: int,
        col_num: int,
        context_radius: int = 1
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts the offending line and a multi-line context excerpt with line numbers and a caret pointer.
        Returns: (offending_line, context_snippet)
        """
        if not source_code:
            return None, None

        lines = source_code.splitlines()
        total_lines = len(lines)
        if line_num < 1 or line_num > total_lines:
            return None, None

        target_idx = line_num - 1
        offending_line = lines[target_idx]

        start_idx = max(0, target_idx - context_radius)
        end_idx = min(total_lines, target_idx + context_radius + 1)

        snippet_lines = []
        for i in range(start_idx, end_idx):
            line_str = lines[i]
            curr_line_no = i + 1
            prefix = " >" if curr_line_no == line_num else "  "
            snippet_lines.append(f"{prefix} {curr_line_no:4d} | {line_str}")

            # Insert caret pointer directly below the offending line
            if curr_line_no == line_num and col_num > 0:
                indent = " " * (7 + max(0, col_num - 1))
                snippet_lines.append(f"{indent}^--- [ERROR HERE]")

        return offending_line, "\n".join(snippet_lines)

    @classmethod
    def extract_errors(
        cls,
        report: Union[ValidationReport, Dict[str, Any]],
        source_code: Optional[str] = None
    ) -> List[ExtractedError]:
        """
        Extracts and enriches all error items from a ValidationReport or raw JSON dictionary.
        Filters out warnings (unless they represent blocking syntax issues) and sorts by location.
        """
        raw_errors: List[Union[ValidationError, Dict[str, Any]]] = []
        source = source_code

        if isinstance(report, ValidationReport):
            raw_errors = list(report.errors)
            if not source and report.source_snippet:
                source = report.source_snippet
        elif isinstance(report, dict):
            raw_errors = report.get("errors", [])
            if not source and "source_snippet" in report:
                source = report["source_snippet"]

        extracted: List[ExtractedError] = []
        for err in raw_errors:
            if isinstance(err, ValidationError):
                rule_id = err.rule_id
                severity = err.severity
                message = err.message
                line = err.line
                column = err.column
                selector = err.selector
            else:
                rule_id = err.get("ruleId", err.get("rule_id", "unknown"))
                severity = err.get("severity", "error")
                message = err.get("message", "")
                line = int(err.get("line", 0))
                column = int(err.get("column", 0))
                selector = err.get("selector")

            category = cls.categorize_rule(rule_id)
            hint = cls.REMEDIATION_HINTS.get(category, cls.REMEDIATION_HINTS[ErrorCategory.GENERAL_ERROR])

            offending_line, context_snippet = None, None
            if source and line > 0:
                offending_line, context_snippet = cls.extract_context_snippet(source, line, column)

            extracted.append(ExtractedError(
                rule_id=rule_id,
                category=category,
                severity=severity,
                message=message,
                line=line,
                column=column,
                selector=selector,
                offending_line=offending_line,
                context_snippet=context_snippet,
                remediation_hint=hint
            ))

        # Sort errors chronologically by line and column
        extracted.sort(key=lambda x: (x.line, x.column))
        return extracted


# ============================================================================
# 2. Error Prompt Formatting for Vision Models
# ============================================================================

class ErrorPromptFormatter:
    """
    Formats extracted AST errors into clear, actionable prompts for vision/multimodal LLMs.
    Supports single-turn refinement prompts as well as multi-turn conversational payloads.
    """

    @classmethod
    def format_diagnostic_prompt(
        cls,
        extracted_errors: List[ExtractedError],
        original_code: str,
        component_type: Optional[str] = None,
        include_schema_rules: bool = True
    ) -> str:
        """
        Creates a structured prompt detailing AST errors and explicit instructions
        for repairing the HTML markup.
        """
        target_name = f"Component '{component_type}'" if component_type else "HTML Document"

        lines = [
            f"### Automated AST Validation Error Report for {target_name}",
            f"The previously generated HTML failed structural validation with {len(extracted_errors)} error(s).",
            "Please carefully review the diagnostics below and provide the corrected code.\n",
            "#### Detected Violations:"
        ]

        for idx, err in enumerate(extracted_errors, start=1):
            lines.append(f"{idx}. **[{err.rule_id}]** (Line {err.line}, Column {err.column}):")
            lines.append(f"   - **Issue**: {err.message}")
            if err.selector:
                lines.append(f"   - **Selector**: `{err.selector}`")
            if err.remediation_hint:
                lines.append(f"   - **Fix Instruction**: {err.remediation_hint}")
            if err.context_snippet:
                lines.append("   - **Code Context**:")
                lines.append(f"     ```html\n{err.context_snippet}\n     ```")
            lines.append("")

        lines.append("#### Erroneous HTML to Repair:")
        lines.append(f"```html\n{original_code.strip()}\n```\n")

        lines.append("#### Repair Requirements:")
        lines.append("1. **Fix All Violations**: Strictly resolve every unclosed element, duplicate ID, and missing attribute listed above.")
        lines.append("2. **Preserve Layout & Styling**: Retain all Tailwind CSS utility classes and visual layout structure.")
        lines.append("3. **Semantic Hierarchy**: Ensure clean, valid HTML5 nesting without introducing new syntax issues.")
        if include_schema_rules:
            lines.append("4. **Output Format**: Return valid JSON adhering to the enforced schema with the repaired HTML in the 'html' field.")

        return "\n".join(lines)

    @classmethod
    def build_multiturn_refinement_messages(
        cls,
        extracted_errors: List[ExtractedError],
        erroneous_payload: Dict[str, Any],
        system_instruction: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Constructs a 3-turn conversational message history for chat completion APIs:
        [System Prompt] -> [Assistant Erroneous Output] -> [User Error Feedback & Repair Request]
        """
        sys_msg = system_instruction or (
            "You are an expert Frontend Web Developer and UI Engineer. "
            "You are operating in an iterative Agentic Refinement Loop. "
            "When given AST validation error logs, you must diagnose and correct "
            "all structural HTML violations while preserving design, layout, and schema conformance."
        )

        full_html = erroneous_payload.get("full_html", "")
        if not full_html and "components" in erroneous_payload:
            full_html = "\n".join([c.get("html", "") for c in erroneous_payload["components"]])

        diagnostic_user_text = cls.format_diagnostic_prompt(
            extracted_errors=extracted_errors,
            original_code=full_html,
            component_type=erroneous_payload.get("layout_type", "UI"),
            include_schema_rules=True
        )

        return [
            {"role": "system", "content": sys_msg},
            {"role": "assistant", "content": json.dumps(erroneous_payload, indent=2)},
            {"role": "user", "content": diagnostic_user_text}
        ]


# ============================================================================
# 3. Agentic Feedback Loop Mechanism
# ============================================================================

class RefinementStatus(str, Enum):
    SUCCESS = "SUCCESS"                               # Validated cleanly with 0 errors
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"     # Exceeded maximum allowed iterations
    UNRECOVERABLE_ERROR = "UNRECOVERABLE_ERROR"       # Unhandled exception during generation
    VALIDATION_BYPASS = "VALIDATION_BYPASS"           # No errors detected initially


@dataclass
class RefinementIterationRecord:
    """Telemetry log for a single refinement iteration."""
    iteration: int
    initial_error_count: int
    resolved_error_count: int
    remaining_error_count: int
    errors_diagnosed: List[Dict[str, Any]]
    execution_time_seconds: float
    repaired_code_snippet: Optional[str] = None


@dataclass
class RefinementLoopResult:
    """Comprehensive outcome of the Agentic Refinement Loop."""
    status: RefinementStatus
    is_valid: bool
    total_iterations: int
    final_payload: Dict[str, Any]
    initial_error_count: int
    final_error_count: int
    history: List[RefinementIterationRecord] = field(default_factory=list)
    total_duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "is_valid": self.is_valid,
            "total_iterations": self.total_iterations,
            "initial_error_count": self.initial_error_count,
            "final_error_count": self.final_error_count,
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "history": [asdict(h) for h in self.history]
        }

    def format_summary(self) -> str:
        """Returns human-readable summary of the refinement process."""
        lines = [
            "============================================================",
            f"  Agentic Refinement Loop Summary: [{self.status.value}]",
            "============================================================",
            f"  Final Valid Status:    {'PASS (0 errors)' if self.is_valid else 'FAIL'}",
            f"  Total Iterations:      {self.total_iterations}",
            f"  Initial Error Count:   {self.initial_error_count}",
            f"  Final Error Count:     {self.final_error_count}",
            f"  Total Execution Time:  {self.total_duration_seconds:.2f}s",
            "------------------------------------------------------------"
        ]
        for h in self.history:
            lines.append(
                f"  Iter #{h.iteration}: {h.initial_error_count} error(s) -> "
                f"{h.remaining_error_count} remaining ({h.execution_time_seconds:.2f}s)"
            )
        lines.append("============================================================")
        return "\n".join(lines)


class AgenticRefinementLoop:
    """
    Coordinates the feedback loop: routes AST validation errors back to the vision model / API,
    tracks multi-iteration convergence, and verifies that repairs eliminate syntax errors.
    """

    def __init__(
        self,
        validator_engine: Optional[ASTValidationEngine] = None,
        generator_fn: Optional[Callable[[Dict[str, Any], List[ExtractedError]], Dict[str, Any]]] = None,
        max_iterations: int = 3
    ):
        """
        Initialize the Refinement Loop.
        
        Args:
            validator_engine: ASTValidationEngine instance (defaults to new instance).
            generator_fn: Optional callable (payload, extracted_errors) -> repaired_payload.
            max_iterations: Maximum refinement retry iterations (default 3).
        """
        self.validator = validator_engine or ASTValidationEngine()
        self.generator_fn = generator_fn or self._default_mock_repair_generator
        self.max_iterations = max_iterations

    @staticmethod
    def _repair_common_html_errors(html: str, errors: List[ExtractedError]) -> str:
        """
        Deterministic, rule-based repair engine used as fallback/mock repairer.
        Handles unclosed elements, duplicate IDs, missing attributes, and quote styles.
        """
        repaired = html

        # Normalize attribute quotes: change single quotes around attribute values to double quotes
        repaired = re.sub(r'([a-zA-Z0-9_\-]+)=\'([^\']*)\'', r'\1="\2"', repaired)

        # 1. Repair Unclosed Elements (close-order)
        if any(e.rule_id == "close-order" for e in errors):
            # Target inline/nested tags that need closing before their immediate parent
            candidate_tags = [
                ("span", "</span"),
                ("p", "</p"),
                ("h1", "</h1"),
                ("h2", "</h2"),
                ("h3", "</h3"),
                ("h4", "</h4"),
                ("h5", "</h5"),
                ("h6", "</h6"),
                ("a", "</a"),
            ]
            closing_markers = [
                "</h1>", "</h2>", "</h3>", "</h4>", "</h5>", "</h6>",
                "</p>", "</nav>", "</header>", "</main>", "</section>", "</div>", "</body>"
            ]

            for tag_name, close_pattern in candidate_tags:
                open_tag_regex = rf"<{tag_name}\b"
                if re.search(open_tag_regex, repaired) and close_pattern not in repaired:
                    # Find last occurrence of the opening tag
                    match = list(re.finditer(open_tag_regex, repaired))[-1]
                    open_pos = match.start()

                    # Find nearest closing parent after open_pos
                    nearest_pos = -1
                    nearest_tag = None
                    for cm in closing_markers:
                        pos = repaired.find(cm, open_pos)
                        if pos != -1 and (nearest_pos == -1 or pos < nearest_pos):
                            nearest_pos = pos
                            nearest_tag = cm

                    if nearest_pos != -1:
                        repaired = repaired[:nearest_pos] + f"</{tag_name}>" + repaired[nearest_pos:]
                    else:
                        repaired += f"</{tag_name}>"

            # Check for unclosed <div> tags
            div_open_count = len(re.findall(r'<div\b', repaired))
            div_close_count = repaired.count("</div")
            if div_open_count > div_close_count:
                diff = div_open_count - div_close_count
                for parent_end in ["</body>", "</main>", "</section>"]:
                    if parent_end in repaired:
                        repaired = repaired.replace(parent_end, ("</div>" * diff) + parent_end, 1)
                        break
                else:
                    repaired += ("</div>" * diff)

        # 2. Repair Duplicate IDs (no-dup-id)
        if any(e.rule_id == "no-dup-id" for e in errors):
            seen_ids = set()
            counter: Dict[str, int] = {}
            def replace_dup_id(match):
                attr_name = match.group(1)
                id_val = match.group(2)
                if id_val in seen_ids:
                    count = counter.get(id_val, 1) + 1
                    counter[id_val] = count
                    new_id = f"{id_val}-{count}"
                    return f'{attr_name}="{new_id}"'
                seen_ids.add(id_val)
                counter[id_val] = 1
                return f'{attr_name}="{id_val}"'

            repaired = re.sub(r'(\bid)=["\']([^"\']+)["\']', replace_dup_id, repaired)

        # 3. Repair Missing Required Attributes (element-required-attributes, wcag/h37, no-implicit-button-type)
        if any(e.rule_id in ("element-required-attributes", "wcag/h37", "no-implicit-button-type") for e in errors):
            def fix_img(match):
                tag = match.group(0)
                if "src=" not in tag:
                    tag = tag.replace("<img", '<img src="placeholder.png"')
                if "alt=" not in tag:
                    tag = tag.replace("<img", '<img alt="UI Component Graphic"')
                return tag
            repaired = re.sub(r'<img\b[^>]*>', fix_img, repaired)

            if "<html" in repaired and "lang=" not in repaired:
                repaired = re.sub(r'<html\b([^>]*)>', r'<html lang="en"\1>', repaired)

            def fix_button(match):
                tag = match.group(0)
                if "type=" not in tag:
                    tag = tag.replace("<button", '<button type="button"')
                return tag
            repaired = re.sub(r'<button\b[^>]*>', fix_button, repaired)

        return repaired

    def _default_mock_repair_generator(
        self,
        current_payload: Dict[str, Any],
        extracted_errors: List[ExtractedError]
    ) -> Dict[str, Any]:
        """
        Default repair generator that applies deterministic AST corrections
        to standalone html, components, and full_html.
        """
        import copy
        repaired_payload = copy.deepcopy(current_payload)

        # 1. Repair standalone html snippet if present
        if "html" in repaired_payload and repaired_payload["html"]:
            repaired_payload["html"] = self._repair_common_html_errors(
                repaired_payload["html"], extracted_errors
            )

        # 2. Repair full_html if present
        if "full_html" in repaired_payload and repaired_payload["full_html"]:
            repaired_payload["full_html"] = self._repair_common_html_errors(
                repaired_payload["full_html"], extracted_errors
            )

        # 3. Repair individual components
        if "components" in repaired_payload:
            for comp in repaired_payload["components"]:
                comp_html = comp.get("html", "")
                if comp_html:
                    comp["html"] = self._repair_common_html_errors(comp_html, extracted_errors)

        return repaired_payload

    def run_snippet_loop(
        self,
        initial_html: str,
        component_type: Optional[str] = None
    ) -> Tuple[str, RefinementLoopResult]:
        """
        Executes refinement loop for an isolated HTML snippet (e.g. single component).
        """
        start_time = time.time()
        current_html = initial_html
        history: List[RefinementIterationRecord] = []

        # Initial validation
        report = self.validator.validate_snippet(current_html)
        initial_errors = ASTErrorExtractor.extract_errors(report, current_html)
        initial_count = len(initial_errors)

        if report.is_valid and initial_count == 0:
            result = RefinementLoopResult(
                status=RefinementStatus.VALIDATION_BYPASS,
                is_valid=True,
                total_iterations=0,
                final_payload={"html": current_html},
                initial_error_count=0,
                final_error_count=0,
                history=[],
                total_duration_seconds=time.time() - start_time
            )
            return current_html, result

        curr_errors = initial_errors
        iteration = 0

        while iteration < self.max_iterations and len(curr_errors) > 0:
            iter_start = time.time()
            iteration += 1

            # 1. Format error prompt
            error_prompt = ErrorPromptFormatter.format_diagnostic_prompt(
                extracted_errors=curr_errors,
                original_code=current_html,
                component_type=component_type,
                include_schema_rules=False
            )
            logger.debug(f"[Iteration {iteration}] Error routing prompt generated:\n{error_prompt[:200]}...")

            # 2. Invoke generator to repair code
            dummy_payload = {"html": current_html}
            repaired_payload = self.generator_fn(dummy_payload, curr_errors)
            repaired_html = repaired_payload.get("html", current_html)

            # 3. Validate repaired snippet
            new_report = self.validator.validate_snippet(repaired_html)
            new_errors = ASTErrorExtractor.extract_errors(new_report, repaired_html)

            resolved = max(0, len(curr_errors) - len(new_errors))
            record = RefinementIterationRecord(
                iteration=iteration,
                initial_error_count=len(curr_errors),
                resolved_error_count=resolved,
                remaining_error_count=len(new_errors),
                errors_diagnosed=[e.to_dict() for e in curr_errors],
                execution_time_seconds=time.time() - iter_start,
                repaired_code_snippet=repaired_html
            )
            history.append(record)

            current_html = repaired_html
            curr_errors = new_errors

            if new_report.is_valid and len(new_errors) == 0:
                break

        final_valid = (len(curr_errors) == 0)
        status = RefinementStatus.SUCCESS if final_valid else RefinementStatus.MAX_RETRIES_EXCEEDED

        result = RefinementLoopResult(
            status=status,
            is_valid=final_valid,
            total_iterations=iteration,
            final_payload={"html": current_html},
            initial_error_count=initial_count,
            final_error_count=len(curr_errors),
            history=history,
            total_duration_seconds=time.time() - start_time
        )
        return current_html, result

    def run_payload_loop(
        self,
        initial_payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], RefinementLoopResult]:
        """
        Executes refinement loop for an entire multi-component UI payload dictionary.
        Validates both individual components and the overall full_html.
        """
        import copy
        start_time = time.time()
        current_payload = copy.deepcopy(initial_payload)
        history: List[RefinementIterationRecord] = []

        # Helper to gather all errors across payload
        def collect_payload_errors(payload: Dict[str, Any]) -> List[ExtractedError]:
            all_errs: List[ExtractedError] = []
            for comp in payload.get("components", []):
                h = comp.get("html", "")
                rep = self.validator.validate_snippet(h)
                errs = ASTErrorExtractor.extract_errors(rep, h)
                all_errs.extend(errs)

            if "full_html" in payload and payload["full_html"]:
                fh = payload["full_html"]
                rep = self.validator.validate_document(fh)
                errs = ASTErrorExtractor.extract_errors(rep, fh)
                all_errs.extend(errs)

            return all_errs

        initial_errors = collect_payload_errors(current_payload)
        initial_count = len(initial_errors)

        if initial_count == 0:
            result = RefinementLoopResult(
                status=RefinementStatus.VALIDATION_BYPASS,
                is_valid=True,
                total_iterations=0,
                final_payload=current_payload,
                initial_error_count=0,
                final_error_count=0,
                history=[],
                total_duration_seconds=time.time() - start_time
            )
            return current_payload, result

        curr_errors = initial_errors
        iteration = 0

        while iteration < self.max_iterations and len(curr_errors) > 0:
            iter_start = time.time()
            iteration += 1

            # Invoke generator callback
            repaired_payload = self.generator_fn(current_payload, curr_errors)
            new_errors = collect_payload_errors(repaired_payload)

            resolved = max(0, len(curr_errors) - len(new_errors))
            record = RefinementIterationRecord(
                iteration=iteration,
                initial_error_count=len(curr_errors),
                resolved_error_count=resolved,
                remaining_error_count=len(new_errors),
                errors_diagnosed=[e.to_dict() for e in curr_errors],
                execution_time_seconds=time.time() - iter_start,
                repaired_code_snippet=repaired_payload.get("full_html")
            )
            history.append(record)

            current_payload = repaired_payload
            curr_errors = new_errors

            if len(new_errors) == 0:
                break

        final_valid = (len(curr_errors) == 0)
        status = RefinementStatus.SUCCESS if final_valid else RefinementStatus.MAX_RETRIES_EXCEEDED

        result = RefinementLoopResult(
            status=status,
            is_valid=final_valid,
            total_iterations=iteration,
            final_payload=current_payload,
            initial_error_count=initial_count,
            final_error_count=len(curr_errors),
            history=history,
            total_duration_seconds=time.time() - start_time
        )
        return current_payload, result
