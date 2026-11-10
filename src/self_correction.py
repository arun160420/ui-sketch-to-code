"""
src/self_correction.py

Week 8 Deliverable (COM71123-10):
Agentic Refinement Loop - Self-Correction

Enables the vision model to reflect on AST validation diagnostics, formulate repair
plans, and self-correct generated UI code through iterative generation-validation cycles
with active convergence monitoring.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.ast_validator import ASTValidationEngine, ValidationError, ValidationReport
from src.refinement_loop import (
    ASTErrorExtractor,
    ErrorCategory,
    ExtractedError,
    ErrorPromptFormatter,
    AgenticRefinementLoop
)
from src.schema import UI_COMPONENT_JSON_SCHEMA, validate_ui_payload

logger = logging.getLogger("SelfCorrectionEngine")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ============================================================================
# 1. Self-Correction & Reflection Prompt Framework
# ============================================================================

class SelfCorrectionPromptEngine:
    """
    Designs advanced reflection and self-repair prompts based on AST error logs.
    Instructs models to analyze failure root causes, formulate repair plans,
    and output clean, compliant HTML5 / Tailwind code adhering to JSON schemas.
    """

    FEW_SHOT_CORRECTION_EXAMPLES = [
        {
            "error_type": "Unclosed Element Tag (close-order)",
            "erroneous": '<nav class="flex gap-4"><span>Home</nav>',
            "reflection": "The <span> tag was opened on line 1 but </nav> closed before </span>. In HTML5 AST, child elements must close before parent elements.",
            "plan": "Insert </span> immediately after 'Home' and before </nav>.",
            "corrected": '<nav class="flex gap-4"><span>Home</span></nav>'
        },
        {
            "error_type": "Duplicate Element Identifier (no-dup-id)",
            "erroneous": '<div id="profile-card"><h2 id="profile-card">Profile</h2></div>',
            "reflection": "Both <div> and <h2> share the identical id='profile-card', violating the DOM requirement that IDs be document-unique.",
            "plan": "Retain id='profile-card' on the parent card and change <h2> to id='profile-card-title'.",
            "corrected": '<div id="profile-card"><h2 id="profile-card-title">Profile</h2></div>'
        },
        {
            "error_type": "Missing Required Attributes (element-required-attributes, wcag/h37)",
            "erroneous": '<div class="avatar"><img class="rounded-full"></div>',
            "reflection": "The <img> element is missing required 'src' and 'alt' attributes for accessibility and rendering compliance.",
            "plan": "Add src='avatar-placeholder.png' and descriptive alt='User Avatar Graphic'.",
            "corrected": '<div class="avatar"><img src="avatar-placeholder.png" alt="User Avatar Graphic" class="rounded-full"></div>'
        },
        {
            "error_type": "Implicit Button Type (no-implicit-button-type)",
            "erroneous": '<button class="btn-primary">Submit</button>',
            "reflection": "The <button> element lacks an explicit 'type' attribute, defaulting to type='submit' which may trigger unintentional form submits.",
            "plan": "Explicitly add type='button' (or type='submit' if within an auth form).",
            "corrected": '<button type="button" class="btn-primary">Submit</button>'
        }
    ]

    @classmethod
    def build_reflection_prompt(
        cls,
        extracted_errors: List[ExtractedError],
        original_code: str,
        component_type: Optional[str] = None,
        include_few_shot: bool = True
    ) -> str:
        """
        Builds a self-reflection prompt prompting the model to articulate:
        1. <reflection>: Root-cause diagnosis of each syntax / AST violation.
        2. <repair_plan>: Minimal-diff correction plan preserving visual styles.
        3. <repaired_code>: Final validated HTML code.
        """
        comp_name = component_type.capitalize() if component_type else "UI Component"

        lines = [
            f"You are an expert AI Frontend Engineer performing an Agentic Self-Correction cycle for {comp_name}.",
            "The generated HTML failed automated AST (Abstract Syntax Tree) validation.",
            "You must carefully REFLECT on the root cause of each failure, create a REPAIR PLAN,",
            "and output the corrected HTML code while preserving all Tailwind CSS utility classes and visual layout.\n",
            "### AST Validation Errors Detected:"
        ]

        for idx, err in enumerate(extracted_errors, start=1):
            lines.append(f"{idx}. [{err.rule_id}] Line {err.line}, Column {err.column}: {err.message}")
            if err.selector:
                lines.append(f"   Selector: `{err.selector}`")
            if err.remediation_hint:
                lines.append(f"   Diagnostic Hint: {err.remediation_hint}")
            if err.context_snippet:
                lines.append("   Offending Code Excerpt:")
                lines.append(f"   ```html\n{err.context_snippet}\n   ```")
            lines.append("")

        if include_few_shot:
            lines.append("### Reference Self-Correction Pattern:")
            ex = cls.FEW_SHOT_CORRECTION_EXAMPLES[0]
            lines.append(f"Example Error: {ex['error_type']}")
            lines.append(f"Erroneous: `{ex['erroneous']}`")
            lines.append(f"Reflection: {ex['reflection']}")
            lines.append(f"Plan: {ex['plan']}")
            lines.append(f"Corrected: `{ex['corrected']}`\n")

        lines.append("### Erroneous Source Code:")
        lines.append(f"```html\n{original_code.strip()}\n```\n")

        lines.append("### Response Format Instructions:")
        lines.append("Perform reflection and output your response structured as follows:")
        lines.append("1. Begin with a `<reflection>` section explaining why the errors occurred.")
        lines.append("2. Include a `<repair_plan>` outlining the specific fixes.")
        lines.append("3. Provide the corrected HTML inside `<repaired_code>` tags (or in valid JSON complying with the UI schema).")

        return "\n".join(lines)

    @classmethod
    def build_component_localized_repair_prompt(
        cls,
        component_id: str,
        component_type: str,
        failing_html: str,
        errors: List[ExtractedError]
    ) -> str:
        """
        Constructs a localized repair prompt targeting a single failing component
        without touching passing components in the document.
        """
        lines = [
            f"### Localized Component Self-Correction: [{component_type.upper()}] (ID: {component_id})",
            f"Component '{component_id}' has {len(errors)} AST syntax violation(s) that must be surgically repaired.",
            "\nErrors to resolve:"
        ]
        for idx, err in enumerate(errors, start=1):
            lines.append(f"  {idx}. [{err.rule_id}] L{err.line}:C{err.column} - {err.message}")
            if err.remediation_hint:
                lines.append(f"     -> Fix: {err.remediation_hint}")

        lines.append(f"\nFailing Component Code:\n```html\n{failing_html.strip()}\n```")
        lines.append("\nReturn ONLY the repaired, self-corrected HTML for this component with all errors fixed.")
        return "\n".join(lines)


# ============================================================================
# 2. Convergence Monitoring & Telemetry
# ============================================================================

class ConvergenceState(str, Enum):
    CONVERGED = "CONVERGED"                   # 0 errors reached - full syntactic compliance
    PROGRESSING = "PROGRESSING"               # Error count decreased compared to previous cycle
    STAGNATING = "STAGNATING"                 # Error count unchanged (stuck on same errors)
    REGRESSING = "REGRESSING"                 # Error count increased (repairs broke new things)
    MAX_CYCLES_EXCEEDED = "MAX_CYCLES_EXCEEDED" # Max iterations reached without 0 errors


@dataclass
class CycleTelemetry:
    """Telemetry data captured for a single self-correction cycle."""
    cycle: int
    initial_errors: int
    final_errors: int
    delta_errors: int  # initial_errors - final_errors
    velocity: float    # delta_errors / initial_errors (rate of resolution)
    state: ConvergenceState
    duration_seconds: float
    repaired_preview: Optional[str] = None
    diagnosed_rules: List[str] = field(default_factory=list)


class ConvergenceMonitor:
    """
    Monitors the trajectory of the self-correction loop across cycles.
    Detects convergence, stagnation, and regression, enforcing early stopping
    to prevent infinite retry loops or quota exhaustion.
    """

    def __init__(self, max_cycles: int = 4, max_stagnation_cycles: int = 2):
        self.max_cycles = max_cycles
        self.max_stagnation_cycles = max_stagnation_cycles
        self.history: List[CycleTelemetry] = []
        self._stagnation_count = 0

    def evaluate_cycle(
        self,
        cycle_num: int,
        error_count_before: int,
        error_count_after: int,
        duration_seconds: float,
        rules: Optional[List[str]] = None,
        code_preview: Optional[str] = None
    ) -> Tuple[ConvergenceState, bool]:
        """
        Evaluates the outcome of a single self-correction cycle.
        Returns (ConvergenceState, should_continue_loop).
        """
        delta = error_count_before - error_count_after
        velocity = (delta / error_count_before) if error_count_before > 0 else 0.0

        if error_count_after == 0:
            state = ConvergenceState.CONVERGED
            self._stagnation_count = 0
            should_continue = False
        elif error_count_after < error_count_before:
            state = ConvergenceState.PROGRESSING
            self._stagnation_count = 0
            should_continue = cycle_num < self.max_cycles
        elif error_count_after == error_count_before:
            state = ConvergenceState.STAGNATING
            self._stagnation_count += 1
            # Stop if stagnating repeatedly
            should_continue = (
                self._stagnation_count < self.max_stagnation_cycles
                and cycle_num < self.max_cycles
            )
        else:
            state = ConvergenceState.REGRESSING
            self._stagnation_count += 1
            should_continue = (
                self._stagnation_count < self.max_stagnation_cycles
                and cycle_num < self.max_cycles
            )

        telemetry = CycleTelemetry(
            cycle=cycle_num,
            initial_errors=error_count_before,
            final_errors=error_count_after,
            delta_errors=delta,
            velocity=round(velocity, 4),
            state=state,
            duration_seconds=round(duration_seconds, 4),
            repaired_preview=code_preview[:120] if code_preview else None,
            diagnosed_rules=rules or []
        )
        self.history.append(telemetry)

        logger.info(
            f"[Cycle {cycle_num}] State: {state.value} | "
            f"Errors: {error_count_before} -> {error_count_after} (Delta: {delta}) | "
            f"Duration: {duration_seconds:.3f}s"
        )
        return state, should_continue

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Computes aggregate convergence metrics across all recorded cycles."""
        if not self.history:
            return {"total_cycles": 0, "final_state": "NONE"}

        first_cycle = self.history[0]
        last_cycle = self.history[-1]
        total_delta = first_cycle.initial_errors - last_cycle.final_errors
        overall_reduction = (
            (total_delta / first_cycle.initial_errors * 100.0)
            if first_cycle.initial_errors > 0 else 100.0
        )

        return {
            "total_cycles": len(self.history),
            "final_state": last_cycle.state.value,
            "initial_error_count": first_cycle.initial_errors,
            "final_error_count": last_cycle.final_errors,
            "total_errors_resolved": max(0, total_delta),
            "error_reduction_percentage": round(overall_reduction, 2),
            "converged": last_cycle.state == ConvergenceState.CONVERGED,
            "total_duration_seconds": round(sum(h.duration_seconds for h in self.history), 4)
        }


