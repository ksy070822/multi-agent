"""FastAPI application entrypoint for PetCare Advisor."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uvicorn

from .config import get_settings
from .shared.types import TriageRequest, TriageResponse, GraphState
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
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


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "petcare_advisor.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
