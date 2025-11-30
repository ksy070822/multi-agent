"""Type definitions for the petcare advisor system."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolContext:
    """Context object passed to tools and agents.
    
    This is a placeholder for ADK-style ToolContext.
    In a real implementation, this would be provided by the ADK framework.
    """
    
    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.state = state or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state."""
        return self.state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in state."""
        self.state[key] = value


class GraphState(BaseModel):
    """Unified state model for LangGraph workflow."""
    
    symptom_data: Optional[Dict[str, Any]] = None
    vision_data: Optional[Dict[str, Any]] = None
    medical_data: Optional[Dict[str, Any]] = None
    triage_data: Optional[Dict[str, Any]] = None
    careplan_data: Optional[Dict[str, Any]] = None
    final_report: Optional[Dict[str, Any]] = None
    image_refs: Optional[list[str]] = None
    user_input: Optional[str] = None
    tool_context: Optional[ToolContext] = Field(default=None, exclude=True)
    
    class Config:
        arbitrary_types_allowed = True


# Request/Response Models for API
class TriageRequest(BaseModel):
    """Request model for triage endpoint."""
    
    symptom_description: str = Field(..., description="Free-text symptom description")
    species: Optional[str] = Field(None, description="Pet species (dog, cat, bird, rabbit, other)")
    breed: Optional[str] = Field(None, description="Pet breed")
    age: Optional[float] = Field(None, description="Pet age in years")
    sex: Optional[str] = Field(None, description="Pet sex (male, female, neutered, spayed)")
    weight: Optional[float] = Field(None, description="Pet weight in kg")
    image_urls: Optional[list[str]] = Field(default_factory=list, description="Optional image URLs")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    # 구조화된 데이터 (선택적)
    department: Optional[str] = Field(None, description="Selected medical department (ortho, derm, digestive, etc.)")
    symptom_tags: Optional[list[str]] = Field(default_factory=list, description="Selected symptom tag IDs")
    follow_up_answers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Answers to follow-up questions")
    free_text: Optional[str] = Field(None, description="Additional free-text description")


class TriageResponse(BaseModel):
    """Response model for triage endpoint."""
    
    success: bool
    report: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

