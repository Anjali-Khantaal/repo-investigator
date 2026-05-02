from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description='Question about the repository')
    repo_path: str | None = Field(default=None, description='Local repository path')
    developer_mode: bool = Field(default=True, description='Whether to return step-by-step developer diagnostics')


class Citation(BaseModel):
    file_path: str
    reason: str


class EvidenceChunk(BaseModel):
    file_path: str
    summary: str
    snippet: str
    score: float
    matched_terms: list[str] = Field(default_factory=list)


class AgentStep(BaseModel):
    stage: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class AskResponse(BaseModel):
    run_id: str
    timestamp_utc: datetime
    mode: Literal['dspy', 'heuristic']
    repo_path: str
    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    evidence: list[EvidenceChunk] = Field(default_factory=list)
    steps: list[AgentStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    latency_ms: int = 0


class RepoInfo(BaseModel):
    name: str
    path: str


class HealthResponse(BaseModel):
    status: Literal['ok']
    agent_mode: str
    effective_mode: Literal['dspy', 'heuristic']
    dspy_available: bool
    mlflow_enabled: bool
    backend_public_url: str
    frontend_public_url: str
    default_repo: str
    known_repos: list[RepoInfo]
    warnings: list[str] = Field(default_factory=list)
