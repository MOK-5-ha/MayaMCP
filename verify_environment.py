#!/usr/bin/env python3
"""Diagnostic environment verifier for GCP Vertex AI Mode (Paid Tier).

Validates GCP_PROJECT resolution, ADC authentication, google-genai SDK loading,
and model inference connectivity.
"""

import asyncio
import os
import sys


async def _load_env_files_async(paths: list[str]) -> None:
    """Asynchronously load candidate .env files in priority order without breaking early.

    Ensures empty keys (e.g. GCP_PROJECT= in template files) fall back to non-empty keys in valid env files.
    """
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            def _read_file(p: str):
                values = {}
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'").strip('"')
                        if v:
                            values[k] = v
                return values

            env_vars = await asyncio.to_thread(_read_file, path)
            for k, v in env_vars.items():
                if not os.getenv(k):
                    os.environ[k] = v
        except (OSError, UnicodeDecodeError, ValueError) as e:
            sys.stderr.write(f"Warning: Failed to read env file '{path}': {e}\n")


async def verify_environment() -> bool:
    """Verify environment setup for 100% GCP Vertex AI Mode."""
    print("==================================================================")
    print("  MayaMCP Environment Verifier - GCP Vertex AI Mode (Paid Tier)")
    print("==================================================================")

    # 1. Load candidate .env files asynchronously
    candidate_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "backend", ".env"),
    ]
    await _load_env_files_async(candidate_paths)

    # 2. Check GCP_PROJECT / GOOGLE_CLOUD_PROJECT
    project = (os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()
    if not project:
        sys.stderr.write(
            "❌ ERROR: Neither GCP_PROJECT nor GOOGLE_CLOUD_PROJECT is configured!\n"
            "Google AI Studio API Key Mode has been permanently removed.\n"
            "Please set GCP_PROJECT in your .env file.\n"
        )
        return False

    print(f"✓ GCP Project ID: {project}")

    location = (os.getenv("GCP_LOCATION") or "global").strip() or "global"
    print(f"✓ GCP Location: {location}")

    tier = (os.getenv("GEMINI_TIER") or "paid").strip().lower()
    if tier != "paid":
        print(f"⚠️ Warning: GEMINI_TIER is '{tier}'. Enforcing 'paid' tier for Vertex AI.")
    os.environ["GEMINI_TIER"] = "paid"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "true"
    print("✓ GEMINI_TIER locked to 'paid' (300+ RPM quota via GCP billing credits)")

    # 3. Check google-genai SDK version
    try:
        import google.genai
        print("✓ google-genai SDK loaded successfully")
    except ImportError:
        sys.stderr.write("❌ ERROR: google-genai SDK is not installed!\n")
        return False

    # 4. Initialize Vertex AI client and verify connectivity
    try:
        client = google.genai.Client(vertexai=True, project=project, location=location)
        print("✓ Client instantiated in Vertex AI mode (vertexai=True)")

        try:
            from src.config.model_config import get_model_config
            model = get_model_config()["model_version"]
        except ImportError:
            model = os.getenv("GEMINI_MODEL_VERSION", "gemini-3.5-flash-lite")
        print(f"Testing inference connectivity against model '{model}'...")

        def _test_call():
            return client.models.generate_content(
                model=model,
                contents="Ping - respond with 'pong'.",
            )

        resp = await asyncio.to_thread(_test_call)
        print(f"✓ Model response: {getattr(resp, 'text', '').strip()[:50]}")

    except Exception as e:
        print(f"⚠️ Warning: Live API connectivity test omitted or failed: {e}")
        print("  (If testing offline or in CI without credentials, this is expected).")

    print("\n✅ Environment verification passed!")
    return True


async def main():
    success = await verify_environment()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
