"""
Component-Specific Code Generation Logic for Week 5.
Defines specialized prompt engineering for the five deterministic UI components:
1. Navigation Bars
2. Login/Signup Forms
3. Hero Sections
4. Content Cards
5. Form Input Fields

Generates modern, accessible semantic HTML5 with utility-first Tailwind CSS.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import json

class UIComponentCategory(str, Enum):
    NAVBAR = "navbar"
    AUTH_FORM = "form"
    HERO = "hero"
    CARD = "card"
    INPUT = "input"

# ==============================================================================
# 1. Specialized Component Prompt Templates
# ==============================================================================

PROMPT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    UIComponentCategory.NAVBAR.value: {
        "name": "Navigation Bar",
        "description": "Responsive top-level navigation with logo, links, mobile menu, and action buttons.",
        "requirements": [
            "Use semantic <nav> tag with role='navigation' and aria-label='Main Navigation'.",
            "Flexbox layout (flex items-center justify-between px-6 py-4 bg-white/90 backdrop-blur border-b border-gray-200).",
            "Include brand logo/title on the left with font-bold text-xl.",
            "Desktop navigation links (hidden md:flex gap-8 text-sm font-medium text-gray-700 hover:text-indigo-600).",
            "Right-aligned Call-to-Action button (px-4 py-2 bg-indigo-600 text-white rounded-lg shadow-sm hover:bg-indigo-700).",
            "Mobile hamburger button placeholder (md:hidden p-2 text-gray-600)."
        ],
        "default_html": (
            '<nav role="navigation" aria-label="Main Navigation" '
            'class="w-full flex items-center justify-between px-6 py-4 bg-white/95 backdrop-blur border-b border-gray-200 sticky top-0 z-50">\n'
            '  <div class="flex items-center gap-3">\n'
            '    <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white font-black text-lg shadow-md">S</div>\n'
            '    <span class="text-xl font-bold tracking-tight text-gray-900">SketchUI</span>\n'
            '  </div>\n'
            '  <div class="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">\n'
            '    <a href="#" class="text-indigo-600 font-semibold transition-colors">Home</a>\n'
            '    <a href="#features" class="hover:text-indigo-600 transition-colors">Features</a>\n'
            '    <a href="#pricing" class="hover:text-indigo-600 transition-colors">Pricing</a>\n'
            '    <a href="#docs" class="hover:text-indigo-600 transition-colors">Docs</a>\n'
            '  </div>\n'
            '  <div class="flex items-center gap-3">\n'
            '    <a href="#login" class="hidden sm:inline-flex text-sm font-medium text-gray-700 hover:text-indigo-600 px-3 py-2">Sign in</a>\n'
            '    <a href="#signup" class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-all">Get Started</a>\n'
            '  </div>\n'
            '</nav>'
        ),
        "default_classes": "w-full flex items-center justify-between px-6 py-4 bg-white/95 border-b border-gray-200"
    },

    UIComponentCategory.AUTH_FORM.value: {
        "name": "Login/Signup Form",
        "description": "High-converting, accessible authentication form with input validation styles and social login.",
        "requirements": [
            "Use semantic <form> container with max-w-md w-full mx-auto p-8 bg-white rounded-2xl shadow-xl border border-gray-100.",
            "Header with title (text-2xl font-bold text-gray-900) and subtitle with switch link.",
            "Email and password fields using styled labels and floating focus rings.",
            "Password field with show/hide toggle affordance.",
            "Remember me checkbox and 'Forgot password?' anchor link aligned horizontally.",
            "Full-width submit button (w-full py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700).",
            "Alternative social login divider ('or continue with')."
        ],
        "default_html": (
            '<div class="max-w-md w-full mx-auto p-8 bg-white rounded-2xl shadow-xl border border-gray-100">\n'
            '  <div class="text-center mb-6">\n'
            '    <h2 class="text-2xl font-bold tracking-tight text-gray-900">Welcome Back</h2>\n'
            '    <p class="text-sm text-gray-500 mt-1">Please enter your details to sign in</p>\n'
            '  </div>\n'
            '  <form class="space-y-4" action="#" method="POST">\n'
            '    <div>\n'
            '      <label for="auth-email" class="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">Email Address</label>\n'
            '      <input type="email" id="auth-email" required placeholder="you@company.com" '
            'class="w-full px-4 py-2.5 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition" />\n'
            '    </div>\n'
            '    <div>\n'
            '      <div class="flex items-center justify-between mb-1.5">\n'
            '        <label for="auth-password" class="text-xs font-semibold uppercase tracking-wider text-gray-700">Password</label>\n'
            '        <a href="#forgot" class="text-xs font-medium text-indigo-600 hover:text-indigo-500">Forgot password?</a>\n'
            '      </div>\n'
            '      <input type="password" id="auth-password" required placeholder="••••••••" '
            'class="w-full px-4 py-2.5 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition" />\n'
            '    </div>\n'
            '    <div class="flex items-center">\n'
            '      <input type="checkbox" id="remember" class="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500" />\n'
            '      <label for="remember" class="ml-2 text-xs text-gray-600">Remember me for 30 days</label>\n'
            '    </div>\n'
            '    <button type="submit" class="w-full py-3 px-4 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-md hover:shadow-lg transition-all">Sign In</button>\n'
            '  </form>\n'
            '  <p class="text-center text-xs text-gray-500 mt-6">Don\'t have an account? <a href="#signup" class="text-indigo-600 font-semibold hover:underline">Sign up</a></p>\n'
            '</div>'
        ),
        "default_classes": "max-w-md w-full mx-auto p-8 bg-white rounded-2xl shadow-xl border border-gray-100"
    },

    UIComponentCategory.HERO.value: {
        "name": "Hero Section",
        "description": "High-impact landing hero with announcement badge, bold typography, CTA buttons, and feature preview.",
        "requirements": [
            "Container with relative overflow-hidden py-16 md:py-24 px-6 max-w-6xl mx-auto text-center.",
            "Announcement badge pill (inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-semibold).",
            "Main headline (text-4xl md:text-6xl font-black text-gray-900 tracking-tight).",
            "Supporting lead paragraph (mt-6 text-lg md:text-xl text-gray-600 max-w-2xl mx-auto).",
            "Call to action group with Primary ('Get Started') and Secondary ('Book a Demo') buttons.",
            "Subtle social proof / feature highlight badges."
        ],
        "default_html": (
            '<section class="relative overflow-hidden py-16 md:py-24 px-6 max-w-6xl mx-auto text-center">\n'
            '  <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold mb-6 shadow-sm">\n'
            '    <span class="w-2 h-2 rounded-full bg-indigo-600 animate-pulse"></span>\n'
            '    <span>Announcing v2.0 AI Sketch Parser</span>\n'
            '  </div>\n'
            '  <h1 class="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-gray-900 max-w-4xl mx-auto leading-tight">\n'
            '    Transform Wireframe Sketches into <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-violet-600">Production Code</span>\n'
            '  </h1>\n'
            '  <p class="mt-6 text-lg md:text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">\n'
            '    Accelerate frontend sprints from hours to seconds. Our OpenCV computer vision and multimodal LLM engine converts pencil drawings into clean Tailwind HTML.\n'
            '  </p>\n'
            '  <div class="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">\n'
            '    <a href="#start" class="w-full sm:w-auto px-6 py-3.5 text-base font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-lg hover:shadow-indigo-200 transition-all">Start Converting Free</a>\n'
            '    <a href="#demo" class="w-full sm:w-auto px-6 py-3.5 text-base font-semibold text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-xl transition-all">Watch 2-Min Demo</a>\n'
            '  </div>\n'
            '</section>'
        ),
        "default_classes": "relative overflow-hidden py-16 md:py-24 px-6 max-w-6xl mx-auto text-center"
    },

    UIComponentCategory.CARD.value: {
        "name": "Content Card",
        "description": "Versatile content/feature card with thumbnail placeholder, category badge, title, excerpt, and action.",
        "requirements": [
            "Card container (bg-white rounded-xl shadow-md hover:shadow-xl transition-all border border-gray-100 overflow-hidden flex flex-col).",
            "Image thumbnail area (aspect-video bg-gradient-to-br from-indigo-50 to-slate-100 relative).",
            "Category badge (text-xs font-semibold uppercase tracking-wider text-indigo-600).",
            "Content title (text-lg font-bold text-gray-900 hover:text-indigo-600 transition).",
            "Descriptive excerpt text (text-sm text-gray-500 line-clamp-3 mt-2).",
            "Footer row with author/metric metadata and interactive action link/button."
        ],
        "default_html": (
            '<div class="bg-white rounded-2xl shadow-md hover:shadow-xl transition-all duration-300 border border-gray-100 overflow-hidden flex flex-col max-w-sm">\n'
            '  <div class="aspect-video bg-gradient-to-br from-indigo-500/10 via-purple-500/10 to-pink-500/10 flex items-center justify-center border-b border-gray-100">\n'
            '    <svg class="w-12 h-12 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>\n'
            '  </div>\n'
            '  <div class="p-6 flex-1 flex flex-col justify-between">\n'
            '    <div>\n'
            '      <span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-600 mb-3">Computer Vision</span>\n'
            '      <h3 class="text-lg font-bold text-gray-900 hover:text-indigo-600 transition-colors">OpenCV Contour Extraction</h3>\n'
            '      <p class="text-sm text-gray-500 mt-2 leading-relaxed">Normalizes pixel boundaries into relative spatial coordinates to guide LLM layout generation.</p>\n'
            '    </div>\n'
            '    <div class="mt-6 pt-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">\n'
            '      <span>5 min read</span>\n'
            '      <a href="#" class="font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1">Learn more &rarr;</a>\n'
            '    </div>\n'
            '  </div>\n'
            '</div>'
        ),
        "default_classes": "bg-white rounded-2xl shadow-md hover:shadow-xl transition-all border border-gray-100 overflow-hidden flex flex-col max-w-sm"
    },

    UIComponentCategory.INPUT.value: {
        "name": "Form Input Field",
        "description": "Accessible, reusable input component with label, validation states, helper text, and icons.",
        "requirements": [
            "Wrapper container with flex flex-col gap-1.5 w-full.",
            "Associated <label> with for attribute, clear text, and required indicator.",
            "Input field (w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent).",
            "Placeholder with clear example formatting.",
            "Optional trailing icon or validation status badge.",
            "Sub-text helper hint or error message area."
        ],
        "default_html": (
            '<div class="flex flex-col gap-1.5 w-full max-w-md">\n'
            '  <label for="comp-input-sample" class="text-xs font-semibold uppercase tracking-wider text-gray-700 flex items-center justify-between">\n'
            '    <span>Project Repository URL</span>\n'
            '    <span class="text-gray-400 font-normal lowercase">Required</span>\n'
            '  </label>\n'
            '  <div class="relative rounded-lg shadow-sm">\n'
            '    <input type="text" id="comp-input-sample" required placeholder="https://github.com/username/repo" '
            'class="w-full px-4 py-2.5 text-sm text-gray-900 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition" />\n'
            '  </div>\n'
            '  <p class="text-xs text-gray-500">Provide the public GitHub repository link for automatic analysis.</p>\n'
            '</div>'
        ),
        "default_classes": "flex flex-col gap-1.5 w-full max-w-md"
    }
}

# ==============================================================================
# 2. Component Prompt Builder & Code Generator
# ==============================================================================

class ComponentCodeGenerator:
    """
    Manages prompt construction and code synthesis for the 5 deterministic UI components.
    """

    def __init__(self):
        self.templates = PROMPT_TEMPLATES

    def get_supported_components(self) -> List[str]:
        """Returns list of supported component type keys."""
        return list(self.templates.keys())

    def build_prompt(
        self,
        component_type: str,
        bounding_box: Optional[List[float]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Builds a specialized prompt for generating a specific UI component.
        """
        c_type = component_type.lower()
        if c_type not in self.templates:
            # Fallback to nearest match
            c_type = UIComponentCategory.CARD.value

        spec = self.templates[c_type]
        reqs = "\n".join([f"- {r}" for r in spec["requirements"]])

        prompt = (
            f"You are an expert UI/UX Engineer specialized in Tailwind CSS.\n"
            f"Generate a deterministic, production-grade {spec['name']} component.\n\n"
            f"Component Requirements:\n{reqs}\n\n"
            f"Bounding Box Coordinates: {bounding_box or [0.0, 0.0, 1.0, 0.2]}\n"
            f"Context: {json.dumps(context or {})}\n\n"
            "Generate clean, modern semantic HTML5 and valid Tailwind CSS utility classes. "
            "Output MUST be strictly valid JSON matching the UI schema."
        )
        return prompt

    def generate_component(
        self,
        component_type: str,
        component_id: str = "comp-1",
        bounding_box: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Returns structured component data with semantic HTML and Tailwind CSS classes.
        """
        c_type = component_type.lower()
        if c_type not in self.templates:
            c_type = UIComponentCategory.CARD.value

        spec = self.templates[c_type]
        bbox = bounding_box or [0.0, 0.0, 1.0, 0.2]

        return {
            "component_id": component_id,
            "component_type": c_type,
            "bounding_box": bbox,
            "html": spec["default_html"],
            "css_classes": spec["default_classes"]
        }

    def generate_all_five_components(self) -> List[Dict[str, Any]]:
        """
        Generates deterministic implementations for all 5 Week 5 components.
        """
        components = []
        ordered_types = [
            (UIComponentCategory.NAVBAR.value, "comp-nav", [0.0, 0.0, 1.0, 0.1]),
            (UIComponentCategory.HERO.value, "comp-hero", [0.0, 0.1, 1.0, 0.45]),
            (UIComponentCategory.CARD.value, "comp-card", [0.05, 0.48, 0.45, 0.85]),
            (UIComponentCategory.INPUT.value, "comp-input", [0.52, 0.48, 0.95, 0.6]),
            (UIComponentCategory.AUTH_FORM.value, "comp-form", [0.52, 0.62, 0.95, 0.98])
        ]

        for c_type, c_id, bbox in ordered_types:
            components.append(self.generate_component(c_type, c_id, bbox))

        return components

    def build_showcase_page(self, components: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Compiles components into a complete, modern HTML5 showcase document with Tailwind CDN.
        """
        comps = components or self.generate_all_five_components()
        navbar_html = next((c["html"] for c in comps if c["component_type"] == "navbar"), "")
        hero_html = next((c["html"] for c in comps if c["component_type"] == "hero"), "")
        card_html = next((c["html"] for c in comps if c["component_type"] == "card"), "")
        input_html = next((c["html"] for c in comps if c["component_type"] == "input"), "")
        form_html = next((c["html"] for c in comps if c["component_type"] == "form"), "")

        page = f"""<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-50">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Week 5: Deterministic UI Components Showcase</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
  </style>
</head>
<body class="min-h-full flex flex-col antialiased text-slate-800">

  <!-- 1. Navigation Bar Component -->
  {navbar_html}

  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-16">

    <!-- 2. Hero Section Component -->
    {hero_html}

    <!-- Component Gallery Grid -->
    <section class="border-t border-slate-200 pt-12">
      <div class="text-center mb-10">
        <h2 class="text-2xl font-bold tracking-tight text-slate-900">Deterministic Component Gallery</h2>
        <p class="text-sm text-slate-500 mt-1">Previewing Cards, Form Inputs, and Authentication Forms styled with Tailwind CSS</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-10 items-start">
        
        <!-- Column 1: Content Card & Input Field -->
        <div class="space-y-8 flex flex-col items-center lg:items-end">
          <div class="w-full max-w-sm">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Component #4: Content Card</span>
            {card_html}
          </div>

          <div class="w-full max-w-sm">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Component #5: Form Input Field</span>
            {input_html}
          </div>
        </div>

        <!-- Column 2: Login/Signup Form -->
        <div class="flex flex-col items-center lg:items-start">
          <div class="w-full max-w-md">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Component #2: Authentication Form</span>
            {form_html}
          </div>
        </div>

      </div>
    </section>

  </main>

  <!-- Footer -->
  <footer class="bg-white border-t border-slate-200 py-6 mt-16 text-center text-xs text-slate-400">
    <p>UI Sketch-to-Code Converter &bull; COM71123-7 Week 5 Milestone &bull; MIET Autonomous</p>
  </footer>

</body>
</html>"""
        return page
