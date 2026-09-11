# MayaMCP Supreme Project Constitution

## Project Overview
MayaMCP is an AI bartending agent (v2.0.0) with conversational drink ordering, voice synthesis, simulated payments, and contextual suggestion chips. It uses Google Gemini (via `google-genai` and `google-adk`) for LLM, Cartesia for TTS, FAISS/Memvid for RAG, and Coinbase CDP AgentKit for crypto payments. The UI is built with Gradio with dynamic suggestion chips, and API resilience is handled by `tenacity`.

## Repository Layout
```
src/
├── config/          # API keys, logging, model settings
├── conversation/    # Phase management, message processing, chip generation
├── llm/             # Gemini client, prompts, function tools, session registry
├── memvid/          # Memvid RAG implementation
├── payments/        # Coinbase CDP crypto payment client and logic
├── rag/             # RAG pipeline (embeddings, retrieval, vector store)
├── routers/         # FastAPI REST & SSE v1 API routers (chat, payments, session)
├── schemas/         # Pydantic v2 data transfer schemas
├── security/        # Input/output scanning, encryption, scan config
├── ui/              # Gradio components, handlers, tab overlay, BYOK modal
├── utils/           # Errors, helpers, state management
└── voice/           # Cartesia TTS integration
tests/               # pytest suite (unit, integration, property-based, BDD, API)
  ├── behavior/      # BDD test suite with pytest-bdd (Gherkin scenarios)
  └── conftest.py    # Shared fixtures and SDK stubs for offline testing
assets/              # Static files (avatar, media)
deploy.py            # Modal Labs deployment
run_maya.sh          # Dev runner script
```

---

## Core Architecture Invariants

1. **100% GCP Vertex AI Mode Vendor Lock-in**: The application operates exclusively in GCP Vertex AI Mode using GCP billing credits (`GCP_PROJECT`, `GCP_LOCATION`, `GEMINI_TIER=paid`). Google AI Studio API Key Mode and free-tier throttles are permanently removed.
2. **Deprecated Environment Variable Literal Prohibition**: The exact literal string identifiers for legacy AI Studio API keys (such as `GEMINI` + `_API_KEY`, `LLM` + `_API_KEY`, and `BACKUP_LLM` + `_API_KEY`) are strictly prohibited repository-wide in all files. Use generalized descriptions in text and dynamic string concatenation in assertions.
3. **Unified LLM Client**: All GenAI calls go through `src/llm/client.py`. Never call the Google SDK directly elsewhere. Always use `get_genai_client()` or `call_gemini_api()`.
4. **Thread-Safe Session & Payment Locking**: Always acquire per-session `RLock` before modifying payment state or session metadata.
5. **Graceful Fallbacks & Fault Isolation**: Memvid → FAISS → no-RAG; Cartesia → text-only; Coinbase CDP → mock crypto payments. Suggestion chip generation is parallel and non-blocking; failures must never break response streaming.
6. **CLI-First Agentic Developer Workflow & MCP Scope Boundaries (Development Environment)**: This invariant strictly governs developer tooling and AI coding assistant workflows (how Antigravity, subagents, and bots build and maintain this repository), NOT the runtime architecture of Maya herself (which runs as a FastAPI/Modal cloud service). Coding agents must operate on a CLI-first, stateful-MCP-sparing architecture: MCP servers are strictly reserved for persistent stateful daemons, AST knowledge graphs (`codebase-memory-mcp`), live browser sessions (`chrome-devtools`), and approved developer gateways (`context7`, `greptile`). All version control, PR management, cloud deployments (`modal`), and build tasks MUST execute through native CLI tools (`gh`, `git`, `modal`) paired with lightweight companion skills rather than stateless MCP servers.
7. **Architectural Perpetuation & Downstream Agent Invariant**: Child agents, subagents, and automated workflows MUST perpetuate this developer CLI-first pattern. Strictly reject adding stateless MCP servers (e.g. for GitHub, Git, Jira, Slack, Linear) whenever a mature CLI or scriptable API exists. Future workflows must defend these boundaries and propagate this discipline across all project rules.

---

## Development Quickstart

### Setup & Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```
Always activate the `.venv` before running any commands.

### Running the Application
```bash
mayamcp                 # Console script
./run_maya.sh           # Development runner
modal serve deploy.py   # Modal Labs Dev
modal deploy deploy.py  # Modal Labs Prod
```

### Testing & Verification
```bash
pytest                    # Full test suite
pytest --cov              # With coverage report
pytest -m unit            # Unit tests only
pytest -m integration     # Integration tests only
pytest -m bdd             # BDD acceptance tests only
pytest -m "not slow"      # Skip slow property tests

# Headless Evals
python scripts/run_evals.py
python tests/eval/eval_crypto_payment.py
```

### Linting & Formatting
```bash
ruff check src/ tests/    # Lint (line-length: 88, target: py310)
mypy src/                 # Type checking
```

