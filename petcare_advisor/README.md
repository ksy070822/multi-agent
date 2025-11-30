# PetCare Advisor

Multi-agent veterinary triage backend system for remote pet health assessment.

## Overview

PetCare Advisor is a Python-based backend system that uses a multi-agent architecture to analyze pet symptoms, perform medical reasoning, determine triage urgency, and generate caregiver-friendly care plans.

## Architecture

The system consists of 5+1 agents:

1. **Symptom Intake Agent** - Parses natural language symptom descriptions into structured data
2. **Vision Agent** (optional) - Analyzes images/video for visual health indicators
3. **Medical Agent** - Performs medical analysis and differential diagnosis
4. **Triage Agent** - Computes urgency level and triage classification
5. **Careplan Agent** - Generates caregiver-friendly guidance
6. **Root Orchestrator Agent** - Coordinates the entire workflow

## Project Structure

```
petcare_advisor/
├── pyproject.toml          # Project configuration and dependencies
├── .env.example            # Environment variables template
├── README.md               # This file
│
└── src/
    └── petcare_advisor/
        ├── __init__.py
        ├── config.py                # Configuration management
        ├── main.py                  # FastAPI application entrypoint
        │
        ├── shared/
        │   ├── __init__.py
        │   ├── constants.py         # System constants
        │   ├── types.py             # Type definitions and GraphState
        │   └── utils.py             # Utility functions
        │
        ├── agents/
        │   ├── __init__.py
        │   ├── root_orchestrator.py # Root orchestrator agent
        │   ├── symptom_intake_agent.py
        │   ├── vision_agent.py
        │   ├── medical_agent.py
        │   ├── triage_agent.py
        │   └── careplan_agent.py
        │
        ├── tools/
        │   ├── __init__.py
        │   ├── report_builder.py   # Final report assembly
        │   └── persistence.py      # Data persistence utilities
        │
        ├── workflow/
        │   ├── __init__.py
        │   └── quality_workflow.py  # LangGraph quality/enrichment flow
        │
        └── tests/
            ├── __init__.py
            ├── test_smoke.py        # Smoke tests
            ├── test_agents.py       # Agent tests
            └── test_api.py          # API endpoint tests
```

## Setup

### Prerequisites

- Python 3.11 or higher
- pip or poetry for package management

### Installation

1. Clone the repository and navigate to the project directory:
```bash
cd petcare_advisor
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
pip install -e ".[dev]"  # For development dependencies
```

4. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

5. Edit `.env` and add your API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

## Running the Application

### Development Server

```bash
python -m petcare_advisor.main
```

Or using uvicorn directly:
```bash
uvicorn petcare_advisor.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service health status.

### Triage Endpoint

```bash
POST /api/triage
```

Request body:
```json
{
  "symptom_description": "My dog has been vomiting for 2 days",
  "species": "dog",
  "breed": "Golden Retriever",
  "age": 5.0,
  "sex": "male",
  "weight": 30.0,
  "image_urls": ["https://example.com/image.jpg"],
  "metadata": {}
}
```

Response:
```json
{
  "success": true,
  "report": {
    "meta": {
      "version": "v1",
      "generated_at": "2024-01-01T00:00:00Z"
    },
    "patient": { ... },
    "summary": { ... },
    "triage": { ... },
    "differential_diagnosis": [ ... ],
    "care_plan": { ... },
    "red_flags": [ ... ]
  },
  "error": null
}
```

## Testing

Run tests with pytest:

```bash
pytest
```

Run with coverage:
```bash
pytest --cov=petcare_advisor --cov-report=html
```

## Development

### Code Style

The project uses:
- **Black** for code formatting
- **Ruff** for linting
- **mypy** for type checking

Format code:
```bash
black src/
```

Lint code:
```bash
ruff check src/
```

Type check:
```bash
mypy src/
```

## Workflow

The triage workflow follows this sequence:

1. User submits symptom description (and optionally images)
2. Root Orchestrator calls Symptom Intake Agent
3. If images provided, Root Orchestrator calls Vision Agent
4. Root Orchestrator calls Medical Agent
5. Root Orchestrator calls Triage Agent
6. Root Orchestrator calls Careplan Agent
7. Root Orchestrator calls Report Builder Tool
8. Final triage report is returned

## Future Enhancements

- LangGraph quality loops for insufficient data scenarios
- Integration with actual LLM APIs (OpenAI, Gemini)
- Database persistence for triage reports
- Additional agents (OCR, EMR integration, clinic recommendation)
- Enhanced vision analysis with multiple image support
- Real-time streaming responses

## License

MIT

## Contributing

Contributions are welcome! Please ensure:
- Code follows the project's style guidelines
- Tests are added for new features
- Documentation is updated as needed

