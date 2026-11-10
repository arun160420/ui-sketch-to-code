"""
src/pipeline.py

End-to-End Sketch-to-Code Generation Pipeline (Week 8: COM71123-10).
Integrates:
1. OpenCV Image Preprocessing (CLAHE, bilateral filter, bounding box normalization).
2. Vision Model Router (GPT-4o-mini cloud primary + local LLaVA-v1.6-7B fallback).
3. AST Validation Engine (html-validate structural parsing).
4. Self-Correction Engine (reflection-guided iterative repair & convergence monitoring).
"""

import logging
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np

from src.preprocess import WireframePreprocessor
from src.model_router import ModelRouter, RoutingStrategy
from src.ast_validator import ASTValidationEngine, ValidationReport
from src.self_correction import (
    SelfCorrectionEngine,
    SelfCorrectionResult,
    ConvergenceState,
    SelfCorrectionPromptEngine
)

logger = logging.getLogger("SketchToCodePipeline")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@dataclass
class PipelineResult:
    """Comprehensive outcome of the end-to-end Sketch-to-Code pipeline."""
    success: bool
    page_title: str
    layout_type: str
    components: List[Dict[str, Any]]
    full_html: str
    full_css: str
    preprocessed_boxes: int
    model_provider: str
    model_used: str
    ast_valid_initially: bool
    self_correction_applied: bool
    convergence_state: str
    total_cycles: int
    final_error_count: int
    total_execution_time_seconds: float
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SketchToCodePipeline:
    """
    Master pipeline unifying wireframe preprocessing, multimodal code generation,
    AST structural validation, and self-correcting agentic refinement loops.
    """

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        preprocessor: Optional[WireframePreprocessor] = None,
        validator: Optional[ASTValidationEngine] = None,
        self_corrector: Optional[SelfCorrectionEngine] = None,
        strategy: Optional[RoutingStrategy] = None
    ):
        self.router = router or ModelRouter(strategy=strategy or RoutingStrategy.AUTO)
        self.preprocessor = preprocessor or WireframePreprocessor()
        self.validator = validator or ASTValidationEngine()
        self.self_corrector = self_corrector or SelfCorrectionEngine(validator_engine=self.validator)

    def process(
        self,
        input_source: Union[str, np.ndarray, Dict[str, Any]],
        image_base64: Optional[str] = None,
        force_mock: bool = False
    ) -> PipelineResult:
        """
        Executes the entire generation, validation, and self-correction lifecycle.
        
        Args:
            input_source: Path to wireframe image, numpy image array, or pre-extracted wireframe_data dict.
            image_base64: Optional base64 encoded image string for multimodal prompting.
            force_mock: If True, executes offline deterministic mock generation.
        """
        pipeline_start = time.time()
        logger.info("Starting Sketch-to-Code generation pipeline...")

        # Step 1: Preprocess Wireframe
        if isinstance(input_source, dict) and "normalized_boxes" in input_source:
            wireframe_data = input_source
            detected_box_count = len(wireframe_data.get("normalized_boxes", []))
        else:
            logger.info("Executing OpenCV wireframe preprocessing...")
            wireframe_data = self.preprocessor.process_pipeline(input_source)
            detected_box_count = wireframe_data.get("total_components", 0)

        # Step 2: Vision Model Code Generation via ModelRouter
        logger.info(f"Generating UI code using routing strategy: {self.router.strategy.value}...")
        generation_result = self.router.generate(
            wireframe_data=wireframe_data,
            image_base64=image_base64,
            force_mock=force_mock
        )
        payload = generation_result.get("data", {})
        metadata = generation_result.get("metadata", {})

        # Step 3: AST Validation Assessment
        logger.info("Performing AST structural validation on generated components...")
        full_html = payload.get("full_html", "")
        initial_report = self.validator.validate_document(full_html)
        ast_valid_initially = initial_report.is_valid

        # Step 4: Self-Correction Loop (if validation fails)
        self_correction_applied = False
        convergence_state = ConvergenceState.CONVERGED.value
        total_cycles = 0
        final_error_count = initial_report.error_count
        correction_metrics = {}

        if not ast_valid_initially:
            logger.info(f"Initial AST validation failed with {initial_report.error_count} error(s). Triggering Self-Correction Engine...")
            self_correction_applied = True
            correction_res = self.self_corrector.self_correct_payload(payload)

            payload = correction_res.final_code
            convergence_state = correction_res.convergence_state.value
            total_cycles = correction_res.total_cycles
            final_error_count = correction_res.final_errors
            correction_metrics = correction_res.metrics
        else:
            logger.info("Generated code passed AST validation on initial attempt. Bypassing refinement loop.")

        total_duration = time.time() - pipeline_start

        return PipelineResult(
            success=(final_error_count == 0),
            page_title=payload.get("page_title", "Generated UI Prototype"),
            layout_type=payload.get("layout_type", "flexbox"),
            components=payload.get("components", []),
            full_html=payload.get("full_html", ""),
            full_css=payload.get("full_css", ""),
            preprocessed_boxes=detected_box_count,
            model_provider=metadata.get("provider", "unknown"),
            model_used=metadata.get("model_used", "unknown"),
            ast_valid_initially=ast_valid_initially,
            self_correction_applied=self_correction_applied,
            convergence_state=convergence_state,
            total_cycles=total_cycles,
            final_error_count=final_error_count,
            total_execution_time_seconds=round(total_duration, 4),
            telemetry={
                "generation_metadata": metadata,
                "correction_metrics": correction_metrics
            }
        )
