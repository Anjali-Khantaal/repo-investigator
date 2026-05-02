from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from .config import Settings


@dataclass
class DummySpan:
    name: str

    def set_inputs(self, _: dict[str, Any]) -> None:
        return None

    def set_outputs(self, _: dict[str, Any]) -> None:
        return None

    def set_attributes(self, _: dict[str, Any]) -> None:
        return None


def safe_import_mlflow():
    try:
        import mlflow  # type: ignore
        return mlflow
    except Exception:
        return None


def configure_mlflow(settings: Settings) -> bool:
    if not settings.enable_mlflow:
        return False
    mlflow = safe_import_mlflow()
    if mlflow is None:
        return False
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment)
        try:
            mlflow.dspy.autolog()
        except Exception:
            pass
        return True
    except Exception:
        return False


@contextmanager
def start_span(name: str, inputs: dict[str, Any] | None = None) -> Iterator[DummySpan | Any]:
    mlflow = safe_import_mlflow()
    if mlflow is None:
        span = DummySpan(name=name)
        if inputs:
            span.set_inputs(inputs)
        yield span
        return

    try:
        with mlflow.start_span(name) as span:
            if inputs:
                span.set_inputs(inputs)
            yield span
    except Exception:
        span = DummySpan(name=name)
        if inputs:
            span.set_inputs(inputs)
        yield span


def log_metric(key: str, value: float) -> None:
    mlflow = safe_import_mlflow()
    if mlflow is None:
        return
    try:
        mlflow.log_metric(key, value)
    except Exception:
        return None


def set_tags(tags: dict[str, Any]) -> None:
    mlflow = safe_import_mlflow()
    if mlflow is None:
        return
    try:
        for key, value in tags.items():
            mlflow.set_tag(key, value)
    except Exception:
        return None
