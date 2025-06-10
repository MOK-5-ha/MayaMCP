#!/usr/bin/env python3
"""
Modal Labs deployment for Maya MCP
"""

import modal

# Create Modal app
app = modal.App("maya-mcp")

# Define persistent storage for Memvid files
storage = modal.Volume.from_name("maya-storage", create_if_missing=True)

# Define the container image with all dependencies and copy source code
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1-mesa-glx", "libglib2.0-0", "libsm6", "libxext6", "libxrender-dev", "libgomp1")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir("src", "/root/src")
)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("maya-secrets")],
    volumes={"/assets": storage},
    scaledown_window=300,
    timeout=600,
    memory=1024,
    max_containers=1,  # Only 1 container for Gradio web server
)
@modal.asgi_app()
def serve_maya():
    """Serve Maya's Gradio interface on Modal"""
    import os
    import sys
    from functools import partial
    
    # Add paths for imports
    sys.path.insert(0, "/root")
    sys.path.insert(0, "/root/src")
    
    # Import Maya components with correct paths
    from src.config.logging_config import setup_logging
    from src.llm.client import initialize_llm
    from src.llm.tools import get_all_tools
    from src.rag.memvid_store import initialize_memvid_store
    from src.voice.tts import initialize_cartesia_client
    from src.ui.launcher import launch_bartender_interface
    from src.ui.handlers import handle_gradio_input
    from src.utils.state_manager import initialize_state
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Maya on Modal Labs...")
    
    # Get API keys from Modal secrets (environment variables)
    google_api_key = os.environ["GOOGLE_API_KEY"]
    cartesia_api_key = os.environ["CARTESIA_API_KEY"]
    
    # Initialize state
    initialize_state()
    
    # Initialize LLM
    tools = get_all_tools()
    llm = initialize_llm(api_key=google_api_key, tools=tools)
    logger.info(f"LLM initialized with {len(tools)} tools")
    
    # Initialize RAG with Memvid (will build video on first run)
    try:
        logger.info("Initializing Memvid RAG system...")
        rag_retriever, rag_documents = initialize_memvid_store()
        rag_index = None
        logger.info(f"Memvid RAG initialized with {len(rag_documents)} documents")
    except Exception as e:
        logger.warning(f"Memvid initialization failed: {e}")
        rag_index, rag_documents, rag_retriever = None, None, None
    
    # Initialize Cartesia TTS
    try:
        cartesia_client = initialize_cartesia_client(cartesia_api_key)
        logger.info("Cartesia TTS initialized")
    except Exception as e:
        logger.warning(f"Cartesia initialization failed: {e}")
        cartesia_client = None
    
    # Create handler with dependencies
    handle_input_with_deps = partial(
        handle_gradio_input,
        llm=llm,
        cartesia_client=cartesia_client,
        rag_index=rag_index,
        rag_documents=rag_documents,
        rag_retriever=rag_retriever,
        api_key=google_api_key
    )
    
    # Import clear state function
    from src.ui.handlers import clear_chat_state
    
    # Create Gradio interface  
    logger.info("Creating Maya's Gradio interface...")
    interface = launch_bartender_interface(
        handle_input_fn=handle_input_with_deps,
        clear_state_fn=clear_chat_state,
        share=False,  # Modal handles sharing
        debug=False
    )
    
    # Mount Gradio app with FastAPI for Modal
    from fastapi import FastAPI
    from gradio.routes import mount_gradio_app
    
    web_app = FastAPI()
    return mount_gradio_app(
        app=web_app,
        blocks=interface,
        path="/"
    )

@app.local_entrypoint()
def main():
    """Local testing entrypoint"""
    print("🍹 Maya MCP deployed to Modal Labs!")
    print("🎬 Video memory will build automatically on first request")
    print("🚀 Access your app at the URL Modal provides")

if __name__ == "__main__":
    main()