"""Triage Agent - Computes urgency level and triage classification using OpenAI GPT-4o-mini."""

import json
import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from ..config import get_settings
from ..shared.constants import OUTPUT_KEY_TRIAGE, TRIAGE_INFO, TRIAGE_LOW, TRIAGE_MODERATE, TRIAGE_HIGH, TRIAGE_EMERGENCY

logger = logging.getLogger(__name__)
settings = get_settings()


class TriageAgentInput(BaseModel):
    """Input schema for triage agent tool."""
    symptom_data: Dict[str, Any] = Field(..., description="Structured symptom data")
    medical_data: Dict[str, Any] = Field(..., description="Medical analysis data")


def _triage_agent_function(
    symptom_data: Dict[str, Any],
    medical_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute urgency score and triage level based on symptoms and medical analysis.
    
    This agent computes:
    - Urgency score (0-5)
    - Triage level (INFO, LOW, MODERATE, HIGH, EMERGENCY)
    - Justification for the triage level
    
    Args:
        symptom_data: Structured symptom data
        medical_data: Medical analysis data
        
    Returns:
        Dictionary with output_key "triage_result" containing triage assessment
    """
    logger.info("[TRIAGE] Computing triage level")
    
    # Initialize OpenAI GPT-4o-mini model
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    
    # Extract relevant data
    symptom_structured = symptom_data.get("structured_data", {})
    medical_structured = medical_data.get("structured_data", {})
    
    # 종 정보 추출
    species = symptom_structured.get('species', '알 수 없음')
    
    # Build context (한글)
    context_parts = []
    context_parts.append(f"종: {species}")
    context_parts.append(f"주요 증상: {', '.join(symptom_structured.get('main_symptoms', []))}")
    context_parts.append(f"위험 신호: {', '.join(symptom_structured.get('red_flags', []))}")
    context_parts.append(f"심각도: {symptom_structured.get('severity_perception', '알 수 없음')}")
    context_parts.append(f"지속 기간: {symptom_structured.get('duration', '알 수 없음')}")
    
    top_diagnosis = medical_structured.get("differential_diagnosis", [])
    if top_diagnosis:
        context_parts.append(f"주요 감별진단: {top_diagnosis[0].get('condition', '알 수 없음')}")
    
    context = "\n".join(context_parts)
    
    # System prompt for triage (병원 컨셉 - 응급실 트리아지 담당)
    system_prompt = f"""당신은 동물병원의 [응급실 트리아지 담당자]입니다. 주치의 선생님의 진단 결과를 바탕으로 현재 상황이 얼마나 급한지 분류하는 것이 당신의 역할입니다.

**중요**: 현재 환자는 **{species}**입니다. 응급도 판단은 반드시 {species}에 특화된 기준을 사용해야 합니다. 다른 종의 기준을 적용하지 마세요.

말투 지침:
- 빠르고 간단하며 직접적이어야 합니다
- 위급도를 명확하게 판단하고, 그 근거를 간결하게 설명합니다
- 보호자가 당황하지 않도록 차분하지만, 긴급한 상황은 확실히 전달합니다

응급도 레벨:
- INFO: 일반 정보 요청, 즉각적인 우려 없음
- LOW: 경미한 문제, 24-48시간 기다려도 됨
- MODERATE: 24시간 내 수의사 방문 권장
- HIGH: 6-12시간 내 수의사 방문 권장
- EMERGENCY: 즉시 수의학적 치료 필요

응급도 점수 (0-5):
- 0: INFO
- 1: LOW
- 2: MODERATE
- 3: HIGH
- 4: EMERGENCY
- 5: 중대 응급

고려사항:
- 위험 신호 지표 (출혈, 경련, 실신, 호흡곤란, 의식불명, 심한 통증)
- 증상 심각도 및 지속 기간
- 위험 요인
- 감별진단 가능성

모든 텍스트는 반드시 한글로 작성하세요.

다음 형식의 유효한 JSON만 반환하세요:
{
    "urgency_score": 숫자 (0-5),
    "triage_level": "INFO|LOW|MODERATE|HIGH|EMERGENCY",
    "justification": "상세한 설명 (한글로 작성)",
    "risk_assessment": "위험 평가 설명 (한글로 작성)",
    "time_sensitivity": 숫자 (수의사 방문 권장 시간, INFO의 경우 null)
}"""
    
    try:
        # Call LLM
        prompt = f"{system_prompt}\n\n케이스 정보:\n{context}"
        response = llm.invoke(prompt)
        content = response.content
        
        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        structured_data = json.loads(content)
        
        # Validate triage level
        valid_levels = [TRIAGE_INFO, TRIAGE_LOW, TRIAGE_MODERATE, TRIAGE_HIGH, TRIAGE_EMERGENCY]
        if structured_data.get("triage_level") not in valid_levels:
            structured_data["triage_level"] = TRIAGE_INFO
        
        logger.info(f"[TRIAGE] Triage level determined: {structured_data.get('triage_level')} (score: {structured_data.get('urgency_score')})")
        
        result = {
            "output_key": OUTPUT_KEY_TRIAGE,
            "structured_data": structured_data,
        }
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"[TRIAGE] JSON parsing error: {e}")
        return {
            "output_key": OUTPUT_KEY_TRIAGE,
            "structured_data": {
                "urgency_score": 0,
                "triage_level": TRIAGE_INFO,
                "justification": "",
                "risk_assessment": "",
                "time_sensitivity": None,
            }
        }
    except Exception as e:
        logger.error(f"[TRIAGE] Error: {e}")
        raise


# Create LangChain tool
triage_agent_tool = StructuredTool.from_function(
    func=_triage_agent_function,
    name="triage_agent",
    description="Compute urgency score and triage level. Use this after medical analysis.",
    args_schema=TriageAgentInput,
)
