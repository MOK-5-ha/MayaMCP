# MayaMCP Project Structure

```
MayaMCP/
├── src/                    # Main source code
│   ├── config/             # Configuration management
│   │   ├── api_keys.py     # API key retrieval from env
│   │   ├── logging_config.py
│   │   └── model_config.py # LLM model settings
│   ├── conversation/       # Conversation handling
│   │   ├── phase_manager.py
│   │   └── processor.py
│   ├── handlers/           # Request handlers
│   ├── llm/                # LLM integration
│   │   ├── client.py       # Unified GenAI client wrapper
│   │   ├── prompts.py      # Prompt templates
│   │   ├── session_registry.py # Lazy loading for BYOK mode
│   │   └── tools.py        # Function calling tools
│   ├── media/              # Media utilities
│   ├── memvid/             # Memvid RAG implementation
│   │   ├── config.py
│   │   ├── encoder.py
│   │   ├── retriever.py
│   │   └── utils.py
│   ├── payments/           # Stripe MCP client and payment logic
│   ├── prompt_engineering/ # Prompt templates
│   ├── rag/                # RAG pipeline
│   │   ├── embeddings.py
│   │   ├── memvid_pipeline.py
│   │   ├── memvid_store.py
│   │   ├── pipeline.py
│   │   ├── retrieval.py
│   │   └── vector_store.py
│   ├── security/           # Input/output scanning and encryption
│   ├── ui/                 # Gradio UI
│   │   ├── components.py
│   │   ├── handlers.py
│   │   └── launcher.py
│   ├── utils/              # Shared utilities
│   │   ├── errors.py       # Error classification helpers
│   │   ├── helpers.py
│   │   └── state_manager.py # Thread-safe payment locking
│   ├── voice/              # TTS integration
│   │   └── tts.py
│   └── mayamcp_cli.py      # CLI entry point
├── tests/                  # Test suite (pytest)
│   ├── conftest.py         # Test fixtures and SDK stubs
│   └── test_*.py           # Test modules
├── assets/                 # Static assets (avatar, media)
├── config/                 # Runtime configuration files
├── data/                   # Data storage
├── notebooks/              # Jupyter notebooks
├── deploy.py               # Modal deployment script
├── main.py                 # Application entry point
├── pyproject.toml          # Project metadata and tool config
└── requirements.txt        # Dependencies
```

## Key Patterns

- **Unified LLM client**: `src/llm/client.py` centralizes all GenAI API interactions.
- **Graceful fallbacks**: RAG uses Memvid → FAISS → no-RAG chain.
- **BYOK mode**: Per-session LLM/TTS clients are lazily created via `src/llm/session_registry.py`.
- **Payment state**: Thread-safe per-session locking with atomic updates (`src/utils/state_manager.py`).
- **Security scanning**: Inputs/outputs are checked for prompt injection and toxicity (`src/security/`).
- **Error handling**: `src/utils/errors.py` provides consistent error classification.
- **Test stubs**: `tests/conftest.py` stubs Google SDKs for offline testing.
- **Config from env**: All API keys and model settings via environment variables.
