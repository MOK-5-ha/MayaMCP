# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
from collections.abc import AsyncIterator

import google.auth
from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner

try:
    from google.cloud import logging as google_cloud_logging
except ImportError:
    google_cloud_logging = None

from src.app_utils import services
from src.app_utils.a2a import attach_a2a_routes
from src.app_utils.telemetry import setup_telemetry
from src.app_utils.typing import Feedback

load_dotenv()
setup_telemetry()
try:
    _, project_id = google.auth.default()
    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger(__name__)
except Exception as auth_err:
    import logging
    logging.basicConfig(level=logging.INFO)
    fallback_logger = logging.getLogger(__name__)
    fallback_logger.warning(f"Could not load GCP credentials ({auth_err}), falling back to standard library logger")
    class MockLogger:
        def log_struct(self, data, severity="INFO"):
            fallback_logger.info(f"STRUCT_LOG [{severity}]: {data}")
        def info(self, msg, *args, **kwargs):
            fallback_logger.info(msg, *args, **kwargs)
        def error(self, msg, *args, **kwargs):
            fallback_logger.error(msg, *args, **kwargs)
    logger = MockLogger()
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from src.agent import app as adk_app
    from src.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


from fastapi.middleware.cors import CORSMiddleware
from src.routers import chat_router, payments_router, session_router

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=False,
    lifespan=lifespan,
)
app.title = "MayaMCP Backend API"
app.description = "FastAPI backend for MayaMCP AI Bartender (REST, SSE, and ADK A2A)"

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 REST and SSE routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")


@app.get("/healthz")
def healthz():
    return PlainTextResponse("ok", media_type="text/plain")


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Mount Gradio sub-app under /ui for backward compatibility / legacy interface access
try:
    from gradio.routes import mount_gradio_app
    from src.ui.launcher import launch_bartender_interface
    
    gradio_blocks = launch_bartender_interface()
    app = mount_gradio_app(app, gradio_blocks, path="/ui")
except Exception as gradio_err:
    logger.info(f"Gradio mounting skipped: {gradio_err}")


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
