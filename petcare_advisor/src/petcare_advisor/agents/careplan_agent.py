"""Careplan Agent - Generates caregiver-friendly guidance using Gemini Pro."""

import json
import logging
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from ..config import get_settings
from ..shared.constants import OUTPUT_KEY_CAREPLAN

logger = logging.getLogger(__name__)
settings = get_settings()


class CareplanAgentInput(BaseModel):
    """Input schema for careplan agent tool."""
    symptom_data: Dict[str, Any] = Field(..., description="Structured symptom data")
    medical_data: Dict[str, Any] = Field(..., description="Medical analysis data")
    triage_data: Dict[str, Any] = Field(..., description="Triage assessment data")


def _careplan_agent_function(
    symptom_data: Dict[str, Any],
    medical_data: Dict[str, Any],
    triage_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate caregiver-friendly guidance based on triage level and medical analysis.
    
    This agent produces:
    - What can be done at home
    - What must be avoided
    - When to go to a vet (NOW vs within 24-48h)
    - Clear "if X happens, go to ER immediately" rules
    - Empathetic, calm, supportive tone
    
    Args:
        symptom_data: Structured symptom data
        medical_data: Medical analysis data
        triage_data: Triage assessment data
        
    Returns:
        Dictionary with output_key "careplan_result" containing care guidance
    """
    logger.info("[CAREPLAN] Generating care plan")
    
    # Initialize Gemini Flash model
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        api_key=settings.gemini_api_key,
        temperature=0.4,
    )
    
    # Extract relevant data
    symptom_structured = symptom_data.get("structured_data", {})
    medical_structured = medical_data.get("structured_data", {})
    triage_structured = triage_data.get("structured_data", {})
    
    # 종 정보 추출
    species = symptom_structured.get('species', '알 수 없음')
    
    # Build context (한글)
    context_parts = []
    context_parts.append(f"종: {species}")
    context_parts.append(f"응급도 레벨: {triage_structured.get('triage_level', '알 수 없음')}")
    context_parts.append(f"응급도 점수: {triage_structured.get('urgency_score', 0)}")
    context_parts.append(f"주요 증상: {', '.join(symptom_structured.get('main_symptoms', []))}")
    context_parts.append(f"시간 민감도: {triage_structured.get('time_sensitivity', '해당 없음')}시간")
    
    top_diagnosis = medical_structured.get("differential_diagnosis", [])
    if top_diagnosis:
        context_parts.append(f"가능성 높은 질환: {top_diagnosis[0].get('condition', '알 수 없음')}")
    
    context = "\n".join(context_parts)
    
    # System prompt for careplan (병원 컨셉 - 치료 계획실 + 약국)
    system_prompt_base = f"""당신은 [치료 계획실 담당자]이자 [약국 상담사]입니다. 주치의 선생님의 진단과 응급실의 위급도 판단을 바탕으로, 보호자가 바로 이해하고 따라 할 수 있는 실용적인 조언을 제공합니다.

**중요**: 현재 환자는 **{species}**입니다. 모든 케어 플랜, 홈 케어 지침, 주의사항은 반드시 {species}에 특화된 내용이어야 합니다. 다른 종에 대한 일반적인 조언을 제공하지 마세요.

말투 지침:
- 보호자가 바로 이해하고 따라 할 수 있는 실용적인 조언을 제공합니다
- 의학적 근거가 있지만 너무 전문적인 설명은 피합니다
- '집에서 할 수 있는 것', '하면 안 되는 것', '병원 방문 기준'을 명확히 안내합니다
- 공감적이고 따뜻하지만, 중요한 주의사항은 확실히 전달합니다

생성할 내용:
- 홈 케어 지침 (집에서 안전하게 할 수 있는 것들)
- 피해야 할 것들 (하지 말아야 할 것들)
- 수의사 방문 시기 (응급도 레벨에 따른 구체적인 시기)
- 응급 지표 (명확한 "X가 발생하면 즉시 응급실로 가세요" 규칙)
- 모니터링 가이드 (관찰해야 할 것들)
- 지지 메시지 (공감적이고 차분한 톤)

톤: 공감적이고, 차분하며, 지지적이고, 명확하게. 의학 용어는 피하고 쉬운 언어를 사용하세요.

모든 내용은 반드시 한글로 작성하세요.

다음 형식의 유효한 JSON만 반환하세요:"""
    
    json_example = """
{
    "home_care_instructions": ["지침1", "지침2", ...],
    "things_to_avoid": ["피할것1", "피할것2", ...],
    "when_to_see_vet": "수의사 방문 시기에 대한 명확한 가이드 (한글로 작성)",
    "emergency_indicators": ["응급지표1", "응급지표2", ...],
    "monitoring_guidance": ["관찰사항1", "관찰사항2", ...],
    "supportive_message": "공감적이고 지지적인 메시지 (한글로 작성)"
}"""
    
    system_prompt = system_prompt_base + json_example
    
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
        
        logger.info(f"[CAREPLAN] Care plan generated: {len(structured_data.get('home_care_instructions', []))} home care instructions")
        
        result = {
            "output_key": OUTPUT_KEY_CAREPLAN,
            "structured_data": structured_data,
        }
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"[CAREPLAN] JSON parsing error: {e}")
        return {
            "output_key": OUTPUT_KEY_CAREPLAN,
            "structured_data": {
                "home_care_instructions": [],
                "things_to_avoid": [],
                "when_to_see_vet": "",
                "emergency_indicators": [],
                "monitoring_guidance": [],
                "supportive_message": "",
            }
        }
    except Exception as e:
        logger.error(f"[CAREPLAN] Error: {e}")
        raise


# Create LangChain tool
careplan_agent_tool = StructuredTool.from_function(
    func=_careplan_agent_function,
    name="careplan_agent",
    description="Generate caregiver-friendly care plan. Use this after triage assessment.",
    args_schema=CareplanAgentInput,
)
