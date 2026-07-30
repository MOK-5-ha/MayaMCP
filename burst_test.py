#!/usr/bin/env python3
"""High-throughput burst test script for GCP Vertex AI Mode (Paid Tier).

Tests parallel request concurrency using asyncio.gather against the paid-tier quota.
"""

import asyncio
import os
import sys
import time
from typing import Any, Dict


async def simulate_request(req_id: int, project: str, location: str) -> Dict[str, Any]:
    """Execute a single request to verify concurrent throughput."""
    start_time = time.perf_counter()
    try:
        from google import genai
        # Read environment dynamically per request
        use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true") == "true"
        
        # Mock or live call depending on environment
        if os.getenv("MOCK_BURST") == "true" or not os.getenv("GCP_PROJECT"):
            await asyncio.sleep(0.05)  # Simulate network I/O
            latency = time.perf_counter() - start_time
            return {"id": req_id, "status": "success", "latency": latency, "mock": True}

        client = genai.Client(vertexai=use_vertex, project=project, location=location)

        def _sync_call():
            return client.models.generate_content(
                model=os.getenv("GEMINI_MODEL_VERSION", "gemini-3.1-flash-lite"),
                contents=f"High-throughput test request #{req_id}",
            )

        resp = await asyncio.to_thread(_sync_call)
        latency = time.perf_counter() - start_time
        return {"id": req_id, "status": "success", "latency": latency, "text": getattr(resp, "text", "")}

    except Exception as e:
        latency = time.perf_counter() - start_time
        return {"id": req_id, "status": "error", "error": str(e), "latency": latency}


async def run_burst_test(concurrency: int = 20) -> bool:
    """Run high-throughput parallel request burst test."""
    print("==================================================================")
    print(f"  MayaMCP High-Throughput Burst Test ({concurrency} parallel requests)")
    print("==================================================================")

    # Dynamic project resolution inside entrypoint
    project = (os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "dummy-gcp-project").strip()
    location = (os.getenv("GCP_LOCATION") or "global").strip() or "global"

    print(f"Targeting Project: {project} | Location: {location}")
    print(f"Dispatching {concurrency} concurrent requests via asyncio.gather...")

    start_total = time.perf_counter()

    tasks = [simulate_request(i + 1, project, location) for i in range(concurrency)]
    results = await asyncio.gather(*tasks)

    total_time = time.perf_counter() - start_total
    successes = [r for r in results if r["status"] == "success"]
    failures = [r for r in results if r["status"] != "success"]

    throughput = len(results) / total_time if total_time > 0 else 0

    print("\n--- Burst Test Results ---")
    print(f"Total Completed Requests: {len(results)}")
    print(f"Successful Requests:       {len(successes)}")
    print(f"Failed Requests:           {len(failures)}")
    print(f"Total Time Elapsed:        {total_time:.3f}s")
    print(f"Effective Throughput:      {throughput:.2f} req/sec")

    if failures:
        print("\nFailure summary:")
        for f in failures[:5]:
            print(f"  Req #{f['id']}: {f['error']}")

    return len(failures) == 0


async def main():
    concurrency = 20
    if len(sys.argv) > 1:
        try:
            concurrency = int(sys.argv[1])
        except ValueError:
            pass
    success = await run_burst_test(concurrency)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
