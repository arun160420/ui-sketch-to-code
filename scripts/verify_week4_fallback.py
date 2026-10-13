"""
Verification and demonstration script for Week 4: LLaVA-v1.6-7B Fallback Integration.
Demonstrates intelligent model routing, fallback execution, and schema enforcement.
"""

import os
import sys
import json

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.preprocess import WireframePreprocessor
from src.model_router import ModelRouter, RoutingStrategy
from src.schema import validate_ui_payload

def main():
    print("=" * 70)
    print("  Week 4: LLaVA-v1.6-7B Fallback Integration & Routing Verification")
    print("=" * 70)

    router = ModelRouter()

    # 1. System Health Check
    health = router.get_system_health()
    print("\n[1] System Diagnostics & Health Status:")
    print(f"    - Routing Strategy: {health['routing_strategy']}")
    print(f"    - Primary (GPT-4o-mini): {'Available' if health['gpt_4o_mini']['available'] else 'Unavailable / Key Missing'}")
    print(f"      * Status Details: {health['gpt_4o_mini']['status']}")
    print(f"      * Masked Key: {health['gpt_4o_mini']['masked_key']}")
    print(f"    - Fallback (LLaVA Local): {'Server Ready' if health['llava_local']['available'] else 'Server Offline / Standby'}")
    print(f"      * Endpoint: {health['llava_local']['endpoint']}")
    print(f"      * Target Model: {health['llava_local']['model']}")
    print(f"      * Status Details: {health['llava_local']['status']}")

    # 2. Wireframe Pre-Processing (CV Module)
    sample_img = "tests/sample_wireframe.png"
    if not os.path.exists(sample_img):
        from tests.generate_samples import create_synthetic_wireframe
        create_synthetic_wireframe(sample_img)

    print("\n[2] Pre-processing Wireframe Geometry:")
    preprocessor = WireframePreprocessor()
    wireframe_result = preprocessor.process(sample_img)
    print(f"    - Canvas Resolution: {wireframe_result['original_shape']}")
    print(f"    - Components Extracted: {wireframe_result['total_components']}")

    # 3. Model Routing & Fallback Execution
    print("\n[3] Executing Model Router (Strategy: AUTO):")
    output = router.generate(wireframe_result)

    ui_data = output["data"]
    metadata = output["metadata"]

    print(f"    - Fallback Triggered: {metadata['fallback_triggered']}")
    if metadata['fallback_triggered']:
        print(f"    - Fallback Reason: {metadata['fallback_reason']}")
    print(f"    - Model Employed: {metadata['model_used']}")
    print(f"    - Provider: {metadata['provider']}")
    print(f"    - Execution Latency: {metadata['execution_time_seconds']}s")

    # 4. JSON Schema Validation
    print("\n[4] Validating Response Schema:")
    validate_ui_payload(ui_data)
    print("    [OK] Output conforms 100% to strict UI_COMPONENT_JSON_SCHEMA!")
    print(f"    - Page Title: {ui_data['page_title']}")
    print(f"    - Layout Type: {ui_data['layout_type']}")
    print(f"    - Structured Components: {len(ui_data['components'])}")

    # 5. Save Artifacts for Week 4
    out_dir = "output/week4"
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, "index.html")
    css_path = os.path.join(out_dir, "styles.css")
    json_path = os.path.join(out_dir, "payload.json")
    meta_path = os.path.join(out_dir, "routing_metadata.json")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(ui_data["full_html"])
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(ui_data["full_css"])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ui_data, f, indent=2)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\n[5] Week 4 Deliverable Artifacts Saved:")
    print(f"    - HTML File: {html_path}")
    print(f"    - CSS File: {css_path}")
    print(f"    - JSON Payload: {json_path}")
    print(f"    - Routing Metadata: {meta_path}")

    print("\n" + "=" * 70)
    print("  Week 4: LLaVA-v1.6-7B Fallback Integration Verified Successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
