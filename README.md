# MayaMCP

Originally created as a capstone project for Kaggle's Gen AI Intensive Course Q1 2025. Meant to demonstrate the skills in generative AI we've learned over the course of a week with a project of our own choosing that utilized at least 5 of those skills. Had 16 days to complete it.

![Image](https://github.com/user-attachments/assets/f89cc02e-e02a-4595-af78-7c87263db632)

After obtaining our Gen AI certificates from completing and submitting the first version of our service-working AI agent, we sought to complete it. Here in June, Gradio & Huggingface are holding an Agents & MCP hackathon, with multiple AI inference engine & foundation labs participating in the way of providing participants with free credits to build with throughout the duration of the competition.

![Image](https://github.com/user-attachments/assets/be6656c8-b338-4a7a-80df-dca6abbdfe34)

So now this project has taken to the MCP turn. Where Anthropic's new protocol is taking the AI development by storm, creating yet another new paradigm is this ever accelerating industry.

This second iteration of Maya, our AI agent, will be bolstered with the power of MCP, open-source AI frameworks, and hardware accelerators. Leaving behind the Google-based vendor lock-in it's initial iteration had with Gemini serving at it's base.

## Features

- Multi-turn conversational ordering system
- Menu management with several beverages
- Real-time streaming voice chat
- Gradio UI with agent avatar
- MCP Stripe integration for simulation of transactions

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

1. Run Maya using the convenience script:

```bash
./run_maya.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

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
- Add tip: "Add a 20% tip"
- Pay: "I'll pay now"

### Voice Features

Maya speaks! Enable audio in your browser to hear her responses.

## Testing

This project includes comprehensive tests for all major components. Tests are organized in the  directory and use pytest for test discovery and execution.

### Running Tests

#### Option 1: Using pytest directly (Recommended)
Requirement already satisfied: pytest in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (8.4.1)
Requirement already satisfied: pytest-mock in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (3.15.1)
Requirement already satisfied: iniconfig>=1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest) (2.1.0)
Requirement already satisfied: packaging>=20 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest) (25.0)
Requirement already satisfied: pluggy<2,>=1.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest) (1.6.0)
Requirement already satisfied: pygments>=2.7.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest) (2.19.2)
Requirement already satisfied: pytest-cov in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (6.2.1)
Requirement already satisfied: pytest>=6.2.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest-cov) (8.4.1)
Requirement already satisfied: coverage>=7.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from coverage[toml]>=7.5->pytest-cov) (7.9.2)
Requirement already satisfied: pluggy>=1.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest-cov) (1.6.0)
Requirement already satisfied: iniconfig>=1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest>=6.2.5->pytest-cov) (2.1.0)
Requirement already satisfied: packaging>=20 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest>=6.2.5->pytest-cov) (25.0)
Requirement already satisfied: pygments>=2.7.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest>=6.2.5->pytest-cov) (2.19.2)

#### Option 2: Using pip install -e (Development mode)
Obtaining file:///Users/pretermodernist/MayaMCP
  Preparing metadata (setup.py): started
  Preparing metadata (setup.py): finished with status 'done'
Collecting google-generativeai>=0.8.0 (from mayamcp==2.0.0)
  Using cached google_generativeai-0.8.5-py3-none-any.whl.metadata (3.9 kB)
Collecting google-genai>=1.0.0 (from mayamcp==2.0.0)
  Using cached google_genai-1.38.0-py3-none-any.whl.metadata (43 kB)
Collecting langchain-google-genai>=2.0.10 (from mayamcp==2.0.0)
  Using cached langchain_google_genai-2.1.12-py3-none-any.whl.metadata (7.1 kB)
Collecting langchain-core>=0.3.50 (from mayamcp==2.0.0)
  Using cached langchain_core-0.3.76-py3-none-any.whl.metadata (3.7 kB)
Requirement already satisfied: python-dotenv>=1.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from mayamcp==2.0.0) (1.1.1)
Requirement already satisfied: requests>=2.31.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from mayamcp==2.0.0) (2.32.4)
Collecting websockets>=12.0 (from mayamcp==2.0.0)
  Using cached websockets-15.0.1-cp313-cp313-macosx_10_13_x86_64.whl.metadata (6.8 kB)
Requirement already satisfied: tenacity>=8.2.3 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from mayamcp==2.0.0) (8.5.0)
Requirement already satisfied: gradio>=4.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from mayamcp==2.0.0) (5.9.1)
Collecting cartesia>=2.0.0 (from mayamcp==2.0.0)
  Using cached cartesia-2.0.9-py3-none-any.whl.metadata (20 kB)
Collecting matplotlib>=3.0.0 (from mayamcp==2.0.0)
  Using cached matplotlib-3.10.6-cp313-cp313-macosx_10_13_x86_64.whl.metadata (11 kB)
Requirement already satisfied: pillow>=8.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from mayamcp==2.0.0) (11.3.0)
Collecting qrcode[pil] (from mayamcp==2.0.0)
  Using cached qrcode-8.2-py3-none-any.whl.metadata (17 kB)
Collecting opencv-python (from mayamcp==2.0.0)
  Using cached opencv_python-4.12.0.88-cp37-abi3-macosx_13_0_x86_64.whl.metadata (19 kB)
Collecting faiss-cpu>=1.10.0 (from mayamcp==2.0.0)
  Using cached faiss_cpu-1.12.0-cp313-cp313-macosx_13_0_x86_64.whl.metadata (5.1 kB)
Requirement already satisfied: numpy>=1.24.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from mayamcp==2.0.0) (2.2.6)
Requirement already satisfied: aiohttp>=3.10.10 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from cartesia>=2.0.0->mayamcp==2.0.0) (3.10.11)
Collecting audioop-lts==0.2.1 (from cartesia>=2.0.0->mayamcp==2.0.0)
  Using cached audioop_lts-0.2.1-cp313-abi3-macosx_10_13_x86_64.whl.metadata (1.6 kB)
Requirement already satisfied: httpx>=0.21.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from cartesia>=2.0.0->mayamcp==2.0.0) (0.28.1)
Collecting httpx-sse==0.4.0 (from cartesia>=2.0.0->mayamcp==2.0.0)
  Using cached httpx_sse-0.4.0-py3-none-any.whl.metadata (9.0 kB)
Collecting iterators>=0.2.0 (from cartesia>=2.0.0->mayamcp==2.0.0)
  Using cached iterators-0.2.0-py3-none-any.whl.metadata (2.7 kB)
Requirement already satisfied: pydantic>=1.9.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from cartesia>=2.0.0->mayamcp==2.0.0) (2.11.7)
Requirement already satisfied: pydantic-core<3.0.0,>=2.18.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from cartesia>=2.0.0->mayamcp==2.0.0) (2.33.2)
Requirement already satisfied: pydub>=0.25.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from cartesia>=2.0.0->mayamcp==2.0.0) (0.25.1)
Requirement already satisfied: typing_extensions>=4.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from cartesia>=2.0.0->mayamcp==2.0.0) (4.14.1)
Requirement already satisfied: aiohappyeyeballs>=2.3.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->mayamcp==2.0.0) (2.6.1)
Requirement already satisfied: aiosignal>=1.1.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->mayamcp==2.0.0) (1.3.2)
Requirement already satisfied: attrs>=17.3.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->mayamcp==2.0.0) (25.3.0)
Requirement already satisfied: frozenlist>=1.1.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->mayamcp==2.0.0) (1.7.0)
Requirement already satisfied: multidict<7.0,>=4.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->mayamcp==2.0.0) (6.4.4)
Requirement already satisfied: yarl<2.0,>=1.12.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->mayamcp==2.0.0) (1.20.1)
Requirement already satisfied: idna>=2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from yarl<2.0,>=1.12.0->aiohttp>=3.10.10->cartesia>=2.0.0->mayamcp==2.0.0) (3.10)
Requirement already satisfied: propcache>=0.2.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from yarl<2.0,>=1.12.0->aiohttp>=3.10.10->cartesia>=2.0.0->mayamcp==2.0.0) (0.3.2)
Requirement already satisfied: packaging in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from faiss-cpu>=1.10.0->mayamcp==2.0.0) (25.0)
Requirement already satisfied: anyio<5.0.0,>=4.8.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-genai>=1.0.0->mayamcp==2.0.0) (4.9.0)
Collecting google-auth<3.0.0,>=2.14.1 (from google-genai>=1.0.0->mayamcp==2.0.0)
  Using cached google_auth-2.40.3-py2.py3-none-any.whl.metadata (6.2 kB)
Requirement already satisfied: sniffio>=1.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from anyio<5.0.0,>=4.8.0->google-genai>=1.0.0->mayamcp==2.0.0) (1.3.1)
Collecting cachetools<6.0,>=2.0.0 (from google-auth<3.0.0,>=2.14.1->google-genai>=1.0.0->mayamcp==2.0.0)
  Using cached cachetools-5.5.2-py3-none-any.whl.metadata (5.4 kB)
Collecting pyasn1-modules>=0.2.1 (from google-auth<3.0.0,>=2.14.1->google-genai>=1.0.0->mayamcp==2.0.0)
  Using cached pyasn1_modules-0.4.2-py3-none-any.whl.metadata (3.5 kB)
Collecting rsa<5,>=3.1.4 (from google-auth<3.0.0,>=2.14.1->google-genai>=1.0.0->mayamcp==2.0.0)
  Using cached rsa-4.9.1-py3-none-any.whl.metadata (5.6 kB)
Requirement already satisfied: certifi in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from httpx>=0.21.2->cartesia>=2.0.0->mayamcp==2.0.0) (2025.7.14)
Requirement already satisfied: httpcore==1.* in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from httpx>=0.21.2->cartesia>=2.0.0->mayamcp==2.0.0) (1.0.9)
Requirement already satisfied: h11>=0.16 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from httpcore==1.*->httpx>=0.21.2->cartesia>=2.0.0->mayamcp==2.0.0) (0.16.0)
Requirement already satisfied: annotated-types>=0.6.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pydantic>=1.9.2->cartesia>=2.0.0->mayamcp==2.0.0) (0.7.0)
Requirement already satisfied: typing-inspection>=0.4.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pydantic>=1.9.2->cartesia>=2.0.0->mayamcp==2.0.0) (0.4.1)
Requirement already satisfied: charset_normalizer<4,>=2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from requests>=2.31.0->mayamcp==2.0.0) (3.4.2)
Requirement already satisfied: urllib3<3,>=1.21.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from requests>=2.31.0->mayamcp==2.0.0) (2.5.0)
Collecting pyasn1>=0.1.3 (from rsa<5,>=3.1.4->google-auth<3.0.0,>=2.14.1->google-genai>=1.0.0->mayamcp==2.0.0)
  Using cached pyasn1-0.6.1-py3-none-any.whl.metadata (8.4 kB)
Collecting google-ai-generativelanguage==0.6.15 (from google-generativeai>=0.8.0->mayamcp==2.0.0)
  Using cached google_ai_generativelanguage-0.6.15-py3-none-any.whl.metadata (5.7 kB)
Collecting google-api-core (from google-generativeai>=0.8.0->mayamcp==2.0.0)
  Using cached google_api_core-2.25.1-py3-none-any.whl.metadata (3.0 kB)
Collecting google-api-python-client (from google-generativeai>=0.8.0->mayamcp==2.0.0)
  Using cached google_api_python_client-2.182.0-py3-none-any.whl.metadata (7.0 kB)
Requirement already satisfied: protobuf in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->mayamcp==2.0.0) (5.29.5)
Requirement already satisfied: tqdm in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->mayamcp==2.0.0) (4.67.1)
Collecting proto-plus<2.0.0dev,>=1.22.3 (from google-ai-generativelanguage==0.6.15->google-generativeai>=0.8.0->mayamcp==2.0.0)
  Using cached proto_plus-1.26.1-py3-none-any.whl.metadata (2.2 kB)
Requirement already satisfied: googleapis-common-protos<2.0.0,>=1.56.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-api-core->google-generativeai>=0.8.0->mayamcp==2.0.0) (1.70.0)
Requirement already satisfied: grpcio<2.0.0,>=1.33.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-api-core[grpc]!=2.0.*,!=2.1.*,!=2.10.*,!=2.2.*,!=2.3.*,!=2.4.*,!=2.5.*,!=2.6.*,!=2.7.*,!=2.8.*,!=2.9.*,<3.0.0dev,>=1.34.1->google-ai-generativelanguage==0.6.15->google-generativeai>=0.8.0->mayamcp==2.0.0) (1.73.1)
Collecting grpcio-status<2.0.0,>=1.33.2 (from google-api-core[grpc]!=2.0.*,!=2.1.*,!=2.10.*,!=2.2.*,!=2.3.*,!=2.4.*,!=2.5.*,!=2.6.*,!=2.7.*,!=2.8.*,!=2.9.*,<3.0.0dev,>=1.34.1->google-ai-generativelanguage==0.6.15->google-generativeai>=0.8.0->mayamcp==2.0.0)
  Using cached grpcio_status-1.75.0-py3-none-any.whl.metadata (1.1 kB)
INFO: pip is looking at multiple versions of grpcio-status to determine which version is compatible with other requirements. This could take a while.
  Using cached grpcio_status-1.74.0-py3-none-any.whl.metadata (1.1 kB)
  Using cached grpcio_status-1.73.1-py3-none-any.whl.metadata (1.1 kB)
  Using cached grpcio_status-1.73.0-py3-none-any.whl.metadata (1.1 kB)
  Using cached grpcio_status-1.72.2-py3-none-any.whl.metadata (1.1 kB)
  Using cached grpcio_status-1.72.1-py3-none-any.whl.metadata (1.1 kB)
  Using cached grpcio_status-1.71.2-py3-none-any.whl.metadata (1.1 kB)
Requirement already satisfied: aiofiles<24.0,>=22.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (23.2.1)
Requirement already satisfied: fastapi<1.0,>=0.115.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.115.6)
Requirement already satisfied: ffmpy in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.6.1)
Requirement already satisfied: gradio-client==1.5.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (1.5.2)
Requirement already satisfied: huggingface-hub>=0.25.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.34.4)
Requirement already satisfied: jinja2<4.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (3.1.6)
Requirement already satisfied: markupsafe~=2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (2.1.5)
Requirement already satisfied: orjson~=3.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (3.11.2)
Requirement already satisfied: pandas<3.0,>=1.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (2.3.0)
Requirement already satisfied: python-multipart>=0.0.18 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.0.20)
Requirement already satisfied: pyyaml<7.0,>=5.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (6.0.2)
Requirement already satisfied: ruff>=0.2.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.12.2)
Requirement already satisfied: safehttpx<0.2.0,>=0.1.6 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.1.6)
Requirement already satisfied: semantic-version~=2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (2.10.0)
Requirement already satisfied: starlette<1.0,>=0.40.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.41.3)
Requirement already satisfied: tomlkit<0.14.0,>=0.12.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.13.3)
Requirement already satisfied: typer<1.0,>=0.12 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.16.0)
Requirement already satisfied: uvicorn>=0.14.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->mayamcp==2.0.0) (0.34.0)
Requirement already satisfied: fsspec in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio-client==1.5.2->gradio>=4.0.0->mayamcp==2.0.0) (2025.5.1)
Collecting websockets>=12.0 (from mayamcp==2.0.0)
  Using cached websockets-14.2-cp313-cp313-macosx_10_13_x86_64.whl.metadata (6.8 kB)
Requirement already satisfied: python-dateutil>=2.8.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pandas<3.0,>=1.0->gradio>=4.0.0->mayamcp==2.0.0) (2.9.0.post0)
Requirement already satisfied: pytz>=2020.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pandas<3.0,>=1.0->gradio>=4.0.0->mayamcp==2.0.0) (2025.2)
Requirement already satisfied: tzdata>=2022.7 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pandas<3.0,>=1.0->gradio>=4.0.0->mayamcp==2.0.0) (2025.2)
Requirement already satisfied: click>=8.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from typer<1.0,>=0.12->gradio>=4.0.0->mayamcp==2.0.0) (8.2.1)
Requirement already satisfied: shellingham>=1.3.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from typer<1.0,>=0.12->gradio>=4.0.0->mayamcp==2.0.0) (1.5.4)
Requirement already satisfied: rich>=10.11.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from typer<1.0,>=0.12->gradio>=4.0.0->mayamcp==2.0.0) (14.1.0)
Requirement already satisfied: filelock in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from huggingface-hub>=0.25.1->gradio>=4.0.0->mayamcp==2.0.0) (3.18.0)
Requirement already satisfied: hf-xet<2.0.0,>=1.1.3 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from huggingface-hub>=0.25.1->gradio>=4.0.0->mayamcp==2.0.0) (1.1.8)
Collecting langsmith>=0.3.45 (from langchain-core>=0.3.50->mayamcp==2.0.0)
  Using cached langsmith-0.4.29-py3-none-any.whl.metadata (14 kB)
Collecting jsonpatch<2.0,>=1.33 (from langchain-core>=0.3.50->mayamcp==2.0.0)
  Using cached jsonpatch-1.33-py2.py3-none-any.whl.metadata (3.0 kB)
Collecting jsonpointer>=1.9 (from jsonpatch<2.0,>=1.33->langchain-core>=0.3.50->mayamcp==2.0.0)
  Using cached jsonpointer-3.0.0-py2.py3-none-any.whl.metadata (2.3 kB)
INFO: pip is looking at multiple versions of langchain-google-genai to determine which version is compatible with other requirements. This could take a while.
Collecting langchain-google-genai>=2.0.10 (from mayamcp==2.0.0)
  Using cached langchain_google_genai-2.1.11-py3-none-any.whl.metadata (6.7 kB)
  Using cached langchain_google_genai-2.1.10-py3-none-any.whl.metadata (7.2 kB)
Requirement already satisfied: filetype<2.0.0,>=1.2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from langchain-google-genai>=2.0.10->mayamcp==2.0.0) (1.2.0)
  Using cached langchain_google_genai-2.1.9-py3-none-any.whl.metadata (7.2 kB)
  Using cached langchain_google_genai-2.1.8-py3-none-any.whl.metadata (7.0 kB)
  Using cached langchain_google_genai-2.1.7-py3-none-any.whl.metadata (7.0 kB)
  Using cached langchain_google_genai-2.1.6-py3-none-any.whl.metadata (7.0 kB)
  Using cached langchain_google_genai-2.1.5-py3-none-any.whl.metadata (5.2 kB)
INFO: pip is still looking at multiple versions of langchain-google-genai to determine which version is compatible with other requirements. This could take a while.
  Using cached langchain_google_genai-2.1.4-py3-none-any.whl.metadata (5.2 kB)
  Using cached langchain_google_genai-2.1.3-py3-none-any.whl.metadata (4.7 kB)
  Using cached langchain_google_genai-2.1.2-py3-none-any.whl.metadata (4.7 kB)
  Using cached langchain_google_genai-2.1.1-py3-none-any.whl.metadata (4.7 kB)
  Using cached langchain_google_genai-2.1.0-py3-none-any.whl.metadata (3.6 kB)
INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
  Using cached langchain_google_genai-2.0.11-py3-none-any.whl.metadata (3.6 kB)
  Using cached langchain_google_genai-2.0.10-py3-none-any.whl.metadata (3.6 kB)
Collecting requests-toolbelt>=1.0.0 (from langsmith>=0.3.45->langchain-core>=0.3.50->mayamcp==2.0.0)
  Using cached requests_toolbelt-1.0.0-py2.py3-none-any.whl.metadata (14 kB)
Collecting zstandard>=0.23.0 (from langsmith>=0.3.45->langchain-core>=0.3.50->mayamcp==2.0.0)
  Using cached zstandard-0.25.0-cp313-cp313-macosx_10_13_x86_64.whl.metadata (3.3 kB)
Collecting contourpy>=1.0.1 (from matplotlib>=3.0.0->mayamcp==2.0.0)
  Using cached contourpy-1.3.3-cp313-cp313-macosx_10_13_x86_64.whl.metadata (5.5 kB)
Collecting cycler>=0.10 (from matplotlib>=3.0.0->mayamcp==2.0.0)
  Using cached cycler-0.12.1-py3-none-any.whl.metadata (3.8 kB)
Collecting fonttools>=4.22.0 (from matplotlib>=3.0.0->mayamcp==2.0.0)
  Using cached fonttools-4.60.0-cp313-cp313-macosx_10_13_x86_64.whl.metadata (111 kB)
Collecting kiwisolver>=1.3.1 (from matplotlib>=3.0.0->mayamcp==2.0.0)
  Using cached kiwisolver-1.4.9-cp313-cp313-macosx_10_13_x86_64.whl.metadata (6.3 kB)
Collecting pyparsing>=2.3.1 (from matplotlib>=3.0.0->mayamcp==2.0.0)
  Downloading pyparsing-3.2.5-py3-none-any.whl.metadata (5.0 kB)
Requirement already satisfied: six>=1.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from python-dateutil>=2.8.2->pandas<3.0,>=1.0->gradio>=4.0.0->mayamcp==2.0.0) (1.17.0)
Requirement already satisfied: markdown-it-py>=2.2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from rich>=10.11.0->typer<1.0,>=0.12->gradio>=4.0.0->mayamcp==2.0.0) (3.0.0)
Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from rich>=10.11.0->typer<1.0,>=0.12->gradio>=4.0.0->mayamcp==2.0.0) (2.19.2)
Requirement already satisfied: mdurl~=0.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich>=10.11.0->typer<1.0,>=0.12->gradio>=4.0.0->mayamcp==2.0.0) (0.1.2)
Collecting httplib2<1.0.0,>=0.19.0 (from google-api-python-client->google-generativeai>=0.8.0->mayamcp==2.0.0)
  Using cached httplib2-0.31.0-py3-none-any.whl.metadata (2.2 kB)
Collecting google-auth-httplib2<1.0.0,>=0.2.0 (from google-api-python-client->google-generativeai>=0.8.0->mayamcp==2.0.0)
  Using cached google_auth_httplib2-0.2.0-py2.py3-none-any.whl.metadata (2.2 kB)
Collecting uritemplate<5,>=3.0.1 (from google-api-python-client->google-generativeai>=0.8.0->mayamcp==2.0.0)
  Using cached uritemplate-4.2.0-py3-none-any.whl.metadata (2.6 kB)
Using cached cartesia-2.0.9-py3-none-any.whl (150 kB)
Using cached audioop_lts-0.2.1-cp313-abi3-macosx_10_13_x86_64.whl (27 kB)
Using cached httpx_sse-0.4.0-py3-none-any.whl (7.8 kB)
Using cached faiss_cpu-1.12.0-cp313-cp313-macosx_13_0_x86_64.whl (8.0 MB)
Using cached google_genai-1.38.0-py3-none-any.whl (245 kB)
Using cached google_auth-2.40.3-py2.py3-none-any.whl (216 kB)
Using cached cachetools-5.5.2-py3-none-any.whl (10 kB)
Using cached rsa-4.9.1-py3-none-any.whl (34 kB)
Using cached google_generativeai-0.8.5-py3-none-any.whl (155 kB)
Using cached google_ai_generativelanguage-0.6.15-py3-none-any.whl (1.3 MB)
Using cached google_api_core-2.25.1-py3-none-any.whl (160 kB)
Using cached grpcio_status-1.71.2-py3-none-any.whl (14 kB)
Using cached proto_plus-1.26.1-py3-none-any.whl (50 kB)
Using cached websockets-14.2-cp313-cp313-macosx_10_13_x86_64.whl (160 kB)
Using cached iterators-0.2.0-py3-none-any.whl (5.0 kB)
Using cached langchain_core-0.3.76-py3-none-any.whl (447 kB)
Using cached jsonpatch-1.33-py2.py3-none-any.whl (12 kB)
Using cached jsonpointer-3.0.0-py2.py3-none-any.whl (7.6 kB)
Using cached langchain_google_genai-2.0.10-py3-none-any.whl (41 kB)
Using cached langsmith-0.4.29-py3-none-any.whl (386 kB)
Using cached matplotlib-3.10.6-cp313-cp313-macosx_10_13_x86_64.whl (8.3 MB)
Using cached contourpy-1.3.3-cp313-cp313-macosx_10_13_x86_64.whl (293 kB)
Using cached cycler-0.12.1-py3-none-any.whl (8.3 kB)
Using cached fonttools-4.60.0-cp313-cp313-macosx_10_13_x86_64.whl (2.3 MB)
Using cached kiwisolver-1.4.9-cp313-cp313-macosx_10_13_x86_64.whl (66 kB)
Using cached pyasn1-0.6.1-py3-none-any.whl (83 kB)
Using cached pyasn1_modules-0.4.2-py3-none-any.whl (181 kB)
Downloading pyparsing-3.2.5-py3-none-any.whl (113 kB)
Using cached requests_toolbelt-1.0.0-py2.py3-none-any.whl (54 kB)
Using cached zstandard-0.25.0-cp313-cp313-macosx_10_13_x86_64.whl (795 kB)
Using cached google_api_python_client-2.182.0-py3-none-any.whl (14.2 MB)
Using cached google_auth_httplib2-0.2.0-py2.py3-none-any.whl (9.3 kB)
Using cached httplib2-0.31.0-py3-none-any.whl (91 kB)
Using cached uritemplate-4.2.0-py3-none-any.whl (11 kB)
Using cached opencv_python-4.12.0.88-cp37-abi3-macosx_13_0_x86_64.whl (57.3 MB)
Using cached qrcode-8.2-py3-none-any.whl (45 kB)
Installing collected packages: zstandard, websockets, uritemplate, qrcode, pyparsing, pyasn1, proto-plus, opencv-python, kiwisolver, jsonpointer, iterators, httpx-sse, fonttools, faiss-cpu, cycler, contourpy, cachetools, audioop-lts, rsa, requests-toolbelt, pyasn1-modules, matplotlib, jsonpatch, httplib2, grpcio-status, langsmith, google-auth, cartesia, langchain-core, google-genai, google-auth-httplib2, google-api-core, google-api-python-client, google-ai-generativelanguage, google-generativeai, langchain-google-genai, mayamcp
  Attempting uninstall: websockets
    Found existing installation: websockets 10.4
    Uninstalling websockets-10.4:
      Successfully uninstalled websockets-10.4
  Attempting uninstall: httpx-sse
    Found existing installation: httpx-sse 0.4.1
    Uninstalling httpx-sse-0.4.1:
      Successfully uninstalled httpx-sse-0.4.1
  Attempting uninstall: audioop-lts
    Found existing installation: audioop-lts 0.2.2
    Uninstalling audioop-lts-0.2.2:
      Successfully uninstalled audioop-lts-0.2.2
  Running setup.py develop for mayamcp

Successfully installed audioop-lts-0.2.1 cachetools-5.5.2 cartesia-2.0.9 contourpy-1.3.3 cycler-0.12.1 faiss-cpu-1.12.0 fonttools-4.60.0 google-ai-generativelanguage-0.6.15 google-api-core-2.25.1 google-api-python-client-2.182.0 google-auth-2.40.3 google-auth-httplib2-0.2.0 google-genai-1.38.0 google-generativeai-0.8.5 grpcio-status-1.71.2 httplib2-0.31.0 httpx-sse-0.4.0 iterators-0.2.0 jsonpatch-1.33 jsonpointer-3.0.0 kiwisolver-1.4.9 langchain-core-0.3.76 langchain-google-genai-2.0.10 langsmith-0.4.29 matplotlib-3.10.6 mayamcp-2.0.0 opencv-python-4.12.0.88 proto-plus-1.26.1 pyasn1-0.6.1 pyasn1-modules-0.4.2 pyparsing-3.2.5 qrcode-8.2 requests-toolbelt-1.0.0 rsa-4.9.1 uritemplate-4.2.0 websockets-14.2 zstandard-0.25.0

#### Option 3: Using PYTHONPATH (Alternative)


### Test Organization

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions and end-to-end workflows
- **Memvid Tests**: Test RAG functionality and document retrieval
- **LLM Tests**: Test language model integration and prompt handling
- **UI Tests**: Test user interface components and handlers

### Test Configuration

The project uses  for test configuration with the following features:

- Automatic test discovery in the  directory
- Custom markers for test categorization
- Strict configuration enforcement
- Colorized output for better readability
- Warning suppression for cleaner test output

### Writing Tests

When writing new tests:

1. Place test files in the  directory
2. Use descriptive test names following the  pattern
3. Use appropriate pytest markers to categorize tests
4. Include both positive and negative test cases
5. Mock external dependencies when possible
6. Use descriptive assertion messages

Example test structure:


### CI/CD Integration

Tests are designed to run in CI environments with:

- No external API dependencies for unit tests
- Mocked third-party services for integration tests
- Configurable test execution based on available resources
- Proper exit codes for build pipeline integration

### Troubleshooting

**Import Errors**: If you encounter import errors, ensure you're using one of the recommended test running methods above. The  file automatically handles path setup for pytest runs.

**Missing Dependencies**: Install test requirements:
Requirement already satisfied: google-generativeai>=0.8.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 1)) (0.8.5)
Requirement already satisfied: google-genai>=1.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 3)) (1.38.0)
Requirement already satisfied: langchain-google-genai>=2.0.10 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 5)) (2.0.10)
Requirement already satisfied: langchain-core>=0.3.50 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 6)) (0.3.76)
Requirement already satisfied: python-dotenv>=1.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 7)) (1.1.1)
Requirement already satisfied: requests>=2.31.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 8)) (2.32.4)
Requirement already satisfied: websockets>=12.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 9)) (14.2)
Requirement already satisfied: tenacity>=8.2.3 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 10)) (8.5.0)
Requirement already satisfied: gradio>=4.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 11)) (5.9.1)
Requirement already satisfied: cartesia>=2.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 12)) (2.0.9)
Requirement already satisfied: matplotlib>=3.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 13)) (3.10.6)
Requirement already satisfied: pillow>=8.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 14)) (11.3.0)
Requirement already satisfied: opencv-python in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 19)) (4.12.0.88)
Requirement already satisfied: faiss-cpu>=1.10.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 22)) (1.12.0)
Requirement already satisfied: numpy>=1.24.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 23)) (2.2.6)
Requirement already satisfied: qrcode[pil] in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from -r requirements.txt (line 18)) (8.2)
Requirement already satisfied: google-ai-generativelanguage==0.6.15 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->-r requirements.txt (line 1)) (0.6.15)
Requirement already satisfied: google-api-core in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->-r requirements.txt (line 1)) (2.25.1)
Requirement already satisfied: google-api-python-client in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->-r requirements.txt (line 1)) (2.182.0)
Requirement already satisfied: google-auth>=2.15.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->-r requirements.txt (line 1)) (2.40.3)
Requirement already satisfied: protobuf in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->-r requirements.txt (line 1)) (5.29.5)
Requirement already satisfied: pydantic in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->-r requirements.txt (line 1)) (2.11.7)
Requirement already satisfied: tqdm in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->-r requirements.txt (line 1)) (4.67.1)
Requirement already satisfied: typing-extensions in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-generativeai>=0.8.0->-r requirements.txt (line 1)) (4.14.1)
Requirement already satisfied: proto-plus<2.0.0dev,>=1.22.3 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-ai-generativelanguage==0.6.15->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (1.26.1)
Requirement already satisfied: googleapis-common-protos<2.0.0,>=1.56.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-api-core->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (1.70.0)
Requirement already satisfied: charset_normalizer<4,>=2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from requests>=2.31.0->-r requirements.txt (line 8)) (3.4.2)
Requirement already satisfied: idna<4,>=2.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from requests>=2.31.0->-r requirements.txt (line 8)) (3.10)
Requirement already satisfied: urllib3<3,>=1.21.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from requests>=2.31.0->-r requirements.txt (line 8)) (2.5.0)
Requirement already satisfied: certifi>=2017.4.17 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from requests>=2.31.0->-r requirements.txt (line 8)) (2025.7.14)
Requirement already satisfied: grpcio<2.0.0,>=1.33.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-api-core[grpc]!=2.0.*,!=2.1.*,!=2.10.*,!=2.2.*,!=2.3.*,!=2.4.*,!=2.5.*,!=2.6.*,!=2.7.*,!=2.8.*,!=2.9.*,<3.0.0dev,>=1.34.1->google-ai-generativelanguage==0.6.15->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (1.73.1)
Requirement already satisfied: grpcio-status<2.0.0,>=1.33.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-api-core[grpc]!=2.0.*,!=2.1.*,!=2.10.*,!=2.2.*,!=2.3.*,!=2.4.*,!=2.5.*,!=2.6.*,!=2.7.*,!=2.8.*,!=2.9.*,<3.0.0dev,>=1.34.1->google-ai-generativelanguage==0.6.15->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (1.71.2)
Requirement already satisfied: cachetools<6.0,>=2.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-auth>=2.15.0->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (5.5.2)
Requirement already satisfied: pyasn1-modules>=0.2.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-auth>=2.15.0->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (0.4.2)
Requirement already satisfied: rsa<5,>=3.1.4 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-auth>=2.15.0->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (4.9.1)
Requirement already satisfied: pyasn1>=0.1.3 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from rsa<5,>=3.1.4->google-auth>=2.15.0->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (0.6.1)
Requirement already satisfied: anyio<5.0.0,>=4.8.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-genai>=1.0.0->-r requirements.txt (line 3)) (4.9.0)
Requirement already satisfied: httpx<1.0.0,>=0.28.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-genai>=1.0.0->-r requirements.txt (line 3)) (0.28.1)
Requirement already satisfied: sniffio>=1.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from anyio<5.0.0,>=4.8.0->google-genai>=1.0.0->-r requirements.txt (line 3)) (1.3.1)
Requirement already satisfied: httpcore==1.* in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from httpx<1.0.0,>=0.28.1->google-genai>=1.0.0->-r requirements.txt (line 3)) (1.0.9)
Requirement already satisfied: h11>=0.16 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from httpcore==1.*->httpx<1.0.0,>=0.28.1->google-genai>=1.0.0->-r requirements.txt (line 3)) (0.16.0)
Requirement already satisfied: annotated-types>=0.6.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pydantic->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (0.7.0)
Requirement already satisfied: pydantic-core==2.33.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pydantic->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (2.33.2)
Requirement already satisfied: typing-inspection>=0.4.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pydantic->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (0.4.1)
Requirement already satisfied: filetype<2.0.0,>=1.2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from langchain-google-genai>=2.0.10->-r requirements.txt (line 5)) (1.2.0)
Requirement already satisfied: langsmith>=0.3.45 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from langchain-core>=0.3.50->-r requirements.txt (line 6)) (0.4.29)
Requirement already satisfied: jsonpatch<2.0,>=1.33 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from langchain-core>=0.3.50->-r requirements.txt (line 6)) (1.33)
Requirement already satisfied: PyYAML>=5.3 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from langchain-core>=0.3.50->-r requirements.txt (line 6)) (6.0.2)
Requirement already satisfied: packaging>=23.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from langchain-core>=0.3.50->-r requirements.txt (line 6)) (25.0)
Requirement already satisfied: jsonpointer>=1.9 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from jsonpatch<2.0,>=1.33->langchain-core>=0.3.50->-r requirements.txt (line 6)) (3.0.0)
Requirement already satisfied: aiofiles<24.0,>=22.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (23.2.1)
Requirement already satisfied: audioop-lts<1.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.2.1)
Requirement already satisfied: fastapi<1.0,>=0.115.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.115.6)
Requirement already satisfied: ffmpy in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.6.1)
Requirement already satisfied: gradio-client==1.5.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (1.5.2)
Requirement already satisfied: huggingface-hub>=0.25.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.34.4)
Requirement already satisfied: jinja2<4.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (3.1.6)
Requirement already satisfied: markupsafe~=2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (2.1.5)
Requirement already satisfied: orjson~=3.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (3.11.2)
Requirement already satisfied: pandas<3.0,>=1.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (2.3.0)
Requirement already satisfied: pydub in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.25.1)
Requirement already satisfied: python-multipart>=0.0.18 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.0.20)
Requirement already satisfied: ruff>=0.2.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.12.2)
Requirement already satisfied: safehttpx<0.2.0,>=0.1.6 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.1.6)
Requirement already satisfied: semantic-version~=2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (2.10.0)
Requirement already satisfied: starlette<1.0,>=0.40.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.41.3)
Requirement already satisfied: tomlkit<0.14.0,>=0.12.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.13.3)
Requirement already satisfied: typer<1.0,>=0.12 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.16.0)
Requirement already satisfied: uvicorn>=0.14.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio>=4.0.0->-r requirements.txt (line 11)) (0.34.0)
Requirement already satisfied: fsspec in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from gradio-client==1.5.2->gradio>=4.0.0->-r requirements.txt (line 11)) (2025.5.1)
Requirement already satisfied: python-dateutil>=2.8.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pandas<3.0,>=1.0->gradio>=4.0.0->-r requirements.txt (line 11)) (2.9.0.post0)
Requirement already satisfied: pytz>=2020.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pandas<3.0,>=1.0->gradio>=4.0.0->-r requirements.txt (line 11)) (2025.2)
Requirement already satisfied: tzdata>=2022.7 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pandas<3.0,>=1.0->gradio>=4.0.0->-r requirements.txt (line 11)) (2025.2)
Requirement already satisfied: click>=8.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from typer<1.0,>=0.12->gradio>=4.0.0->-r requirements.txt (line 11)) (8.2.1)
Requirement already satisfied: shellingham>=1.3.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from typer<1.0,>=0.12->gradio>=4.0.0->-r requirements.txt (line 11)) (1.5.4)
Requirement already satisfied: rich>=10.11.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from typer<1.0,>=0.12->gradio>=4.0.0->-r requirements.txt (line 11)) (14.1.0)
Requirement already satisfied: aiohttp>=3.10.10 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from cartesia>=2.0.0->-r requirements.txt (line 12)) (3.10.11)
Requirement already satisfied: httpx-sse==0.4.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from cartesia>=2.0.0->-r requirements.txt (line 12)) (0.4.0)
Requirement already satisfied: iterators>=0.2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from cartesia>=2.0.0->-r requirements.txt (line 12)) (0.2.0)
Requirement already satisfied: contourpy>=1.0.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from matplotlib>=3.0.0->-r requirements.txt (line 13)) (1.3.3)
Requirement already satisfied: cycler>=0.10 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from matplotlib>=3.0.0->-r requirements.txt (line 13)) (0.12.1)
Requirement already satisfied: fonttools>=4.22.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from matplotlib>=3.0.0->-r requirements.txt (line 13)) (4.60.0)
Requirement already satisfied: kiwisolver>=1.3.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from matplotlib>=3.0.0->-r requirements.txt (line 13)) (1.4.9)
Requirement already satisfied: pyparsing>=2.3.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from matplotlib>=3.0.0->-r requirements.txt (line 13)) (3.2.5)
Requirement already satisfied: aiohappyeyeballs>=2.3.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->-r requirements.txt (line 12)) (2.6.1)
Requirement already satisfied: aiosignal>=1.1.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->-r requirements.txt (line 12)) (1.3.2)
Requirement already satisfied: attrs>=17.3.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->-r requirements.txt (line 12)) (25.3.0)
Requirement already satisfied: frozenlist>=1.1.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->-r requirements.txt (line 12)) (1.7.0)
Requirement already satisfied: multidict<7.0,>=4.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->-r requirements.txt (line 12)) (6.4.4)
Requirement already satisfied: yarl<2.0,>=1.12.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from aiohttp>=3.10.10->cartesia>=2.0.0->-r requirements.txt (line 12)) (1.20.1)
Requirement already satisfied: propcache>=0.2.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from yarl<2.0,>=1.12.0->aiohttp>=3.10.10->cartesia>=2.0.0->-r requirements.txt (line 12)) (0.3.2)
Requirement already satisfied: filelock in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from huggingface-hub>=0.25.1->gradio>=4.0.0->-r requirements.txt (line 11)) (3.18.0)
Requirement already satisfied: hf-xet<2.0.0,>=1.1.3 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from huggingface-hub>=0.25.1->gradio>=4.0.0->-r requirements.txt (line 11)) (1.1.8)
Requirement already satisfied: requests-toolbelt>=1.0.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from langsmith>=0.3.45->langchain-core>=0.3.50->-r requirements.txt (line 6)) (1.0.0)
Requirement already satisfied: zstandard>=0.23.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from langsmith>=0.3.45->langchain-core>=0.3.50->-r requirements.txt (line 6)) (0.25.0)
Requirement already satisfied: six>=1.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from python-dateutil>=2.8.2->pandas<3.0,>=1.0->gradio>=4.0.0->-r requirements.txt (line 11)) (1.17.0)
Requirement already satisfied: markdown-it-py>=2.2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from rich>=10.11.0->typer<1.0,>=0.12->gradio>=4.0.0->-r requirements.txt (line 11)) (3.0.0)
Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from rich>=10.11.0->typer<1.0,>=0.12->gradio>=4.0.0->-r requirements.txt (line 11)) (2.19.2)
Requirement already satisfied: mdurl~=0.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich>=10.11.0->typer<1.0,>=0.12->gradio>=4.0.0->-r requirements.txt (line 11)) (0.1.2)
Requirement already satisfied: httplib2<1.0.0,>=0.19.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-api-python-client->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (0.31.0)
Requirement already satisfied: google-auth-httplib2<1.0.0,>=0.2.0 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-api-python-client->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (0.2.0)
Requirement already satisfied: uritemplate<5,>=3.0.1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from google-api-python-client->google-generativeai>=0.8.0->-r requirements.txt (line 1)) (4.2.0)
Requirement already satisfied: pytest in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (8.4.1)
Requirement already satisfied: pytest-mock in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (3.15.1)
Requirement already satisfied: pytest-cov in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (6.2.1)
Requirement already satisfied: iniconfig>=1 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest) (2.1.0)
Requirement already satisfied: packaging>=20 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest) (25.0)
Requirement already satisfied: pluggy<2,>=1.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest) (1.6.0)
Requirement already satisfied: pygments>=2.7.2 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from pytest) (2.19.2)
Requirement already satisfied: coverage>=7.5 in /Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages (from coverage[toml]>=7.5->pytest-cov) (7.9.2)

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
..
