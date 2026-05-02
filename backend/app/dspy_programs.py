from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .llm import safe_import_dspy


@dataclass(slots=True)
class DSPyPrograms:
    planner: Any
    answerer: Any
    critic: Any


def build_programs() -> DSPyPrograms:
    dspy = safe_import_dspy()
    if dspy is None:
        raise RuntimeError('DSPy is not installed.')

    planner = dspy.ChainOfThought(
        'question, repo_map -> search_terms, file_hints, search_rationale'
    )
    answerer = dspy.ChainOfThought(
        'question, evidence -> answer, cited_file_paths, confidence_summary'
    )
    critic = dspy.ChainOfThought(
        'question, answer, evidence -> grounded, issues, revised_answer'
    )
    return DSPyPrograms(planner=planner, answerer=answerer, critic=critic)
