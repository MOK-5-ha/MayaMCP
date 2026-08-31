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

"""Unit tests for evaluation rubrics in src/eval/rubrics.py."""

import pytest
from pydantic import ValidationError

from src.eval.rubrics import PointwiseEvaluationRubric, TrajectoryEvaluationRubric


def test_trajectory_rubric_valid():
    """Test valid TrajectoryEvaluationRubric instantiation."""
    rubric = TrajectoryEvaluationRubric(
        multi_hop_synthesis_score=5,
        context_precision_score=4,
        faithfulness_score=5,
        trajectory_soundness_score=4,
        reasoning_justification="Step-by-step reasoning justification for the test score.",
        is_fallback=False,
    )
    assert rubric.multi_hop_synthesis_score == 5
    assert rubric.is_fallback is False


def test_trajectory_rubric_extra_forbidden():
    """Test extra fields are forbidden in TrajectoryEvaluationRubric."""
    with pytest.raises(ValidationError):
        TrajectoryEvaluationRubric(
            multi_hop_synthesis_score=5,
            context_precision_score=4,
            faithfulness_score=5,
            trajectory_soundness_score=4,
            reasoning_justification="Step-by-step reasoning justification.",
            unauthorized_extra_field="malicious_payload",
        )


def test_trajectory_rubric_range_validation():
    """Test out-of-range scores raise ValidationError."""
    with pytest.raises(ValidationError):
        TrajectoryEvaluationRubric(
            multi_hop_synthesis_score=6,  # > 5
            context_precision_score=4,
            faithfulness_score=5,
            trajectory_soundness_score=4,
            reasoning_justification="Step-by-step reasoning justification.",
        )

    with pytest.raises(ValidationError):
        TrajectoryEvaluationRubric(
            multi_hop_synthesis_score=0,  # < 1
            context_precision_score=4,
            faithfulness_score=5,
            trajectory_soundness_score=4,
            reasoning_justification="Step-by-step reasoning justification.",
        )


def test_pointwise_rubric_valid():
    """Test valid PointwiseEvaluationRubric instantiation."""
    rubric = PointwiseEvaluationRubric(
        score=4,
        explanation="The response was clear and concise.",
        is_fallback=False,
    )
    assert rubric.score == 4
    assert rubric.is_fallback is False
