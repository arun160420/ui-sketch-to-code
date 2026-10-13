# PowerShell script to generate Microsoft PowerPoint (.pptx) presentation
# Following MIET Autonomous Guidelines for UI Sketch-to-Code Converter

$ErrorActionPreference = "Stop"

$pptApp = New-Object -ComObject PowerPoint.Application
$pptApp.Visible = [Microsoft.Office.Core.MsoTriState]::msoTrue

$presentation = $pptApp.Presentations.Add()

# Apply slide dimension (16:9 Widescreen)
$presentation.PageSetup.SlideWidth = 960
$presentation.PageSetup.SlideHeight = 540

$blue = 0x8B3214       # Navy Blue #14328b (BGR: 0x8b3214)
$darkGray = 0x222222   # Dark text #222222
$lightBg = 0xF8F9FA    # Light background

function Add-HeaderSlide($title, $subtitle) {
    $slide = $presentation.Slides.Add($presentation.Slides.Count + 1, 12) # Blank
    
    # Header Accent bar
    $bar = $slide.Shapes.AddShape(1, 0, 0, 960, 10)
    $bar.Fill.Solid()
    $bar.Fill.ForeColor.RGB = 0x8B3214
    $bar.Line.Visible = [Microsoft.Office.Core.MsoTriState]::msoFalse
    
    # Institution
    $inst = $slide.Shapes.AddTextbox(1, 60, 40, 840, 40)
    $inst.TextFrame.TextRange.Text = "MODEL INSTITUTE OF ENGINEERING AND TECHNOLOGY (AUTONOMOUS)"
    $inst.TextFrame.TextRange.Font.Size = 14
    $inst.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
    $inst.TextFrame.TextRange.Font.Color.RGB = 0x8B3214
    
    # Sub Institute
    $instSub = $slide.Shapes.AddTextbox(1, 60, 70, 840, 30)
    $instSub.TextFrame.TextRange.Text = "Department of Computer Science & Engineering | NAAC 'A' Grade | Session 2026-27"
    $instSub.TextFrame.TextRange.Font.Size = 11
    $instSub.TextFrame.TextRange.Font.Color.RGB = 0x666666
    
    # Title
    $titleBox = $slide.Shapes.AddTextbox(1, 60, 150, 840, 80)
    $titleBox.TextFrame.TextRange.Text = $title
    $titleBox.TextFrame.TextRange.Font.Size = 32
    $titleBox.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
    $titleBox.TextFrame.TextRange.Font.Color.RGB = 0x222222
    
    # Subtitle / Details
    $subBox = $slide.Shapes.AddTextbox(1, 60, 240, 840, 200)
    $subBox.TextFrame.TextRange.Text = $subtitle
    $subBox.TextFrame.TextRange.Font.Size = 14
    $subBox.TextFrame.TextRange.Font.Color.RGB = 0x444444
    return $slide
}

function Add-StandardSlide($slideNumber, $title, $bulletPoints) {
    $slide = $presentation.Slides.Add($presentation.Slides.Count + 1, 12) # Blank
    
    # Top Navy Banner
    $bar = $slide.Shapes.AddShape(1, 0, 0, 960, 8)
    $bar.Fill.Solid()
    $bar.Fill.ForeColor.RGB = 0x8B3214
    $bar.Line.Visible = [Microsoft.Office.Core.MsoTriState]::msoFalse
    
    # Slide Title
    $titleBox = $slide.Shapes.AddTextbox(1, 60, 30, 840, 50)
    $titleBox.TextFrame.TextRange.Text = $title
    $titleBox.TextFrame.TextRange.Font.Size = 24
    $titleBox.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
    $titleBox.TextFrame.TextRange.Font.Color.RGB = 0x8B3214
    
    # Sub-header category
    $sub = $slide.Shapes.AddTextbox(1, 60, 75, 840, 20)
    $sub.TextFrame.TextRange.Text = "UI Sketch-to-Code Converter | COM71123 Milestone Presentation"
    $sub.TextFrame.TextRange.Font.Size = 10
    $sub.TextFrame.TextRange.Font.Color.RGB = 0x888888
    
    # Body Box
    $contentBox = $slide.Shapes.AddTextbox(1, 60, 105, 840, 390)
    $tf = $contentBox.TextFrame
    $tf.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
    
    $fullText = ($bulletPoints -join "`n`n")
    $tf.TextRange.Text = $fullText
    $tf.TextRange.Font.Size = 14
    $tf.TextRange.Font.Color.RGB = 0x333333
    
    # Slide Number Footer
    $footer = $slide.Shapes.AddTextbox(1, 840, 500, 80, 25)
    $footer.TextFrame.TextRange.Text = "$slideNumber / 12"
    $footer.TextFrame.TextRange.Font.Size = 10
    $footer.TextFrame.TextRange.Font.Color.RGB = 0x999999
    
    return $slide
}

