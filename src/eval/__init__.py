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

"""MayaMCP Vertex AI Gen AI Evaluation Engine and Agent-as-a-Judge package."""

from src.eval.agent_judge import (
    calculate_token_cost,
    compute_token_efficiency_score,
    evaluate_agent_trajectory,
    isolate_fallback_benchmark_aggregates,
)
from src.eval.eval_task import (
    build_evaluation_dataframe,
    run_vertex_eval_task,
)
from src.eval.rubrics import (
    PointwiseEvaluationRubric,
    TrajectoryEvaluationRubric,
)
from src.eval.sanitizer import (
    sanitize_eval_input,
    wrap_xml_context,
)

__all__ = [
    "TrajectoryEvaluationRubric",
    "PointwiseEvaluationRubric",
    "sanitize_eval_input",
    "wrap_xml_context",
    "evaluate_agent_trajectory",
    "compute_token_efficiency_score",
    "calculate_token_cost",
    "isolate_fallback_benchmark_aggregates",
    "build_evaluation_dataframe",
    "run_vertex_eval_task",
]
