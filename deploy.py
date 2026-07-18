#!/usr/bin/env python3
"""
Modal Labs deployment for Maya MCP
"""

import modal
import os
import time
import threading

# Create Modal app
app = modal.App("maya-mcp")

# Define persistent storage for Memvid files
storage = modal.Volume.from_name("maya-storage", create_if_missing=True)

# Define distributed state for user sessions
app_state = modal.Dict.from_name("maya-app-state", create_if_missing=True)

# Define the container image with all dependencies and install the package
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1-mesa-glx", "libglib2.0-0", "libsm6", "libxext6", "libxrender-dev", "libgomp1")
    .pip_install_from_requirements("requirements.txt")
    # Add the project and install it so absolute imports work without sys.path hacks
    .add_local_dir(".", "/app")
    .pip_install("/app")
)

# Optionally stage raw source for debugging/reference to avoid bloating the image by default
_stage_debug = os.getenv("STAGE_DEBUG_SOURCE") or os.getenv("DEBUG")
if (_stage_debug or "").strip().lower() in {"1", "true", "yes", "on"}:
    image = image.add_local_dir("src", "/root/src")
# Resource configuration (configurable via environment variables)
# Note: MODAL_MAX_CONTAINERS is read from the host environment at deploy time
# and passed as a static value to the @app.function decorator. 
# Changing runtime env vars or dashboard settings will not affect this limit.
MEMORY_MB = int(os.environ.get("MODAL_MEMORY_MB", "4096"))
MODAL_MAX_CONTAINERS = int(os.environ.get("MODAL_MAX_CONTAINERS", "3"))

if MEMORY_MB <= 0:
    raise ValueError(f"MODAL_MEMORY_MB must be positive, got {MEMORY_MB}")
if MODAL_MAX_CONTAINERS <= 0:
    raise ValueError(f"MODAL_MAX_CONTAINERS must be positive, got {MODAL_MAX_CONTAINERS}")

# Build secret list starting with the named secret for late-binding/rotation
maya_secrets_list = [modal.Secret.from_name("maya-secrets")]

# Build local overrides dict, only including non-empty host env values for required keys
REQUIRED_KEYS = ["GEMINI_API_KEY", "CARTESIA_API_KEY", "MAYA_MASTER_KEY"]
overrides = {}
for key in REQUIRED_KEYS:
    val = os.environ.get(key)
    if val and val.strip():
        overrides[key] = val.strip()
    else:
        # Warn if missing locally; we don't know if it's in the named secret yet
        # but Modal will error at deploy/runtime if it's missing from both.
        print(f"WEB_DEPLOY: Warning - {key} is missing from host environment. "
              f"Container will rely on named secret 'maya-secrets'.")

# If we have overrides, add them as a second secret (overwrites named secret if clash)
if overrides:
    maya_secrets_list.append(modal.Secret.from_dict(overrides))



