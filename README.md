# MayaMCP

Originally created as a capstone project for Kaggle's Gen AI Intensive Course Q1 2025. Meant to demonstrate the skills in generative AI we've learned over the course of a week with a project of our own choosing that utilized at least 5 of those skills. Had 16 days to complete it.

![Image](https://github.com/user-attachments/assets/f89cc02e-e02a-4595-af78-7c87263db632)

After obtaining our Gen AI certificates from completing and submitting the first version of our service-working AI agent, we sought to complete it. Here in June, Gradio & Huggingface are holding an Agents & MCP hackathon, with multiple AI inference engine & foundation labs participating in the way of providing participants with free credits to build with throughout the duration of the competition.

![Image](https://github.com/user-attachments/assets/be6656c8-b338-4a7a-80df-dca6abbdfe34)

So now this project has taken to the MCP turn. Where Anthropic's new protocol is taking the AI development by storm, creating yet another new paradigm is this ever-accelerating industry.

This second iteration of Maya, our AI agent, will be bolstered with the power of MCP, open-source AI frameworks, and hardware accelerators. Leaving behind the Google-based vendor lock-in it's initial iteration had with Gemini serving at it's base.

## Features

- Multi-turn conversational ordering system
- Menu management with several beverages
- Real-time streaming voice chat
- Gradio UI with agent avatar
- **Stripe Payment Integration** (Test Mode)
  - $1000 starting balance for simulated bar experience
  - Live tab counter overlay on Maya's avatar
  - Animated balance/tab updates with visual feedback
  - Tip selection (10%, 15%, 20%) with toggle behavior
  - Stripe payment links via MCP server (with mock fallback)
  - Low balance warnings (orange < $50, red at $0)

## Project Structure

- `config/`: Configuration files separate from code
- `src/`: Core source code with modular organization
- `data/`: Organized storage for different data types
- `examples/`: Implementation references
- `notebooks/`: Experimentation and analysis

## Architecture Updates

- Unified Google GenAI client wrapper in `src/llm/client.py` centralizes API key usage and generation config mapping for both LangChain and direct SDK calls
- Model validation at startup warns if `GEMINI_MODEL_VERSION` is unrecognized but continues to run
- Uses the Google AI Studio SDK (`google-generativeai`) for the free-tier Gemini API; LangChain integration via `langchain-google-genai`.

### Model Information

- Default model: Google Gemini 2.5 Flash Lite (model id: `gemini-2.5-flash-lite`)
- You can override the model via `GEMINI_MODEL_VERSION` in your `.env`

## Security

Maya features a built-in security layer powered by `llm-guard` that protects against:

- **Prompt Injection**: Detects and blocks malicious inputs attempting to manipulate the agent.
- **Input/Output Toxicity**: Filters toxic content in both user inputs and agent responses.

The security features fail open to ensure availability if the scanning engine encounters errors.

To enable security features, ensure the optional dependencies are installed:

```bash
pip install ".[security]"
# or
pip install -r requirements.txt
```

## Setup

Follow these steps to get Maya running locally.

## Quick Start

1. Clone repository

```bash
git clone <repository-url>
cd MayaMCP
```

1. Create `.env` file with your API keys:

```bash
# API Keys
GEMINI_API_KEY=your_google_api_key_here
CARTESIA_API_KEY=your_cartesia_api_key_here

# Model Configuration (optional)
GEMINI_MODEL_VERSION=gemini-2.5-flash-lite
TEMPERATURE=0.7
MAX_OUTPUT_TOKENS=2048

### Environment Configuration (optional)
PYTHON_ENV=development
DEBUG=True
```

1. Install and run Maya (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
mayamcp
```

Alternative run:

```bash
python main.py
```

Legacy script (optional):

```bash
./run_maya.sh
```

Note: `pip install -e .` installs dependencies from `requirements.txt` and sets up the `mayamcp` console command.

Note: `pip install -r requirements.txt` installs the Google AI Studio SDK (`google-generativeai`) used throughout `src/` and the LangChain integration. If `google-genai` is present, it is not used in this project.

## API Keys Required

### Google Gemini API

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Add to `.env` as `GEMINI_API_KEY`

### Cartesia TTS API

1. Visit [Cartesia](https://cartesia.ai/)
2. Sign up for free tier
3. Generate API key
4. Add to `.env` as `CARTESIA_API_KEY`

### Stripe API (Optional - for real payment links)

The payment feature works out of the box with mock payments. For real Stripe integration:

1. Visit [Stripe Dashboard](https://dashboard.stripe.com/register)
2. Create a free account (no credit card required)
3. Ensure **Test Mode** is enabled (toggle in top-right)
4. Go to **Developers → API Keys**
5. Copy your test secret key (`sk_test_...`)
6. Configure the Stripe MCP server (see below)

> ⚠️ **Important**: Only use test mode keys. The implementation enforces test mode for safety.

#### Stripe MCP Server Setup

Create `.kiro/settings/mcp.json` (or copy from `.kiro/settings/mcp.json.example`):

```json
{
  "mcpServers": {
    "stripe": {
      "command": "uvx",
      "args": ["mcp-server-stripe"],
      "env": {
        "STRIPE_SECRET_KEY": "sk_test_YOUR_TEST_KEY_HERE"
      },
      "disabled": false,
      "autoApprove": ["create_payment_link", "get_payment_link"]
    }
  }
}
```

Without this configuration, Maya uses mock payment links (fully functional for demos).

#### Test Card Numbers

When testing payments, use Stripe's test cards:
- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- Any future expiry date and 3-digit CVC work.

Startup validation: On launch, Maya validates required API keys and logs clear, actionable messages if any are missing. The configured `GEMINI_MODEL_VERSION` is also checked against a known list; unrecognized models produce a warning without stopping the app.

## Usage

This section covers typical usage patterns.

### Running the Application

After setup, Maya will launch a Gradio web interface accessible at:

- Local: `http://localhost:7860`
- Public: Gradio will provide a shareable link

### Interacting with Maya

#### Ordering

- Example: "I'd like a martini on the rocks"

#### Checking order

- Example: "What's in my order?"

#### Recommendations

- Example: "Something fruity please"

#### Billing/Payment

- View bill: "What's my total?"
- Check balance: "What's my balance?"
- Add tip: Click tip buttons (10%, 15%, 20%) or say "Add a 20% tip"
- Pay: "I'll pay now"

### Tab Counter & Balance Display

Maya's avatar includes a real-time tab overlay showing:
- **Tab**: Running total of your drink orders
- **Balance**: Remaining funds (starts at $1000)
- **Tip buttons**: Quick-select 10%, 15%, or 20% tip
- **Visual feedback**: Animated count-up effects when values change
- **Low balance warnings**: Orange text below $50, red at $0

The overlay updates automatically as you order drinks and is positioned at the bottom-left of Maya's avatar.

### Voice Features

Maya speaks! Enable audio in your browser to hear her responses.

## Testing

This project includes comprehensive tests for all major components. Tests are organized in the `tests/` directory and use pytest for test discovery and execution.

### Running Tests

#### Option 1: Using pytest directly (Recommended)

- Run tests: `pytest`
- Optional: coverage `pytest --cov` or verbose `pytest -v`

#### Option 2: Using pip install -e (Development mode)

- Install in editable mode: `pip install -e .`
- Run tests: `pytest`

Prerequisites: Python 3.12+ and pip installed; activate your virtual environment if using one.

#### Option 3: Using PYTHONPATH (Alternative)


### Test Organization

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions and end-to-end workflows
- **Memvid Tests**: Test RAG functionality and document retrieval
- **LLM Tests**: Test language model integration and prompt handling
- **UI Tests**: Test user interface components and handlers

### Test Configuration

The project uses `pytest.ini` for test configuration with the following features:

- Automatic test discovery in the `tests/` directory
- Custom markers for test categorization
- Strict configuration enforcement
- Colorized output for better readability
- Warning suppression for cleaner test output

### Writing Tests

When writing new tests:

1. Place test files in the `tests/` directory
2. Use descriptive test names following the `test_*.py` pattern
3. Use appropriate pytest markers to categorize tests
4. Include both positive and negative test cases
5. Mock external dependencies when possible
6. Use descriptive assertion messages

Example test structure:

```python
# tests/test_bartender.py
"""Minimal example tests for bartender order processing."""


def test_order_processing_success():
    """Order with a valid drink should be processed successfully."""
    # TODO: replace with real setup and assertions
    pass


def test_order_processing_invalid_drink():
    """Ordering an unknown drink should be handled gracefully."""
    # TODO: replace with real setup and assertions
    pass
```

### CI/CD Integration

Tests are designed to run in CI environments with:

- No external API dependencies for unit tests
- Mocked third-party services for integration tests
- Configurable test execution based on available resources
- Proper exit codes for build pipeline integration

### Troubleshooting

**Import Errors**: If you encounter import errors, ensure you're using one of the recommended test methods above. The `tests/conftest.py` file automatically handles path setup for pytest runs.

**Missing Dependencies**: Install requirements and test tooling:

```bash
pip install -r requirements.txt
pip install pytest pytest-mock pytest-cov
```

Example:
```bash
# optional: create and activate a clean virtual environment
python -m venv .venv && source .venv/bin/activate

# install project and test dependencies
pip install -r requirements.txt
pip install pytest pytest-mock pytest-cov

# run tests
pytest -q
```

**API Key Issues**: Most tests use mocked services, but some integration tests may require API keys. Check individual test files for specific requirements.

## Error Handling and Graceful Fallbacks

- API call resilience: Specific handling for rate limits (429), authentication/authorization (401/403), and network timeouts; exponential backoff retries via tenacity; rich logging
- RAG fallbacks: Memvid -> FAISS -> no RAG, with warnings and safe empty results instead of crashes
- LLM and tool calling: Guards for missing/invalid responses, parameter validation for tool calls, and bartender-friendly fallback messages on failures
- TTS resilience: If Cartesia TTS fails, Maya responds with text-only; retry logic for transient errors
- User experience: Errors never break the conversational flow; logs include enough context for debugging without exposing sensitive information

## Deployment on Modal

This project includes a Modal Labs deployment (see `deploy.py`). You can use the Modal CLI to develop and deploy:

- Development: `modal serve deploy.py`
- Deploy: `modal deploy deploy.py`

### Resource configuration (environment variables)

The deployment function reads the following environment variables to configure resources without code changes:

- `MODAL_MEMORY_MB` (default: `4096`)
  - Container memory in megabytes (e.g., `8192` for 8 GB)
- `MODAL_MAX_CONTAINERS` (default: `3`)
  - Maximum number of containers for autoscaling/concurrency (e.g., `5`)

You can set these environment variables in your deployment environment (e.g., Modal project/environment settings) to tune resource usage as you monitor real traffic.

### Observability and tuning

At startup, the service logs the configured resource values and attempts to read cgroups for memory usage:

- `Configured resources: MEMORY_MB=..., MAX_CONTAINERS=...`
- `Container memory usage at start: X.Y MB / Z.W MB`

Use these to:

- Validate your configuration took effect
- Monitor headroom vs. actual usage
- Iterate on `MODAL_MEMORY_MB` and `MODAL_MAX_CONTAINERS` based on load and p95 latency

API keys (`GEMINI_API_KEY`, `CARTESIA_API_KEY`) are still expected via environment variables/secrets as before.

### Deployment checklist

Use this quick checklist when deploying on Modal:

- API keys configured
  - `GEMINI_API_KEY`
  - `CARTESIA_API_KEY`
- Resource tuning (optional)
  - `MODAL_MEMORY_MB` (e.g., 4096, 8192)
  - `MODAL_MAX_CONTAINERS` (e.g., 3, 5)
- Expected startup logs
  - `Configured resources: MEMORY_MB=..., MAX_CONTAINERS=...`
  - `Container memory usage at start: ...`
- Monitoring
  - Scrape `GET /metrics` (Prometheus format) for:
    - `maya_config_memory_mb`
    - `maya_config_max_containers`
    - `maya_container_memory_usage_bytes`
    - `maya_container_memory_limit_bytes`

### Prometheus scrape configuration example

Add a job to your Prometheus `scrape_configs` that points to your deployed Modal app URL and the `/metrics` path. Replace `<modal-app-host>` with the hostname Modal gives you (no protocol):

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'maya-mcp'
    scrape_interval: 15s
    static_configs:
      - targets: ['<modal-app-host>']
    metrics_path: /metrics
    scheme: https
```

Exposed metrics (subset):

- `maya_config_memory_mb` (gauge)
- `maya_config_max_containers` (gauge)
- `maya_container_memory_usage_bytes` (gauge)
- `maya_container_memory_limit_bytes` (gauge)
- `maya_container_cpu_usage_seconds_total` (counter)
- `maya_process_uptime_seconds` (gauge)
