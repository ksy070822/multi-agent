"""Symptom Intake Agent - Parses user's natural language symptom description using Gemini Flash."""

import json
import logging
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from ..config import get_settings
from ..shared.constants import OUTPUT_KEY_SYMPTOM_INTAKE

logger = logging.getLogger(__name__)
settings = get_settings()


class SymptomIntakeInput(BaseModel):
    """Input schema for symptom intake tool."""
    user_input: str = Field(..., description="Natural language symptom description from user")


def _symptom_intake_function(user_input: str) -> Dict[str, Any]:
    """Parse user's natural language symptom description into structured JSON.
    
    This agent extracts:
    - species, breed, age, sex, weight (if available)
    - main symptoms
    - onset time & duration
    - severity (guardian's perception)
    - appetite, water intake, urination/defecation changes
    - behavior changes (lethargy, restlessness, etc.)
    - any "red flag" indicators (bleeding, seizure, collapse, etc.)
    
    Args:
        user_input: Natural language symptom description from user
        
    Returns:
        Dictionary with output_key "symptom_intake_result" containing structured symptom data
    """
    logger.info(f"[SYMPTOM_INTAKE] Processing user input: {user_input[:100]}...")
    
    # Initialize Gemini Flash model
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        api_key=settings.gemini_api_key,
        temperature=0.2,
    )
    
    # System prompt for symptom intake (병원 컨셉 - 접수 도우미 + 간호사)
    system_prompt = """당신은 동물병원의 [접수 도우미]이자 [간호사]입니다. 보호자가 말씀해주신 증상을 친절하고 꼼꼼하게 정리하는 것이 당신의 역할입니다.

말투 지침:
- 친절하고 따뜻하지만 너무 전문적이지 않게 합니다
- 보호자가 부담 없게 느끼도록 일상적인 표현을 사용합니다
- 증상을 이해하고 정리하는 것이 목적입니다
- 전문 진단은 하지 않습니다 (주치의 선생님께 전달할 정보만 정리)

보호자가 이미 진료과와 증상 태그를 선택했다면, 그 정보를 우선적으로 활용하세요.
구조화된 정보가 제공되면 더 정확하게 정리할 수 있습니다.

다음 정보를 추출하세요:
- 종(species), 품종(breed), 나이(age), 성별(sex), 체중(weight) (언급된 경우)
- 주요 증상 목록
- 발병 시점 및 지속 기간
- 심각도 (보호자 인식: 경미, 보통, 심각)
- 식욕 변화 (증가, 감소, 없음, 알 수 없음)
- 수분 섭취 변화 (증가, 감소, 없음, 알 수 없음)
- 배뇨 변화 (증가, 감소, 이상, 없음, 알 수 없음)
- 배변 변화 (설사, 변비, 혈변, 없음, 알 수 없음)
- 행동 변화 (무기력, 불안, 공격성, 숨기기 등)
- 위험 신호 지표 (출혈, 경련, 실신, 호흡곤란, 의식불명, 심한 통증)

모든 텍스트는 반드시 한글로 작성하세요.

다음 형식의 유효한 JSON만 반환하세요:
{
    "species": "개|고양이|새|토끼|기타|null",
    "breed": "문자열|null",
    "age": 숫자|null,
    "sex": "수컷|암컷|중성화수컷|중성화암컷|null",
    "weight": 숫자|null,
    "main_symptoms": ["증상1", "증상2", ...],
    "onset_time": "문자열|null",
    "duration": "문자열|null",
    "severity_perception": "경미|보통|심각|null",
    "appetite_changes": "증가|감소|없음|알 수 없음|null",
    "water_intake_changes": "증가|감소|없음|알 수 없음|null",
    "urination_changes": "증가|감소|이상|없음|알 수 없음|null",
    "defecation_changes": "설사|변비|혈변|없음|알 수 없음|null",
    "behavior_changes": ["변화1", "변화2", ...],
    "red_flags": ["출혈", "경련", ...],
    "raw_input": "원본 사용자 입력"
}"""
    
    try:
        # Call LLM
        response = llm.invoke(f"{system_prompt}\n\nUser input: {user_input}")
        content = response.content
        
        # Parse JSON from response
        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        structured_data = json.loads(content)
        
        logger.info(f"[SYMPTOM_INTAKE] Successfully parsed symptoms: {len(structured_data.get('main_symptoms', []))} symptoms found")
        
        result = {
            "output_key": OUTPUT_KEY_SYMPTOM_INTAKE,
            "structured_data": structured_data,
        }
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"[SYMPTOM_INTAKE] JSON parsing error: {e}")
        # Fallback to basic structure
        return {
            "output_key": OUTPUT_KEY_SYMPTOM_INTAKE,
            "structured_data": {
                "main_symptoms": [],
                "raw_input": user_input,
            },
        }
    except Exception as e:
        logger.error(f"[SYMPTOM_INTAKE] Error: {e}")
        raise


# Create LangChain tool
symptom_intake_tool = StructuredTool.from_function(
    func=_symptom_intake_function,
    name="symptom_intake_agent",
    description="Parse natural language symptom description into structured JSON. Use this first in the triage pipeline.",
    args_schema=SymptomIntakeInput,
)
