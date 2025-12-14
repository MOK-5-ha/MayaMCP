# MayaMCP Product Overview

MayaMCP is an AI bartending agent that provides a conversational ordering experience. Originally a Kaggle Gen AI Intensive Course capstone project, now enhanced with MCP (Model Context Protocol) integration.

## Core Capabilities

- Multi-turn conversational drink ordering
- Menu management with beverage catalog
- Real-time streaming voice chat (TTS via Cartesia)
- RAG-enhanced responses using Memvid/FAISS
- MCP Stripe integration for payment simulation
- Gradio web UI with agent avatar

## User Interactions

- Ordering drinks: "I'd like a martini on the rocks"
- Checking orders: "What's in my order?"
- Getting recommendations: "Something fruity please"
- Billing: "What's my total?" / "Add a 20% tip" / "I'll pay now"

## Design Philosophy

- Graceful degradation: RAG fallbacks (Memvid → FAISS → no RAG)
- Resilient API handling with retries and exponential backoff
- Errors never break conversational flow
- Text-only fallback if TTS fails