@app.function(
    image=image,
    secrets=maya_secrets_list,
    volumes={"/root/assets": storage},
    scaledown_window=300,
    timeout=600,
    memory=MEMORY_MB,
    max_containers=MODAL_MAX_CONTAINERS,  # Static deployment-time limit
)
@modal.asgi_app()
def serve_maya():
    """Serve Maya's Gradio interface on Modal"""
    import os
    import sys
    from functools import partial
    
    # Access the distributed app state
    # Note: modal.Dict objects are available as global variables in the function scope if defined in the app
    # but strictly speaking we access the one attached to the app or defined globally.
    # In Modal, globals defined in the module are accessible.
    state_store = app_state

    # Add paths for imports

    # Import Maya components using absolute package imports (package is installed in image)
    from config.logging_config import setup_logging
    from llm.tools import get_all_tools
    from rag.memvid_store import initialize_memvid_store
    from ui.launcher import launch_bartender_interface
    from ui.handlers import handle_gradio_input, clear_chat_state
    from ui.api_key_modal import handle_key_submission
    from utils.state_manager import initialize_state
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Maya on Modal Labs...")

    # Log configured resources for observability
    logger.info(f"Configured resources: MEMORY_MB={MEMORY_MB}, MODAL_MAX_CONTAINERS={MODAL_MAX_CONTAINERS}")

    # Read container memory usage from cgroups (v2 or v1) for monitoring
    def _read_cgroup_memory():
        try:
            # Current usage
            current = None
            for p in ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory/memory.usage_in_bytes"):
                if os.path.exists(p):
                    with open(p, "r") as f:
                        current = int(f.read().strip())
                    break
            # Memory limit
            limit = None
            for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
                if os.path.exists(p):
                    with open(p, "r") as f:
                        raw = f.read().strip()
                        if raw != "max":
                            limit = int(raw)
                    break
            return current, limit
        except Exception:
            logger.debug("Failed to read cgroup memory", exc_info=True)
            return None, None


    cur, lim = _read_cgroup_memory()
    if cur is not None:
        cur_mb = cur / (1024 * 1024)
        if lim:
            lim_mb = lim / (1024 * 1024)
            logger.info(f"Container memory usage at start: {cur_mb:.1f} MB / {lim_mb:.1f} MB")
        else:
            logger.info(f"Container memory usage at start: {cur_mb:.1f} MB (no cgroup limit detected)")



    # Keys are now optional for the main app (BYOK) but still used for RAG initialisation
    google_api_key = os.getenv("GEMINI_API_KEY")
    if not (google_api_key and google_api_key.strip()):
        google_api_key = None
        logger.info("No server-side Gemini API key found; RAG will use session keys or be skipped")
    else:
        google_api_key = google_api_key.strip()

    # Initialize state
    initialize_state()
    
    # Resolve singletons once during module init
    try:
        from utils.session_manager import get_session_manager
        from utils.memory_monitor import get_memory_monitor
        session_manager = get_session_manager()
        memory_monitor = get_memory_monitor()
    except Exception as e:
        logger.error(f"Failed to initialize monitors: {e}")
        session_manager = None
        memory_monitor = None
    
    # Initialize session manager and start background cleanup
    cleanup_thread = None
    stop_event = threading.Event()
    
    try:
        from utils.session_manager import cleanup_expired_sessions_background
        cleanup_thread = cleanup_expired_sessions_background(
            interval_seconds=300, stop_event=stop_event, session_manager=session_manager
        )
        logger.info("Session manager initialized with background cleanup")
        
        # Store thread reference for shutdown
        cleanup_thread_ref = [cleanup_thread]
    except Exception as e:
        logger.warning(f"Failed to initialize session manager: {e}")
        cleanup_thread = None

    # Get tool definitions (static, shared)
    tools = get_all_tools()
    logger.info(f"Loaded {len(tools)} tool definitions")

    # Initialize RAG with Memvid (will build video on first run)
    rag_index = None
    rag_documents = None
    rag_retriever = None

    if google_api_key:
        try:
            logger.info("Initializing Memvid RAG system...")
            rag_retriever, rag_documents = initialize_memvid_store()
            logger.info(f"Memvid RAG initialized with {len(rag_documents)} documents")
        except Exception as e:
            logger.warning(f"Memvid initialization failed: {e}. Attempting FAISS fallback...")
            try:
                from rag.vector_store import initialize_vector_store
                rag_index, rag_documents = initialize_vector_store()
                logger.info(f"FAISS RAG initialized with {len(rag_documents)} documents")
            except Exception as e2:
                logger.warning(f"FAISS initialization also failed: {e2}. Continuing without RAG.")
    else:
        logger.info("Skipping RAG initialization (no server-side Gemini key)")

    # NOTE: LLM and TTS are NOT initialised here (BYOK mode).
    # Per-session clients are lazily created via src/llm/session_registry.

    # Create handler with dependencies
    handle_input_with_deps = partial(
        handle_gradio_input,
        tools=tools,
        rag_index=rag_index,
        rag_documents=rag_documents,
        rag_retriever=rag_retriever,
        rag_api_key=google_api_key,
        app_state=state_store
    )

    clear_state_with_deps = partial(clear_chat_state, app_state=state_store)

    handle_keys_with_deps = partial(handle_key_submission, app_state=state_store)

    # Create Gradio interface
    logger.info("Creating Maya's Gradio interface...")
    interface = launch_bartender_interface(
        handle_input_fn=handle_input_with_deps,
        clear_state_fn=clear_state_with_deps,
        handle_key_submission_fn=handle_keys_with_deps,
    )
    
    # Mount Gradio app with FastAPI for Modal
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    from gradio.routes import mount_gradio_app
    from contextlib import asynccontextmanager
    
    # Track process start time for uptime metric
    START_TIME = time.time()
    
    # Shutdown hook for graceful cleanup
    def shutdown_cleanup_thread():
        """Gracefully stop the cleanup thread."""
        if cleanup_thread_ref[0]:
            stop_event.set()  # Signal thread to stop
            cleanup_thread_ref[0].join(timeout=5.0)  # Wait for graceful shutdown
            cleanup_thread_ref[0] = None

    @asynccontextmanager
    async def app_lifespan(app: FastAPI):
        yield
        shutdown_cleanup_thread()

    web_app = FastAPI(lifespan=app_lifespan)


    @web_app.get("/healthz")
    def healthz():
        # Check critical dependencies
        checks = []
        
        # Memory health check
        try:
            from utils.memory_monitor import check_memory_health
            memory_healthy = check_memory_health()
            if not memory_healthy:
                checks.append("Container memory pressure detected")
        except Exception as e:
            logger.warning(f"Memory health check failed: {e}")
        
        # Check RAG availability (either Memvid or FAISS)
        # Only mandatory if server-side key is provided (non-BYOK for RAG)
        if google_api_key is not None:
            rag_available = False
            if rag_retriever is not None or rag_index is not None:
                # Check that we have documents
                if rag_documents and len(rag_documents) > 0:
                    rag_available = True
            
            if not rag_available:
                checks.append("RAG not initialized or no documents available")

        if checks:
            return PlainTextResponse(
                f"unhealthy: {', '.join(checks)}",
                status_code=503,
                media_type="text/plain",
            )
        return PlainTextResponse("ok", media_type="text/plain")


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