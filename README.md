# MayaMCP

Originally created as a capstone project for Kaggle's Gen AI Intensive Course Q1 2025. Meant to demonstrate the skills in generative AI we've learned over the course of a week with a project of our own choosing that utilized at least 5 of those skills. Had 16 days to complete it.<br><br>


<img width="1231" alt="Image" src="https://github.com/user-attachments/assets/f89cc02e-e02a-4595-af78-7c87263db632" /><br><br>

After obtaining our Gen AI certificates from completing and submitting the first version of our service-working AI agent, we sought to complete it. Here in June, Gradio & Huggingface are holding an Agents & MCP hackathon, with multiple AI inference engine & foundation labs participating in the way of providing participants with free credits to build with throughout the duration of the competition.<br><br>


![Image](https://github.com/user-attachments/assets/be6656c8-b338-4a7a-80df-dca6abbdfe34)<br><br>


So now this project has taken to the MCP turn. Where Anthropic's new protocol is taking the AI development by storm, creating yet another new paradigm is this ever accelerating industry.

This second iteration of Maya, our AI agent, will be bolstered with the power of MCP, open-source AI frameworks, and hardware accelerators. Leaving behind the Google-based vendor lock-in it's initial iteration had with Gemini serving at it's base.

# Features
- Multi-turn conversational ordering system
- Menu management with several beverages
- Real-time streaming voice chat
- Gradio UI with agent avatar
- MCP Stripe integration for simulation of transactions

# Project Structure
- `config/`: Configuration files separate from code
- `src/`: Core source code with modular organization
- `data/`: Organized storage for different data types
- `examples/`: Implementation references
- `notebooks/`: Experimentation and analysis

# Setup

## Quick Start
1. Clone repository
```bash
git clone <repository-url>
cd MayaMCP
```

2. Create `.env` file with your API keys:
```bash
# API Keys
GEMINI_API_KEY=your_google_api_key_here
CARTESIA_API_KEY=your_cartesia_api_key_here

# Model Configuration (optional)
GEMINI_MODEL_VERSION=gemini-2.5-flash-preview-04-17
TEMPERATURE=0.7
MAX_OUTPUT_TOKENS=2048

# Environment Configuration (optional)
PYTHON_ENV=development
DEBUG=True
```

3. Run Maya using the convenience script:
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

# Usage

## Running the Application
After setup, Maya will launch a Gradio web interface accessible at:
- Local: `http://localhost:7860`
- Public: Gradio will provide a shareable link

## Interacting with Maya
- **Order drinks**: "I'd like a martini on the rocks"
- **Check order**: "What's in my order?"
- **Get recommendations**: "Something fruity please"
- **View bill**: "What's my total?"
- **Add tip**: "Add a 20% tip"
- **Pay**: "I'll pay now"

## Voice Features
Maya speaks! Enable audio in your browser to hear her responses.

# Notes
..
