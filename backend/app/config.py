from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / 'data' / 'runs'


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


@dataclass(slots=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    runs_dir: Path = RUNS_DIR
    backend_host: str = field(default_factory=lambda: os.getenv('BACKEND_HOST', '0.0.0.0'))
    backend_port: int = field(default_factory=lambda: _as_int(os.getenv('BACKEND_PORT'), 8001))
    backend_public_url: str = field(default_factory=lambda: os.getenv('BACKEND_PUBLIC_URL', 'http://localhost:8001'))
    frontend_public_url: str = field(default_factory=lambda: os.getenv('FRONTEND_PUBLIC_URL', 'http://localhost:8501'))

    default_repo: str = field(default_factory=lambda: os.getenv('DEFAULT_REPO', 'sample_repos/demo_service'))
    allow_any_repo: bool = field(default_factory=lambda: _as_bool(os.getenv('ALLOW_ANY_REPO'), True))
    allowed_repo_roots_raw: list[str] = field(default_factory=lambda: _split_csv(os.getenv('ALLOWED_REPO_ROOTS')))

    max_files_in_map: int = field(default_factory=lambda: _as_int(os.getenv('MAX_FILES_IN_MAP'), 200))
    max_candidate_files: int = field(default_factory=lambda: _as_int(os.getenv('MAX_CANDIDATE_FILES'), 8))
    max_matches_per_file: int = field(default_factory=lambda: _as_int(os.getenv('MAX_MATCHES_PER_FILE'), 5))
    max_snippet_chars: int = field(default_factory=lambda: _as_int(os.getenv('MAX_SNIPPET_CHARS'), 1500))

    agent_mode: str = field(default_factory=lambda: os.getenv('AGENT_MODE', 'auto').strip().lower())
    llm_provider: str = field(default_factory=lambda: os.getenv('LLM_PROVIDER', 'ollama_chat').strip().lower())
    llm_model: str = field(default_factory=lambda: os.getenv('LLM_MODEL', 'llama3.2:3b'))
    llm_api_base: str = field(default_factory=lambda: os.getenv('LLM_API_BASE', 'http://localhost:11434'))
    llm_api_key: str = field(default_factory=lambda: os.getenv('LLM_API_KEY', ''))
    llm_temperature: float = field(default_factory=lambda: _as_float(os.getenv('LLM_TEMPERATURE'), 0.0))

    enable_mlflow: bool = field(default_factory=lambda: _as_bool(os.getenv('ENABLE_MLFLOW'), True))
    mlflow_tracking_uri: str = field(default_factory=lambda: os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000'))
    mlflow_experiment: str = field(default_factory=lambda: os.getenv('MLFLOW_EXPERIMENT', 'repo-investigator'))

    nemo_backend_url: str = field(default_factory=lambda: os.getenv('NEMO_BACKEND_URL', 'http://localhost:8001'))
    nemo_default_repo: str = field(default_factory=lambda: os.getenv('NEMO_DEFAULT_REPO', 'sample_repos/demo_service'))
    nemo_llm_base_url: str = field(default_factory=lambda: os.getenv('NEMO_LLM_BASE_URL', 'http://localhost:11434/v1'))
    nemo_llm_model: str = field(default_factory=lambda: os.getenv('NEMO_LLM_MODEL', 'llama3.2:3b'))

    def __post_init__(self) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def allowed_repo_roots(self) -> list[Path]:
        roots = [self.project_root]
        for raw in self.allowed_repo_roots_raw:
            roots.append(self.resolve_user_path(raw))
        deduped: list[Path] = []
        seen: set[Path] = set()
        for root in roots:
            if root not in seen:
                seen.add(root)
                deduped.append(root)
        return deduped

    def resolve_user_path(self, raw_path: str | Path) -> Path:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    def resolve_repo_path(self, requested: str | None) -> Path:
        raw = requested or self.default_repo
        resolved = self.resolve_user_path(raw)
        if not resolved.exists():
            raise FileNotFoundError(f'Repository path does not exist: {resolved}')
        if not resolved.is_dir():
            raise NotADirectoryError(f'Repository path is not a directory: {resolved}')
        if self.allow_any_repo:
            return resolved
        for root in self.allowed_repo_roots:
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue
        roots = ', '.join(str(item) for item in self.allowed_repo_roots)
        raise PermissionError(f'Repository path {resolved} is outside allowed roots: {roots}')

    def list_known_repos(self) -> list[Path]:
        candidates: list[Path] = []
        sample_root = self.project_root / 'sample_repos'
        if sample_root.exists():
            for path in sorted(sample_root.iterdir()):
                if path.is_dir():
                    candidates.append(path)
        default_path = self.resolve_user_path(self.default_repo)
        if default_path.exists() and default_path.is_dir() and default_path not in candidates:
            candidates.append(default_path)
        return candidates


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
