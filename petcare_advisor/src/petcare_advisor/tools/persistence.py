"""Persistence Tool - Handles data persistence for triage reports."""

from typing import Dict, Any, Optional
from datetime import datetime
import json


def save_triage_report(
    report: Dict[str, Any],
    filepath: Optional[str] = None,
) -> str:
    """Save triage report to file.
    
    Args:
        report: Triage report dictionary to save
        filepath: Optional filepath (will generate if not provided)
        
    Returns:
        Path to saved file
    """
    if filepath is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filepath = f"triage_report_{timestamp}.json"
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return filepath


def load_triage_report(filepath: str) -> Dict[str, Any]:
    """Load triage report from file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Triage report dictionary
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

