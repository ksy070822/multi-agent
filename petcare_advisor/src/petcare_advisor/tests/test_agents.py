"""Tests for agent functionality."""

import pytest
from ..agents.symptom_intake_agent import symptom_intake_agent
from ..agents.vision_agent import vision_agent
from ..agents.medical_agent import medical_agent
from ..agents.triage_agent import triage_agent
from ..agents.careplan_agent import careplan_agent
from ..shared.types import ToolContext
from ..shared.constants import (
    OUTPUT_KEY_SYMPTOM_INTAKE,
    OUTPUT_KEY_VISION_ANALYSIS,
    OUTPUT_KEY_MEDICAL_ANALYSIS,
    OUTPUT_KEY_TRIAGE,
    OUTPUT_KEY_CAREPLAN,
)


def test_symptom_intake_agent():
    """Test symptom intake agent."""
    tool_context = ToolContext()
    result = symptom_intake_agent(
        user_input="My cat is not eating and seems lethargic",
        tool_context=tool_context,
    )
    assert result["output_key"] == OUTPUT_KEY_SYMPTOM_INTAKE
    assert "structured_data" in result
    assert tool_context.get(OUTPUT_KEY_SYMPTOM_INTAKE) == result


def test_vision_agent_with_images():
    """Test vision agent with image URLs."""
    tool_context = ToolContext()
    image_urls = ["https://example.com/image1.jpg"]
    result = vision_agent(
        image_urls=image_urls,
        tool_context=tool_context,
    )
    assert result["output_key"] == OUTPUT_KEY_VISION_ANALYSIS
    assert result["structured_data"]["has_images"] is True
    assert tool_context.get(OUTPUT_KEY_VISION_ANALYSIS) == result


def test_vision_agent_without_images():
    """Test vision agent without images."""
    tool_context = ToolContext()
    result = vision_agent(
        image_urls=None,
        tool_context=tool_context,
    )
    assert result["output_key"] == OUTPUT_KEY_VISION_ANALYSIS
    assert result["structured_data"]["has_images"] is False


def test_medical_agent():
    """Test medical agent."""
    tool_context = ToolContext()
    # Set up prerequisite data
    tool_context.set(OUTPUT_KEY_SYMPTOM_INTAKE, {
        "output_key": OUTPUT_KEY_SYMPTOM_INTAKE,
        "structured_data": {"main_symptoms": ["vomiting"]},
    })
    result = medical_agent(tool_context=tool_context)
    assert result["output_key"] == OUTPUT_KEY_MEDICAL_ANALYSIS
    assert "structured_data" in result


def test_triage_agent():
    """Test triage agent."""
    tool_context = ToolContext()
    # Set up prerequisite data
    tool_context.set(OUTPUT_KEY_MEDICAL_ANALYSIS, {
        "output_key": OUTPUT_KEY_MEDICAL_ANALYSIS,
        "structured_data": {"confidence": 0.8},
    })
    result = triage_agent(tool_context=tool_context)
    assert result["output_key"] == OUTPUT_KEY_TRIAGE
    assert "urgency_score" in result["structured_data"]


def test_careplan_agent():
    """Test careplan agent."""
    tool_context = ToolContext()
    # Set up prerequisite data
    tool_context.set(OUTPUT_KEY_TRIAGE, {
        "output_key": OUTPUT_KEY_TRIAGE,
        "structured_data": {"triage_level": "MODERATE"},
    })
    tool_context.set(OUTPUT_KEY_MEDICAL_ANALYSIS, {
        "output_key": OUTPUT_KEY_MEDICAL_ANALYSIS,
        "structured_data": {},
    })
    result = careplan_agent(tool_context=tool_context)
    assert result["output_key"] == OUTPUT_KEY_CAREPLAN
    assert "home_care_instructions" in result["structured_data"]

