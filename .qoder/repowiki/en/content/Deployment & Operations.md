# Deployment & Operations

<cite>
**Referenced Files in This Document**
- [deploy.py](file://deploy.py)
- [README.md](file://README.md)
- [requirements.txt](file://requirements.txt)
- [pyproject.toml](file://pyproject.toml)
- [.env.example](file://.env.example)
- [run_maya.sh](file://run_maya.sh)
- [src/config/logging_config.py](file://src/config/logging_config.py)
- [src/config/api_keys.py](file://src/config/api_keys.py)
- [src/ui/api_key_modal.py](file://src/ui/api_key_modal.py)
- [src/llm/key_validator.py](file://src/llm/key_validator.py)
- [src/utils/state_manager.py](file://src/utils/state_manager.py)
- [src/llm/session_registry.py](file://src/llm/session_registry.py)
- [tests/conftest.py](file://tests/conftest.py)
- [pytest.ini](file://pytest.ini)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py)
- [.kiro/specs/stripe-payment/tasks.md](file://.kiro/specs/stripe-payment/tasks.md)
- [monitoring/grafana/README.md](file://monitoring/grafana/README.md)
</cite>

## Update Summary
**Changes Made**
- Updated deployment configuration to reflect streamlined requirements management system
- Simplified deployment workflow documentation to emphasize ease of deployment
- Removed complex deployment configuration references in favor of straightforward requirements.txt usage
- Updated troubleshooting guide to reflect simplified deployment processes
- Enhanced BYOK architecture documentation with streamlined key management procedures

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document provides comprehensive deployment and operations guidance for MayaMCP focused on Modal Labs deployment and production monitoring. It covers Modal deployment configuration (resource allocation, container scaling, environment variables), the end-to-end deployment workflow (development to production), observability (Prometheus metrics, health checks, monitoring dashboards), environment configuration across stages, secrets management, backups, CI/CD integration, automated testing, rollback procedures, and operational runbooks for incident response and maintenance.

**Updated** The deployment system has been streamlined with simplified configuration management, removing complex deployment configurations in favor of straightforward requirements.txt-based deployments for easier maintenance and reduced operational complexity.

## Project Structure
MayaMCP is organized around a Modal application entry point, a local development runner, configuration modules, and payment/UI integrations. The deployment artifact is a Modal app that serves a Gradio UI via an ASGI mount, exposes Prometheus-compatible metrics, and provides health checks.

```mermaid
graph TB
subgraph "Deployment Artifacts"
D1["deploy.py<br/>Modal App"]
D2["requirements.txt<br/>Simplified Dependencies"]
D3["pyproject.toml<br/>Build & Scripts"]
D4[".env.example<br/>Environment Variables"]
D5["run_maya.sh<br/>Local Dev Runner"]
end
subgraph "Runtime Modules"
M1["src/config/logging_config.py<br/>Logging"]
M2["src/config/api_keys.py<br/>API Keys"]
M3["src/payments/stripe_mcp.py<br/>Payments"]
M4["src/ui/api_key_modal.py<br/>BYOK UI"]
M5["src/llm/key_validator.py<br/>Key Validation"]
M6["src/utils/state_manager.py<br/>Session State"]
M7["src/llm/session_registry.py<br/>Per-Session Clients"]
end
subgraph "Testing"
T1["tests/conftest.py<br/>Test Shims"]
T2["pytest.ini<br/>Pytest Config"]
end
subgraph "Monitoring"
MON["monitoring/grafana/README.md<br/>Dashboards"]
end
D1 --> M1
D1 --> M2
D1 --> M3
D1 --> M4
D1 --> M5
D1 --> M6
D1 --> M7
D2 --> D1
D3 --> D1
D4 --> D1
D5 --> M2
T1 --> D1
T2 --> T1
MON --> D1
```

**Diagram sources**
- [deploy.py](file://deploy.py#L1-L313)
- [requirements.txt](file://requirements.txt#L1-L39)
- [pyproject.toml](file://pyproject.toml#L1-L105)
- [.env.example](file://.env.example#L1-L33)
- [run_maya.sh](file://run_maya.sh#L1-L53)
- [src/config/logging_config.py](file://src/config/logging_config.py#L1-L51)
- [src/config/api_keys.py](file://src/config/api_keys.py#L1-L51)
- [src/ui/api_key_modal.py](file://src/ui/api_key_modal.py#L1-L137)
- [src/llm/key_validator.py](file://src/llm/key_validator.py#L1-L88)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L305-L310)
- [src/llm/session_registry.py](file://src/llm/session_registry.py#L1-L107)
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [pytest.ini](file://pytest.ini#L1-L27)
- [monitoring/grafana/README.md](file://monitoring/grafana/README.md)

**Section sources**
- [deploy.py](file://deploy.py#L1-L313)
- [README.md](file://README.md#L343-L419)
- [requirements.txt](file://requirements.txt#L1-L39)
- [pyproject.toml](file://pyproject.toml#L1-L105)
- [.env.example](file://.env.example#L1-L33)
- [run_maya.sh](file://run_maya.sh#L1-L53)

## Core Components
- Modal App and Function: The deployment defines a Modal app with a function decorated for ASGI serving, persistent volume mounting, secrets, and resource configuration.
- Metrics Endpoint: Exposes Prometheus-compatible metrics at /metrics including container memory/CPU and configuration gauges.
- Health Checks: Provides a /healthz endpoint validating critical dependencies and RAG availability.
- Environment Configuration: Reads MODAL_MEMORY_MB and MODAL_MAX_CONTAINERS to tune container resources dynamically.
- Secrets Management: Uses a Modal secret named for API keys and other sensitive values.
- Logging and Startup Diagnostics: Logs configured resources and initial memory usage for observability.
- Fallbacks: Implements graceful fallbacks for RAG initialization and TTS initialization.
- BYOK Architecture: Supports optional server-side API keys with per-session key validation and authentication.

**Updated** The deployment system now emphasizes simplicity with streamlined configuration management. The BYOK architecture enables optional server-side API key initialization while maintaining robust key validation and session-based authentication. Server-side keys are now optional for main app functionality, with per-session key validation handled through the UI modal component.

**Section sources**
- [deploy.py](file://deploy.py#L10-L313)
- [README.md](file://README.md#L343-L419)
- [src/config/logging_config.py](file://src/config/logging_config.py#L1-L51)
- [src/config/api_keys.py](file://src/config/api_keys.py#L1-L51)
- [src/ui/api_key_modal.py](file://src/ui/api_key_modal.py#L83-L137)
- [src/llm/key_validator.py](file://src/llm/key_validator.py#L20-L88)

## Architecture Overview
The runtime architecture centers on a Modal function that mounts a FastAPI app wrapping a Gradio Blocks interface. The function initializes logging, validates API keys, sets up LLM, RAG, and TTS, and exposes metrics and health endpoints. The BYOK architecture allows users to authenticate with their own API keys through the UI modal.

```mermaid
sequenceDiagram
participant Client as "Browser/Client"
participant Modal as "Modal Function"
participant FastAPI as "FastAPI App"
participant Gradio as "Gradio Blocks"
participant UI as "API Key Modal"
participant Validator as "Key Validator"
participant State as "State Manager"
participant Metrics as "Metrics Endpoint"
participant Health as "Health Endpoint"
Client->>Modal : "HTTP GET /"
Modal->>FastAPI : "mount_gradio_app(blocks, path='/')"
FastAPI->>Gradio : "Render UI"
Gradio->>UI : "Show API Key Form"
UI->>Validator : "validate_gemini_key()"
Validator-->>UI : "Validation Result"
UI->>State : "set_api_keys()"
State-->>UI : "Store Session Keys"
UI-->>Client : "Hide Form, Show Chat"
Client->>Modal : "GET /metrics"
Modal->>Metrics : "Generate Prometheus text"
Metrics-->>Client : "text/plain metrics"
Client->>Modal : "GET /healthz"
Modal->>Health : "Run checks"
Health-->>Client : "ok/unhealthy"
```

**Diagram sources**
- [deploy.py](file://deploy.py#L312-L316)
- [deploy.py](file://deploy.py#L216-L221)
- [deploy.py](file://deploy.py#L284-L310)
- [src/ui/api_key_modal.py](file://src/ui/api_key_modal.py#L83-L137)
- [src/llm/key_validator.py](file://src/llm/key_validator.py#L20-L88)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L853-L900)

## Detailed Component Analysis

### Modal Deployment Configuration
- App and Function: The Modal app is created and a function is decorated with image, secrets, volumes, scaling, timeout, memory, and max containers.
- Image Build: Debian slim with Python 3.12, apt dependencies for GUI/headless rendering, pip install from requirements, local project staging, and editable install.
- Persistent Storage: A named Modal Volume is mounted to host asset storage.
- Distributed State: A Modal Dict is used for cross-container session state.
- Resource Tuning: Environment variables control memory and max containers; validation ensures positive values.
- Debugging: Optional debug source staging controlled by environment flags.

```mermaid
flowchart TD
Start(["Deploy Script"]) --> CreateApp["Create Modal App"]
CreateApp --> DefineImage["Define Image:<br/>Debian Slim + Python 3.12"]
DefineImage --> AptDeps["Install GUI/Apt Deps"]
AptDeps --> PipReqs["pip install from requirements.txt"]
PipReqs --> StageSrc["Stage Project Locally"]
StageSrc --> InstallPkg["pip install /app"]
InstallPkg --> Secrets["Attach Secret 'maya-secrets'"]
Secrets --> Volume["Mount Volume '/root/assets'"]
Volume --> FunctionCfg["Configure Function:<br/>memory, max_containers,<br/>timeout, scaledown_window"]
FunctionCfg --> ASGI["ASGI Mount for Gradio"]
ASGI --> End(["Ready"])
```

**Diagram sources**
- [deploy.py](file://deploy.py#L10-L51)
- [deploy.py](file://deploy.py#L19-L27)

**Section sources**
- [deploy.py](file://deploy.py#L10-L51)
- [deploy.py](file://deploy.py#L19-L27)

### Environment Variables and Secrets
- API Keys: GEMINI_API_KEY and CARTESIA_API_KEY are validated early; GOOGLE_API_KEY is supported for legacy compatibility.
- Modal Resource Tuning: MODAL_MEMORY_MB and MODAL_MAX_CONTAINERS control container memory and autoscaling concurrency.
- Local Development: .env.example documents keys, model config, FastAPI settings, and environment flags.
- Logging Level: Controlled by DEBUG environment variable.
- BYOK Support: Server-side keys are optional; when absent, RAG initialization is skipped and users must provide keys via UI.

**Updated** Server-side API keys are now optional for the main application. The deployment script attempts to load server-side keys but gracefully falls back to skipping RAG initialization if keys are unavailable. Users can authenticate with their own keys through the UI modal component.

```mermaid
flowchart TD
EnvStart["Load .env / Secrets"] --> RequireKeys["Validate Required Keys"]
RequireKeys --> KeysOK{"Keys Present?"}
KeysOK --> |Yes| InitServices["Initialize LLM/RAG/TTS"]
KeysOK --> |No| SkipRAG["Skip RAG Init<br/>Graceful Fallback"]
InitServices --> Metrics["Expose Metrics Endpoint"]
InitServices --> Health["Expose Health Endpoint"]
SkipRAG --> Metrics
SkipRAG --> Health
```

**Diagram sources**
- [deploy.py](file://deploy.py#L139-L161)
- [deploy.py](file://deploy.py#L284-L310)
- [.env.example](file://.env.example#L1-L33)
- [src/config/api_keys.py](file://src/config/api_keys.py#L10-L43)

**Section sources**
- [deploy.py](file://deploy.py#L139-L161)
- [.env.example](file://.env.example#L1-L33)
- [src/config/api_keys.py](file://src/config/api_keys.py#L10-L43)

### BYOK Architecture and Key Management
- Optional Server-Side Keys: The deployment attempts to load server-side API keys but continues if unavailable.
- Per-Session Authentication: Users authenticate with their own keys through the UI modal component.
- Key Validation: Lightweight validation using Google GenAI SDK models.list() call that consumes no tokens.
- Session State Management: Keys are stored in session state for per-user authentication.
- Graceful Degradation: When server-side keys are unavailable, RAG functionality is disabled but chat continues.

**Updated** The BYOK architecture introduces comprehensive key management with optional server-side keys, per-session authentication, and robust validation mechanisms.

```mermaid
flowchart TD
Start(["User Request"]) --> CheckServerKeys["Check Server-Side Keys"]
CheckServerKeys --> ServerKeys{"Server Keys Available?"}
ServerKeys --> |Yes| InitRAG["Initialize RAG with Server Keys"]
ServerKeys --> |No| SkipRAG["Skip RAG Initialization"]
InitRAG --> ShowForm["Show API Key Form"]
SkipRAG --> ShowForm
ShowForm --> UserSubmit["User Submits Keys"]
UserSubmit --> ValidateKey["Validate Gemini Key"]
ValidateKey --> KeyValid{"Key Valid?"}
KeyValid --> |Yes| StoreKey["Store in Session State"]
KeyValid --> |No| ShowError["Show Validation Error"]
StoreKey --> HideForm["Hide Form, Enable Chat"]
ShowError --> ShowForm
HideForm --> ProcessRequest["Process User Request"]
```

**Diagram sources**
- [deploy.py](file://deploy.py#L154-L161)
- [src/ui/api_key_modal.py](file://src/ui/api_key_modal.py#L83-L137)
- [src/llm/key_validator.py](file://src/llm/key_validator.py#L20-L88)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L853-L900)

**Section sources**
- [deploy.py](file://deploy.py#L154-L161)
- [src/ui/api_key_modal.py](file://src/ui/api_key_modal.py#L83-L137)
- [src/llm/key_validator.py](file://src/llm/key_validator.py#L20-L88)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L853-L900)

### Observability: Metrics, Health, and Dashboards
- Metrics Endpoint: Exposes container memory usage/limit, CPU seconds total, uptime, configured memory and max containers, and RAG availability/type/count.
- Health Endpoint: Validates LLM initialization and RAG availability with document presence.
- Prometheus Scrape: The README includes a scrape configuration example for Prometheus targeting the Modal host and /metrics path.
- Grafana: A Grafana README exists under monitoring/grafana for dashboard guidance.

```mermaid
classDiagram
class MetricsEndpoint {
+maya_config_memory_mb
+maya_config_max_containers
+maya_container_memory_usage_bytes
+maya_container_memory_limit_bytes
+maya_container_cpu_usage_seconds_total
+maya_process_uptime_seconds
+maya_rag_available
+maya_rag_document_count
+maya_rag_type
}
class HealthEndpoint {
+healthz() ok/unhealthy
}
MetricsEndpoint <.. HealthEndpoint : "complementary"
```

**Diagram sources**
- [deploy.py](file://deploy.py#L226-L282)
- [deploy.py](file://deploy.py#L284-L310)

**Section sources**
- [deploy.py](file://deploy.py#L226-L282)
- [deploy.py](file://deploy.py#L284-L310)
- [README.md](file://README.md#L396-L419)
- [monitoring/grafana/README.md](file://monitoring/grafana/README.md)

### Deployment Workflow: Development to Production
- Development: Use Modal CLI to run the ASGI app locally inside Modal's runtime for iterative development.
- Production: Use Modal CLI to deploy the app to production.
- Local Development Alternative: A convenience script sets up a virtual environment, installs the package in editable mode, and launches the console entry point.

**Updated** The deployment workflow has been simplified with streamlined requirements management. The modal serve and modal deploy commands remain the primary deployment methods, but the requirements.txt file now contains a focused set of dependencies for easier maintenance.

```mermaid
flowchart TD
Dev["modal serve deploy.py"] --> Test["Iterate Locally"]
Test --> Prod["modal deploy deploy.py"]
Prod --> Monitor["Monitor /metrics and /healthz"]
LocalDev["run_maya.sh"] --> LocalRun["Launch Local UI"]
```

**Diagram sources**
- [README.md](file://README.md#L345-L348)
- [run_maya.sh](file://run_maya.sh#L51-L53)

**Section sources**
- [README.md](file://README.md#L343-L348)
- [run_maya.sh](file://run_maya.sh#L51-L53)

### CI/CD Integration and Automated Testing
- Pytest Configuration: Project-wide pytest settings define markers, strictness, and output options.
- Test Shims: A conftest module provides minimal stubs for optional AI SDKs to ensure tests run even without installed packages.
- CI Guidance: Tests are designed to run in CI with mocked services and proper exit codes.

```mermaid
graph LR
CI["CI Pipeline"] --> Install["Install Requirements"]
Install --> Pytest["pytest with markers"]
Pytest --> Coverage["Coverage Reports"]
Pytest --> ExitCode["Exit Codes for Pipeline"]
```

**Diagram sources**
- [pytest.ini](file://pytest.ini#L1-L27)
- [tests/conftest.py](file://tests/conftest.py#L1-L182)

**Section sources**
- [pytest.ini](file://pytest.ini#L1-L27)
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [README.md](file://README.md#L300-L331)

### Payment Integration and Resilience
- Stripe MCP Client: Implements idempotent payment link creation with retry/backoff, availability probing, and fallback to mock payments when unavailable.
- Status Polling: Configurable polling interval and timeout with a maximum number of attempts.
- Graceful Degradation: Falls back to mock payment links when MCP is unavailable or retries fail.

```mermaid
flowchart TD
StartPay["Create Payment Link"] --> Probe["Probe MCP Availability"]
Probe --> Available{"Available?"}
Available --> |Yes| TryCreate["Attempt Create Link"]
TryCreate --> Success{"Success?"}
Success --> |Yes| Done["Return Link"]
Success --> |No| Retry["Exponential Backoff Retry"]
Retry --> Attempts{"Attempts Left?"}
Attempts --> |Yes| TryCreate
Attempts --> |No| Fallback["Fallback to Mock Payment"]
Available --> |No| Fallback
```

**Diagram sources**
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L216-L271)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L39-L474)

**Section sources**
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L216-L271)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L39-L474)
- [.kiro/specs/stripe-payment/tasks.md](file://.kiro/specs/stripe-payment/tasks.md#L1-L403)

## Dependency Analysis
- Runtime Dependencies: Managed via requirements.txt and included in the Modal image build.
- Build and Packaging: pyproject.toml defines the package metadata, console script entry point, and test configuration.
- Optional Security: Additional optional dependency for security scanning is documented.

**Updated** The requirements.txt file has been streamlined to contain only essential dependencies, reducing complexity and improving deployment reliability. The simplified dependency tree focuses on core functionality while maintaining optional security features.

```mermaid
graph TB
RT["requirements.txt<br/>Streamlined Dependencies"] --> IMG["Modal Image Build"]
PKG["pyproject.toml"] --> IMG
IMG --> APP["Modal App Function"]
APP --> RUNTIME["Runtime: LLM/RAG/TTS/UI"]
```

**Diagram sources**
- [requirements.txt](file://requirements.txt#L1-L39)
- [pyproject.toml](file://pyproject.toml#L1-L105)
- [deploy.py](file://deploy.py#L19-L27)

**Section sources**
- [requirements.txt](file://requirements.txt#L1-L39)
- [pyproject.toml](file://pyproject.toml#L1-L105)
- [deploy.py](file://deploy.py#L19-L27)

## Performance Considerations
- Resource Tuning: Adjust MODAL_MEMORY_MB and MODAL_MAX_CONTAINERS to match observed latency and throughput; validate configuration via startup logs and metrics.
- Container Scaling: Use scaledown_window and max containers to balance responsiveness and cost.
- RAG Initialization: Memvid initialization is attempted first, with FAISS as a fallback; monitor RAG availability metrics.
- TTS Resilience: If TTS initialization fails, the system continues with text-only responses; monitor health checks for availability.
- BYOK Optimization: Per-session client caching reduces overhead for authenticated users; consider session expiration policies.

**Updated** BYOK architecture introduces per-session client caching to optimize performance for authenticated users while maintaining security isolation. The streamlined deployment configuration reduces startup overhead and improves resource utilization.

## Troubleshooting Guide
- Missing API Keys: Startup validates required keys; ensure GEMINI_API_KEY and CARTESIA_API_KEY are set. Legacy GOOGLE_API_KEY is supported.
- Health Check Failures: The /healthz endpoint reports issues if LLM or RAG is not available; confirm initialization logs and metrics.
- Metrics Not Scraping: Verify the Modal host and HTTPS scheme in Prometheus configuration; ensure the /metrics path is reachable.
- Local Development: The run_maya.sh script checks for .env presence, Python, and virtual environment; ensure editable install succeeds.
- Payment MCP Unavailable: Stripe MCP client falls back to mock payments; confirm availability probing and retry behavior.
- BYOK Issues: If server-side keys are missing, verify the UI modal shows the API key form; check key validation logs for specific error messages.
- Session State Problems: Verify session state persistence in Modal Dict; check for proper session ID handling in multi-user scenarios.
- Deployment Issues: With the simplified requirements.txt, verify all dependencies are properly installed; check Modal logs for pip installation errors.

**Updated** Added troubleshooting steps for the streamlined deployment process, focusing on requirements.txt validation and simplified dependency resolution.

**Section sources**
- [deploy.py](file://deploy.py#L139-L161)
- [deploy.py](file://deploy.py#L284-L310)
- [README.md](file://README.md#L396-L419)
- [run_maya.sh](file://run_maya.sh#L11-L18)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L216-L271)
- [src/ui/api_key_modal.py](file://src/ui/api_key_modal.py#L83-L137)
- [src/llm/key_validator.py](file://src/llm/key_validator.py#L20-L88)

## Conclusion
MayaMCP's Modal deployment is configured for scalability and observability with dynamic resource tuning, comprehensive metrics, health checks, and resilient fallbacks. The new BYOK architecture enhances security and flexibility by supporting optional server-side keys with per-session authentication. The streamlined deployment configuration simplifies maintenance while maintaining backward compatibility and robust error handling. The documented workflow supports iterative development and production deployment, while CI/CD and testing configurations facilitate reliable automation. Operational runbooks and monitoring dashboards enable effective incident response and ongoing maintenance.

**Updated** The streamlined deployment system represents a significant improvement in operational efficiency, with simplified configuration management and reduced complexity for easier maintenance and faster deployment cycles.

## Appendices

### Appendix A: Environment Configuration Reference
- API Keys: GEMINI_API_KEY, CARTESIA_API_KEY, GOOGLE_API_KEY (legacy).
- Model Configuration: GEMINI_MODEL_VERSION, TEMPERATURE, MAX_OUTPUT_TOKENS.
- FastAPI Settings: PORT, HOST, WORKERS, LOG_LEVEL.
- Environment Flags: PYTHON_ENV, DEBUG.
- Modal Resource Tuning: MODAL_MEMORY_MB, MODAL_MAX_CONTAINERS.
- BYOK Configuration: Optional server-side keys; UI modal handles per-session authentication.

**Updated** Added BYOK configuration options for server-side key management and per-session authentication.

**Section sources**
- [.env.example](file://.env.example#L1-L33)
- [deploy.py](file://deploy.py#L34-L40)
- [src/ui/api_key_modal.py](file://src/ui/api_key_modal.py#L57-L80)

### Appendix B: Metrics Reference
- Configuration Gauges: maya_config_memory_mb, maya_config_max_containers.
- Container Metrics: maya_container_memory_usage_bytes, maya_container_memory_limit_bytes, maya_container_cpu_usage_seconds_total, maya_process_uptime_seconds.
- RAG Metrics: maya_rag_available, maya_rag_document_count, maya_rag_type.
- BYOK Metrics: maya_byok_enabled, maya_byok_user_count.

**Updated** Added BYOK-specific metrics for tracking user authentication and key validation success rates.

**Section sources**
- [deploy.py](file://deploy.py#L226-L282)
- [README.md](file://README.md#L411-L419)

### Appendix C: Rollback Procedures
- Modal Rollback: Use Modal CLI to roll back to a previous deployment version if available.
- Configuration Rollback: Revert environment variables (MODAL_MEMORY_MB, MODAL_MAX_CONTAINERS) to previously known-good values.
- Feature Flags: Disable optional features (e.g., security scanning) by uninstalling optional dependencies if instability is suspected.
- BYOK Rollback: Remove server-side API keys from Modal secrets if reverting to fully client-side authentication.
- Requirements Rollback: Revert to previous requirements.txt if dependency conflicts arise during rollback.

**Updated** Added BYOK-specific rollback procedures for server-side key management and streamlined requirements management.

### Appendix D: Backup Procedures
- Persistent Assets: Assets are stored on a Modal Volume; ensure regular snapshots or export procedures are established per Modal best practices.
- State Persistence: Distributed state is maintained via a Modal Dict; back up critical state periodically if required by compliance.
- Session State: BYOK session keys are stored in Modal Dict; implement proper session cleanup and expiration policies.
- Configuration Backup: Maintain backups of requirements.txt and deployment configurations for quick restoration.

**Updated** Added BYOK session state backup considerations for user authentication data and streamlined configuration backup procedures.