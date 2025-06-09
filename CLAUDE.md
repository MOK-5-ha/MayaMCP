# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MayaMCP is an AI bartending agent named "Maya" that works at the philosophical bar "MOK 5-ha" (pronounced "Moksha"). The project demonstrates advanced generative AI capabilities including conversational agents, RAG, function calling, and text-to-speech integration.

## Development Setup

### Installation
```bash
pip install -r requirements.txt
```

### Running the Application
The application is now modular and can be run with:
```bash
./run_maya.sh
```

Or manually:
```bash
python main.py
```

### Development Commands
- **Run application**: `python main.py`
- **Run with development setup**: `./run_maya.sh`
- **Install dependencies**: `pip install -r requirements.txt`
- **Create virtual environment**: `python3 -m venv venv`

### Legacy Notebook
The original implementation is preserved in `notebooks/bartending-agent-maya.ipynb` for reference.

## Architecture

### Current Implementation (Modular Functional)
The application follows a modular functional architecture with these key components:

**RAG System:**
- FAISS vector database for personality responses
- Google Embedding API (embedding-001) for document vectorization
- 10 pre-defined personality documents for small talk enhancement

**LLM Integration:**
- Google Gemini 2.5 Flash model via LangChain ChatGoogleGenerativeAI
- Tool binding for 10+ specialized bartending functions
- Conversation state management across greeting/ordering/small-talk phases

**Function Calling Tools:**
- `get_menu()` - Drink catalog with pricing and modifiers
- `add_to_order()` - Order management with quantity/modifiers support
- `get_bill()` / `pay_bill()` - Billing and payment processing
- `add_tip()` - Tip calculation (percentage or fixed amount)
- `get_recommendation()` - Preference-based drink suggestions

**Voice Integration:**
- Cartesia API for text-to-speech conversion
- Automatic audio generation for all Maya responses
- Pronunciation optimization ("MOK 5-ha" → "Moksha")

**Conversation Management:**
- 4-phase conversation flow: greeting → order_taking → small_talk → reorder_prompt
- Global state tracking for turn counts and conversation phase
- 4-turn small talk cycle between orders

### Modular Architecture (Current)
The `src/` directory structure contains the implemented modular components:

```
src/
├── config/          # Configuration management (API keys, logging, model config)
├── rag/            # RAG system (embeddings, vector store, retrieval, pipeline)
├── llm/            # LLM integration (client, tools, prompts)
├── conversation/   # Conversation management (processor, phase manager)
├── voice/          # TTS integration (Cartesia client, audio generation)
├── ui/             # Gradio interface (handlers, components, launcher)
└── utils/          # Utilities (state management, helpers)
```

**Key Modules:**
- `src/config/` - Environment and API key management
- `src/rag/` - Complete RAG pipeline with FAISS vector search
- `src/llm/tools.py` - All 10 bartending function tools
- `src/conversation/processor.py` - Main conversation orchestration
- `src/voice/tts.py` - Cartesia TTS integration
- `src/ui/launcher.py` - Gradio interface setup

## API Requirements

**Required API Keys:**
- `GOOGLE_API_KEY` - For Gemini LLM and embedding models
- `CARTESIA_API_KEY` - For text-to-speech functionality

Keys should be set as Kaggle secrets when running in Kaggle environment, or as environment variables locally.

## Key Design Patterns

**Global State Management:**
- `conversation_state` tracks conversation phase and turn counts
- `order_history` maintains persistent order data across session
- `current_process_order_state` provides tool-accessible state during processing

**RAG Pipeline:**
1. Query embedding generation
2. FAISS similarity search against personality documents
3. Context-aware response generation with retrieved passages
4. Fallback to direct LLM responses for order-related queries

**Tool Execution Loop:**
The `process_order()` function implements a tool-calling loop where the LLM can request multiple tool executions before providing a final response to the user.

## Development Considerations

**Functional Programming Architecture:**
The codebase follows functional programming principles with pure functions and minimal global state. Each module exposes clear functional interfaces.

**State Management:**
Global state is managed through `src/utils/state_manager.py` with functions for conversation tracking and order management. This approach works for single-user applications but would need session management for multi-user deployment.

**Voice Integration:**
Audio autoplay depends on browser settings. The interface works without audio but voice responses enhance the experience significantly.

**Menu System:**
The menu is defined in `src/llm/tools.py` in the `get_menu()` function. Menu changes require updating the tool's return string and following the specific price format pattern.

**Configuration Management:**
All configuration is handled through environment variables loaded from `.env` file. See `src/config/` modules for configuration management.

**Error Handling:**
The application includes comprehensive error handling with fallbacks for RAG and TTS failures, ensuring Maya continues to function even when external services are unavailable.