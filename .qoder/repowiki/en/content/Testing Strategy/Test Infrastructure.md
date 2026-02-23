# Test Infrastructure

<cite>
**Referenced Files in This Document**
- [pytest.ini](file://pytest.ini)
- [pyproject.toml](file://pyproject.toml)
- [tests/conftest.py](file://tests/conftest.py)
- [tests/test_memvid.py](file://tests/test_memvid.py)
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py)
- [tests/test_llm_client.py](file://tests/test_llm_client.py)
- [tests/test_processor_rag.py](file://tests/test_processor_rag.py)
- [tests/test_generation.py](file://tests/test_generation.py)
- [tests/test_ui_components.py](file://tests/test_ui_components.py)
- [tests/test_errors.py](file://tests/test_errors.py)
- [tests/test_model_config.py](file://tests/test_model_config.py)
- [src/llm/client.py](file://src/llm/client.py)
- [src/utils/errors.py](file://src/utils/errors.py)
- [src/config/model_config.py](file://src/config/model_config.py)
- [.env.example](file://.env.example)
- [.env](file://.env)
- [requirements.txt](file://requirements.txt)
</cite>

## Update Summary
**Changes Made**
- Enhanced documentation of GenAITimeoutError exception type support for improved timeout scenario handling
- Updated default model version and temperature behavior documentation reflecting new Gemini 3.0 Flash model as default
- Added comprehensive coverage of new timeout error handling capabilities in LLM client testing
- Updated error classification and logging documentation to include GenAITimeoutError support
- Enhanced test suite documentation to reflect new default model configuration behavior

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
This document explains MayaMCP's test infrastructure and configuration management. It covers pytest configuration, custom markers, test discovery patterns, fixtures and environment setup via conftest.py, test execution workflow, coverage reporting, and CI considerations. The infrastructure now features comprehensive Google GenAI SDK stubs with complete exception class hierarchies, enhanced timeout error handling capabilities, and updated default model configuration behavior. It provides practical guidance on test configuration options, environment variable management, test data organization, performance optimization, parallel execution strategies, debugging failures, and maintaining consistent test execution across environments.

## Project Structure
MayaMCP organizes tests under the tests/ directory with a dedicated conftest.py for global fixtures and shims. Configuration is split between pytest.ini and pyproject.toml. Environment variables are managed via .env and .env.example, while dependencies are declared in requirements.txt. The enhanced testing infrastructure includes comprehensive Google GenAI SDK stubs with complete exception hierarchies for offline compatibility, including new GenAITimeoutError support for timeout scenarios.

```mermaid
graph TB
subgraph "Root"
PIni["pytest.ini"]
PToml["pyproject.toml"]
EnvEx[".env.example"]
Env[".env"]
Req["requirements.txt"]
end
subgraph "Tests"
Cfg["tests/conftest.py"]
T1["tests/test_memvid.py"]
T2["tests/test_maya_memvid_full.py"]
T3["tests/test_llm_client.py"]
T4["tests/test_processor_rag.py"]
T5["tests/test_generation.py"]
T6["tests/test_ui_components.py"]
T7["tests/test_errors.py"]
T8["tests/test_model_config.py"]
end
subgraph "Enhanced Infrastructure"
Stub["Google GenAI SDK Stubs<br/>Complete Exception Hierarchy"]
Mock["Improved Mocking<br/>Offline Compatibility"]
Err["Error Classification<br/>Consistent Logging"]
Timeout["GenAITimeoutError Support<br/>Enhanced Timeout Handling"]
ModelCfg["Default Model Config<br/>Gemini 3.0 Flash Default"]
end
PIni --> Cfg
PToml --> Cfg
Cfg --> T1
Cfg --> T2
Cfg --> T3
Cfg --> T4
Cfg --> T5
Cfg --> T6
Cfg --> T7
Cfg --> T8
Stub --> T3
Stub --> T5
Err --> T7
Timeout --> T3
ModelCfg --> T8
EnvEx --> T1
EnvEx --> T2
EnvEx --> T8
Env --> T1
Env --> T2
Req --> T3
```

**Diagram sources**
- [pytest.ini](file://pytest.ini#L1-L27)
- [pyproject.toml](file://pyproject.toml#L48-L64)
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [tests/test_memvid.py](file://tests/test_memvid.py#L1-L123)
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py#L1-L250)
- [tests/test_llm_client.py](file://tests/test_llm_client.py#L1-L422)
- [tests/test_processor_rag.py](file://tests/test_processor_rag.py#L1-L83)
- [tests/test_generation.py](file://tests/test_generation.py#L1-L178)
- [tests/test_ui_components.py](file://tests/test_ui_components.py#L1-L334)
- [tests/test_errors.py](file://tests/test_errors.py#L1-L69)
- [tests/test_model_config.py](file://tests/test_model_config.py#L1-L408)
- [src/llm/client.py](file://src/llm/client.py#L1-L217)
- [src/utils/errors.py](file://src/utils/errors.py#L1-L39)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L127)
- [.env.example](file://.env.example#L1-L33)
- [.env](file://.env#L1-L12)
- [requirements.txt](file://requirements.txt#L1-L41)

**Section sources**
- [pytest.ini](file://pytest.ini#L1-L27)
- [pyproject.toml](file://pyproject.toml#L48-L64)
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [.env.example](file://.env.example#L1-L33)
- [.env](file://.env#L1-L12)
- [requirements.txt](file://requirements.txt#L1-L41)

## Core Components
- Pytest configuration and discovery:
  - Discovery patterns: test files, classes, and functions are matched by configured patterns.
  - Strict options enforce marker and config discipline.
  - Custom markers define categories for selective execution.
- Coverage configuration:
  - Coverage source and omission rules are defined centrally.
- Global fixtures and environment shims:
  - Comprehensive Google GenAI SDK stubbing ensures tests run even when external SDKs are not installed.
  - Complete exception class hierarchy mirrors real SDK structure for offline compatibility, including GenAITimeoutError.
  - Session-scoped flag controls expensive resource rebuilds.
- Environment variables:
  - API keys and model/runtime settings are documented in .env.example and populated in .env.
- Enhanced error handling:
  - Consistent error classification and logging across all test scenarios.
  - Comprehensive error type coverage for authentication, authorization, rate limiting, and timeout scenarios.
  - New GenAITimeoutError support for enhanced timeout error handling.
- Updated model configuration:
  - Default model version now uses Gemini 3.0 Flash model.
  - Intelligent temperature defaults based on model version (1.0 for Gemini 3.x, 0.7 for older models).

Key configuration anchors:
- pytest.ini: test discovery, strictness, warnings, and markers.
- pyproject.toml: pytest options and coverage configuration.
- tests/conftest.py: global fixtures, CLI options, comprehensive SDK stubs, and exception hierarchies.
- src/llm/client.py: enhanced error handling with SDK-specific exception mapping and GenAITimeoutError support.
- src/utils/errors.py: shared error classification and logging utilities.
- src/config/model_config.py: updated default model configuration with intelligent temperature defaults.
- tests/test_errors.py: comprehensive error classification testing.
- tests/test_model_config.py: model configuration testing with default values.

**Section sources**
- [pytest.ini](file://pytest.ini#L1-L27)
- [pyproject.toml](file://pyproject.toml#L48-L83)
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [src/llm/client.py](file://src/llm/client.py#L1-L217)
- [src/utils/errors.py](file://src/utils/errors.py#L1-L39)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L127)
- [tests/test_errors.py](file://tests/test_errors.py#L1-L69)
- [tests/test_model_config.py](file://tests/test_model_config.py#L1-L408)
- [.env.example](file://.env.example#L1-L33)
- [.env](file://.env#L1-L12)

## Architecture Overview
The test architecture centers on pytest with centralized configuration and shared fixtures. Tests leverage comprehensive Google GenAI SDK stubs with complete exception hierarchies to isolate dependencies. Enhanced mocking capabilities ensure offline compatibility while maintaining realistic error scenarios. The new GenAITimeoutError support provides specialized timeout handling for GenAI operations. Environment variables feed configuration for LLM clients and RAG components with updated default model settings. Coverage is configured to measure source code only. Error classification and logging provide consistent behavior across all test scenarios.

```mermaid
graph TB
Pytest["Pytest Runner"]
Cfg["tests/conftest.py<br/>Comprehensive SDK Stubs"]
Markers["Custom Markers<br/>slow, integration, unit,<br/>memvid, rag, llm, ui"]
Disc["Discovery Patterns<br/>test_*.py, Test*, test_*"]
Cov["Coverage Config<br/>tool.coverage.*"]
Env["Environment Variables<br/>.env and .env.example"]
Ext["External SDKs<br/>google-generativeai, others"]
Err["Error Classification<br/>Consistent Logging"]
Timeout["GenAITimeoutError Support<br/>Enhanced Timeout Handling"]
ModelCfg["Model Config<br/>Gemini 3.0 Flash Default"]
Pytest --> Disc
Pytest --> Markers
Pytest --> Cfg
Pytest --> Cov
Cfg --> Ext
Cfg --> Err
Cfg --> Timeout
Cfg --> ModelCfg
Env --> Pytest
```

**Diagram sources**
- [pytest.ini](file://pytest.ini#L4-L26)
- [pyproject.toml](file://pyproject.toml#L48-L83)
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [src/llm/client.py](file://src/llm/client.py#L1-L217)
- [src/utils/errors.py](file://src/utils/errors.py#L1-L39)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L127)
- [.env.example](file://.env.example#L1-L33)
- [.env](file://.env#L1-L12)

## Detailed Component Analysis

### Pytest Configuration and Discovery
- Discovery patterns:
  - testpaths, python_files, python_classes, python_functions define how tests are discovered.
- Strictness:
  - strict-markers and strict-config ensure markers and configuration are validated.
- Output and warnings:
  - disable-warnings and short traceback improve readability.
  - color output enhances terminal UX.
- Custom markers:
  - slow, integration, unit, memvid, rag, llm, ui enable targeted selection and categorization.

Execution examples:
- Run all tests: pytest
- Run only unit tests: pytest -m unit
- Skip slow tests: pytest -m "not slow"

**Section sources**
- [pytest.ini](file://pytest.ini#L3-L26)

### Coverage Reporting Setup
- Source inclusion and omission:
  - Coverage runs against src and omits tests and caches.
- Report exclusions:
  - Lines such as __repr__, NotImplementedError, and main guards are excluded from coverage reports.
- Tool configuration:
  - Coverage settings are defined under tool.coverage.* in pyproject.toml.

Usage:
- Run coverage: coverage run -m pytest && coverage report
- HTML report: coverage html

**Section sources**
- [pyproject.toml](file://pyproject.toml#L66-L83)

### Conftest Configuration: Enhanced Fixtures, Stubs, and CLI Options
- Comprehensive SDK stubbing:
  - Ensures tests can run even if google-generativeai is not installed by creating complete stubs for required APIs.
  - Provides complete exception class hierarchy mirroring real SDK structure.
  - Includes Client, types, and errors modules with realistic API signatures.
  - **New**: Added GenAITimeoutError class for specialized timeout handling in GenAI operations.
  - **New**: TimeoutError alias points to GenAITimeoutError for SDK compatibility.
- Enhanced exception class hierarchy:
  - Base APIError class with specialized subclasses for different error types.
  - Complete coverage of authentication, authorization, rate limiting, and timeout scenarios.
  - Common aliases for SDK compatibility (e.g., PermissionDeniedError).
- Autouse compatibility fixture:
  - Maintains backward compatibility without side effects.
- CLI option and fixture:
  - --force-rebuild toggles expensive resource rebuilds.
  - force_rebuild_flag fixture resolves priority: CLI flag > environment variable > default.

Enhanced exception hierarchy structure:
```mermaid
flowchart TD
APIError["APIError (Base)"] --> ClientError["ClientError"]
APIError --> ServerError["ServerError"]
APIError --> FunctionInvocationError["FunctionInvocationError"]
APIError --> NotFoundError["NotFoundError"]
APIError --> InvalidArgumentError["InvalidArgumentError"]
APIError --> AuthenticationError["AuthenticationError"]
APIError --> UnauthenticatedError["UnauthenticatedError"]
APIError --> RateLimitError["RateLimitError"]
APIError --> GenAITimeoutError["GenAITimeoutError (New)"]
GenAITimeoutError --> TimeoutErrorAlias["TimeoutError (Alias)"]
APIError --> PermissionDenied["PermissionDenied"]
PermissionDenied --> PermissionDeniedError["PermissionDeniedError (Alias)"]
```

**Diagram sources**
- [tests/conftest.py](file://tests/conftest.py#L25-L83)

Priority resolution flow:
```mermaid
flowchart TD
Start(["Fixture Entry"]) --> CheckCLI["Check CLI flag '--force-rebuild'"]
CheckCLI --> |True| ReturnTrue["Return True"]
CheckCLI --> |False| CheckEnv["Read environment variable 'TEST_FORCE_REBUILD'"]
CheckEnv --> |1| ReturnTrue
CheckEnv --> |Not 1| Default["Default False"]
ReturnTrue --> End(["Exit"])
Default --> End
```

**Diagram sources**
- [tests/conftest.py](file://tests/conftest.py#L155-L182)

**Section sources**
- [tests/conftest.py](file://tests/conftest.py#L1-L182)

### Enhanced Error Handling and Classification
- Comprehensive error classification:
  - Shared utility for consistent error logging across all components.
  - Regex-based classification for rate limits, authentication, and timeouts.
  - Fallback to string matching for compatibility with various error formats.
  - **New**: Enhanced timeout detection supporting both built-in TimeoutError and GenAITimeoutError.
- SDK-specific error mapping:
  - Dynamic mapping of SDK error classes to local exception types.
  - Graceful fallback when SDK is unavailable or error classes differ.
  - Support for both explicit SDK error types and attribute-based detection.
  - **New**: Dedicated GenaiTimeoutError handling in LLM client for specialized timeout scenarios.
- Offline testing compatibility:
  - Complete exception hierarchy ensures tests work without real SDK installation.
  - Consistent error behavior regardless of SDK availability.
  - **New**: GenAITimeoutError support enables realistic timeout testing scenarios.

Error classification patterns:
- Rate limit detection: "429" codes or "rate limit" phrases (case-insensitive)
- Authentication detection: "401"/"403" codes or auth-related terms
- **New**: Timeout detection: "timeout" phrases, TimeoutError instances, or GenAITimeoutError
- Fallback: generic error logging for unclassified exceptions

**Section sources**
- [src/llm/client.py](file://src/llm/client.py#L1-L217)
- [src/utils/errors.py](file://src/utils/errors.py#L1-L39)
- [tests/test_errors.py](file://tests/test_errors.py#L1-L69)

### Enhanced Model Configuration and Default Behavior
- **Updated**: Default model version now uses "gemini-3.0-flash" instead of previous default.
- Intelligent temperature defaults:
  - Gemini 3.x models: temperature defaults to 1.0 (recommended for reasoning capabilities)
  - Older models (2.x and earlier): temperature defaults to 0.7
- Environment variable handling:
  - GEMINI_MODEL_VERSION: overrides default model selection
  - TEMPERATURE: overrides default temperature behavior
  - MAX_OUTPUT_TOKENS: sets maximum output tokens with 2048 as default
- Configuration validation:
  - Invalid environment values log warnings and fall back to defaults
  - Empty model version returns empty string for dynamic selection

Configuration examples:
- Default behavior: gemini-3.0-flash with temperature 1.0
- Custom model: GEMINI_MODEL_VERSION=gemini-2.5-pro with temperature 0.7
- Custom temperature: TEMPERATURE=0.9 overrides model-specific defaults

**Section sources**
- [src/config/model_config.py](file://src/config/model_config.py#L1-L127)
- [tests/test_model_config.py](file://tests/test_model_config.py#L139-L195)

### Test Execution Workflow
- Typical flow:
  - pytest loads configuration and markers.
  - Discover tests per patterns.
  - Execute tests with fixtures applied.
  - Comprehensive SDK stubs handle external dependencies.
  - Collect results and produce coverage reports.
- Selective execution:
  - Use -m to select categories (e.g., unit, memvid).
  - Use --force-rebuild to force rebuilds when needed.
- Enhanced error handling:
  - Consistent error classification across all test scenarios.
  - Comprehensive exception hierarchy for realistic error testing.
  - **New**: GenAITimeoutError support enables comprehensive timeout scenario testing.

Example commands:
- pytest -m unit -v
- pytest tests/test_memvid.py -k "test_memvid_integration" --force-rebuild
- pytest tests/test_errors.py -v
- pytest tests/test_llm_client.py -k "timeout" -v

**Section sources**
- [pytest.ini](file://pytest.ini#L3-L26)
- [tests/conftest.py](file://tests/conftest.py#L155-L182)
- [src/llm/client.py](file://src/llm/client.py#L1-L217)

### Environment Variable Management
- Template and defaults:
  - .env.example lists API keys, model settings, FastAPI settings, and environment flags.
- Local overrides:
  - .env provides actual values for local development.
- Usage in tests:
  - Tests read API keys and model parameters from environment-backed configuration modules.
  - **New**: Model configuration respects updated default values and intelligent temperature behavior.

Common variables:
- GEMINI_API_KEY, CARTESIA_API_KEY
- **Updated**: GEMINI_MODEL_VERSION defaults to "gemini-3.0-flash" (previously "gemini-3-flash-preview")
- TEMPERATURE: intelligent defaults based on model version (1.0 for Gemini 3.x, 0.7 for older)
- MAX_OUTPUT_TOKENS: 2048 default
- PYTHON_ENV, DEBUG
- TEST_FORCE_REBUILD (controls rebuild behavior in tests)

**Section sources**
- [.env.example](file://.env.example#L1-L33)
- [.env](file://.env#L1-L12)
- [tests/test_memvid.py](file://tests/test_memvid.py#L1-L123)
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py#L1-L250)
- [src/config/model_config.py](file://src/config/model_config.py#L54-L64)

### Test Data Organization
- Test fixtures and mocking:
  - Many tests use monkeypatch and mock to isolate external dependencies.
  - Enhanced mocking capabilities with comprehensive SDK stubs.
  - **New**: GenAITimeoutError support enables realistic timeout scenario testing.
- Shared test utilities:
  - conftest.py centralizes comprehensive shims and flags.
  - Error classification utilities for consistent logging.
  - **New**: Model configuration testing validates default behavior and environment overrides.
- Test categories:
  - LLM client tests validate configuration and API calls with enhanced error handling.
  - RAG and Memvid tests validate prompt construction and retrieval.
  - UI tests validate asset provisioning and error handling.
  - Error classification tests validate comprehensive error handling scenarios.
  - **New**: Model configuration tests validate default values and intelligent temperature behavior.

Examples:
- LLM client tests with enhanced error handling: [tests/test_llm_client.py](file://tests/test_llm_client.py#L1-L422)
- RAG and Memvid pipeline tests: [tests/test_generation.py](file://tests/test_generation.py#L1-L178)
- UI avatar setup tests: [tests/test_ui_components.py](file://tests/test_ui_components.py#L1-L334)
- Comprehensive error classification tests: [tests/test_errors.py](file://tests/test_errors.py#L1-L69)
- **New**: Model configuration tests: [tests/test_model_config.py](file://tests/test_model_config.py#L1-L408)

**Section sources**
- [tests/test_llm_client.py](file://tests/test_llm_client.py#L1-L422)
- [tests/test_generation.py](file://tests/test_generation.py#L1-L178)
- [tests/test_ui_components.py](file://tests/test_ui_components.py#L1-L334)
- [tests/test_errors.py](file://tests/test_errors.py#L1-L69)
- [tests/test_model_config.py](file://tests/test_model_config.py#L1-L408)

### Custom Markers for Test Categorization
- Defined markers:
  - slow, integration, unit
  - Additional functional markers used in tests: memvid, rag, llm, ui
- Selection:
  - Use -m to filter by category.
  - Deselect with -m "not <marker>".

Practical usage:
- Run only fast unit tests: pytest -m "unit and not slow"
- Focus on Memvid: pytest -m memvid

Note: While functional markers (memvid, rag, llm, ui) are used in tests, they are not declared in pytest.ini. To ensure strict enforcement, declare them in markers.

**Section sources**
- [pytest.ini](file://pytest.ini#L16-L23)
- [tests/test_memvid.py](file://tests/test_memvid.py#L1-L123)
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py#L1-L250)
- [tests/test_processor_rag.py](file://tests/test_processor_rag.py#L1-L83)

### Enhanced Test Fixtures and Shared Utilities
- force_rebuild_flag:
  - Resolves rebuild policy from CLI or environment.
- Comprehensive SDK stubs:
  - google-generativeai and google.genai stubs ensure tests run without installed SDKs.
  - Complete exception hierarchy with realistic error types, including GenAITimeoutError.
  - Client, types, and errors modules with proper API signatures.
  - **New**: GenAITimeoutError class provides specialized timeout handling for GenAI operations.
- Enhanced error classification utilities:
  - Shared error classification and logging across all components.
  - Comprehensive testing of error handling scenarios.
  - **New**: GenAITimeoutError support enables realistic timeout error testing.
- Monkeypatches and mocks:
  - Used extensively to simulate external systems (HTTP, LLM APIs, image processing).
- **New**: Model configuration utilities:
  - Intelligent temperature defaults based on model version.
  - Environment variable validation and fallback behavior.

Enhanced example patterns:
- Using force_rebuild_flag in Memvid tests: [tests/test_memvid.py](file://tests/test_memvid.py#L27-L64)
- Mocking LLM client calls with enhanced error handling: [tests/test_llm_client.py](file://tests/test_llm_client.py#L285-L301)
- Comprehensive error classification validation: [tests/test_errors.py](file://tests/test_errors.py#L1-L69)
- Prompt construction validation: [tests/test_generation.py](file://tests/test_generation.py#L30-L178)
- **New**: Model configuration validation: [tests/test_model_config.py](file://tests/test_model_config.py#L139-L195)

**Section sources**
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [tests/test_memvid.py](file://tests/test_memvid.py#L1-L123)
- [tests/test_llm_client.py](file://tests/test_llm_client.py#L1-L422)
- [tests/test_generation.py](file://tests/test_generation.py#L1-L178)
- [tests/test_errors.py](file://tests/test_errors.py#L1-L69)
- [tests/test_model_config.py](file://tests/test_model_config.py#L1-L408)

### Continuous Integration Considerations
- CI-friendly defaults:
  - force_rebuild defaults to False to speed up CI runs.
  - Strict markers and config reduce flakiness.
  - Comprehensive SDK stubs ensure CI stability without external dependencies.
  - **New**: Default model configuration uses Gemini 3.0 Flash for optimal CI performance.
- Recommended CI steps:
  - Install dependencies from requirements.txt.
  - Optionally set TEST_FORCE_REBUILD=1 for full rebuilds in CI stages that require it.
  - Run pytest with selected markers to partition jobs.
  - Generate coverage and publish reports.
  - Enhanced error handling ensures consistent CI behavior across different environments.
  - **New**: Model configuration tests validate default behavior without requiring environment setup.

**Section sources**
- [tests/conftest.py](file://tests/conftest.py#L155-L182)
- [pytest.ini](file://pytest.ini#L8-L13)
- [requirements.txt](file://requirements.txt#L1-L41)
- [src/config/model_config.py](file://src/config/model_config.py#L54-L64)

## Dependency Analysis
- Internal dependencies:
  - Tests depend on src modules for LLM, RAG, UI, utilities, and model configuration.
  - conftest.py depends on pytest and optionally on google-generativeai.
  - Enhanced error handling utilities provide shared functionality.
  - **New**: Model configuration utilities provide intelligent default behavior.
- External dependencies:
  - google-generativeai and related packages are optional for tests.
  - Testing libraries include pytest and hypothesis.
  - Enhanced error classification utilities support comprehensive error handling.
  - **New**: GenAITimeoutError support requires updated SDK stubs.

```mermaid
graph TB
T["tests/*"]
Src["src/*"]
Ggai["google-generativeai (optional)"]
Pyt["pytest"]
Hyp["hypothesis"]
ErrUtil["src/utils/errors.py<br/>Error Classification"]
ModelCfg["src/config/model_config.py<br/>Model Configuration"]
T --> Src
T --> Pyt
T --> Hyp
T -.-> Ggai
ErrUtil --> T
ModelCfg --> T
```

**Diagram sources**
- [tests/test_llm_client.py](file://tests/test_llm_client.py#L1-L422)
- [tests/test_generation.py](file://tests/test_generation.py#L1-L178)
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [src/utils/errors.py](file://src/utils/errors.py#L1-L39)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L127)
- [requirements.txt](file://requirements.txt#L1-L41)

**Section sources**
- [tests/test_llm_client.py](file://tests/test_llm_client.py#L1-L422)
- [tests/test_generation.py](file://tests/test_generation.py#L1-L178)
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [src/utils/errors.py](file://src/utils/errors.py#L1-L39)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L127)
- [requirements.txt](file://requirements.txt#L1-L41)

## Performance Considerations
- Skip expensive operations in CI:
  - Use force_rebuild_flag to avoid rebuilding Memvid stores unless necessary.
- Selective execution:
  - Use -m unit and -m "not slow" to focus on fast tests.
- Enhanced mocking reduces external dependencies:
  - Comprehensive SDK stubs eliminate network latency and flakiness.
  - Realistic exception hierarchies provide accurate error simulation.
  - **New**: GenAITimeoutError support enables efficient timeout scenario testing.
- Coverage overhead:
  - Keep coverage enabled for PR checks; consider parallel coverage collection in CI.
- Error handling efficiency:
  - Shared error classification utilities reduce code duplication.
  - Comprehensive error testing ensures reliable error handling without performance impact.
  - **New**: Intelligent model configuration defaults optimize performance for modern models.
- **New**: Default Gemini 3.0 Flash model provides better performance characteristics than older models.

## Troubleshooting Guide
- Missing optional SDK:
  - Tests should still run due to comprehensive stubs; if they fail, verify stubs are active.
  - Enhanced exception hierarchy ensures realistic error simulation without SDK.
  - **New**: GenAITimeoutError support ensures timeout scenarios work without real SDK.
- API key issues:
  - Ensure .env contains valid keys; tests skip when keys are missing.
- Slow or flaky tests:
  - Use -m "not slow" to exclude heavy tests.
  - For Memvid tests, use --force-rebuild to refresh data.
  - Enhanced error handling provides consistent behavior across environments.
- Debugging test failures:
  - Use -v and --tb=short for concise traces.
  - Add logging to tests to capture runtime behavior.
  - Enhanced error classification provides detailed error context.
  - **New**: GenAITimeoutError tests help diagnose timeout-related issues.
- Coverage gaps:
  - Confirm tool.coverage settings and omit patterns.
  - Comprehensive error handling ensures thorough coverage of error scenarios.
- Offline testing compatibility:
  - Enhanced SDK stubs ensure tests run without external dependencies.
  - Complete exception hierarchy provides realistic error simulation.
  - **New**: GenAITimeoutError support enables comprehensive timeout testing.
- **New**: Model configuration issues:
  - Verify GEMINI_MODEL_VERSION environment variable if default behavior differs.
  - Check TEMPERATURE environment variable for custom temperature settings.
  - Model configuration tests validate default behavior and environment overrides.

**Section sources**
- [tests/conftest.py](file://tests/conftest.py#L1-L182)
- [.env](file://.env#L1-L12)
- [pytest.ini](file://pytest.ini#L8-L13)
- [pyproject.toml](file://pyproject.toml#L66-L83)
- [src/llm/client.py](file://src/llm/client.py#L1-L217)
- [src/utils/errors.py](file://src/utils/errors.py#L1-L39)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L127)

## Conclusion
MayaMCP's enhanced test infrastructure combines centralized pytest configuration, comprehensive fixtures, and environment-driven behavior to support reliable, maintainable, and efficient testing. The new comprehensive Google GenAI SDK stubs with complete exception hierarchies, including GenAITimeoutError support, improved mocking capabilities, and better offline testing compatibility provide robust foundation for testing. The updated default model configuration with Gemini 3.0 Flash as default and intelligent temperature behavior ensures optimal performance characteristics. By leveraging markers, selective execution, enhanced error handling, comprehensive timeout scenario testing, and coverage configuration, teams can ensure consistent test outcomes across development and CI environments. The enhanced error classification utilities, comprehensive exception hierarchy, and intelligent model configuration ensure reliable error handling while maintaining test performance. Adopting the recommended practices and maintaining configuration parity will keep the test suite scalable, dependable, and compatible across different environments.

## Appendices

### Appendix A: Enhanced Example Commands
- Run unit tests only: pytest -m unit -v
- Exclude slow tests: pytest -m "not slow"
- Force Memvid rebuilds: pytest --force-rebuild tests/test_memvid.py
- Generate coverage: coverage run -m pytest && coverage report
- Test error classification: pytest tests/test_errors.py -v
- Test with comprehensive SDK stubs: pytest tests/test_llm_client.py -k "error" -v
- **New**: Test timeout scenarios: pytest tests/test_llm_client.py -k "timeout" -v
- **New**: Test model configuration: pytest tests/test_model_config.py -v

**Section sources**
- [pytest.ini](file://pytest.ini#L8-L13)
- [tests/conftest.py](file://tests/conftest.py#L155-L182)
- [pyproject.toml](file://pyproject.toml#L66-L83)
- [tests/test_errors.py](file://tests/test_errors.py#L1-L69)
- [tests/test_llm_client.py](file://tests/test_llm_client.py#L285-L301)
- [tests/test_model_config.py](file://tests/test_model_config.py#L1-L408)

### Appendix B: Enhanced Environment Variables Reference
- API keys: GEMINI_API_KEY, CARTESIA_API_KEY
- **Updated**: Model settings: GEMINI_MODEL_VERSION (defaults to "gemini-3.0-flash"), TEMPERATURE (intelligent defaults: 1.0 for Gemini 3.x, 0.7 for older), MAX_OUTPUT_TOKENS (2048 default)
- Runtime: PYTHON_ENV, DEBUG
- Test control: TEST_FORCE_REBUILD
- Enhanced error handling: Comprehensive error classification and logging
- **New**: GenAITimeoutError support: Specialized timeout handling for GenAI operations

**Section sources**
- [.env.example](file://.env.example#L1-L33)
- [.env](file://.env#L1-L12)
- [tests/conftest.py](file://tests/conftest.py#L78-L83)
- [src/utils/errors.py](file://src/utils/errors.py#L1-L39)
- [src/config/model_config.py](file://src/config/model_config.py#L54-L64)

### Appendix C: Enhanced Exception Class Hierarchy Reference
- Base APIError class with specialized subclasses:
  - ClientError, ServerError, FunctionInvocationError
  - NotFoundError, InvalidArgumentError
  - AuthenticationError, UnauthenticatedError
  - RateLimitError, TimeoutError (alias), GenAITimeoutError (New)
  - PermissionDenied with PermissionDeniedError alias
- **New**: GenAITimeoutError provides specialized timeout handling for GenAI operations
- **New**: TimeoutError alias points to GenAITimeoutError for SDK compatibility
- Common aliases for SDK compatibility
- Realistic exception signatures for comprehensive testing

**Section sources**
- [tests/conftest.py](file://tests/conftest.py#L25-L83)
- [src/llm/client.py](file://src/llm/client.py#L33-L41)
- [tests/test_errors.py](file://tests/test_errors.py#L1-L69)

### Appendix D: Enhanced Model Configuration Reference
- **Updated**: Default model version: "gemini-3.0-flash" (previously "gemini-3-flash-preview")
- Intelligent temperature defaults:
  - Gemini 3.x models: 1.0 (recommended for reasoning capabilities)
  - Older models (2.x and earlier): 0.7
- Environment variable behavior:
  - GEMINI_MODEL_VERSION: overrides default model selection
  - TEMPERATURE: overrides default temperature behavior
  - MAX_OUTPUT_TOKENS: sets maximum output tokens with 2048 as default
- Validation and fallback:
  - Invalid environment values log warnings and fall back to defaults
  - Empty model version returns empty string for dynamic selection

**Section sources**
- [src/config/model_config.py](file://src/config/model_config.py#L31-L64)
- [tests/test_model_config.py](file://tests/test_model_config.py#L139-L195)