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
    volumes={"/assets": storage},
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

    # Add paths for imports

    # Import Maya components using absolute package imports (package is installed in image)
    from config.logging_config import setup_logging
    from llm.client import initialize_llm
    from llm.tools import get_all_tools
    from rag.memvid_store import initialize_memvid_store
    from voice.tts import initialize_cartesia_client
    from ui.launcher import launch_bartender_interface
    from ui.handlers import handle_gradio_input
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
    def _require_env(name: str) -> str:
        val = os.getenv(name)
        if not val or not val.strip():
            raise RuntimeError(f"Missing required environment variable: {name}")
        return val

    google_api_key = _require_env("GOOGLE_API_KEY")
    cartesia_api_key = _require_env("CARTESIA_API_KEY")

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
    from ui.handlers import clear_chat_state

    # Create Gradio interface
    logger.info("Creating Maya's Gradio interface...")
    interface = launch_bartender_interface(
        handle_input_fn=handle_input_with_deps,
        clear_state_fn=clear_chat_state
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
        return "\n".join(lines) + "\n"

    @web_app.get("/metrics")
    def metrics():
        return PlainTextResponse(_metrics_text(), media_type="text/plain")

    @web_app.get("/healthz")
    def healthz():
        # Check critical dependencies
        checks = []
        if llm is None:
            checks.append("LLM not initialized")

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