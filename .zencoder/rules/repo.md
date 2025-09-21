---
description: Repository Information Overview
alwaysApply: true
---

# MayaMCP Information

## Summary
MayaMCP is an AI Bartending Agent that uses generative AI to create a conversational ordering system. Originally created as a capstone project for Kaggle's Gen AI Intensive Course, it has evolved to incorporate the Multi-party Computation Protocol (MCP). The agent, named Maya, provides a conversational interface for ordering drinks, with features including real-time streaming voice chat, menu management, and simulated transactions.

## Structure
- `src/`: Core source code with modular organization (conversation, llm, rag, voice, ui, etc.)
- `tests/`: Test files for various components using pytest
- `assets/`: Static resources including avatar images and memory files
- `config/`: Configuration files separate from code
- `data/`: Organized storage for different data types
- `examples/`: Implementation references
- `notebooks/`: Experimentation and analysis
- `monitoring/`: Monitoring setup with Grafana

## Language & Runtime
**Language**: Python
**Version**: 3.12.9 (specified in .python-version)
**Build System**: setuptools
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- google-generativeai (≥0.8.0): Google GenAI SDK
- langchain-google-genai (≥2.0.10): LangChain integration
- gradio (≥4.0.0): Web UI framework
- cartesia (≥2.0.0): Text-to-speech functionality
- tenacity (≥8.2.3): Retry logic for API calls
- modal: Deployment framework

**Development Dependencies**:
- pytest: Testing framework
- ruff: Python linter

## Build & Installation
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py

# Alternative: use the convenience script
./run_maya.sh
```

## Deployment
**Framework**: Modal Labs
**Configuration**: 
- Memory: Configurable via MODAL_MEMORY_MB (default: 4096)
- Scaling: Configurable via MODAL_MAX_CONTAINERS (default: 3)
**Commands**:
```bash
# Development
modal serve deploy.py

# Production deployment
modal deploy deploy.py
```

## Testing
**Framework**: pytest
**Test Location**: tests/ directory
**Naming Convention**: test_*.py
**Run Command**:
```bash
pytest
```

## Main Files
**Entry Points**:
- main.py: Local application entry point
- deploy.py: Modal deployment entry point

**Core Components**:
- src/llm/client.py: LLM client wrapper
- src/voice/tts.py: Text-to-speech functionality
- src/ui/launcher.py: Gradio interface setup
- src/rag/: Retrieval-augmented generation components
- src/conversation/: Conversation management