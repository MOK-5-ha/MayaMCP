#!/usr/bin/env python3
"""
Modal Labs deployment for Maya MCP
"""

import modal
import os
import time

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
MEMORY_MB = int(os.environ.get("MODAL_MEMORY_MB", "4096"))
MAX_CONTAINERS = int(os.environ.get("MODAL_MAX_CONTAINERS", "3"))

if MEMORY_MB <= 0:
    raise ValueError(f"MODAL_MEMORY_MB must be positive, got {MEMORY_MB}")
if MAX_CONTAINERS <= 0:
    raise ValueError(f"MODAL_MAX_CONTAINERS must be positive, got {MAX_CONTAINERS}")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("maya-secrets")],
    volumes={"/root/assets": storage},
    scaledown_window=300,
    timeout=600,
    memory=MEMORY_MB,
    max_containers=MAX_CONTAINERS,
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
    logger.info(f"Configured resources: MEMORY_MB={MEMORY_MB}, MAX_CONTAINERS={MAX_CONTAINERS}")

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

    # Read container CPU usage from cgroups
    def _read_cgroup_cpu_seconds():
        try:
            # cgroup v2: cpu.stat contains usage_usec
            p_v2 = "/sys/fs/cgroup/cpu.stat"
            if os.path.exists(p_v2):
                with open(p_v2, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) == 2 and parts[0] == "usage_usec":
                            usec = int(parts[1])
                            return usec / 1_000_000.0
            # cgroup v1: cpuacct.usage contains nanoseconds
            p_v1 = "/sys/fs/cgroup/cpuacct/cpuacct.usage"
            if os.path.exists(p_v1):
                with open(p_v1, "r") as f:
                    ns = int(f.read().strip())
                    return ns / 1_000_000_000.0
        except Exception:
            return None
        return None

    cur, lim = _read_cgroup_memory()
    if cur is not None:
        cur_mb = cur / (1024 * 1024)
        if lim:
            lim_mb = lim / (1024 * 1024)
            logger.info(f"Container memory usage at start: {cur_mb:.1f} MB / {lim_mb:.1f} MB")
        else:
            logger.info(f"Container memory usage at start: {cur_mb:.1f} MB (no cgroup limit detected)")



    # Validate and fetch required API keys early
    # Helper that checks multiple env var names for backwards compatibility
    def _require_any(*names: str) -> str:
        """Return the first set env var from names, or raise if none are set.
        
        Preferred name should come first (e.g., GEMINI_API_KEY before GOOGLE_API_KEY).
        """
        for name in names:
            val = os.getenv(name)
            if val and val.strip():
                return val.strip()
        raise RuntimeError(
            f"Missing required environment variable: set one of {', '.join(names)}"
        )

    # GEMINI_API_KEY is preferred (matches config.api_keys); GOOGLE_API_KEY for legacy support
    # Keys are now optional for the main app (BYOK) but still used for RAG initialisation
    google_api_key = None
    try:
        google_api_key = _require_any("GEMINI_API_KEY", "GOOGLE_API_KEY")
    except RuntimeError:
        logger.info("No server-side Gemini API key found; RAG will use session keys or be skipped")

    # Initialize state
    initialize_state()

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

    web_app = FastAPI()

    # Track process start time for uptime metric
    START_TIME = time.time()

    # Prometheus-style metrics endpoint
    def _metrics_text():
        lines = []
        # Configured resources
        lines.append('# HELP maya_config_memory_mb Configured container memory in MB')
        lines.append('# TYPE maya_config_memory_mb gauge')
        lines.append(f'maya_config_memory_mb {MEMORY_MB}')
        lines.append('# HELP maya_config_max_containers Configured max containers for autoscaling')
        lines.append('# TYPE maya_config_max_containers gauge')
        lines.append(f'maya_config_max_containers {MAX_CONTAINERS}')
        # cgroup memory
        cur, lim = _read_cgroup_memory()
        if cur is not None:
            lines.append('# HELP maya_container_memory_usage_bytes Container memory usage in bytes')
            lines.append('# TYPE maya_container_memory_usage_bytes gauge')
            lines.append(f'maya_container_memory_usage_bytes {cur}')
        if lim is not None:
            lines.append('# HELP maya_container_memory_limit_bytes Container memory limit in bytes')
            lines.append('# TYPE maya_container_memory_limit_bytes gauge')
            lines.append(f'maya_container_memory_limit_bytes {lim}')
        # CPU usage seconds total
        cpu_sec = _read_cgroup_cpu_seconds()
        if cpu_sec is not None:
            lines.append('# HELP maya_container_cpu_usage_seconds_total Total container CPU time in seconds')
            lines.append('# TYPE maya_container_cpu_usage_seconds_total counter')
            lines.append(f'maya_container_cpu_usage_seconds_total {cpu_sec}')
        # Uptime seconds
        uptime = max(0.0, time.time() - START_TIME)
        lines.append('# HELP maya_process_uptime_seconds Process uptime in seconds')
        lines.append('# TYPE maya_process_uptime_seconds gauge')
        lines.append(f'maya_process_uptime_seconds {uptime}')
        
        # RAG availability and document count
        rag_type = "none"
        rag_doc_count = 0
        if rag_retriever is not None:
            rag_type = "memvid"
        elif rag_index is not None:
            rag_type = "faiss"
        
        if rag_documents:
            rag_doc_count = len(rag_documents)
        
        lines.append('# HELP maya_rag_available RAG system availability (1=available, 0=unavailable)')
        lines.append('# TYPE maya_rag_available gauge')
        lines.append(f'maya_rag_available {1 if rag_type != "none" and rag_doc_count > 0 else 0}')
        
        lines.append('# HELP maya_rag_document_count Number of documents in RAG system')
        lines.append('# TYPE maya_rag_document_count gauge')
        lines.append(f'maya_rag_document_count {rag_doc_count}')
        
        lines.append('# HELP maya_rag_type RAG implementation type (memvid=1, faiss=2, none=0)')
        lines.append('# TYPE maya_rag_type gauge')
        rag_type_value = {"none": 0, "memvid": 1, "faiss": 2}.get(rag_type, 0)
        lines.append(f'maya_rag_type {rag_type_value}')
        
        return "\n".join(lines) + "\n"

    @web_app.get("/metrics")
    def metrics():
        return PlainTextResponse(_metrics_text(), media_type="text/plain")

    @web_app.get("/healthz")
    def healthz():
        # Check critical dependencies
        checks = []
        
        # Check RAG availability (either Memvid or FAISS)
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