---

## Environment Variables

Maya operates in 100% GCP Vertex AI Mode using Application Default Credentials (ADC) and GCP billing credits.

### Required
- `GCP_PROJECT` — Google Cloud Platform Project ID
- `GCP_LOCATION` — GCP Location (defaults to `global`)
- `GEMINI_TIER` — Locked to `paid` (high-throughput concurrency quota)
- `CARTESIA_API_KEY` — Cartesia TTS API key

### Optional
- `GEMINI_MODEL_VERSION` — defaults to `gemini-3.5-flash-lite`
- `TEMPERATURE` — defaults to `1.0`
- `MAX_OUTPUT_TOKENS` — defaults to `8192`
- `MAYA_MASTER_KEY` — Fernet key for encrypting session data
- `CDP_API_KEY_ID` — Coinbase CDP API key ID
- `CDP_API_KEY_SECRET` — Coinbase CDP API key secret
- `CDP_MERCHANT_PRIVATE_KEY` — Wallet private key for Base Sepolia (optional)
- `CDP_RECEIVER_ADDRESS` — Merchant wallet address (optional)

---

## Constitution & Rule Maintenance Protocol

This section governs how AI agents must interpret, maintain, and update repository rules:

1. **Root `AGENTS.md` Scope**: Reserved strictly for core project identity, primary architectural invariants, environment quickstarts, and rule navigation pointers. **Do not add granular function, component, or test rules directly to this file.**
2. **`.agents/rules/` Scope**: Detailed implementation guardrails, DB transaction guidelines, logging privacy, BDD/test patterns, UI event chaining, and hygiene MUST be added to or updated within modular files under `.agents/rules/`.
3. **Proposal Workflow**: Before modifying project rules (e.g., via `/learn`, slash commands, or code review resolutions), AI agents MUST:
   - Check existing workspace rules under `.agents/rules/`.
   - Create or update an implementation plan or learning proposal artifact (within the conversation artifact directory) outlining the rule classification, rationale, and precise text diffs.
   - Set `request_feedback: true` on the artifact and obtain explicit user approval before writing rule changes to disk.

---

## Modular Rule Index & Navigation

Detailed engineering rules are organized modularly in the [`.agents/rules/`](.agents/rules/) directory:

- [**Architecture & Security Rules**](.agents/rules/architecture_and_security.md): Concurrency locking, distributed session store, optimistic payments, async SSE unblocking, security scanning, batch caching, token budgeting, and developer tooling governance (CLI-first workflow & stateful MCP boundaries).
- [**UI, Suggestion Chips & Voice Rules**](.agents/rules/ui_and_voice.md): Parallel suggestion chip generation, Gradio state propagation, event chaining (`.then()`), Phaser 3 asset lifecycle, Cartesia TTS streaming, and WCAG accessibility.
- [**Testing, BDD & Evaluation Rules**](.agents/rules/testing_and_hygiene.md): Native SDK mocking, BDD Gherkin patterns, rate limit test safety, ADK stream mock event contracts, production invalidation testing, non-blocking streaming assertions, and Vertex AI evals.
- [**Style, Linting & Formatting Rules**](.agents/rules/style_and_formatting.md): Ruff rules, Mypy typing standards, conventional commits, pre-commit hygiene, GitHub CLI (`gh`) operational guardrails, and CLI output hygiene & token conservation protocol.

---

## Adding a New Tool
1. Define tool schema in `src/llm/tools.py`
2. Implement handler in `src/conversation/processor.py`
3. Add tests in `tests/`

---

## Don't (Supreme Behavioral Deny List)
- Call Google SDK directly outside `src/llm/client.py` (use `get_genai_client` or `call_gemini_api`)
- Use Google AI Studio API key mode or free-tier rate limits
- Hardcode API keys, credentials, or secrets in any file
- Skip error handling for external API calls or break the graceful fallback chain
- Add tests that require real external API calls without mocking
- Use Coinbase CDP mainnet keys in development (Base Sepolia testnet only)
- Modify payment or session state without acquiring the session `RLock`
- Directly commit or push changes to `main` or `master` (feature branches and PRs only)
- Autonomously merge pull requests
- Introduce or configure stateless MCP servers for Git, GitHub, Jira, Slack, Linear, or cloud management (use native CLI binaries: `gh`, `git`, `modal`, `gcloud`)
- Execute unprojected or unbounded CLI commands without output limits (`--json`, `--limit`, `--format`, or `head`/`jq` filtering)
- Tamper with git remotes (`git remote add/set-url/remove`) or add untrusted submodules (`git submodule add/update`)
- Eagerly materialize streaming generators using `list()` or list comprehensions
- Manually cancel mock futures or manipulate internal task states in test steps (always exercise the production trigger path)
- Test background task timeout/failure handling solely through direct helper calls without also asserting that the primary response stream generator completes promptly (< 0.5s)
