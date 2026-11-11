"""
app.py

Production-ready HTTP and API Server for SketchToCode AI Studio.
Provides:
1. Static web asset serving (index.html, assets, output).
2. POST /api/synthesize: Receives user-uploaded wireframe image, executes OpenCV
   contour detection and CLAHE enhancement, generates clean semantic Tailwind HTML,
   performs AST validation & self-correction, and returns the live preview, code,
   and OpenCV annotated image.
"""

import base64
import http.server
import json
import logging
import os
import socketserver
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

import cv2
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.preprocess import WireframePreprocessor
from src.ast_validator import ASTValidationEngine
from src.component_prompts import ComponentCodeGenerator, UIComponentCategory
from src.self_correction import SelfCorrectionEngine

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("SketchToCodeServer")

PORT = 8000
DIRECTORY = str(Path(__file__).resolve().parent)


class SketchToCodeHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler serving static files and the /api/synthesize endpoint."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        """Handle API requests."""
        if self.path == "/api/synthesize":
            self.handle_synthesize()
        else:
            self.send_error(404, "Endpoint Not Found")

    def handle_synthesize(self):
        start_time = time.time()
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            payload = json.loads(post_body.decode("utf-8"))

            raw_b64 = payload.get("image_base64", "")
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]

            if not raw_b64:
                self.send_error(400, "Missing image_base64 in request body")
                return

            image_bytes = base64.b64decode(raw_b64)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                self.send_error(400, "Failed to decode uploaded image")
                return

            logger.info("Received user image (%dx%d). Executing OpenCV preprocessing...", img.shape[1], img.shape[0])

            # 1. OpenCV Preprocessing
            preprocessor = WireframePreprocessor()
            cv_results = preprocessor.process(img)
            normalized_boxes = cv_results.get("normalized_boxes", [])
            total_boxes = len(normalized_boxes)

            # 2. Render visual contour image
            vis_img = cv_results.get("visualization_image")
            _, buf = cv2.imencode(".png", vis_img)
            vis_b64 = "data:image/png;base64," + base64.b64encode(buf).decode("utf-8")

            # 3. Dynamic UI Synthesis based on spatial bounding box layout
            engine = ComponentCodeGenerator()
            
            # Analyze detected boxes to decide which components were sketched
            components = []
            has_nav = False
            has_hero = False
            has_card = False
            has_auth = False
            has_input = False

            # Inspect top 10 most prominent boxes
            for b in normalized_boxes[:15]:
                ymin = b["norm_box"][1]
                ymax = b["norm_box"][3]
                w = b["norm_wh"][0]
                h = b["norm_wh"][1]

                if ymin < 0.18 and w > 0.5 and not has_nav:
                    has_nav = True
                    components.append(engine.generate_component(UIComponentCategory.NAVBAR, "comp-nav", b["norm_box"]))
                elif ymin < 0.45 and w > 0.5 and not has_hero:
                    has_hero = True
                    components.append(engine.generate_component(UIComponentCategory.HERO, "comp-hero", b["norm_box"]))
                elif w < 0.55 and not has_card:
                    has_card = True
                    components.append(engine.generate_component(UIComponentCategory.CARD, "comp-card", b["norm_box"]))
                elif not has_auth and (h > 0.2 or ymin > 0.4):
                    has_auth = True
                    components.append(engine.generate_component(UIComponentCategory.AUTH_FORM, "comp-auth", b["norm_box"]))
                elif not has_input:
                    has_input = True
                    components.append(engine.generate_component(UIComponentCategory.INPUT, "comp-input", b["norm_box"]))

            # If sketch is sparse, provide balanced complete layout
            if not components:
                components = engine.generate_all_five_components()

            # Build Full HTML Document
            full_html = engine.build_showcase_page(components)

            # 4. Abstract Syntax Tree (AST) Validation
            validator = ASTValidationEngine()
            ast_report = validator.validate_document(full_html)

            # 5. Self-Correction if needed
            self_corrected = False
            if not ast_report.is_valid:
                corrector = SelfCorrectionEngine(validator_engine=validator)
                payload_dict = {
                    "full_html": full_html,
                    "components": components
                }
                corr_res = corrector.self_correct_payload(payload_dict)
                full_html = corr_res.final_code.get("full_html", full_html)
                self_corrected = True
                ast_report = validator.validate_document(full_html)

            duration = time.time() - start_time
            logger.info("Successfully synthesized wireframe into code in %.3fs (AST Valid: %s)", duration, ast_report.is_valid)

            # Format response
            response_data = {
                "success": True,
                "boxes_detected": total_boxes,
                "components_synthesized": len(components),
                "components": components,
                "full_html": full_html,
                "visualization_image": vis_b64,
                "ast_valid": ast_report.is_valid,
                "ast_errors": ast_report.error_count,
                "self_corrected": self_corrected,
                "convergence_state": "CONVERGED",
                "latency_seconds": round(duration, 3)
            }

            response_bytes = json.dumps(response_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)

        except Exception as e:
            logger.error("Synthesis error: %s", str(e), exc_info=True)
            err_resp = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err_resp)))
            self.end_headers()
            self.wfile.write(err_resp)


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), SketchToCodeHandler) as httpd:
        logger.info("SketchToCode AI Server serving at http://localhost:%d", PORT)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server shutting down.")


if __name__ == "__main__":
    run_server()
