#!/usr/bin/env python3
"""Deprecated Weave runner shim. Forwards execution to scripts/run_evals.py."""

import os
import sys

print("⚠️  NOTICE: Weights & Biases Weave evaluations have been deprecated in favor of Google Cloud Vertex AI Gen AI Evaluation Service.")
print("    Redirecting to scripts/run_evals.py...\n")

sys.path.insert(0, os.getcwd())
from scripts.run_evals import run_evaluation  # noqa: E402

if __name__ == "__main__":
    run_evaluation()
