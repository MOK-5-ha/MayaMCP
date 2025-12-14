# MayaMCP Tech Stack

## Language & Runtime

- Python 3.8+ (3.12+ recommended)
- Package management via pip with setuptools

## Core Dependencies

- **LLM**: Google Gemini via `google-generativeai` SDK and `langchain-google-genai`
- **UI**: Gradio 4.x
- **TTS**: Cartesia
- **RAG**: FAISS (faiss-cpu), custom Memvid pipeline
- **HTTP/Retry**: tenacity, requests, websockets
- **Config**: python-dotenv

## Build & Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode (recommended)
pip install -e .

# Run the application
mayamcp
# or: python main.py
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov

# Verbose output
pytest -v

# Skip slow tests
pytest -m "not slow"
```

Test markers: `slow`, `integration`, `unit`

## Linting & Type Checking

- Ruff configured in pyproject.toml (line-length: 88)
- MyPy cache present (type checking available)

## Deployment

- Modal Labs deployment via `deploy.py`
- Dev: `modal serve deploy.py`
- Prod: `modal deploy deploy.py`

## Required Environment Variables

```bash
GEMINI_API_KEY=your_google_api_key
CARTESIA_API_KEY=your_cartesia_api_key

# Optional
GEMINI_MODEL_VERSION=gemini-2.5-flash-lite
TEMPERATURE=0.7
MAX_OUTPUT_TOKENS=2048
```
