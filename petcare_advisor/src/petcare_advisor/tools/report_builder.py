"""Report Builder Tool - Assembles final triage report from all agent results."""

import logging
from typing import Dict, Any, Optional
from ..shared.utils import get_iso_datetime

logger = logging.getLogger(__name__)


def build_final_report(
    symptom: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
    medical: Dict[str, Any],
    triage: Dict[str, Any],
    careplan: Dict[str, Any],
) -> Dict[str, Any]:
    """Assemble final triage report JSON from all agent results.
    
    Args:
        symptom: Symptom intake result
        vision: Optional vision analysis result
        medical: Medical analysis result
        triage: Triage assessment result
        careplan: Care plan result
        
    Returns:
        Final triage report dictionary
    """
    logger.info("[REPORT_BUILDER] Assembling final report")
    
    # Extract structured data
    symptom_data = symptom.get("structured_data", {})
    vision_data = vision.get("structured_data", {}) if vision else {}
    medical_data = medical.get("structured_data", {})
    triage_data = triage.get("structured_data", {})
    careplan_data = careplan.get("structured_data", {})
    
    # Build patient information
    patient_info = {
        "species": symptom_data.get("species"),
        "breed": symptom_data.get("breed"),
        "age": symptom_data.get("age"),
        "sex": symptom_data.get("sex"),
        "weight": symptom_data.get("weight"),
    }
    
    # Build summary
    summary = {
        "main_symptoms": symptom_data.get("main_symptoms", []),
        "onset_time": symptom_data.get("onset_time"),
        "duration": symptom_data.get("duration"),
        "severity_perception": symptom_data.get("severity_perception"),
    }
    
    # Build final report
    report = {
        "meta": {
            "version": "v1",
            "generated_at": get_iso_datetime(),
        },
        "patient": patient_info,
        "summary": summary,
        "triage": {
            "urgency_score": triage_data.get("urgency_score", 0),
            "triage_level": triage_data.get("triage_level", "INFO"),
            "justification": triage_data.get("justification", ""),
            "risk_assessment": triage_data.get("risk_assessment", ""),
            "time_sensitivity": triage_data.get("time_sensitivity"),
        },
        "differential_diagnosis": medical_data.get("differential_diagnosis", []),
        "care_plan": {
            "home_care_instructions": careplan_data.get("home_care_instructions", []),
            "things_to_avoid": careplan_data.get("things_to_avoid", []),
            "when_to_see_vet": careplan_data.get("when_to_see_vet", ""),
            "emergency_indicators": careplan_data.get("emergency_indicators", []),
            "monitoring_guidance": careplan_data.get("monitoring_guidance", []),
            "supportive_message": careplan_data.get("supportive_message", ""),
        },
        "red_flags": symptom_data.get("red_flags", []),
    }
    
    # Add vision analysis if available
    if vision_data.get("has_images"):
        report["vision_analysis"] = {
            "visual_findings": vision_data.get("visual_findings", []),
            "wound_detected": vision_data.get("wound_detected", False),
            "swelling_detected": vision_data.get("swelling_detected", False),
            "skin_issues_detected": vision_data.get("skin_issues_detected", False),
            "eye_issues_detected": vision_data.get("eye_issues_detected", False),
        }
    
    logger.info("[REPORT_BUILDER] Final report assembled successfully")
    
    return report
