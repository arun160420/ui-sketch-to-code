"""
Verification script for Week 5: Component-Specific Code Generation Logic.
Generates and validates the five deterministic UI components:
1. Navigation Bars
2. Login/Signup Forms
3. Hero Sections
4. Content Cards
5. Form Input Fields
Compiles the full showcase page with Tailwind CSS into output/week5/index.html.
"""

import os
import sys
import json

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.component_prompts import ComponentCodeGenerator, UIComponentCategory
from src.schema import validate_ui_payload

def main():
    print("=" * 70)
    print("  Week 5: Component-Specific Code Generation Logic (Tailwind CSS)")
    print("=" * 70)

    generator = ComponentCodeGenerator()
    supported = generator.get_supported_components()

    print(f"\n[1] Supported Deterministic UI Components ({len(supported)}):")
    for idx, c_type in enumerate(supported, 1):
        spec = generator.templates[c_type]
        print(f"    {idx}. {spec['name']} ('{c_type}') - {len(spec['requirements'])} prompt design rules")

    print("\n[2] Generating and Validating Prompts for Each Component:")
    for c_type in supported:
        spec = generator.templates[c_type]
        prompt = generator.build_prompt(c_type, bounding_box=[0.0, 0.0, 1.0, 0.15])
        print(f"\n    [+] Prompt Template for {spec['name'].upper()}:")
        print(f"        - Target Component: {spec['name']}")
        print(f"        - Prompt Length: {len(prompt)} characters")
        print(f"        - First requirement: {spec['requirements'][0]}")

    print("\n[3] Synthesizing Component Code (HTML5 + Tailwind CSS):")
    components = generator.generate_all_five_components()
    for comp in components:
        print(f"    - [{comp['component_type'].upper()}] ID: {comp['component_id']}")
        print(f"      * Classes: {comp['css_classes'][:60]}...")
        print(f"      * HTML Snippet: {len(comp['html'])} chars")

    # Validate against strict UI schema
    mock_payload = {
        "page_title": "Week 5 Deterministic UI Components Showcase",
        "layout_type": "flexbox",
        "components": [
            {
                "component_id": c["component_id"],
                "component_type": c["component_type"],
                "bounding_box": c["bounding_box"],
                "html": c["html"],
                "css_classes": c["css_classes"]
            }
            for c in components
        ],
        "full_html": generator.build_showcase_page(components),
        "full_css": "/* Powered by Tailwind CSS CDN */"
    }

    validate_ui_payload(mock_payload)
    print("\n[4] Schema Validation Check:")
    print("    [OK] All 5 components conform 100% to strict UI_COMPONENT_JSON_SCHEMA!")

    # Save deliverables
    out_dir = "output/week5"
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, "index.html")
    json_path = os.path.join(out_dir, "components.json")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(mock_payload["full_html"])

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(mock_payload, f, indent=2)

    print(f"\n[5] Week 5 Deliverable Artifacts Generated:")
    print(f"    - Renderable HTML Page: {html_path}")
    print(f"    - Component Payload JSON: {json_path}")

    print("\n" + "=" * 70)
    print("  Week 5: Component-Specific Code Generation Logic Verified!")
    print("=" * 70)

if __name__ == "__main__":
    main()
