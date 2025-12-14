# AGENTS.md

This document provides guidance for AI agents working with the MayaMCP codebase.

## Project Overview

MayaMCP is an AI bartending agent that provides conversational drink ordering with voice synthesis. It uses Google Gemini for LLM, Cartesia for TTS, and FAISS/Memvid for RAG.

## Repository Structure

```
MayaMCP/
├── src/                    # Main source code
│   ├── config/             # API keys, logging, model settings
│   ├── conversation/       # Phase management, message processing
│   ├── llm/                # Gemini client, prompts, function tools
│   ├── memvid/             # Memvid RAG implementation
│   ├── rag/                # RAG pipeline (embeddings, retrieval, vector store)
│   ├── ui/                 # Gradio components and handlers
│   ├── utils/              # Errors, helpers, state management
│   └── voice/              # Cartesia TTS integration
├── tests/                  # pytest test suite
├── assets/                 # Static files (avatar, media)
├── deploy.py               # Modal Labs deployment
└── main.py                 # Application entry point
```

## Key Patterns

### Unified LLM Client
All GenAI API calls go through `src/llm/client.py`. Never call the Google SDK directly elsewhere.

### Graceful Fallbacks
The system degrades gracefully:
- RAG: Memvid → FAISS → no-RAG
- TTS: Cartesia → text-only response
- API errors never break conversation flow

### Error Handling
Use `src/utils/errors.py` for consistent error classification. Log context without exposing sensitive data.

### Configuration
All API keys and settings come from environment variables. See `src/config/api_keys.py`.

## Development Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Run application
mayamcp
# or: python main.py

# Run tests
pytest                    # All tests
pytest --cov              # With coverage
pytest -v                 # Verbose
pytest -m "not slow"      # Skip slow tests

# Deployment (Modal)
modal serve deploy.py     # Dev
modal deploy deploy.py    # Prod
```

## Testing Guidelines

- Tests live in `tests/` with `test_*.py` naming
- `tests/conftest.py` provides fixtures and SDK stubs for offline testing
- Use markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.unit`
- Mock external APIs (Google, Cartesia) - don't make real calls in tests
- Property-based tests use Hypothesis (`.hypothesis/` cache present)

## Environment Variables

Required:
- `GEMINI_API_KEY` - Google AI Studio API key
- `CARTESIA_API_KEY` - Cartesia TTS API key

Optional:
- `GEMINI_MODEL_VERSION` - Model ID (default: `gemini-2.5-flash-lite`)
- `TEMPERATURE` - LLM temperature (default: `0.7`)
- `MAX_OUTPUT_TOKENS` - Response limit (default: `2048`)

## Code Style

- Python 3.8+ compatible
- Ruff linter configured (line-length: 88)
- MyPy for type checking
- Follow existing patterns in each module

## Important Files

| File | Purpose |
|------|---------|
| `src/llm/client.py` | Centralized GenAI client wrapper |
| `src/llm/tools.py` | Function calling tool definitions |
| `src/conversation/processor.py` | Main conversation logic |
| `src/utils/state_manager.py` | Order and session state |
| `src/ui/handlers.py` | Gradio event handlers |
| `tests/conftest.py` | Test fixtures and API stubs |

## Common Tasks

### Adding a New Tool
1. Define tool schema in `src/llm/tools.py`
2. Implement handler in `src/conversation/processor.py`
3. Add tests in `tests/`

### Modifying RAG
1. Pipeline logic in `src/rag/pipeline.py`
2. Memvid-specific code in `src/rag/memvid_pipeline.py`
3. Vector operations in `src/rag/vector_store.py`

### UI Changes
1. Components in `src/ui/components.py`
2. Event handlers in `src/ui/handlers.py`
3. App launch in `src/ui/launcher.py`

## Specs

Feature specifications live in `.kiro/specs/`. Each spec contains:
- `requirements.md` - User stories and acceptance criteria
- `design.md` - Architecture and correctness properties
- `tasks.md` - Implementation checklist

## Don't

- Call Google SDK directly outside `src/llm/client.py`
- Hardcode API keys or secrets
- Skip error handling for external API calls
- Break the graceful fallback chain
- Add tests that require real API calls without mocking
