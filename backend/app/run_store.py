from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import AskResponse


class RunStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run_path(self, run_id: str) -> Path:
        return self.base_dir / f'{run_id}.json'

    def save(self, response: AskResponse) -> None:
        path = self._run_path(response.run_id)
        path.write_text(response.model_dump_json(indent=2), encoding='utf-8')

    def load(self, run_id: str) -> AskResponse | None:
        path = self._run_path(run_id)
        if not path.exists():
            return None
        return AskResponse.model_validate_json(path.read_text(encoding='utf-8'))

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.base_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                payload = json.loads(path.read_text(encoding='utf-8'))
                items.append({
                    'run_id': payload['run_id'],
                    'question': payload['question'],
                    'repo_path': payload['repo_path'],
                    'mode': payload['mode'],
                    'timestamp_utc': payload['timestamp_utc'],
                })
            except Exception:
                continue
        return items
