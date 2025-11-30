"""Utility functions for the petcare advisor system."""

from typing import Any, Dict
from datetime import datetime


def safe_state_access(state: Dict[str, Any]) -> Dict[str, Any]:
    """Safely access state dictionary.
    
    Args:
        state: State dictionary to access safely
        
    Returns:
        A safe copy of the state dictionary
    """
    return {k: v for k, v in state.items()}


def get_iso_datetime() -> str:
    """Get current datetime in ISO format.
    
    Returns:
        ISO formatted datetime string
    """
    return datetime.utcnow().isoformat() + "Z"


def validate_triage_level(level: str) -> bool:
    """Validate that a triage level is valid.
    
    Args:
        level: Triage level to validate
        
    Returns:
        True if valid, False otherwise
    """
    from .constants import TRIAGE_LEVELS
    return level in TRIAGE_LEVELS


def validate_urgency_score(score: int) -> bool:
    """Validate that an urgency score is in valid range (0-5).
    
    Args:
        score: Urgency score to validate
        
    Returns:
        True if valid, False otherwise
    """
    return 0 <= score <= 5

