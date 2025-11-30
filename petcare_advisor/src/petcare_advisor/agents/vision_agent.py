"""Vision Agent - Analyzes images/video for visual cues using GPT-4o Vision."""

import json
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from ..config import get_settings
from ..shared.constants import OUTPUT_KEY_VISION_ANALYSIS

logger = logging.getLogger(__name__)
settings = get_settings()


class VisionAnalysisInput(BaseModel):
    """Input schema for vision analysis tool."""
    symptom_data: Optional[Dict[str, Any]] = Field(None, description="Structured symptom data from symptom intake")
    image_refs: List[str] = Field(..., description="List of image URLs to analyze")


def _vision_analysis_function(
    symptom_data: Optional[Dict[str, Any]],
    image_refs: List[str],
) -> Dict[str, Any]:
    """Analyze images/video for visual cues related to pet health.
    
    This agent analyzes:
    - Wounds, swelling, skin/eye issues
    - Posture and visible distress
    - Any visual indicators of health problems
    
    Args:
        symptom_data: Optional structured symptom data for context
        image_refs: List of image URLs to analyze
        
    Returns:
        Dictionary with output_key "vision_analysis_result" containing visual analysis data
    """
    logger.info(f"[VISION_ANALYSIS] Analyzing {len(image_refs)} image(s)")
    
    if not image_refs:
        logger.warning("[VISION_ANALYSIS] No images provided")
        return {
            "output_key": OUTPUT_KEY_VISION_ANALYSIS,
            "structured_data": {
                "has_images": False,
                "visual_findings": [],
                "confidence": None,
            }
        }
    
    # Initialize GPT-4o Vision model
    llm = ChatOpenAI(
        model="gpt-4o",
        openai_api_key=settings.openai_api_key,
        temperature=0.2,
    )
    
    # Build context from symptom data (한글)
    symptom_context = ""
    species = "알 수 없음"
    if symptom_data:
        symptom_structured = symptom_data.get("structured_data", {})
        symptoms = symptom_structured.get("main_symptoms", [])
        species = symptom_structured.get("species", "알 수 없음")
        if symptoms:
            symptom_context = f"반려동물 증상: {', '.join(symptoms)}"
    
    # System prompt for vision analysis (병원 컨셉 - 검사실 분석관)
    system_prompt = f"""당신은 동물병원의 [검사실 분석관]입니다. 보호자가 제공한 사진, 영상, 기록을 바탕으로 차분하고 분석적인 설명을 제공합니다.

**중요**: 현재 환자는 **{species}**입니다. 이미지 분석 시 반드시 {species}에 특화된 특징을 고려하세요. 다른 종의 일반적인 특징을 적용하지 마세요.

말투 지침:
- 차분하고 분석적인 설명을 제공합니다
- 가능성을 말할 때는 단정 표현을 피하고 "의심됩니다", "가능성이 있습니다" 같은 표현을 사용합니다
- 보호자가 불안하지 않도록 과한 표현은 피합니다
- 객관적이고 정확한 관찰 결과를 전달합니다

반려동물 이미지를 분석하여 시각적 건강 지표를 찾으세요.

찾아야 할 것들:
- 상처, 절개, 찰과상
- 부종 또는 염증
- 피부 문제 (발진, 병변, 변색)
- 안구 문제 (분비물, 충혈, 혼탁)
- 자세 이상
- 시각적 고통 징후
- 기타 시각적 건강 지표

모든 텍스트는 반드시 한글로 작성하세요.

다음 형식의 유효한 JSON만 반환하세요:
{
    "has_images": true,
    "image_count": 숫자,
    "visual_findings": ["발견1", "발견2", ...],
    "wound_detected": 불린값,
    "swelling_detected": 불린값,
    "skin_issues_detected": 불린값,
    "eye_issues_detected": 불린값,
    "posture_abnormalities": 불린값,
    "visible_distress": 불린값,
    "confidence": 숫자 (0-1),
    "detailed_observations": "상세 관찰 내용 (한글로 작성)"
}"""
    
    try:
        # Prepare image messages
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": f"{system_prompt}\n\n{symptom_context}"},
                    *[{"type": "image_url", "image_url": {"url": url}} for url in image_refs]
                ]
            )
        ]
        
        # Call LLM
        response = llm.invoke(messages)
        content = response.content
        
        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        structured_data = json.loads(content)
        structured_data["image_urls"] = image_refs
        
        logger.info(f"[VISION_ANALYSIS] Analysis complete: {len(structured_data.get('visual_findings', []))} findings")
        
        result = {
            "output_key": OUTPUT_KEY_VISION_ANALYSIS,
            "structured_data": structured_data,
        }
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"[VISION_ANALYSIS] JSON parsing error: {e}")
        return {
            "output_key": OUTPUT_KEY_VISION_ANALYSIS,
            "structured_data": {
                "has_images": True,
                "image_count": len(image_refs),
                "image_urls": image_refs,
                "visual_findings": [],
                "wound_detected": False,
                "swelling_detected": False,
                "skin_issues_detected": False,
                "eye_issues_detected": False,
                "posture_abnormalities": False,
                "visible_distress": False,
                "confidence": None,
            }
        }
    except Exception as e:
        logger.error(f"[VISION_ANALYSIS] Error: {e}")
        raise


# Create LangChain tool
vision_analysis_tool = StructuredTool.from_function(
    func=_vision_analysis_function,
    name="vision_analysis_agent",
    description="Analyze pet images for visual health indicators. Use this after symptom intake if images are available.",
    args_schema=VisionAnalysisInput,
)
