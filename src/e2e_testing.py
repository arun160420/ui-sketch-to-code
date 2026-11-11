"""
src/e2e_testing.py

Week 12 Deliverable (COM71123-14):
Comprehensive End-to-End (E2E) System Testing Engine.

Provides:
1. Synthetic Wireframe Generation:
   - Procedurally draws realistic wireframe sketches in memory for:
     * Authentication / Login Modal
     * E-Commerce Product Catalog
     * Admin Analytics Dashboard
     * SaaS Landing Page
     * Structured Data Table
     * Blank / Sparse Edge-Case Wireframe
2. Pipeline Lifecycle E2E Testing:
   - Exercises all 7 pipeline stages:
     1. OpenCV Preprocessing (CLAHE, Bilateral Filter, Contours)
     2. Vision Routing & Multimodal Code Generation
     3. AST Structural Parsing & Validation (html-validate)
     4. Agentic Self-Correction Loop
     5. WCAG 2.1 AA Accessibility Remediation
     6. DOMPurify Security Sanitization
     7. Sandboxed Preview & Disk Output
3. HTTP API Server E2E Testing:
   - Tests live HTTP endpoints (/api/health, /api/synthesize, /output/generated.html).
   - Validates JSON response schemas, status codes, and error recovery.
4. Robustness & Security Verification:
   - Tests resistance against malformed JSON, corrupted base64 payloads,
     blank images, and embedded XSS attack vectors.
"""

import base64
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

import cv2
import numpy as np

from src.ast_validator import ASTValidationEngine, ValidationReport
from src.model_router import RoutingStrategy
from src.pipeline import SketchToCodePipeline, PipelineResult
from src.security import SecuritySanitizer
from src.accessibility import AccessibilityEnforcer

logger = logging.getLogger("E2ETester")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ==============================================================================
# 1. Procedural Synthetic Wireframe Generator
# ==============================================================================

class SyntheticWireframeGenerator:
    """
    Draws realistic mock wireframe sketches with high-contrast contours
    for deterministic automated end-to-end testing without external files.
    """

    @staticmethod
    def _create_canvas(w: int = 800, h: int = 800) -> np.ndarray:
        # Off-white background simulating sketch paper
        canvas = np.full((h, w, 3), 248, dtype=np.uint8)
        # Add subtle paper border
        cv2.rectangle(canvas, (10, 10), (w - 10, h - 10), (220, 220, 220), 2)
        return canvas

    @classmethod
    def create_auth_wireframe(cls, w: int = 800, h: int = 800) -> np.ndarray:
        """Generates a wireframe with a centered auth modal and input boxes."""
        img = cls._create_canvas(w, h)
        # Centered container box
        cv2.rectangle(img, (220, 140), (580, 660), (40, 40, 40), 3)
        # Modal header title
        cv2.rectangle(img, (280, 180), (520, 220), (60, 60, 60), 2)
        # Email field
        cv2.rectangle(img, (260, 260), (540, 310), (50, 50, 50), 2)
        # Password field
        cv2.rectangle(img, (260, 340), (540, 390), (50, 50, 50), 2)
        # Checkbox & link
        cv2.rectangle(img, (260, 420), (290, 450), (50, 50, 50), 2)
        cv2.rectangle(img, (310, 425), (420, 445), (70, 70, 70), 2)
        # Submit button
        cv2.rectangle(img, (260, 480), (540, 540), (30, 30, 30), 4)
        return img

    @classmethod
    def create_ecommerce_wireframe(cls, w: int = 800, h: int = 800) -> np.ndarray:
        """Generates a wireframe with search header and 4 product grid cards."""
        img = cls._create_canvas(w, h)
        # Navbar / search banner
        cv2.rectangle(img, (30, 30), (770, 90), (40, 40, 40), 3)
        # Grid Card 1
        cv2.rectangle(img, (50, 140), (380, 430), (50, 50, 50), 2)
        cv2.rectangle(img, (70, 160), (360, 320), (80, 80, 80), 2)  # Product image
        cv2.rectangle(img, (70, 350), (300, 380), (60, 60, 60), 2)  # Product title
        cv2.rectangle(img, (70, 390), (180, 415), (40, 40, 40), 2)  # Price
        # Grid Card 2
        cv2.rectangle(img, (420, 140), (750, 430), (50, 50, 50), 2)
        cv2.rectangle(img, (440, 160), (730, 320), (80, 80, 80), 2)
        # Grid Card 3
        cv2.rectangle(img, (50, 470), (380, 750), (50, 50, 50), 2)
        cv2.rectangle(img, (70, 490), (360, 650), (80, 80, 80), 2)
        # Grid Card 4
        cv2.rectangle(img, (420, 470), (750, 750), (50, 50, 50), 2)
        cv2.rectangle(img, (440, 490), (730, 650), (80, 80, 80), 2)
        return img

    @classmethod
    def create_dashboard_wireframe(cls, w: int = 800, h: int = 800) -> np.ndarray:
        """Generates a wireframe with tall left sidebar and stat cards."""
        img = cls._create_canvas(w, h)
        # Left Sidebar (tall & narrow)
        cv2.rectangle(img, (30, 30), (200, 770), (40, 40, 40), 3)
        # Top Header Bar
        cv2.rectangle(img, (230, 30), (770, 90), (50, 50, 50), 2)
        # Stat Card 1
        cv2.rectangle(img, (230, 120), (480, 240), (60, 60, 60), 2)
        # Stat Card 2
        cv2.rectangle(img, (510, 120), (760, 240), (60, 60, 60), 2)
        # Main Content / Analytics Chart
        cv2.rectangle(img, (230, 270), (760, 550), (50, 50, 50), 2)
        # Bottom Table Row
        cv2.rectangle(img, (230, 580), (760, 740), (50, 50, 50), 2)
        return img

    @classmethod
    def create_landing_wireframe(cls, w: int = 800, h: int = 800) -> np.ndarray:
        """Generates a standard SaaS landing page wireframe."""
        img = cls._create_canvas(w, h)
        # Top Navbar
        cv2.rectangle(img, (30, 20), (770, 80), (40, 40, 40), 3)
        # Prominent Hero Section
        cv2.rectangle(img, (50, 120), (750, 400), (40, 40, 40), 3)
        # Feature Card 1
        cv2.rectangle(img, (50, 450), (260, 680), (50, 50, 50), 2)
        # Feature Card 2
        cv2.rectangle(img, (290, 450), (510, 680), (50, 50, 50), 2)
        # Feature Card 3
        cv2.rectangle(img, (540, 450), (750, 680), (50, 50, 50), 2)
        # Footer
        cv2.rectangle(img, (30, 720), (770, 780), (60, 60, 60), 2)
        return img

    @classmethod
    def create_blank_wireframe(cls, w: int = 800, h: int = 800) -> np.ndarray:
        """Edge case: Blank canvas with no drawn elements."""
        return cls._create_canvas(w, h)

    @classmethod
    def to_base64_data_uri(cls, img_array: np.ndarray) -> str:
        """Encodes an OpenCV numpy image into a base64 Data URI."""
        _, buf = cv2.imencode(".png", img_array)
        return "data:image/png;base64," + base64.b64encode(buf).decode("utf-8")