# ============================================================================
# 3. Self-Correction Engine & Pipeline Integration
# ============================================================================

@dataclass
class SelfCorrectionResult:
    """Outcome of the self-correction engine execution."""
    converged: bool
    final_code: Union[str, Dict[str, Any]]
    initial_errors: int
    final_errors: int
    total_cycles: int
    convergence_state: ConvergenceState
    metrics: Dict[str, Any]
    cycle_history: List[CycleTelemetry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "converged": self.converged,
            "initial_errors": self.initial_errors,
            "final_errors": self.final_errors,
            "total_cycles": self.total_cycles,
            "convergence_state": self.convergence_state.value,
            "metrics": self.metrics,
            "cycle_history": [asdict(c) for c in self.cycle_history]
        }

    def format_summary(self) -> str:
        """Returns a formatted CLI-friendly summary of the self-correction run."""
        lines = [
            "============================================================",
            f"  Self-Correction Engine Summary: [{self.convergence_state.value}]",
            "============================================================",
            f"  Converged to 0 Errors: {'YES (Clean AST)' if self.converged else 'NO'}",
            f"  Total Cycles Executed: {self.total_cycles}",
            f"  Initial Error Count:   {self.initial_errors}",
            f"  Final Error Count:     {self.final_errors}",
            f"  Error Reduction Rate:  {self.metrics.get('error_reduction_percentage', 0)}%",
            f"  Total Execution Time:  {self.metrics.get('total_duration_seconds', 0)}s",
            "------------------------------------------------------------"
        ]
        for c in self.cycle_history:
            lines.append(
                f"  Cycle #{c.cycle}: {c.initial_errors} -> {c.final_errors} errors "
                f"(Δ: {c.delta_errors}, State: {c.state.value}) in {c.duration_seconds:.2f}s"
            )
        lines.append("============================================================")
        return "\n".join(lines)


