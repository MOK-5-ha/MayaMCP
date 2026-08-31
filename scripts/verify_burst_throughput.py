#!/usr/bin/env python3
"""
High-Throughput Burst Verification Script for GCP Vertex AI Paid Tier (300+ RPM).
Fires 25 concurrent requests to verify high quota throughput with zero 429 errors.
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

load_dotenv()

# Verify GCP_PROJECT is set
gcp_project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
if not gcp_project:
    # Set active gcloud project as fallback if present
    os.environ["GCP_PROJECT"] = "gen-lang-client-0070523080"
    gcp_project = "gen-lang-client-0070523080"

from src.llm.client import get_genai_client, get_model_name  # noqa: E402

CONCURRENCY = 25
PROMPT = "Reply in one word: 'Ready'."


def send_request(request_id: int):
    start_time = time.time()
    try:
        client = get_genai_client()
        model_name = get_model_name()
        response = client.models.generate_content(
            model=model_name,
            contents=PROMPT,
        )
        elapsed = time.time() - start_time
        text = response.text.strip() if response and hasattr(response, "text") and response.text else "OK"
        return {"id": request_id, "success": True, "elapsed": elapsed, "text": text, "error": None}
    except Exception as e:
        elapsed = time.time() - start_time
        return {"id": request_id, "success": False, "elapsed": elapsed, "text": "", "error": str(e)}


def run_burst_test():
    print("=" * 65)
    print(f"  GCP Vertex AI High-Throughput Burst Test ({CONCURRENCY} Parallel Requests)")
    print(f"  Project:  {gcp_project}")
    print(f"  Model:    {get_model_name()}")
    print("=" * 65)

    start_burst = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(send_request, i) for i in range(1, CONCURRENCY + 1)]
        for future in as_completed(futures):
            results.append(future.result())

    total_time = time.time() - start_burst
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    rate_limited = [r for r in results if r["error"] and ("429" in r["error"] or "RESOURCE_EXHAUSTED" in r["error"])]

    avg_latency = sum(r["elapsed"] for r in results) / len(results) if results else 0.0

    print("\nResults Summary:")
    print(f"  - Total Requests:      {len(results)}")
    print(f"  - Successful:          {len(successful)}")
    print(f"  - Failed:              {len(failed)}")
    print(f"  - Rate Limited (429):  {len(rate_limited)}")
    print(f"  - Total Burst Time:    {total_time:.2f} seconds")
    print(f"  - Avg Latency/Request: {avg_latency:.2f} seconds")

    if rate_limited:
        print("\n[✗] FAIL: Rate limit (429) errors detected during high-throughput burst!")
        return 1

    if len(successful) < CONCURRENCY:
        print(f"\n[!] WARNING: {len(failed)} requests failed. Failure details:")
        for f in failed:
            print(f"    Request {f['id']}: {f['error']}")
        return 1

    print("\n[✓] SUCCESS: 100% of burst requests completed with ZERO rate limit errors.")
    return 0


if __name__ == "__main__":
    sys.exit(run_burst_test())
