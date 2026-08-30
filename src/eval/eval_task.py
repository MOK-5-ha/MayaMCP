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

"""Vertex AI Gen AI Evaluation Service (vertexai.preview.evaluation.EvalTask) integration."""

import logging
import os
from typing import Any

import pandas as pd

from src.app_utils.telemetry import get_tracer, record_genai_attributes
from src.eval.sanitizer import sanitize_eval_input

logger = logging.getLogger(__name__)


def build_evaluation_dataframe(
    dataset_items: list[dict[str, Any]],
    model_outputs: list[dict[str, Any]],
) -> pd.DataFrame:
    """Build a pandas DataFrame conforming to Vertex AI EvalTask requirements.

    Args:
        dataset_items: List of benchmark items (turns, expected_logic, reference_trajectory).
        model_outputs: List of model outputs (responses, predicted_trajectory, visemes, final_order).

    Returns:
        pd.DataFrame formatted for EvalTask.
    """
    rows = []
    for item, output in zip(dataset_items, model_outputs, strict=False):
        prompt_text = "\n".join(item["turns"]) if isinstance(item.get("turns"), list) else str(item.get("turns", ""))
        response_text = "\n".join(output.get("responses", [])) if isinstance(output.get("responses"), list) else str(output.get("responses", ""))
        ref_text = str(item.get("expected_logic", item.get("reference", "")))

        rows.append({
            "prompt": sanitize_eval_input(prompt_text),
            "response": sanitize_eval_input(response_text),
            "reference": sanitize_eval_input(ref_text),
            "predicted_trajectory": output.get("predicted_trajectory", []),
            "reference_trajectory": item.get("reference_trajectory", []),
        })

    return pd.DataFrame(rows)


def run_vertex_eval_task(
    dataset_items: list[dict[str, Any]],
    model_outputs: list[dict[str, Any]],
    gcp_project: str | None = None,
    gcp_location: str | None = None,
) -> Any:
    """Execute evaluation using vertexai.preview.evaluation.EvalTask with OpenTelemetry telemetry.

    Instruments the evaluation run with OpenTelemetry spans. If Vertex AI EvalTask execution fails
    (e.g. ADC credentials absent or offline test run), catches the exception, logs to telemetry,
    and emits a dedicated 'vertex_eval.local_fallback' span.

    Args:
        dataset_items: Test cases with turns, expected_logic, reference_trajectory.
        model_outputs: Model outputs with responses, predicted_trajectory.
        gcp_project: GCP Project ID.
        gcp_location: GCP Location.

    Returns:
        EvalResult object from EvalTask, or None if executed under local fallback.
    """
    project = gcp_project or os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "dummy-gcp-project"
    location = gcp_location or os.getenv("GCP_LOCATION", "global")
    vertex_loc = "us-central1" if location == "global" else location

    eval_df = build_evaluation_dataframe(dataset_items, model_outputs)

    tracer = get_tracer("mayamcp.eval")

    with tracer.start_as_current_span("vertexai.evaluation_task") as eval_span:
        record_genai_attributes(
            eval_span,
            system="vertex_ai",
            model=os.getenv("GEMINI_MODEL_VERSION", "gemini-3.1-flash-lite"),
        )
        eval_span.set_attribute("gen_ai.evaluation.item_count", len(dataset_items))

        try:
            import vertexai
            from vertexai.preview.evaluation import (
                EvalTask,
                PointwiseMetric,
                PointwiseMetricPromptTemplate,
            )

            vertexai.init(project=project, location=vertex_loc)

            # 1. Pointwise Faithfulness Metric with static rubric prefix
            faithfulness_template = PointwiseMetricPromptTemplate(
                criteria={
                    "faithfulness": (
                        "Evaluate whether Maya's responses strictly satisfy the required bartender persona, "
                        "recipe facts, bar knowledge, and expected order logic."
                    )
                },
                rating_rubric={
                    "5": "Completely compliant. Perfectly meets bartender persona, recipe facts, and order logic.",
                    "3": "Partially compliant. Minor deviations but conversational flow and recipes intact.",
                    "1": "Non-compliant. Severe hallucination, roleplay hijack, or calculation error.",
                },
                input_variables=["prompt", "response", "reference"],
            )
            faithfulness_metric = PointwiseMetric(
                metric="bartender_faithfulness",
                metric_prompt_template=faithfulness_template,
                system_instruction="You are an expert impartial evaluation judge.",
            )

            # 2. Pointwise Response Quality Metric
            quality_template = PointwiseMetricPromptTemplate(
                criteria={
                    "response_quality": (
                        "Evaluate the conversational quality, helpfulness, empathy, and tone of Maya's responses."
                    )
                },
                rating_rubric={
                    "5": "High quality. Natural, empathetic bartending tone, engaging, concise, and clear.",
                    "3": "Acceptable quality. Somewhat brief, but meets the conversational need.",
                    "1": "Poor quality. Broken output, repetitive phrases, or incoherent replies.",
                },
                input_variables=["prompt", "response", "reference"],
            )
            quality_metric = PointwiseMetric(
                metric="bartender_response_quality",
                metric_prompt_template=quality_template,
                system_instruction="You are an expert evaluation judge assessing conversational quality.",
            )

            eval_task = EvalTask(
                dataset=eval_df,
                metrics=[
                    faithfulness_metric,
                    quality_metric,
                    "trajectory_exact_match",
                    "trajectory_precision",
                    "trajectory_recall",
                    "trajectory_single_tool_use",
                    "rouge_l_sum",
                ],
            )

            logger.info("Running Vertex AI EvalTask...")
            eval_result = eval_task.evaluate()

            eval_span.set_attribute("gen_ai.evaluation.status", "success")
            return eval_result

        except Exception as exc:
            logger.warning(
                f"Vertex AI EvalTask managed service not reachable in current environment: {exc}. "
                "Emitting vertex_eval.local_fallback span."
            )
            if hasattr(eval_span, "record_exception"):
                eval_span.record_exception(exc)
            eval_span.set_attribute("gen_ai.evaluation.status", "failed_fallback_dispatched")

            # Dedicated fallback span for local rule evaluation
            with tracer.start_as_current_span("vertex_eval.local_fallback") as fallback_span:
                record_genai_attributes(fallback_span, system="local_rules")
                fallback_span.set_attribute("eval.fallback_reason", str(exc))
                fallback_span.set_attribute("eval.fallback_executed", True)

            return None
