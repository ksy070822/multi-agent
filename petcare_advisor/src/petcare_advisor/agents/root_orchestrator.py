"""Root Orchestrator Agent - Controls the entire triage pipeline following TRD rules."""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel

from ..shared.types import GraphState
from ..tools.report_builder import build_final_report
from .symptom_intake_agent import symptom_intake_tool
from .vision_agent import vision_analysis_tool
from .medical_agent import medical_analysis_tool
from .triage_agent import triage_agent_tool
from .careplan_agent import careplan_agent_tool

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# -----------------------------------------------------
# Root Agent Prompt (TRD-style)
# -----------------------------------------------------

ROOT_ORCHESTRATOR_SYSTEM_PROMPT = """
You are the Root Orchestrator Agent for a veterinary triage system called PetCare Advisor.

MANDATORY RULES (TRD):
1. You MUST call exactly ONE tool per response.
2. NEVER call two tools at the same time.
3. Tool calls MUST follow the exact pipeline sequence:
    (1) symptom intake agent
    (2) vision agent (only if image context exists)
    (3) medical agent
    (4) triage agent
    (5) careplan agent
    (6) final report builder
4. You NEVER perform medical reasoning yourself.
5. All medical reasoning MUST be delegated to sub-agents.
6. Always read existing GraphState using SAFE mode.
7. After finishing all steps, return a JSON response:
       { "status": "complete", "report": <final_report_json> }
8. Log all decisions using DEBUG notes.
"""


# -----------------------------------------------------
# Root Orchestrator Agent Function
# -----------------------------------------------------

def root_orchestrator(state: GraphState, user_input: str) -> Dict[str, Any]:
    """
    High-level dispatcher controlled by FastAPI or LangGraph.
    Reads GraphState and decides which agent to call next.
    Follows TRD rules: ONE tool call per step, sequential execution.
    
    Args:
        state: Current GraphState
        user_input: User's symptom description
        
    Returns:
        Dictionary with status and updated state or final report
    """
    # Step 0 — Safe extraction of existing state
    safe_state = state.model_dump(exclude_none=True)
    
    # ------------------------------
    # STEP 1: SYMPTOM INTAKE
    # ------------------------------
    if state.symptom_data is None:
        logger.info("[DEBUG] Step 1: Calling Symptom Intake Agent")
        print("[DEBUG] Step 1: Calling Symptom Intake Agent")
        
        try:
            result = symptom_intake_tool.invoke({"user_input": user_input})
            logger.info(f"[DEBUG] Symptom Intake completed: {len(result.get('structured_data', {}).get('main_symptoms', []))} symptoms found")
            return {
                "status": "in_progress",
                "step": "symptom_intake",
                "symptom_data": result,
            }
        except Exception as e:
            logger.error(f"[ERROR] Symptom Intake failed: {e}")
            raise
    
    # ------------------------------
    # STEP 2: VISION (optional)
    # ------------------------------
    if state.vision_data is None and safe_state.get("image_refs"):
        logger.info("[DEBUG] Step 2: Vision context detected → Calling Vision Agent")
        print("[DEBUG] Step 2: Vision context detected → Calling Vision Agent")
        
        try:
            result = vision_analysis_tool.invoke({
                "symptom_data": state.symptom_data,
                "image_refs": safe_state.get("image_refs", [])
            })
            logger.info(f"[DEBUG] Vision Analysis completed: {result.get('structured_data', {}).get('has_images', False)}")
            return {
                "status": "in_progress",
                "step": "vision_analysis",
                "vision_data": result,
            }
        except Exception as e:
            logger.error(f"[ERROR] Vision Analysis failed: {e}")
            raise
    
    # ------------------------------
    # STEP 3: MEDICAL AGENT
    # ------------------------------
    if state.medical_data is None:
        logger.info("[DEBUG] Step 3: Calling Medical Agent")
        print("[DEBUG] Step 3: Calling Medical Agent")
        
        try:
            result = medical_analysis_tool.invoke({
                "symptom_data": state.symptom_data,
                "vision_data": state.vision_data
            })
            logger.info(f"[DEBUG] Medical Analysis completed: {len(result.get('structured_data', {}).get('differential_diagnosis', []))} diagnoses")
            return {
                "status": "in_progress",
                "step": "medical_analysis",
                "medical_data": result,
            }
        except Exception as e:
            logger.error(f"[ERROR] Medical Analysis failed: {e}")
            raise
    
    # ------------------------------
    # STEP 4: TRIAGE AGENT
    # ------------------------------
    if state.triage_data is None:
        logger.info("[DEBUG] Step 4: Calling Triage Agent")
        print("[DEBUG] Step 4: Calling Triage Agent")
        
        try:
            result = triage_agent_tool.invoke({
                "symptom_data": state.symptom_data,
                "medical_data": state.medical_data
            })
            logger.info(f"[DEBUG] Triage completed: Level={result.get('structured_data', {}).get('triage_level')}, Score={result.get('structured_data', {}).get('urgency_score')}")
            return {
                "status": "in_progress",
                "step": "triage",
                "triage_data": result,
            }
        except Exception as e:
            logger.error(f"[ERROR] Triage failed: {e}")
            raise
    
    # ------------------------------
    # STEP 5: CAREPLAN AGENT
    # ------------------------------
    if state.careplan_data is None:
        logger.info("[DEBUG] Step 5: Calling Careplan Agent")
        print("[DEBUG] Step 5: Calling Careplan Agent")
        
        try:
            result = careplan_agent_tool.invoke({
                "symptom_data": state.symptom_data,
                "medical_data": state.medical_data,
                "triage_data": state.triage_data
            })
            logger.info(f"[DEBUG] Careplan completed: {len(result.get('structured_data', {}).get('home_care_instructions', []))} instructions")
            return {
                "status": "in_progress",
                "step": "careplan",
                "careplan_data": result,
            }
        except Exception as e:
            logger.error(f"[ERROR] Careplan failed: {e}")
            raise
    
    # ------------------------------
    # STEP 6: FINAL REPORT
    # ------------------------------
    if state.final_report is None:
        logger.info("[DEBUG] Step 6: Building final report")
        print("[DEBUG] Step 6: Building final report")
        
        try:
            report = build_final_report(
                symptom=state.symptom_data,
                vision=state.vision_data,
                medical=state.medical_data,
                triage=state.triage_data,
                careplan=state.careplan_data
            )
            logger.info("[DEBUG] Final report built successfully")
            return {
                "status": "complete",
                "report": report
            }
        except Exception as e:
            logger.error(f"[ERROR] Report building failed: {e}")
            raise
    
    # Fallback - all steps complete
    logger.info("[DEBUG] All steps completed, returning final report")
    return {
        "status": "complete",
        "report": state.final_report
    }
