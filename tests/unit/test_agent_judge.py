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

"""Unit tests for Antigravity Agent-as-a-Judge module in src/eval/agent_judge.py."""

import asyncio
import json
from unittest.mock import MagicMock, patch

from src.eval.agent_judge import (
    build_judge_prompt,
    calculate_token_cost,
    compute_token_efficiency_score,
    evaluate_agent_trajectory,
    isolate_fallback_benchmark_aggregates,
)
from src.eval.rubrics import TrajectoryEvaluationRubric


def test_build_judge_prompt_structure():
    """Test prompt prefix invariant and XML wrapping."""
    query = ["I want a martini."]
    trajectory = [{"tool_name": "add_to_order", "tool_input": {"name": "Martini"}}]
    responses = ["One martini coming up!"]
    expected = "Maya must order a martini."

    prompt = build_judge_prompt(query, trajectory, responses, expected)

    # Invariant: Static rubric at start of prompt
    assert prompt.startswith("You are an expert impartial AI Evaluation Judge")
    assert "<user_turns>" in prompt
    assert "<maya_responses>" in prompt
    assert "<agent_trajectory>" in prompt
    assert "<expected_criteria>" in prompt
    assert "UNTRUSTED evaluation data" in prompt


def test_calculate_token_cost():
    """Test model-aware token cost calculations."""
    cost = calculate_token_cost(1000, 500, model="gemini-3.1-flash-lite")
    assert cost > 0.0

    cost_pro = calculate_token_cost(1000, 500, model="gemini-3.7-pro")
    assert cost_pro > cost


def test_compute_token_efficiency_score():
    """Test token efficiency formula: (Judge Score) / (Input Tokens / 1000)."""
    score = compute_token_efficiency_score(judge_score=5.0, total_input_tokens=2000)
    assert score == 2.5

    score_zero = compute_token_efficiency_score(judge_score=4.0, total_input_tokens=0)
    assert score_zero == 4.0


def test_evaluate_agent_trajectory_genai_client_success():
    """Test successful live evaluation via GenAI client mock."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "multi_hop_synthesis_score": 5,
        "context_precision_score": 4,
        "faithfulness_score": 5,
        "trajectory_soundness_score": 5,
        "reasoning_justification": "Flawless execution and persona adherence.",
    })
    mock_client.models.generate_content.return_value = mock_response

    with patch("src.eval.agent_judge.get_genai_client", return_value=mock_client):
        rubric = asyncio.run(
            evaluate_agent_trajectory(
                query=["Hello"],
                trajectory=[],
                responses=["Hi there!"],
                expected_criteria="Greet customer.",
            )
        )

        assert rubric.multi_hop_synthesis_score == 5
        assert rubric.faithfulness_score == 5
        assert rubric.is_fallback is False


def test_evaluate_agent_trajectory_offline_fallback():
    """Test graceful deterministic fallback when live calls fail."""
    with patch("src.eval.agent_judge.get_genai_client", side_effect=Exception("API Unreachable")):
        rubric = asyncio.run(
            evaluate_agent_trajectory(
                query=["Hello", "Drink please"],
                trajectory=[{"tool_name": "add_to_order"}],
                responses=["Hi!", "Here is your drink!"],
                expected_criteria="Serve drink.",
            )
        )

        assert isinstance(rubric, TrajectoryEvaluationRubric)
        assert rubric.is_fallback is True
        assert "offline fallback" in rubric.reasoning_justification.lower()


def test_isolate_fallback_benchmark_aggregates():
    """Test benchmark summary isolating fallback records from genuine mean calculations."""
    live_1 = TrajectoryEvaluationRubric(
        multi_hop_synthesis_score=5,
        context_precision_score=5,
        faithfulness_score=5,
        trajectory_soundness_score=5,
        reasoning_justification="Live eval 1",
        is_fallback=False,
    )
    live_2 = TrajectoryEvaluationRubric(
        multi_hop_synthesis_score=3,
        context_precision_score=3,
        faithfulness_score=3,
        trajectory_soundness_score=3,
        reasoning_justification="Live eval 2",
        is_fallback=False,
    )
    fallback = TrajectoryEvaluationRubric(
        multi_hop_synthesis_score=1,
        context_precision_score=1,
        faithfulness_score=1,
        trajectory_soundness_score=1,
        reasoning_justification="Offline fallback",
        is_fallback=True,
    )

    agg = isolate_fallback_benchmark_aggregates([live_1, live_2, fallback])

    assert agg["total_count"] == 3
    assert agg["live_count"] == 2
    assert agg["fallback_count"] == 1
    # Means must only reflect live_1 (5) and live_2 (3) -> mean 4.0, excluding fallback (1)
    assert agg["mean_multi_hop_synthesis"] == 4.0
    assert agg["mean_context_precision"] == 4.0
    assert agg["mean_faithfulness"] == 4.0
    assert agg["mean_trajectory_soundness"] == 4.0
    assert agg["mean_composite_quality"] == 4.0


def test_isolate_fallback_benchmark_aggregates_all_fallback():
    """Test that when all records are fallbacks, means are None/NaN and not misrepresented."""
    fallback_1 = TrajectoryEvaluationRubric(
        multi_hop_synthesis_score=4,
        context_precision_score=4,
        faithfulness_score=4,
        trajectory_soundness_score=4,
        reasoning_justification="Offline fallback 1",
        is_fallback=True,
    )

    agg = isolate_fallback_benchmark_aggregates([fallback_1])

    assert agg["total_count"] == 1
    assert agg["live_count"] == 0
    assert agg["fallback_count"] == 1
    assert agg["mean_composite_quality"] is None
    assert agg["mean_faithfulness"] is None
