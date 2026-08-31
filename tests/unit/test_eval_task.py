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

"""Unit tests for Vertex AI EvalTask integration in src/eval/eval_task.py."""

from unittest.mock import MagicMock, patch

import pandas as pd

from src.eval.eval_task import build_evaluation_dataframe, run_vertex_eval_task


def test_build_evaluation_dataframe():
    """Test building a pandas DataFrame formatted for Vertex AI EvalTask."""
    dataset_items = [
        {
            "turns": ["I'll have a martini."],
            "expected_logic": "Order a martini.",
            "reference_trajectory": [{"tool_name": "add_to_order"}],
        }
    ]
    model_outputs = [
        {
            "responses": ["Martini added."],
            "predicted_trajectory": [{"tool_name": "add_to_order"}],
        }
    ]

    df = build_evaluation_dataframe(dataset_items, model_outputs)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "prompt" in df.columns
    assert "response" in df.columns
    assert "reference" in df.columns
    assert "predicted_trajectory" in df.columns
    assert "reference_trajectory" in df.columns


def test_run_vertex_eval_task_offline_fallback():
    """Test that when Vertex AI EvalTask raises an exception, the function logs and returns None safely."""
    dataset_items = [
        {
            "turns": ["I'll have a martini."],
            "expected_logic": "Order a martini.",
        }
    ]
    model_outputs = [
        {
            "responses": ["Martini added."],
        }
    ]

    with patch("vertexai.init", side_effect=Exception("ADC Unavailable")):
        result = run_vertex_eval_task(dataset_items, model_outputs, "test-proj", "us-central1")
        assert result is None
