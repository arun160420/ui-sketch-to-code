"""
src/ast_validator.py

Week 6 Deliverable (COM71123-8):
Abstract Syntax Tree (AST) Validation Engine

Integrates html-validate via Node.js to enforce structural integrity, HTML5
semantic hierarchy, attribute compliance, and syntax rules for both full
HTML documents and generated UI component snippets.
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Configure logging
logger = logging.getLogger("ASTValidator")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@dataclass
class ValidationError:
    """Represents an individual structural or semantic validation error/warning."""
    rule_id: str
    severity: str  # "error" | "warning"
    message: str
    line: int
    column: int
    offset: Optional[int] = None
    size: Optional[int] = None
    selector: Optional[str] = None
    rule_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    """Encapsulates the complete AST validation outcome, diagnostics, and metrics."""
    is_valid: bool
    error_count: int
    warning_count: int
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    source_snippet: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }

    def format_summary(self) -> str:
        """Returns a formatted CLI-friendly summary report."""
        status_icon = "PASS" if self.is_valid else "FAIL"
        lines = [
            f"=== AST Validation Report: [{status_icon}] ===",
            f"Total Errors:   {self.error_count}",
            f"Total Warnings: {self.warning_count}",
        ]
        if self.errors:
            lines.append("\n[ERRORS]:")
            for idx, err in enumerate(self.errors, start=1):
                loc = f"Line {err.line}, Col {err.column}"
                lines.append(f"  {idx}. [{err.rule_id}] ({loc}): {err.message}")
                if err.selector:
                    lines.append(f"     Target Selector: {err.selector}")
        if self.warnings:
            lines.append("\n[WARNINGS]:")
            for idx, warn in enumerate(self.warnings, start=1):
                loc = f"Line {warn.line}, Col {warn.column}"
                lines.append(f"  {idx}. [{warn.rule_id}] ({loc}): {warn.message}")
                if warn.selector:
                    lines.append(f"     Target Selector: {warn.selector}")
        return "\n".join(lines)

    def format_markdown_report(self) -> str:
        """Returns a Markdown-formatted diagnostic report."""
        status_badge = "Pass" if self.is_valid else "Fail"
        md = [
            f"### AST Validation Report: **{status_badge}**\n",
            f"- **Structural Integrity**: {'Valid' if self.is_valid else 'Violations Detected'}",
            f"- **Error Count**: `{self.error_count}`",
            f"- **Warning Count**: `{self.warning_count}`\n",
        ]
        if self.errors:
            md.append("#### Errors")
            md.append("| # | Rule ID | Location | Message | Target Selector |")
            md.append("|---|---|---|---|---|")
            for idx, err in enumerate(self.errors, start=1):
                sel = f"`{err.selector}`" if err.selector else "-"
                md.append(f"| {idx} | `{err.rule_id}` | L{err.line}:C{err.column} | {err.message} | {sel} |")
            md.append("")
        if self.warnings:
            md.append("#### Warnings")
            md.append("| # | Rule ID | Location | Message | Target Selector |")
            md.append("|---|---|---|---|---|")
            for idx, warn in enumerate(self.warnings, start=1):
                sel = f"`{warn.selector}`" if warn.selector else "-"
                md.append(f"| {idx} | `{warn.rule_id}` | L{warn.line}:C{warn.column} | {warn.message} | {sel} |")
            md.append("")
        return "\n".join(md)


class ASTValidationEngine:
    """
    Core AST Validation Engine interfacing with html-validate.
    
    Provides snippet-level and document-level structural parsing,
    error capture, and status reporting for UI-generated HTML.
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        bridge_script_path: Optional[Union[str, Path]] = None,
        node_executable: str = "node"
    ):
        """
        Initialize the AST Validation Engine.
        
        Args:
            config_path: Optional path to .htmlvalidate.json. Defaults to project root.
            bridge_script_path: Optional path to validate_html_ast.js runner.
            node_executable: Node binary name or path ('node' by default).
        """
        self.node_executable = node_executable

        # Resolve project root relative to this file
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir.parent

        if config_path:
            self.config_path = Path(config_path).resolve()
        else:
            default_config = project_root / ".htmlvalidate.json"
            self.config_path = default_config if default_config.exists() else None

        if bridge_script_path:
            self.bridge_script = Path(bridge_script_path).resolve()
        else:
            self.bridge_script = project_root / "scripts" / "validate_html_ast.js"

        logger.debug(
            f"Initialized ASTValidationEngine with bridge: {self.bridge_script}, config: {self.config_path}"
        )

    def _execute_runner(
        self,
        html_content: str,
        is_snippet: bool = False,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Executes the Node.js html-validate bridge via subprocess with stdin.
        """
        cmd = [self.node_executable, str(self.bridge_script), "--stdin"]
        if is_snippet:
            cmd.append("--snippet")
        if self.config_path and self.config_path.exists():
            cmd.extend(["--config", str(self.config_path)])

        try:
            process = subprocess.run(
                cmd,
                input=html_content,
                text=True,
                capture_output=True,
                timeout=timeout,
                encoding="utf-8",
                check=False
            )
            raw_stdout = process.stdout.strip()

            if not raw_stdout:
                # If stdout is empty, check stderr
                logger.error(f"Node bridge returned empty stdout. stderr: {process.stderr}")
                return {
                    "valid": False,
                    "errorCount": 1,
                    "warningCount": 0,
                    "errors": [{
                        "ruleId": "bridge-execution-error",
                        "severity": "error",
                        "message": process.stderr or "Empty output from validator bridge",
                        "line": 0,
                        "column": 0
                    }],
                    "warnings": []
                }

            return json.loads(raw_stdout)

        except subprocess.TimeoutExpired:
            logger.error(f"Validation timed out after {timeout} seconds.")
            return {
                "valid": False,
                "errorCount": 1,
                "warningCount": 0,
                "errors": [{
                    "ruleId": "timeout-error",
                    "severity": "error",
                    "message": f"Validation timed out after {timeout} seconds",
                    "line": 0,
                    "column": 0
                }],
                "warnings": []
            }
        except FileNotFoundError:
            logger.error(f"Node.js binary '{self.node_executable}' not found.")
            return {
                "valid": False,
                "errorCount": 1,
                "warningCount": 0,
                "errors": [{
                    "ruleId": "node-not-found",
                    "severity": "error",
                    "message": f"Node.js executable '{self.node_executable}' not found in PATH",
                    "line": 0,
                    "column": 0
                }],
                "warnings": []
            }
        except json.JSONDecodeError as jde:
            logger.error(f"Failed to parse bridge JSON output: {jde}. Raw: {raw_stdout}")
            return {
                "valid": False,
                "errorCount": 1,
                "warningCount": 0,
                "errors": [{
                    "ruleId": "json-parse-error",
                    "severity": "error",
                    "message": f"Failed to parse validator output: {str(jde)}",
                    "line": 0,
                    "column": 0
                }],
                "warnings": []
            }

    def _parse_report(self, data: Dict[str, Any], source: Optional[str] = None) -> ValidationReport:
        """Converts raw JSON dictionary into a structured ValidationReport dataclass."""
        errors: List[ValidationError] = []
        for e in data.get("errors", []):
            errors.append(ValidationError(
                rule_id=e.get("ruleId", "unknown"),
                severity=e.get("severity", "error"),
                message=e.get("message", ""),
                line=int(e.get("line", 0)),
                column=int(e.get("column", 0)),
                offset=e.get("offset"),
                size=e.get("size"),
                selector=e.get("selector"),
                rule_url=e.get("ruleUrl")
            ))

        warnings: List[ValidationError] = []
        for w in data.get("warnings", []):
            warnings.append(ValidationError(
                rule_id=w.get("ruleId", "unknown"),
                severity=w.get("severity", "warning"),
                message=w.get("message", ""),
                line=int(w.get("line", 0)),
                column=int(w.get("column", 0)),
                offset=w.get("offset"),
                size=w.get("size"),
                selector=w.get("selector"),
                rule_url=w.get("ruleUrl")
            ))

        is_valid = bool(data.get("valid", len(errors) == 0))
        error_count = int(data.get("errorCount", len(errors)))
        warning_count = int(data.get("warningCount", len(warnings)))

        return ValidationReport(
            is_valid=is_valid,
            error_count=error_count,
            warning_count=warning_count,
            errors=errors,
            warnings=warnings,
            source_snippet=source,
            raw_response=data
        )

    def validate_snippet(self, html_snippet: str) -> ValidationReport:
        """
        Validates an isolated HTML snippet (e.g., component navbar, button, form).
        Disables document-level requirements (like doctype).
        """
        if not html_snippet or not html_snippet.strip():
            return ValidationReport(
                is_valid=False,
                error_count=1,
                warning_count=0,
                errors=[ValidationError(
                    rule_id="empty-input",
                    severity="error",
                    message="HTML snippet is empty or contains only whitespace.",
                    line=0,
                    column=0
                )],
                source_snippet=html_snippet
            )

        data = self._execute_runner(html_snippet, is_snippet=True)
        report = self._parse_report(data, source=html_snippet)
        logger.info(
            f"Snippet Validation: {'PASSED' if report.is_valid else 'FAILED'} "
            f"({report.error_count} errors, {report.warning_count} warnings)"
        )
        return report

    def validate_document(self, full_html: str) -> ValidationReport:
        """
        Validates a complete HTML document (with or without DOCTYPE/HTML structure).
        """
        if not full_html or not full_html.strip():
            return ValidationReport(
                is_valid=False,
                error_count=1,
                warning_count=0,
                errors=[ValidationError(
                    rule_id="empty-input",
                    severity="error",
                    message="HTML document is empty.",
                    line=0,
                    column=0
                )],
                source_snippet=full_html
            )

        data = self._execute_runner(full_html, is_snippet=False)
        report = self._parse_report(data, source=full_html)
        logger.info(
            f"Document Validation: {'PASSED' if report.is_valid else 'FAILED'} "
            f"({report.error_count} errors, {report.warning_count} warnings)"
        )
        return report

    def validate_file(self, file_path: Union[str, Path]) -> ValidationReport:
        """
        Validates an HTML file on disk.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            return ValidationReport(
                is_valid=False,
                error_count=1,
                warning_count=0,
                errors=[ValidationError(
                    rule_id="file-not-found",
                    severity="error",
                    message=f"File not found: {path}",
                    line=0,
                    column=0
                )]
            )

        content = path.read_text(encoding="utf-8")
        return self.validate_document(content)

    def validate_ui_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates all components in a generated UI payload, checking each
        component snippet and the overall full_html if present.
        
        Returns an enriched status dictionary containing component-by-component
        and document-wide validation reports.
        """
        results: Dict[str, Any] = {
            "all_valid": True,
            "components": [],
            "document_report": None
        }

        # 1. Validate individual components
        components = payload.get("components", [])
        for comp in components:
            comp_id = comp.get("component_id", "unknown")
            snippet = comp.get("html", "")
            report = self.validate_snippet(snippet)

            if not report.is_valid:
                results["all_valid"] = False

            results["components"].append({
                "component_id": comp_id,
                "component_type": comp.get("component_type", "unknown"),
                "is_valid": report.is_valid,
                "error_count": report.error_count,
                "warning_count": report.warning_count,
                "errors": [e.to_dict() for e in report.errors],
                "warnings": [w.to_dict() for w in report.warnings]
            })

        # 2. Validate full_html if present
        if "full_html" in payload and payload["full_html"]:
            doc_report = self.validate_document(payload["full_html"])
            if not doc_report.is_valid:
                results["all_valid"] = False
            results["document_report"] = doc_report.to_dict()

        return results
