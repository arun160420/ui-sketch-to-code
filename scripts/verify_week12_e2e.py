"""
scripts/verify_week12_e2e.py

Verification script for Week 12 Deliverable (COM71123-14):
End-to-End (E2E) System Testing of the Complete System.

Executes:
1. Full 7-stage pipeline testing across 4 layout archetypes (Landing, Auth, E-commerce, Dashboard).
2. Live HTTP API endpoint verification (/api/health, /api/synthesize).
3. Robustness edge-case verification (blank wireframe, corrupted base64, malformed JSON).
4. End-to-end security penetration test against stored and reflected XSS vectors.
Exports:
- output/week12/e2e_report.json
- output/week12/index.html (Interactive E2E System Dashboard)
"""

from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time

# Ensure repository root is in python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.e2e_testing import E2ESystemTester, SyntheticWireframeGenerator


def run_week12_e2e_verification():
    print("=" * 70)
    print("  Week 12 Verification: End-to-End Testing of the Complete System")
    print("  Course Milestone: COM71123-14")
    print("=" * 70)

    output_dir = REPO_ROOT / "output" / "week12"
    output_dir.mkdir(parents=True, exist_ok=True)

    tester = E2ESystemTester(base_url="http://localhost:8000")

    print("\n[Executing E2E Test Suite across all 4 system categories]...")
    report = tester.run_all_e2e_tests()

    print(f"\n  - Total E2E Tests Executed: {report.total_tests}")
    print(f"  - Tests Passed:             {report.passed_tests}")
    print(f"  - Tests Failed:             {report.failed_tests}")
    print(f"  - System Pass Rate:         {report.pass_rate_percentage}%\n")

    for idx, res in enumerate(report.results, 1):
        status_icon = "✓ PASS" if res.passed else "✗ FAIL"
        print(f"  [{status_icon}] {idx:2d}. {res.test_name:<44s} ({res.duration_ms:6.2f} ms)")
        if not res.passed and res.error_message:
            print(f"         Error: {res.error_message}")

    assert report.failed_tests == 0, f"{report.failed_tests} E2E tests failed!"

    # Save JSON report
    json_path = output_dir / "e2e_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)
    print(f"\n[OK] JSON E2E Audit Report saved to: {json_path}")

    # Generate interactive HTML dashboard
    results_cards = []
    for r in report.results:
        badge_color = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" if r.passed else "bg-rose-500/10 text-rose-400 border-rose-500/20"
        status_text = "PASSED" if r.passed else "FAILED"
        details_json = json.dumps(r.details, indent=2)

        results_cards.append(f"""
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-lg">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="w-2.5 h-2.5 rounded-full {'bg-emerald-500' if r.passed else 'bg-rose-500'}"></span>
              <h3 class="font-bold text-slate-100 text-sm">{r.test_name}</h3>
              <span class="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono capitalize">{r.category}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-xs font-mono text-slate-400">{r.duration_ms:.2f} ms</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full border font-bold {badge_color}">{status_text}</span>
            </div>
          </div>
          <pre class="mt-3 p-3 rounded-xl bg-slate-950 text-slate-400 text-xs font-mono overflow-x-auto border border-slate-800/60">{details_json}</pre>
        </div>
        """)

    html_dashboard = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Week 12: End-to-End System Testing & Release Audit</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Inter', sans-serif; }}
    code, pre {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
  <!-- Milestone Navigation Bar -->
  <div class="bg-slate-900 border-b border-slate-800 px-6 py-2.5 text-xs flex items-center justify-between">
    <div class="flex items-center gap-2">
      <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
      <span class="font-semibold text-slate-300">COM71123-14</span>
      <span class="text-slate-500">|</span>
      <span class="text-slate-400">Week 12: End-to-End System Testing</span>
    </div>
    <div class="flex items-center gap-4 text-slate-400">
      <a href="http://localhost:8000" class="hover:text-indigo-400 transition-colors">← Main Studio</a>
      <a href="http://localhost:8000/output/week11/index.html" class="hover:text-indigo-400 transition-colors">Week 11 (Perf)</a>
      <a href="http://localhost:8000/output/week10/index.html" class="hover:text-indigo-400 transition-colors">Week 10 (Security)</a>
      <a href="http://localhost:8000/output/week9/index.html" class="hover:text-indigo-400 transition-colors">Week 9 (WCAG)</a>
    </div>
  </div>

  <div class="max-w-6xl mx-auto px-6 py-8">
    <!-- Header -->
    <div class="flex items-center justify-between pb-6 border-b border-slate-800">
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
          <span>🚀 End-to-End System Testing</span>
          <span class="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">100% PRODUCTION READY</span>
        </h1>
        <p class="text-sm text-slate-400 mt-1">Full-stack integration verification spanning OpenCV Preprocessing, AI Synthesis, AST Validation, WCAG Accessibility, and DOMPurify Security.</p>
      </div>
      <div class="text-right text-xs text-slate-400">
        <div>Audit Executed: <span class="text-slate-200 font-mono">{report.timestamp}</span></div>
        <div class="mt-0.5">Test Pass Rate: <span class="text-emerald-400 font-bold">{report.pass_rate_percentage}%</span></div>
      </div>
    </div>

    <!-- Overview Scorecards -->
    <div class="grid grid-cols-1 sm:grid-cols-4 gap-5 my-8">
      <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
        <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Tests</span>
        <div class="text-3xl font-extrabold text-white mt-1">{report.total_tests}</div>
        <div class="text-xs text-slate-500 mt-1">Across 4 testing suites</div>
      </div>
      <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
        <span class="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Passed Tests</span>
        <div class="text-3xl font-extrabold text-emerald-400 mt-1">{report.passed_tests}</div>
        <div class="text-xs text-emerald-500/80 mt-1">100% success rate</div>
      </div>
      <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
        <span class="text-xs font-semibold text-rose-400 uppercase tracking-wider">Failed Tests</span>
        <div class="text-3xl font-extrabold text-slate-100 mt-1">{report.failed_tests}</div>
        <div class="text-xs text-slate-500 mt-1">0 regressions detected</div>
      </div>
      <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
        <span class="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Production Status</span>
        <div class="text-3xl font-extrabold text-indigo-400 mt-1">VERIFIED</div>
        <div class="text-xs text-indigo-300/80 mt-1">Deployment Ready</div>
      </div>
    </div>

    <!-- Test Results Feed -->
    <div class="space-y-4 mb-8">
      {"".join(results_cards)}
    </div>

    <!-- Pipeline Architecture Matrix -->
    <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
      <h2 class="text-lg font-bold text-white mb-4">Complete 7-Stage System Pipeline Verification</h2>
      <div class="grid grid-cols-1 md:grid-cols-7 gap-3 text-center text-xs">
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="font-bold text-indigo-400">Step 1</div>
          <div class="font-semibold text-white mt-1">OpenCV</div>
          <div class="text-[10px] text-slate-400 mt-0.5">Contour Extraction</div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="font-bold text-indigo-400">Step 2</div>
          <div class="font-semibold text-white mt-1">Vision AI</div>
          <div class="text-[10px] text-slate-400 mt-0.5">Multimodal Synthesis</div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="font-bold text-indigo-400">Step 3</div>
          <div class="font-semibold text-white mt-1">AST Engine</div>
          <div class="text-[10px] text-slate-400 mt-0.5">HTML Structural Tree</div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="font-bold text-indigo-400">Step 4</div>
          <div class="font-semibold text-white mt-1">Refinement</div>
          <div class="text-[10px] text-slate-400 mt-0.5">Self-Correction Loop</div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="font-bold text-indigo-400">Step 5</div>
          <div class="font-semibold text-white mt-1">WCAG 2.1 AA</div>
          <div class="text-[10px] text-slate-400 mt-0.5">Semantic Enforcement</div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="font-bold text-indigo-400">Step 6</div>
          <div class="font-semibold text-white mt-1">DOMPurify</div>
          <div class="text-[10px] text-slate-400 mt-0.5">Security Sanitizer</div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
          <div class="font-bold text-indigo-400">Step 7</div>
          <div class="font-semibold text-white mt-1">Sandboxed</div>
          <div class="text-[10px] text-slate-400 mt-0.5">Monaco / Iframe</div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

    html_path = output_dir / "index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_dashboard)
    print(f"[OK] Interactive HTML E2E Dashboard saved to: {html_path}")

    print("\n  Week 12 E2E Verification Complete: Complete System Tested Successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_week12_e2e_verification()
