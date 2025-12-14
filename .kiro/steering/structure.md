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
│   ├── llm/                # LLM integration
│   │   ├── client.py       # Unified GenAI client wrapper
│   │   ├── prompts.py      # Prompt templates
│   │   └── tools.py        # Function calling tools
│   ├── memvid/             # Memvid RAG implementation
│   │   ├── config.py
│   │   ├── encoder.py
│   │   ├── retriever.py
│   │   └── utils.py
│   ├── rag/                # RAG pipeline
│   │   ├── embeddings.py
│   │   ├── memvid_pipeline.py
│   │   ├── memvid_store.py
│   │   ├── pipeline.py
│   │   ├── retrieval.py
│   │   └── vector_store.py
│   ├── ui/                 # Gradio UI
│   │   ├── components.py
│   │   ├── handlers.py
│   │   └── launcher.py
│   ├── utils/              # Shared utilities
│   │   ├── errors.py       # Error classification helpers
│   │   ├── helpers.py
│   │   └── state_manager.py
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

- **Unified LLM client**: `src/llm/client.py` centralizes all GenAI API interactions
- **Graceful fallbacks**: RAG uses Memvid → FAISS → no-RAG chain
- **Error handling**: `src/utils/errors.py` provides consistent error classification
- **Test stubs**: `tests/conftest.py` stubs Google SDKs for offline testing
- **Config from env**: All API keys and model settings via environment variables
