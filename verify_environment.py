#!/usr/bin/env python3
"""
Environment Verification Script for MayaMCP GCP Vertex AI & Gemini Configuration.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

def verify_environment():
    print("=" * 60)
    print("  MayaMCP GCP Vertex AI & Gemini Environment Verifier")
    print("=" * 60)

    gcp_project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    gcp_location = os.getenv("GCP_LOCATION", "global").strip() or "global"
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    gemini_tier = os.getenv("GEMINI_TIER", "free").strip().lower()

    print(f"[*] GEMINI_TIER: {gemini_tier}")

    if gcp_project and gcp_project.strip():
        print(f"[✓] Mode: GCP Vertex AI Mode")
        print(f"    - GCP Project ID: {gcp_project.strip()}")
        print(f"    - GCP Location:   {gcp_location}")
    elif gemini_api_key and gemini_api_key.strip():
        print(f"[✓] Mode: Google AI Studio Mode")
        print(f"    - API Key:        {gemini_api_key[:6]}...{gemini_api_key[-4:]}")
    else:
        print("[✗] Error: Neither GCP_PROJECT/GOOGLE_CLOUD_PROJECT nor GEMINI_API_KEY is configured!")
        print("    Please set GCP_PROJECT or GEMINI_API_KEY in your .env file or environment.")
        return 1

    try:
        from src.llm.client import get_genai_client
        client = get_genai_client()
        print(f"[✓] genai.Client successfully instantiated ({type(client).__name__})")
    except Exception as e:
        print(f"[✗] Failed to instantiate genai.Client: {e}")
        return 1

    print("\n[✓] Environment verification passed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(verify_environment())
