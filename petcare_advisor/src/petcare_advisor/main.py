"""FastAPI application entrypoint for PetCare Advisor."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uvicorn

from .config import get_settings
from .shared.types import TriageRequest, TriageResponse, GraphState, QuestionRequest, QuestionResponse
import httpx
from .agents.root_orchestrator import root_orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PetCare Advisor API",
    description="Multi-agent veterinary triage backend system",
    version="0.1.0",
)

# CORS middleware
# GitHub Pages 도메인 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://ksy070822.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get settings
settings = get_settings()


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information.
    
    Returns:
        API information dictionary
    """
    return {
        "service": "PetCare Advisor API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "triage": "/api/triage",
            "question": "/api/question",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "message": "반려동물 응급도 평가 API 서버입니다. /docs에서 API 문서를 확인하세요."
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint.
    
    Returns:
        Health status dictionary
    """
    return {"status": "healthy", "service": "petcare-advisor"}


@app.post("/api/triage", response_model=TriageResponse)
async def triage_endpoint(request: TriageRequest) -> TriageResponse:
    """Main triage endpoint that processes symptom descriptions.
    
    This endpoint:
    - Accepts free-text symptom description
    - Optionally accepts metadata (species, age, etc.)
    - Optionally accepts image references
    - Invokes Root Orchestrator Agent following TRD rules
    - Returns final triage report JSON
    
    Args:
        request: Triage request with symptom description and optional metadata
        
    Returns:
        Triage response with final report or error
    """
    try:
        logger.info(f"[API] Received triage request: {request.symptom_description[:100]}...")
        
        # 종 정보 정규화 (dog, cat 등으로 통일)
        species_normalized = None
        if request.species:
            species_lower = request.species.lower()
            if species_lower in ['cat', '고양이', 'cat']:
                species_normalized = '고양이'
            elif species_lower in ['dog', '개', '강아지', 'dog']:
                species_normalized = '개'
            elif species_lower in ['rabbit', '토끼']:
                species_normalized = '토끼'
            elif species_lower in ['hamster', '햄스터']:
                species_normalized = '햄스터'
            elif species_lower in ['bird', '새']:
                species_normalized = '새'
            elif species_lower in ['hedgehog', '고슴도치']:
                species_normalized = '고슴도치'
            elif species_lower in ['reptile', '파충류']:
                species_normalized = '파충류'
            else:
                species_normalized = request.species
        
        # Initialize GraphState
        # 구조화된 데이터가 있으면 symptom_description에 포함
        enhanced_description = request.symptom_description
        
        # 종 정보를 명확히 포함
        if species_normalized:
            enhanced_description = f"[종: {species_normalized}] {enhanced_description}"
        
        # 구조화된 데이터가 있으면 추가
        if request.department and request.symptom_tags:
            enhanced_description = f"[종: {species_normalized or '알 수 없음'}] [진료과: {request.department}] [증상 태그: {', '.join(request.symptom_tags)}] {request.free_text or request.symptom_description}"
            if request.follow_up_answers:
                answers_text = ' '.join([f"{k}: {v}" for k, v in request.follow_up_answers.items()])
                enhanced_description += f" [추가 정보: {answers_text}]"
        
        state = GraphState(
            user_input=enhanced_description,
            image_refs=request.image_urls or [],
        )
        
        # Execute pipeline step by step (TRD: one tool per step)
        # Step 1: Symptom Intake
        result = root_orchestrator(state, request.symptom_description)
        if result.get("status") != "in_progress":
            return TriageResponse(success=False, report=None, error="Unexpected result from symptom intake")
        
        state.symptom_data = result.get("symptom_data")
        
        # Step 2: Vision (if images provided)
        if request.image_urls:
            result = root_orchestrator(state, request.symptom_description)
            if result.get("status") == "in_progress":
                state.vision_data = result.get("vision_data")
        
        # Step 3: Medical Analysis
        result = root_orchestrator(state, request.symptom_description)
        if result.get("status") != "in_progress":
            return TriageResponse(success=False, report=None, error="Unexpected result from medical analysis")
        state.medical_data = result.get("medical_data")
        
        # Step 4: Triage
        result = root_orchestrator(state, request.symptom_description)
        if result.get("status") != "in_progress":
            return TriageResponse(success=False, report=None, error="Unexpected result from triage")
        state.triage_data = result.get("triage_data")
        
        # Step 5: Careplan
        result = root_orchestrator(state, request.symptom_description)
        if result.get("status") != "in_progress":
            return TriageResponse(success=False, report=None, error="Unexpected result from careplan")
        state.careplan_data = result.get("careplan_data")
        
        # Step 6: Final Report
        result = root_orchestrator(state, request.symptom_description)
        if result.get("status") != "complete":
            return TriageResponse(success=False, report=None, error="Failed to build final report")
        
        final_report = result.get("report")
        logger.info("[API] Triage pipeline completed successfully")
        
        return TriageResponse(
            success=True,
            report=final_report,
            error=None,
        )
    except Exception as e:
        logger.error(f"[API] Error in triage endpoint: {e}", exc_info=True)
        return TriageResponse(
            success=False,
            report=None,
            error=str(e),
        )


@app.post("/api/question", response_model=QuestionResponse)
async def question_endpoint(request: QuestionRequest) -> QuestionResponse:
    """Follow-up question endpoint that answers user questions about diagnosis.

    This endpoint:
    - Accepts a user question about the current diagnosis
    - Uses Gemini API to generate a professional veterinary response
    - Returns the answer in Korean

    Args:
        request: Question request with user question and context

    Returns:
        Question response with AI-generated answer or error
    """
    try:
        logger.info(f"[API] Received question: {request.question[:50]}...")

        # Get Gemini API key
        gemini_api_key = settings.gemini_api_key
        if not gemini_api_key:
            logger.error("[API] Gemini API key not configured")
            return QuestionResponse(
                success=False,
                answer=None,
                error="Gemini API 키가 설정되지 않았습니다."
            )

        # Extract pet info
        pet_info = request.pet_info or {}
        pet_name = pet_info.get('petName', '반려동물')
        species = pet_info.get('species', 'dog')
        species_kor = '개' if species == 'dog' else '고양이' if species == 'cat' else species
        breed = pet_info.get('breed', '미등록')
        age = pet_info.get('age', '미등록')
        weight = pet_info.get('weight')

        # Extract diagnosis info
        diagnosis = request.diagnosis_result or {}
        diagnosis_name = diagnosis.get('diagnosis', '일반 건강 이상')
        risk_level = diagnosis.get('riskLevel', diagnosis.get('emergency', 'moderate'))
        triage_level = diagnosis.get('triage_level', 'yellow')
        triage_score = diagnosis.get('triage_score', 'N/A')
        actions = diagnosis.get('actions', [])
        owner_sheet = diagnosis.get('ownerSheet', {})
        immediate_actions = owner_sheet.get('immediate_home_actions', actions)
        things_to_avoid = owner_sheet.get('things_to_avoid', [])
        monitoring_guide = owner_sheet.get('monitoring_guide', [])
        care_guide = diagnosis.get('careGuide', '')

        # Build prompt
        prompt = f"""당신은 전문 수의사입니다. 반려동물 보호자의 질문에 대해 정확하고 친절하게 답변해주세요.

[반려동물 정보]
- 이름: {pet_name}
- 종류: {species_kor}
- 품종: {breed}
- 나이: {age}세
{f'- 체중: {weight}kg' if weight else ''}

[현재 진단 결과]
- 진단명: {diagnosis_name}
- 위험도: {risk_level}
- 응급도: {triage_level}
- Triage Score: {triage_score}/5

[권장 조치사항]
{chr(10).join([f'{i+1}. {a}' for i, a in enumerate(immediate_actions)]) if immediate_actions else '추가 조치사항 없음'}

[피해야 할 행동]
{chr(10).join([f'{i+1}. {a}' for i, a in enumerate(things_to_avoid)]) if things_to_avoid else '없음'}

[관찰 포인트]
{chr(10).join([f'{i+1}. {a}' for i, a in enumerate(monitoring_guide)]) if monitoring_guide else '없음'}

{f'[케어 가이드]{chr(10)}{care_guide}' if care_guide else ''}

[보호자 질문]
{request.question}

위 질문에 대해 다음을 포함하여 답변해주세요:
1. 질문에 대한 구체적이고 실용적인 답변
2. 현재 진단 결과와 연관된 조언
3. 구체적인 실행 방법 (예: 음식 추천, 케어 방법, 주의사항)
4. 필요시 병원 방문 시점 안내

답변은 친절하고 이해하기 쉽게 작성하되, 전문적이고 정확해야 합니다. 추측이나 검증되지 않은 정보는 제공하지 마세요."""

        # Call Gemini API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 1024,
                    }
                },
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(f"[API] Gemini API error: {response.status_code}")
                return QuestionResponse(
                    success=False,
                    answer=None,
                    error=f"Gemini API 호출 실패: {response.status_code}"
                )

            data = response.json()

            if not data.get("candidates") or not data["candidates"][0].get("content"):
                return QuestionResponse(
                    success=False,
                    answer=None,
                    error="Gemini API 응답 형식 오류"
                )

            answer = data["candidates"][0]["content"]["parts"][0]["text"]

            if not answer or answer.strip() == "":
                return QuestionResponse(
                    success=False,
                    answer=None,
                    error="빈 답변을 받았습니다"
                )

            logger.info("[API] Question answered successfully")
            return QuestionResponse(
                success=True,
                answer=answer.strip(),
                error=None
            )

    except Exception as e:
        logger.error(f"[API] Error in question endpoint: {e}", exc_info=True)
        return QuestionResponse(
            success=False,
            answer=None,
            error=str(e)
        )


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "petcare_advisor.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