Write-Host "Creating Slide 1: Project Title & Team Details..."
Add-HeaderSlide -title "UI Sketch-to-Code Converter" `
  -subtitle "Automated Front-End Code Generation from Hand-Drawn Wireframes using Computer Vision and Vision-Language Models`n`nProject Team:`n• Student Name: Arun Sharma (and Team Members)`n• Course Code: COM71123 | B.Tech CSE (7th Semester)`n• Supervisor / Mentor: Project Evaluation Committee`n• Repository: https://github.com/arun1645/ui-sketch-to-code"

Write-Host "Creating Slide 2: Problem Statement..."
Add-StandardSlide -slideNumber 2 -title "Problem Statement & Relevance" -bulletPoints @(
  "• The Prototyping Bottleneck: Translating paper sketches into web code (HTML/CSS) is an error-prone, manual process that consumes up to 40% of early-stage front-end development sprints.",
  "• Repetitive Boilerplate Burden: Developers repeatedly rewrite standard UI layout components (headers, navbars, cards, inputs, and buttons) from static mockup drawings.",
  "• Physical Sketch Artifacts: Real-world hand drawings suffer from shadows, uneven ambient lighting, faint pencil lines, and varied camera angles.",
  "• Need for the Proposed Solution: An intelligent, automated pipeline that cleans sketch images, extracts normalized UI components, and enforces strict JSON code synthesis."
)

Write-Host "Creating Slide 3: Background & Existing Solutions..."
Add-StandardSlide -slideNumber 3 -title "Background & Existing Solutions" -bulletPoints @(
  "• Traditional OCR & Edge Detection: Tools like Tesseract or standard Canny detectors extract raw text and bounding boxes, but fail completely at understanding semantic UI hierarchy or generating responsive layouts.",
  "• Pure Cloud LLM Direct Prompting: Passing raw sketch photos directly to general-purpose LLMs leads to severe hallucinations, unstructured markdown output, and missed elements under faint lighting.",
  "• Commercial Closed Tools (Uizard / Figma Plugins): Highly proprietary, require expensive recurring subscription costs, and cannot operate in private or offline institutional settings.",
  "• Our Motivation: Build an open-source, hybrid pipeline combining OpenCV contrast normalization with multimodal models (GPT-4o-mini & local LLaVA) governed by strict JSON schemas."
)

Write-Host "Creating Slide 4: Project Objectives & Scope..."
Add-StandardSlide -slideNumber 4 -title "Project Objectives & Scope" -bulletPoints @(
  "• Objective 1 (Image Pre-Processing): Normalize hand-drawn sketches via CLAHE, bilateral filtering, and aspect-ratio preserved canvas padding (800x800).",
  "• Objective 2 (Component Normalization): Detect contours and extract normalized bounding box coordinates [0.0 - 1.0] for layout understanding.",
  "• Objective 3 (Schema-Enforced Generation): Integrate GPT-4o-mini with strict JSON Schema output enforcement for valid HTML5 and CSS.",
  "• Objective 4 (Hybrid Local Fallback): Deploy locally hosted LLaVA-v1.6-7B via Ollama for resilient, zero-cost, offline execution.",
  "• Project Scope: Covers hand-drawn wireframes, multi-component layouts (navbar, forms, cards, buttons), and responsive Flexbox/Grid CSS."
)

Write-Host "Creating Slide 5: Proposed Solution..."
Add-StandardSlide -slideNumber 5 -title "Proposed Solution: Hybrid Vision Pipeline" -bulletPoints @(
  "• Dual-Stage Architecture: Visual geometry extraction is cleanly separated from code synthesis, feeding normalized coordinates rather than raw noisy pixels into the AI.",
  "• Strict JSON Schema Contract: A formal Draft-2020-12 schema strictly validates component IDs, bounding boxes, semantic HTML, and CSS classes before rendering.",
  "• Intelligent Dual-Model Router: Seamlessly balances cloud throughput and local privacy: Primary cloud model (GPT-4o-mini) with automatic failover to local model (LLaVA-v1.6-7B via Ollama).",
  "• Test-Driven Modularity: Built with 100% automated test coverage across vision, schema, and API failover mechanisms."
)

Write-Host "Creating Slide 6: System Architecture / Methodology..."
Add-StandardSlide -slideNumber 6 -title "System Architecture & Methodology" -bulletPoints @(
  "• Stage 1 (OpenCV Vision Core): Grayscale conversion -> CLAHE contrast boost -> Bilateral edge-preserving denoising -> Adaptive Gaussian binarization -> 800x800 aspect padding -> Bounding box normalization.",
  "• Stage 2 (Intelligent Model Router): Performs credential and health checks. Automatically chooses between GPT-4o-mini and local LLaVA-v1.6-7B based on network, key availability, and latency.",
  "• Stage 3 (Schema Validation & Code Synthesis): Validates model output with Pydantic & JSONSchema -> Emits renderable index.html, responsive styles.css, and routing metadata.",
  "• Technology Stack: Python 3.12, OpenCV (cv2), Pytest, OpenAI API, Ollama (LLaVA:7b), Node.js (DOMPurify, html-validate)."
)

Write-Host "Creating Slide 7: Implementation Progress (Weeks 1 to 4)..."
Add-StandardSlide -slideNumber 7 -title "Implementation Progress to Date" -bulletPoints @(
  "• Week 1 (Environment & Gitflow): Initialized Gitflow branching (main, develop, feature/*) on GitHub (arun1645/ui-sketch-to-code). Setup Python .venv, Node.js tools, and Ollama LLaVA:7b model.",
  "• Week 2 (Vision Pre-Processing): Created src/preprocess.py with CLAHE, bilateral denoising, adaptive thresholding, 800x800 canvas standardization, and normalized bounding box extraction.",
  "• Week 3 (GPT-4o-mini Integration): Created src/gpt_client.py and src/schema.py with secure .env key management, strict JSON schema enforcement, and robust API error handling.",
  "• Week 4 (LLaVA Fallback Integration): Created src/ollama_client.py and src/model_router.py for local LLaVA-v1.6-7B REST calls and automatic switching when cloud credentials or network are unavailable."
)

Write-Host "Creating Slide 8: Demonstration / Evidence of Progress..."
Add-StandardSlide -slideNumber 8 -title "Demonstration & Evidence of Progress" -bulletPoints @(
  "• Visual Computer Vision Outputs: Verified contrast-enhanced outputs (enhanced.png, binary.png) and detected UI component bounding boxes (bounding_boxes.png) in tests/sample_outputs/.",
  "• Automated Test Suite Execution: 30 out of 30 unit tests passing (100% success rate in 19s) via Pytest across vision, API, router, and schema enforcement modules.",
  "• Functional Code Generation: Verified end-to-end execution producing renderable HTML prototypes (output/week3/index.html and output/week4/index.html) with responsive styling.",
  "• Repository Verification: Working tree clean, all feature branches merged into develop and pushed to remote origin on GitHub."
)

Write-Host "Creating Slide 9: Plane Progress & Milestone Tracking..."
Add-StandardSlide -slideNumber 9 -title "Plane Progress & Milestone Tracking" -bulletPoints @(
  "• COM71123-3 (Week 1): Setup environments, Git branching strategy, and local Ollama model -> [STATUS: DONE]",
  "• COM71123-4 (Week 2): OpenCV pre-processing, contrast enhancement, bounding box normalization -> [STATUS: DONE]",
  "• COM71123-5 (Week 3): GPT-4o-mini integration with strict JSON schema enforcement -> [STATUS: DONE]",
  "• COM71123-6 (Week 4): LLaVA-v1.6-7B fallback integration and intelligent model router -> [STATUS: DONE]",
  "• COM71123-7 (Week 5): DOMPurify HTML sanitization and automated syntax validation -> [STATUS: IN PROGRESS]",
  "• COM71123-8 (Week 6): Interactive Web Dashboard with Real-Time Live Preview -> [STATUS: PLANNED]"
)

Write-Host "Creating Slide 10: Challenges & Corrective Actions..."
Add-StandardSlide -slideNumber 10 -title "Challenges & Corrective Actions" -bulletPoints @(
  "• Challenge 1 (Geometric Distortion during Resizing): Direct resizing distorted component aspect ratios. Corrective Action: Implemented aspect-ratio preserved scaling with symmetric border padding.",
  "• Challenge 2 (LLM Output Formatting Inconsistency): Standard LLMs hallucinate conversational filler and markdown backticks. Corrective Action: Enforced strict JSON schema validation (Draft-2020-12) via Pydantic.",
  "• Challenge 3 (Commercial API Key Dependency): Cloud APIs incur costs and fail if offline. Corrective Action: Integrated local LLaVA-v1.6-7B via Ollama as an automated zero-cost fallback.",
  "• Challenge 4 (Windows Terminal Git Credentials): Account collision during push. Corrective Action: Automated credential helpers and clean environment variable isolation."
)

Write-Host "Creating Slide 11: Upcoming Milestones & Work Plan..."
Add-StandardSlide -slideNumber 11 -title "Upcoming Milestones & Work Plan" -bulletPoints @(
  "• Week 5 (Code Sanitization & Linting): Connect Node.js DOMPurify and html-validate to strip unsafe tags and verify W3C compliance automatically.",
  "• Week 6 (Interactive Web Application): Build a web interface allowing users to upload a photo of a sketch and view the live rendered page side-by-side with generated code.",
  "• Week 7 (Multi-Layout Benchmarking): Benchmark accuracy across diverse real-world paper wireframes, mobile UI mockups, and complex multi-column grids.",
  "• Week 8 (Final Evaluation & Deployment): Prepare comprehensive technical documentation, packaging, containerization, and final project defense."
)

Write-Host "Creating Slide 12: References & Acknowledgements..."
Add-StandardSlide -slideNumber 12 -title "References & Acknowledgements" -bulletPoints @(
  "• References:`n  1. Bradski, G. 'The OpenCV Library', Dr. Dobb's Journal of Software Tools, 2000.`n  2. Liu, H. et al. 'Visual Instruction Tuning (LLaVA)', NeurIPS 2023.`n  3. OpenAI API Documentation on Structured Outputs and JSON Schema Enforcement, 2024.`n  4. World Wide Web Consortium (W3C) HTML5 & CSS3 Specifications.`n  5. Driessen, V. 'A Successful Git Branching Model', 2010.",
  "• Acknowledgements:`n  We express our sincere thanks to our Project Supervisor and the faculty of the Department of Computer Science & Engineering, Model Institute of Engineering and Technology (MIET), for their continuous guidance, technical feedback, and support."
)

$outPath = "C:\Users\ashar\ui-sketch-to-code\UI_Sketch_to_Code_Presentation.pptx"
$presentation.SaveAs($outPath)
$presentation.Close()
$pptApp.Quit()

Write-Host "`nSUCCESS: Presentation created at: $outPath"
