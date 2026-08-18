#!/usr/bin/env python3
"""Deprecated Weave runner shim. Forwards execution to scripts/run_evals.py."""

import sys
import os

print("⚠️  NOTICE: Weights & Biases Weave evaluations have been deprecated in favor of Google Cloud Vertex AI Gen AI Evaluation Service.")
print("    Redirecting to scripts/run_evals.py...\n")

sys.path.insert(0, os.getcwd())
from scripts.run_evals import run_evaluation

if __name__ == "__main__":
    run_evaluation()
