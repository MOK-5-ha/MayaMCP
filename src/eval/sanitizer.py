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

"""Prompt defense and zero-trust input sanitization for LLM evaluators and judges."""

import re
from typing import Any

# Special LLM instruction control tokens to strip
_SPECIAL_TOKENS_PATTERN = re.compile(
    r"(\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>|<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|user\|>|<\|assistant\|>)",
    re.IGNORECASE,
)

# Instruction override attempt patterns
_INSTRUCTION_OVERRIDE_PATTERN = re.compile(
    r"\b(ignore|disregard|forget|bypass|override|drop|abandon|cancel|reset)\b.{0,60}\b(instructions?|prompts?|rules?|directives?|system)\b",
    re.IGNORECASE,
)

# Directives attempting to force or manipulate judge scores
_SCORING_DIRECTIVE_PATTERN = re.compile(
    r"\b(assign|give|set|rate|award|provide|score|force|yield|return|change|make|update|alter|adjust|modify|declare)\b.{0,40}\b(maximum|highest|perfect|top|best|worst|minimum|\b5\b|\b1\b|\b0\b|\b100\b|full\s+marks?|five\s+stars?)\b",
    re.IGNORECASE,
)


def sanitize_eval_input(text: Any) -> str:
    """Pre-sanitize untrusted evaluation inputs to neutralize prompt injection and scoring manipulation.

    Neutralizes:
    - Special LLM instruction tokens ([INST], <<SYS>>, <|im_start|>, etc.)
    - Instruction override attempts (ignore previous instructions, etc.)
    - Score manipulation directives (assign 5, give maximum score, etc.)
    - Potentially harmful raw XML/HTML delimiters

    Args:
        text: Untrusted text or object to sanitize.

    Returns:
        Sanitized text safe to embed inside evaluator XML context blocks.
    """
    if text is None:
        return ""

    raw_str = str(text)

    # 1. Strip special LLM instruction tokens
    sanitized = _SPECIAL_TOKENS_PATTERN.sub("[SANITIZED_TOKEN]", raw_str)

    # 2. Defuse instruction override attempts
    sanitized = _INSTRUCTION_OVERRIDE_PATTERN.sub("[SANITIZED_OVERRIDE_ATTEMPT]", sanitized)

    # 3. Defuse scoring manipulation directives
    sanitized = _SCORING_DIRECTIVE_PATTERN.sub("[SANITIZED_SCORING_DIRECTIVE]", sanitized)

    # 4. Escape angle brackets to prevent closing XML context boundaries prematurely
    # We preserve readability while escaping raw tags in untrusted data
    sanitized = sanitized.replace("<", "&lt;").replace(">", "&gt;")

    return sanitized.strip()


def wrap_xml_context(tag_name: str, content: Any) -> str:
    """Wrap content in dedicated XML boundaries with explicit zero-trust labeling.

    Args:
        tag_name: The XML tag name (e.g. 'user_turns', 'maya_responses', 'expected_criteria').
        content: The content string or structure to embed.

    Returns:
        XML-formatted context block.
    """
    clean_tag = re.sub(r"[^a-zA-Z0-9_-]", "", tag_name)
    sanitized_body = sanitize_eval_input(content)
    return f"<{clean_tag}>\n{sanitized_body}\n</{clean_tag}>"
