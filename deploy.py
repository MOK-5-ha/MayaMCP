#!/usr/bin/env python3
"""
Modal Labs deployment for Maya MCP
"""

import modal

# Create Modal app
app = modal.App("maya-mcp")

# Define persistent storage for Memvid files
storage = modal.Volume.from_name("maya-storage", create_if_missing=True)

# Define the container image with all dependencies
image = modal.Image.debian_slim(python_version="3.12").pip_install_from_requirements("requirements.txt")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("maya-secrets")],
    volumes={"/assets": storage},
    allow_concurrent_inputs=10,
    timeout=300,
    memory=1024,
)
@modal.web_server(port=7860, startup_timeout=60)
def serve_maya():
    """Serve Maya's Gradio interface on Modal"""
    import os
    import sys
    
    # Add src to path
    sys.path.insert(0, "/root/src")
    
    # Import Maya components
    from src.config import get_api_keys, setup_logging
    from src.llm import initialize_llm, get_all_tools
    from src.rag import initialize_memvid_store
    from src.voice import initialize_cartesia_client
    from src.ui import launch_bartender_interface
    from src.utils import initialize_state
    from functools import partial
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Maya on Modal Labs...")
    
    # Override API keys from Modal secrets
    api_keys = {
        "google_api_key": os.environ["GOOGLE_API_KEY"],
        "cartesia_api_key": os.environ["CARTESIA_API_KEY"]
    }
    
    # Initialize state
    initialize_state()
    
    # Initialize LLM
    tools = get_all_tools()
    llm = initialize_llm(api_key=api_keys["google_api_key"], tools=tools)
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
        cartesia_client = initialize_cartesia_client(api_keys["cartesia_api_key"])
        logger.info("Cartesia TTS initialized")
    except Exception as e:
        logger.warning(f"Cartesia initialization failed: {e}")
        cartesia_client = None
    
    # Create handler with dependencies
    from src.ui.handlers import handle_gradio_input
    
    handle_input_with_deps = partial(
        handle_gradio_input,
        llm=llm,
        cartesia_client=cartesia_client,
        rag_index=rag_index,
        rag_documents=rag_documents,
        rag_retriever=rag_retriever,
        api_key=api_keys["google_api_key"]
    )
    
    # Launch Gradio interface
    logger.info("Launching Maya's Gradio interface...")
    interface = launch_bartender_interface(
        handle_input_func=handle_input_with_deps,
        share=False,  # Modal handles sharing
        debug=False
    )
    
    return interface

@app.local_entrypoint()
def main():
    """Local testing entrypoint"""
    print("🍹 Maya MCP deployed to Modal Labs!")
    print("🎬 Video memory will build automatically on first request")
    print("🚀 Access your app at the URL Modal provides")

if __name__ == "__main__":
    main()