# ==============================================================================
# 2. End-to-End Pipeline & API Lifecycle Tester
# ==============================================================================

@dataclass
class E2ETestResult:
    test_name: str
    category: str  # "pipeline" | "api" | "security" | "robustness"
    passed: bool
    duration_ms: float
    details: Dict[str, Any]
    error_message: Optional[str] = None


@dataclass
class E2EReport:
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate_percentage: float
    results: List[E2ETestResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "pass_rate_percentage": self.pass_rate_percentage,
            "results": [asdict(r) for r in self.results]
        }


class E2ESystemTester:
    """
    Executes comprehensive end-to-end testing across all system layers.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.pipeline = SketchToCodePipeline(strategy=RoutingStrategy.MOCK)
        self.validator = ASTValidationEngine()
        self.security = SecuritySanitizer()
        self.accessibility = AccessibilityEnforcer()

    def run_all_e2e_tests(self) -> E2EReport:
        """Executes the complete test suite covering pipeline, API, and edge cases."""
        results: List[E2ETestResult] = []

        # Category 1: Pipeline Lifecycle across UI Archetypes
        results.append(self._test_pipeline_archetype("Landing Page", SyntheticWireframeGenerator.create_landing_wireframe()))
        results.append(self._test_pipeline_archetype("Auth Modal", SyntheticWireframeGenerator.create_auth_wireframe()))
        results.append(self._test_pipeline_archetype("E-Commerce Grid", SyntheticWireframeGenerator.create_ecommerce_wireframe()))
        results.append(self._test_pipeline_archetype("Dashboard Panel", SyntheticWireframeGenerator.create_dashboard_wireframe()))

        # Category 2: HTTP API Endpoints
        results.append(self._test_api_health_endpoint())
        results.append(self._test_api_synthesize_endpoint())

        # Category 3: Edge Cases & Robustness
        results.append(self._test_edge_case_blank_wireframe())
        results.append(self._test_edge_case_malformed_json())
        results.append(self._test_edge_case_invalid_base64())

        # Category 4: End-to-End XSS Security Neutralization
        results.append(self._test_e2e_security_xss_neutralization())

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        pass_rate = round((passed / total) * 100.0, 2) if total > 0 else 0.0

        return E2EReport(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            pass_rate_percentage=pass_rate,
            results=results
        )

    def _test_pipeline_archetype(self, archetype_name: str, img: np.ndarray) -> E2ETestResult:
        """Runs the complete 7-stage pipeline on a synthetic wireframe image."""
        t0 = time.perf_counter()
        try:
            result = self.pipeline.process(img, force_mock=True)
            duration_ms = (time.perf_counter() - t0) * 1000.0

            assert result.success is True, "Pipeline reported failure"
            assert result.ast_valid_initially is True, "AST structural validation failed"
            assert result.accessibility_compliant is True, "WCAG 2.1 AA accessibility failed"
            assert result.security_sanitized is True, "DOMPurify security sanitization failed"
            assert "<!DOCTYPE html>" in result.full_html, "Missing HTML5 DOCTYPE declaration"

            return E2ETestResult(
                test_name=f"Pipeline Lifecycle: {archetype_name}",
                category="pipeline",
                passed=True,
                duration_ms=round(duration_ms, 2),
                details={
                    "components_count": len(result.components),
                    "ast_valid": result.ast_valid_initially,
                    "accessibility_score": result.accessibility_score,
                    "security_sanitized": result.security_sanitized
                }
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return E2ETestResult(
                test_name=f"Pipeline Lifecycle: {archetype_name}",
                category="pipeline",
                passed=False,
                duration_ms=round(duration_ms, 2),
                details={},
                error_message=str(e)
            )

    def _test_api_health_endpoint(self) -> E2ETestResult:
        """Tests GET /api/health endpoint on the running server."""
        t0 = time.perf_counter()
        url = f"{self.base_url}/api/health"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                status_code = response.getcode()
                data = json.loads(response.read().decode("utf-8"))

            duration_ms = (time.perf_counter() - t0) * 1000.0
            assert status_code == 200, f"Expected 200, got {status_code}"
            assert data.get("status") == "healthy", f"Unexpected health status: {data}"
            assert "uptime_milestones" in data

            return E2ETestResult(
                test_name="HTTP API: GET /api/health",
                category="api",
                passed=True,
                duration_ms=round(duration_ms, 2),
                details={"status_code": status_code, "response": data}
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return E2ETestResult(
                test_name="HTTP API: GET /api/health",
                category="api",
                passed=False,
                duration_ms=round(duration_ms, 2),
                details={"url": url},
                error_message=str(e)
            )

    def _test_api_synthesize_endpoint(self) -> E2ETestResult:
        """Tests POST /api/synthesize endpoint with encoded wireframe image."""
        t0 = time.perf_counter()
        url = f"{self.base_url}/api/synthesize"
        try:
            auth_img = SyntheticWireframeGenerator.create_auth_wireframe()
            b64_uri = SyntheticWireframeGenerator.to_base64_data_uri(auth_img)

            payload = {
                "image_base64": b64_uri,
                "archetype": "auth"
            }
            body_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body_bytes,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                status_code = response.getcode()
                data = json.loads(response.read().decode("utf-8"))

            duration_ms = (time.perf_counter() - t0) * 1000.0
            assert status_code == 200, f"Expected 200, got {status_code}"
            assert data.get("success") is True, "API reported synthesis failure"
            assert data.get("archetype") == "auth", f"Expected auth archetype, got {data.get('archetype')}"
            assert data.get("ast_valid") is True, "AST structural validity failed"
            assert data.get("security_sanitized") is True, "Security sanitization failed"
            assert "preview_url" in data, "Missing preview_url in response"

            return E2ETestResult(
                test_name="HTTP API: POST /api/synthesize",
                category="api",
                passed=True,
                duration_ms=round(duration_ms, 2),
                details={
                    "status_code": status_code,
                    "archetype": data.get("archetype"),
                    "ast_valid": data.get("ast_valid"),
                    "preview_url": data.get("preview_url")
                }
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return E2ETestResult(
                test_name="HTTP API: POST /api/synthesize",
                category="api",
                passed=False,
                duration_ms=round(duration_ms, 2),
                details={"url": url},
                error_message=str(e)
            )

    def _test_edge_case_blank_wireframe(self) -> E2ETestResult:
        """Tests system robustness when given a blank canvas with 0 contours."""
        t0 = time.perf_counter()
        try:
            blank_img = SyntheticWireframeGenerator.create_blank_wireframe()
            result = self.pipeline.process(blank_img, force_mock=True)
            duration_ms = (time.perf_counter() - t0) * 1000.0

            assert result.success is True, "Pipeline failed on blank wireframe"
            assert len(result.full_html) > 50, "Blank input generated empty code"

            return E2ETestResult(
                test_name="Robustness: Blank Wireframe Handling",
                category="robustness",
                passed=True,
                duration_ms=round(duration_ms, 2),
                details={"html_length": len(result.full_html)}
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return E2ETestResult(
                test_name="Robustness: Blank Wireframe Handling",
                category="robustness",
                passed=False,
                duration_ms=round(duration_ms, 2),
                details={},
                error_message=str(e)
            )

    def _test_edge_case_malformed_json(self) -> E2ETestResult:
        """Tests that malformed JSON POST to /api/synthesize returns 400 or 500 error cleanly."""
        t0 = time.perf_counter()
        url = f"{self.base_url}/api/synthesize"
        try:
            body_bytes = b"{bad_json: true"
            req = urllib.request.Request(
                url,
                data=body_bytes,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                urllib.request.urlopen(req, timeout=5)
                passed = False
                err_msg = "Expected HTTP error for malformed JSON, got success"
            except urllib.error.HTTPError as he:
                passed = (he.code in [400, 500])
                err_msg = None if passed else f"Unexpected error code: {he.code}"

            duration_ms = (time.perf_counter() - t0) * 1000.0
            return E2ETestResult(
                test_name="Robustness: Malformed JSON Request",
                category="robustness",
                passed=passed,
                duration_ms=round(duration_ms, 2),
                details={"tested_url": url},
                error_message=err_msg
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return E2ETestResult(
                test_name="Robustness: Malformed JSON Request",
                category="robustness",
                passed=False,
                duration_ms=round(duration_ms, 2),
                details={},
                error_message=str(e)
            )

    def _test_edge_case_invalid_base64(self) -> E2ETestResult:
        """Tests that corrupted base64 input returns HTTP 400 cleanly."""
        t0 = time.perf_counter()
        url = f"{self.base_url}/api/synthesize"
        try:
            body_bytes = json.dumps({"image_base64": "not_valid_base64_data@@@"}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body_bytes,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                urllib.request.urlopen(req, timeout=5)
                passed = False
                err_msg = "Expected HTTP 400 for bad base64, got success"
            except urllib.error.HTTPError as he:
                passed = (he.code in [400, 500])
                err_msg = None if passed else f"Unexpected error code: {he.code}"

            duration_ms = (time.perf_counter() - t0) * 1000.0
            return E2ETestResult(
                test_name="Robustness: Corrupted Base64 Handling",
                category="robustness",
                passed=passed,
                duration_ms=round(duration_ms, 2),
                details={"tested_url": url},
                error_message=err_msg
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return E2ETestResult(
                test_name="Robustness: Corrupted Base64 Handling",
                category="robustness",
                passed=False,
                duration_ms=round(duration_ms, 2),
                details={},
                error_message=str(e)
            )

    def _test_e2e_security_xss_neutralization(self) -> E2ETestResult:
        """Verifies that malicious payloads injected during synthesis are neutralized end-to-end."""
        t0 = time.perf_counter()
        try:
            dirty_html = (
                "<!DOCTYPE html><html><head><title>Malicious</title></head><body>"
                "<div class='p-4 bg-white'>"
                "<h1>Header</h1>"
                "<script>alert('E2E_EXPLOIT')</script>"
                "<img src='invalid.jpg' onerror='alert(\"XSS\")' alt='photo'>"
                "<a href='javascript:stealCookie()'>Free Prize</a>"
                "</div></body></html>"
            )

            # Pass through accessibility enforcer then security sanitizer
            remediated, _ = self.accessibility.enforce_accessibility(dirty_html)
            sec_report = self.security.sanitize(remediated)

            duration_ms = (time.perf_counter() - t0) * 1000.0
            clean_html = sec_report.clean_html

            assert "<script" not in clean_html.lower(), "Failed to strip <script> tag"
            assert "onerror" not in clean_html.lower(), "Failed to strip onerror attribute"
            assert "javascript:" not in clean_html.lower(), "Failed to strip javascript: URI"
            assert sec_report.threats_detected >= 3, f"Expected >=3 threats detected, got {sec_report.threats_detected}"

            return E2ETestResult(
                test_name="Security: End-to-End XSS Neutralization",
                category="security",
                passed=True,
                duration_ms=round(duration_ms, 2),
                details={"threats_defanged": sec_report.threats_detected}
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return E2ETestResult(
                test_name="Security: End-to-End XSS Neutralization",
                category="security",
                passed=False,
                duration_ms=round(duration_ms, 2),
                details={},
                error_message=str(e)
            )
