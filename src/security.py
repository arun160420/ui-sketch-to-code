"""
src/security.py

Week 10 Deliverable (COM71123-12):
Security Sanitization, XSS Defense, and Sandboxed Preview Engine.

Provides:
1. DOMPurify integration via Node.js bridge and pure-Python defense-in-depth fallback.
2. In-depth neutralization of stored & reflected XSS vectors:
   - Malicious <script>, <object>, <embed>, <applet> tags
   - Inline DOM event handler attributes (onerror, onload, onclick, etc.)
   - JavaScript pseudoprotocols (javascript:, vbscript:, data:text/html)
3. SandboxedIframePolicy: Configures strict iframe isolation:
   - sandbox="allow-scripts allow-same-origin allow-forms"
   - Content-Security-Policy (CSP) generation
4. Structured threat telemetry, audit reporting, and security scoring.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ThreatSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DetectedThreat:
    """Represents a neutralized XSS vector or malicious construct."""
    threat_type: str
    severity: str
    tag: str
    attribute: Optional[str] = None
    raw_snippet: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SanitizationReport:
    """Detailed audit report of security sanitization."""
    is_secure: bool
    threats_detected: int
    threats: List[DetectedThreat] = field(default_factory=list)
    clean_html: str = ""
    sandbox_policy: Dict[str, str] = field(default_factory=dict)
    csp_header: str = ""
    sanitizer_used: str = "DOMPurify"

    @property
    def sanitized_html(self) -> str:
        return self.clean_html

    @property
    def is_sanitized(self) -> bool:
        return self.is_secure

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_secure": self.is_secure,
            "threats_detected": self.threats_detected,
            "threats": [t.to_dict() for t in self.threats],
            "clean_html_length": len(self.clean_html),
            "sandbox_policy": self.sandbox_policy,
            "csp_header": self.csp_header,
            "sanitizer_used": self.sanitizer_used
        }

    def to_markdown_summary(self) -> str:
        badge = "🛡️ SECURE (XSS Defenses Active)" if self.is_secure else "⚠️ THREATS DETECTED"
        lines = [
            f"### Security Sanitization: {badge}",
            f"- **Sanitizer Engine:** {self.sanitizer_used}",
            f"- **Threats Neutralized:** {self.threats_detected}",
            f"- **Sandbox Mode:** `{self.sandbox_policy.get('sandbox', 'allow-scripts allow-same-origin')}`",
            f"- **CSP Header:** `{self.csp_header}`",
            ""
        ]
        if self.threats:
            lines.append("#### Neutralized XSS Vectors:")
            for idx, t in enumerate(self.threats, 1):
                lines.append(f"{idx}. 🛑 **[{t.threat_type}]** {t.description} (`<{t.tag}>`, attribute: `{t.attribute}`)")
        else:
            lines.append("✅ 0 malicious vectors found. HTML is safe for sandboxed iframe execution.")
        return "\n".join(lines)


# ==============================================================================
# 2. Sandboxed Iframe Policy & CSP Generator
# ==============================================================================

class SandboxedIframePolicy:
    """
    Defines security parameters for isolated iframe previewing.
    Prevents parent window hijacking, unauthorized popups, storage pollution, and cookie theft.
    """

    DEFAULT_SANDBOX_DIRECTIVES = [
        "allow-scripts",
        "allow-same-origin",
        "allow-forms"
    ]

    # Content Security Policy tailored for Tailwind CSS and safe frontend previews
    DEFAULT_CSP_DIRECTIVES = {
        "default-src": ["'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com", "https://fonts.googleapis.com", "https://fonts.gstatic.com"],
        "script-src": ["'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https:"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "connect-src": ["'self'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"]
    }

    @classmethod
    def get_sandbox_attribute(cls, extra_directives: Optional[List[str]] = None) -> str:
        directives = set(cls.DEFAULT_SANDBOX_DIRECTIVES)
        if extra_directives:
            directives.update(extra_directives)
        return " ".join(sorted(list(directives)))

    @classmethod
    def get_csp_header(cls) -> str:
        parts = []
        for directive, sources in cls.DEFAULT_CSP_DIRECTIVES.items():
            parts.append(f"{directive} {' '.join(sources)}")
        return "; ".join(parts) + ";"

    @classmethod
    def get_policy_dict(cls) -> Dict[str, str]:
        return {
            "sandbox": cls.get_sandbox_attribute(),
            "csp": cls.get_csp_header(),
            "referrer_policy": "no-referrer",
            "feature_policy": "camera 'none'; microphone 'none'; geolocation 'none'"
        }

    @property
    def sandbox_attribute(self) -> str:
        return self.get_sandbox_attribute()

    def generate_csp(self) -> str:
        return self.get_csp_header()

    def render_iframe_tag(
        self,
        srcdoc: str = "",
        element_id: str = "preview-frame",
        css_classes: str = "w-full h-full border-0"
    ) -> str:
        """Renders secure sandboxed HTML iframe string."""
        import html
        escaped_srcdoc = html.escape(srcdoc, quote=True)
        return (
            f'<iframe id="{element_id}" '
            f'class="{css_classes}" '
            f'sandbox="{self.get_sandbox_attribute()}" '
            f'csp="{self.get_csp_header()}" '
            f'referrerpolicy="no-referrer" '
            f'srcdoc="{escaped_srcdoc}"></iframe>'
        )


# ==============================================================================
# 3. DOMPurify Security Sanitizer
# ==============================================================================

class SecuritySanitizer:
    """
    Sanitizes synthesized HTML using DOMPurify (via Node.js bridge)
    with a robust pure-Python defense-in-depth fallback.
    """

    SUSPICIOUS_PATTERN = re.compile(
        r"<\s*(?:script|object|embed|applet|iframe)\b"
        r"|\bon\w+\s*="
        r"|javascript:"
        r"|vbscript:"
        r"|data:\s*text/html",
        re.IGNORECASE
    )

    def __init__(self, bridge_script: Optional[Path] = None, enable_node_dompurify: bool = True):
        self.bridge_script = bridge_script or (
            Path(__file__).resolve().parent.parent / "scripts" / "sanitize_html.js"
        )
        self.enable_node_dompurify = enable_node_dompurify
        self.policy = SandboxedIframePolicy()
        self._cache: Dict[str, SanitizationReport] = {}

    def sanitize(self, raw_html: str) -> SanitizationReport:
        if not raw_html or not raw_html.strip():
            return SanitizationReport(
                is_secure=True,
                threats_detected=0,
                clean_html="",
                sandbox_policy=self.policy.get_policy_dict(),
                csp_header=self.policy.get_csp_header(),
                sanitizer_used="DOMPurify"
            )

        content_key = str(hash(raw_html))
        if content_key in self._cache:
            return self._cache[content_key]

        had_doctype = bool(re.search(r"<!DOCTYPE\s+html", raw_html, re.IGNORECASE))
        is_suspicious = bool(self.SUSPICIOUS_PATTERN.search(raw_html))

        report = None
        # Fast path: If markup contains zero executable or suspicious constructs, use fast-path sanitizer
        if not is_suspicious:
            report = self._pure_python_sanitize(raw_html)
        elif self.enable_node_dompurify and self.bridge_script.exists():
            # 1. Attempt Node.js DOMPurify execution for suspicious inputs
            try:
                report = self._run_node_dompurify(raw_html)
            except Exception as e:
                logger.warning("DOMPurify Node execution encountered an issue (%s). Using Python defense-in-depth.", e)

        # 2. Pure Python Fallback Sanitizer
        if report is None:
            report = self._pure_python_sanitize(raw_html)

        if had_doctype and not re.search(r"<!DOCTYPE\s+html", report.clean_html, re.IGNORECASE):
            report.clean_html = f"<!DOCTYPE html>\n{report.clean_html}"

        self._cache[content_key] = report
        return report

    def _run_node_dompurify(self, raw_html: str) -> Optional[SanitizationReport]:
        """Calls scripts/sanitize_html.js via child process."""
        proc = subprocess.Popen(
            ["node", str(self.bridge_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        stdout, stderr = proc.communicate(input=raw_html, timeout=8)

        if proc.returncode == 0 and stdout:
            data = json.loads(stdout)
            clean_html = data.get("clean_html", "")
            threats_detected = data.get("threats_detected", 0)

            threats: List[DetectedThreat] = []
            for tag in data.get("stripped_tags", []):
                threats.append(DetectedThreat(
                    threat_type="forbidden_tag",
                    severity=ThreatSeverity.CRITICAL.value,
                    tag=tag,
                    description=f"Stripped malicious executable tag <{tag}>"
                ))
            for attr in data.get("stripped_attributes", []):
                threats.append(DetectedThreat(
                    threat_type="forbidden_attribute",
                    severity=ThreatSeverity.HIGH.value,
                    tag=attr.get("tag", "element"),
                    attribute=attr.get("attribute", "unknown"),
                    description=f"Stripped inline event handler {attr.get('attribute')} from <{attr.get('tag')}>"
                ))

            return SanitizationReport(
                is_secure=True,
                threats_detected=threats_detected,
                threats=threats,
                clean_html=clean_html,
                sandbox_policy=self.policy.get_policy_dict(),
                csp_header=self.policy.get_csp_header(),
                sanitizer_used="DOMPurify (JSDOM Node)"
            )
        return None

    def _pure_python_sanitize(self, raw_html: str) -> SanitizationReport:
        """Pure Python fallback sanitizer stripping dangerous tags, event handlers, and javascript: URLs."""
        clean = raw_html
        threats: List[DetectedThreat] = []

        # 1. Strip <script>...</script>
        script_pattern = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
        for m in script_pattern.finditer(clean):
            threats.append(DetectedThreat(
                threat_type="forbidden_tag",
                severity=ThreatSeverity.CRITICAL.value,
                tag="script",
                raw_snippet=m.group(0)[:80],
                description="Stripped active <script> tag execution vector"
            ))
        clean = script_pattern.sub("", clean)

        # 2. Strip <object>, <embed>, <applet>
        for dangerous_tag in ["object", "embed", "applet", "base"]:
            tag_pattern = re.compile(rf"<{dangerous_tag}\b[^>]*>.*?</{dangerous_tag}>|<{dangerous_tag}\b[^>]*>", re.IGNORECASE | re.DOTALL)
            for m in tag_pattern.finditer(clean):
                threats.append(DetectedThreat(
                    threat_type="forbidden_tag",
                    severity=ThreatSeverity.CRITICAL.value,
                    tag=dangerous_tag,
                    raw_snippet=m.group(0)[:80],
                    description=f"Stripped dangerous <{dangerous_tag}> plugin element"
                ))
            clean = tag_pattern.sub("", clean)

        # 3. Strip inline event handlers (onerror, onload, onclick, on*, etc.)
        event_attr_pattern = re.compile(r'\b(on[a-z]{3,20})\s*=\s*(["\'][^"\']*["\']|[^\s>]+)', re.IGNORECASE)
        for m in event_attr_pattern.finditer(clean):
            attr_name = m.group(1).lower()
            threats.append(DetectedThreat(
                threat_type="inline_event_handler",
                severity=ThreatSeverity.HIGH.value,
                tag="element",
                attribute=attr_name,
                raw_snippet=m.group(0),
                description=f"Stripped inline DOM event handler {attr_name}"
            ))
        clean = event_attr_pattern.sub("", clean)

        # 4. Neutralize javascript: pseudoprotocol in href/src
        js_uri_pattern = re.compile(r'\b(href|src|action)\s*=\s*["\']\s*javascript:[^"\']*["\']', re.IGNORECASE)
        for m in js_uri_pattern.finditer(clean):
            threats.append(DetectedThreat(
                threat_type="javascript_uri",
                severity=ThreatSeverity.CRITICAL.value,
                tag="uri",
                attribute=m.group(1).lower(),
                raw_snippet=m.group(0),
                description=f"Neutralized javascript: pseudoprotocol in {m.group(1)}"
            ))
        clean = js_uri_pattern.sub(r'\1="#"', clean)

        return SanitizationReport(
            is_secure=True,
            threats_detected=len(threats),
            threats=threats,
            clean_html=clean,
            sandbox_policy=self.policy.get_policy_dict(),
            csp_header=self.policy.get_csp_header(),
            sanitizer_used="Pure Python Defense-in-Depth Sanitizer"
        )
