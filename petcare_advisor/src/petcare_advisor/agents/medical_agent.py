"""Medical Agent - Performs medical analysis based on symptoms and vision data using OpenAI GPT-4o-mini."""

import json
import logging
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from ..config import get_settings
from ..shared.constants import OUTPUT_KEY_MEDICAL_ANALYSIS

logger = logging.getLogger(__name__)
settings = get_settings()


class MedicalAnalysisInput(BaseModel):
    """Input schema for medical analysis tool."""
    symptom_data: Dict[str, Any] = Field(..., description="Structured symptom data from symptom intake")
    vision_data: Optional[Dict[str, Any]] = Field(None, description="Optional vision analysis data")


def _medical_analysis_function(
    symptom_data: Dict[str, Any],
    vision_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Perform medical analysis using structured symptom and vision data.
    
    This agent produces:
    - Differential diagnosis candidates list
    - Risk factors (age, breed, chronic disease, etc.)
    - Additional questions that would be useful
    - Additional tests/exams recommended in a clinic
    - Confidence or certainty indicator
    
    Args:
        symptom_data: Structured symptom data
        vision_data: Optional vision analysis data
        
    Returns:
        Dictionary with output_key "medical_analysis_result" containing medical analysis
    """
    logger.info("[MEDICAL_ANALYSIS] Starting medical analysis")
    
    # Initialize OpenAI GPT-4o-mini model
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.openai_api_key,
        temperature=0.1,
    )
    
    # Extract relevant data
    symptom_structured = symptom_data.get("structured_data", {})
    vision_structured = vision_data.get("structured_data", {}) if vision_data else {}
    
    # Build context (한글)
    context_parts = []
    context_parts.append(f"종: {symptom_structured.get('species', '알 수 없음')}")
    context_parts.append(f"품종: {symptom_structured.get('breed', '알 수 없음')}")
    context_parts.append(f"나이: {symptom_structured.get('age', '알 수 없음')}세")
    context_parts.append(f"주요 증상: {', '.join(symptom_structured.get('main_symptoms', []))}")
    context_parts.append(f"지속 기간: {symptom_structured.get('duration', '알 수 없음')}")
    context_parts.append(f"심각도: {symptom_structured.get('severity_perception', '알 수 없음')}")
    
    if vision_structured.get("has_images"):
        context_parts.append(f"시각적 발견: {', '.join(vision_structured.get('visual_findings', []))}")
    
    context = "\n".join(context_parts)
    
    # 종 정보 추출
    species = symptom_structured.get('species', '알 수 없음')
    
    # System prompt for medical analysis (병원 컨셉 - 주치의)
    # JSON 예시의 중괄호를 이스케이프하기 위해 f-string과 일반 문자열을 분리
    system_prompt_base = f"""당신은 반려동물의 [주치의 수의사]입니다. 접수 도우미와 간호사가 정리한 증상 정보를 바탕으로 전문적인 의학적 분석을 수행합니다.

**중요**: 현재 환자는 **{species}**입니다. 모든 진단, 분석, 권장사항은 반드시 {species}에 특화된 내용이어야 합니다. 다른 종(예: 개, 고양이)에 대한 일반적인 정보를 제공하지 마세요.

말투 지침:
- 전문적이면서도 보호자가 이해하기 쉽게 설명합니다
- 전문 용어는 사용할 수 있지만 반드시 쉬운 말로 해석해줍니다
- 지나친 공포 유발은 피하고, 필요한 경고는 정확히 전달합니다
- 가능한 원인들을 체계적으로 분석하고, 각 원인에 대한 가능성을 명확히 제시합니다

제공할 내용:
- 감별진단 후보 목록 (가능성 순서대로 정렬된 가능한 질환 목록)
- 위험 요인 (나이, 품종, 만성 질환 등)
- 진단을 좁히는 데 도움이 되는 추가 질문들
- 병원 방문 시 권장 검사/진찰 항목
- 분석에 대한 신뢰도 (0-1)

모든 텍스트는 반드시 한글로 작성하세요.

다음 형식의 유효한 JSON만 반환하세요:"""
    
    json_example = """
{
    "differential_diagnosis": [
        {"condition": "질환명", "likelihood": "높음|보통|낮음", "reasoning": "이유 설명"},
        ...
    ],
    "risk_factors": ["위험요인1", "위험요인2", ...],
    "additional_questions": ["질문1", "질문2", ...],
    "recommended_tests": ["검사1", "검사2", ...],
    "recommended_exams": ["진찰1", "진찰2", ...],
    "confidence": 숫자 (0-1),
    "certainty_level": "높음|보통|낮음",
    "notes": "추가 메모"
}"""
    
    system_prompt = system_prompt_base + json_example
    
    try:
        # Call LLM
        prompt = f"{system_prompt}\n\n환자 정보:\n{context}"
        response = llm.invoke(prompt)
        content = response.content
        
        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        structured_data = json.loads(content)
        
        logger.info(f"[MEDICAL_ANALYSIS] Analysis complete: {len(structured_data.get('differential_diagnosis', []))} differential diagnoses")
        
        result = {
            "output_key": OUTPUT_KEY_MEDICAL_ANALYSIS,
            "structured_data": structured_data,
        }
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"[MEDICAL_ANALYSIS] JSON parsing error: {e}")
        return {
            "output_key": OUTPUT_KEY_MEDICAL_ANALYSIS,
            "structured_data": {
                "differential_diagnosis": [],
                "risk_factors": [],
                "additional_questions": [],
                "recommended_tests": [],
                "recommended_exams": [],
                "confidence": None,
                "certainty_level": None,
                "notes": "",
            }
        }
    except Exception as e:
        logger.error(f"[MEDICAL_ANALYSIS] Error: {e}")
        raise


# Create LangChain tool
medical_analysis_tool = StructuredTool.from_function(
    func=_medical_analysis_function,
    name="medical_analysis_agent",
    description="Perform medical analysis and differential diagnosis. Use this after symptom intake (and vision analysis if available).",
    args_schema=MedicalAnalysisInput,
)