class SelfCorrectionEngine:
    """
    Master Self-Correction Engine coordinating iterative generation,
    reflection-guided repair, localized component healing, and convergence monitoring.
    """

    def __init__(
        self,
        validator_engine: Optional[ASTValidationEngine] = None,
        repair_generator_fn: Optional[Callable[[Dict[str, Any], List[ExtractedError]], Dict[str, Any]]] = None,
        max_cycles: int = 3,
        max_stagnation_cycles: int = 2
    ):
        self.validator = validator_engine or ASTValidationEngine()
        self.generator_fn = repair_generator_fn or self._default_reflection_repair_generator
        self.max_cycles = max_cycles
        self.max_stagnation_cycles = max_stagnation_cycles

    def _default_reflection_repair_generator(
        self,
        payload: Dict[str, Any],
        errors: List[ExtractedError]
    ) -> Dict[str, Any]:
        """
        Deterministic, reflection-informed repair generator applying rule-based
        AST corrections while preserving layout and Tailwind classes.
        """
        repairer = AgenticRefinementLoop(validator_engine=self.validator)
        return repairer._default_mock_repair_generator(payload, errors)

    def self_correct_snippet(
        self,
        html_code: str,
        component_type: Optional[str] = None
    ) -> SelfCorrectionResult:
        """
        Executes self-correction cycle on an isolated component HTML snippet.
        """
        start_time = time.time()
        monitor = ConvergenceMonitor(
            max_cycles=self.max_cycles,
            max_stagnation_cycles=self.max_stagnation_cycles
        )

        current_html = html_code
        initial_report = self.validator.validate_snippet(current_html)
        initial_errors = ASTErrorExtractor.extract_errors(initial_report, current_html)
        initial_count = len(initial_errors)

        if initial_count == 0:
            monitor.evaluate_cycle(
                cycle_num=0,
                error_count_before=0,
                error_count_after=0,
                duration_seconds=time.time() - start_time,
                code_preview=current_html
            )
            return SelfCorrectionResult(
                converged=True,
                final_code=current_html,
                initial_errors=0,
                final_errors=0,
                total_cycles=0,
                convergence_state=ConvergenceState.CONVERGED,
                metrics=monitor.get_summary_metrics(),
                cycle_history=monitor.history
            )

        curr_errors = initial_errors
        cycle = 0

        while cycle < self.max_cycles:
            cycle_start = time.time()
            cycle += 1

            # 1. Build reflection prompt
            reflection_prompt = SelfCorrectionPromptEngine.build_reflection_prompt(
                extracted_errors=curr_errors,
                original_code=current_html,
                component_type=component_type
            )
            logger.debug(f"[Cycle {cycle}] Generated reflection prompt:\n{reflection_prompt[:180]}...")

            # 2. Invoke repair generator
            dummy_payload = {"html": current_html}
            repaired_payload = self.generator_fn(dummy_payload, curr_errors)
            repaired_html = repaired_payload.get("html", current_html)

            # 3. Validate repaired markup
            new_report = self.validator.validate_snippet(repaired_html)
            new_errors = ASTErrorExtractor.extract_errors(new_report, repaired_html)

            cycle_duration = time.time() - cycle_start
            state, should_continue = monitor.evaluate_cycle(
                cycle_num=cycle,
                error_count_before=len(curr_errors),
                error_count_after=len(new_errors),
                duration_seconds=cycle_duration,
                rules=[e.rule_id for e in curr_errors],
                code_preview=repaired_html
            )

            current_html = repaired_html
            curr_errors = new_errors

            if not should_continue:
                break

        final_converged = (len(curr_errors) == 0)
        final_state = ConvergenceState.CONVERGED if final_converged else monitor.history[-1].state

        return SelfCorrectionResult(
            converged=final_converged,
            final_code=current_html,
            initial_errors=initial_count,
            final_errors=len(curr_errors),
            total_cycles=cycle,
            convergence_state=final_state,
            metrics=monitor.get_summary_metrics(),
            cycle_history=monitor.history
        )

    def self_correct_payload(
        self,
        payload: Dict[str, Any]
    ) -> SelfCorrectionResult:
        """
        Executes localized component-level self-correction across an entire multi-component
        UI payload, followed by document-level reconciliation.
        """
        import copy
        start_time = time.time()
        monitor = ConvergenceMonitor(
            max_cycles=self.max_cycles,
            max_stagnation_cycles=self.max_stagnation_cycles
        )

        current_payload = copy.deepcopy(payload)

        # Helper to gather all errors
        def collect_errors(p: Dict[str, Any]) -> List[ExtractedError]:
            errs = []
            for comp in p.get("components", []):
                h = comp.get("html", "")
                rep = self.validator.validate_snippet(h)
                errs.extend(ASTErrorExtractor.extract_errors(rep, h))
            if "full_html" in p and p["full_html"]:
                fh = p["full_html"]
                rep = self.validator.validate_document(fh)
                errs.extend(ASTErrorExtractor.extract_errors(rep, fh))
            return errs

        initial_errors = collect_errors(current_payload)
        initial_count = len(initial_errors)

        if initial_count == 0:
            return SelfCorrectionResult(
                converged=True,
                final_code=current_payload,
                initial_errors=0,
                final_errors=0,
                total_cycles=0,
                convergence_state=ConvergenceState.CONVERGED,
                metrics=monitor.get_summary_metrics(),
                cycle_history=[]
            )

        curr_errors = initial_errors
        cycle = 0

        while cycle < self.max_cycles:
            cycle_start = time.time()
            cycle += 1

            # 1. Localized Component Repair: Repair each failing component individually
            for comp in current_payload.get("components", []):
                comp_html = comp.get("html", "")
                comp_id = comp.get("component_id", "comp")
                comp_type = comp.get("component_type", "component")
                rep = self.validator.validate_snippet(comp_html)
                comp_errs = ASTErrorExtractor.extract_errors(rep, comp_html)

                if comp_errs:
                    logger.info(f"Targeted self-correction for component '{comp_id}' ({len(comp_errs)} errors)")
                    repaired_comp_payload = self.generator_fn({"html": comp_html}, comp_errs)
                    repaired_comp_html = repaired_comp_payload.get("html", comp_html)
                    # Reconcile into full_html
                    if "full_html" in current_payload and comp_html in current_payload["full_html"]:
                        current_payload["full_html"] = current_payload["full_html"].replace(comp_html, repaired_comp_html)
                    comp["html"] = repaired_comp_html

            # 2. Document Reconciliation: Re-validate & repair full_html
            if "full_html" in current_payload and current_payload["full_html"]:
                doc_html = current_payload["full_html"]
                doc_rep = self.validator.validate_document(doc_html)
                doc_errs = ASTErrorExtractor.extract_errors(doc_rep, doc_html)
                if doc_errs:
                    repaired_doc_payload = self.generator_fn({"full_html": doc_html}, doc_errs)
                    current_payload["full_html"] = repaired_doc_payload.get("full_html", doc_html)

            # 3. Post-cycle assessment
            new_errors = collect_errors(current_payload)
            cycle_duration = time.time() - cycle_start

            state, should_continue = monitor.evaluate_cycle(
                cycle_num=cycle,
                error_count_before=len(curr_errors),
                error_count_after=len(new_errors),
                duration_seconds=cycle_duration,
                rules=[e.rule_id for e in curr_errors],
                code_preview=current_payload.get("full_html")
            )

            curr_errors = new_errors
            if not should_continue:
                break

        final_converged = (len(curr_errors) == 0)
        final_state = ConvergenceState.CONVERGED if final_converged else monitor.history[-1].state

        return SelfCorrectionResult(
            converged=final_converged,
            final_code=current_payload,
            initial_errors=initial_count,
            final_errors=len(curr_errors),
            total_cycles=cycle,
            convergence_state=final_state,
            metrics=monitor.get_summary_metrics(),
            cycle_history=monitor.history
        )
