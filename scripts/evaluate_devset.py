from __future__ import annotations

import json
from pathlib import Path

from backend.app.agent import RepoInvestigatorService
from backend.app.config import get_settings
from backend.app.schemas import AskRequest


def main() -> None:
    settings = get_settings()
    service = RepoInvestigatorService(settings)
    dataset_path = Path('eval/devset.jsonl')
    rows = [json.loads(line) for line in dataset_path.read_text(encoding='utf-8').splitlines() if line.strip()]

    total = len(rows)
    file_hit_count = 0
    nonempty_answer_count = 0

    for row in rows:
        response = service.ask(AskRequest(question=row['question'], repo_path=row['repo_path'], developer_mode=False))
        cited_files = {item.file_path for item in response.citations}
        expected_files = set(row.get('expected_files', []))
        if cited_files.intersection(expected_files):
            file_hit_count += 1
        if response.answer.strip():
            nonempty_answer_count += 1

    print('Evaluation summary')
    print('------------------')
    print(f'Total examples: {total}')
    print(f'File-hit accuracy: {file_hit_count}/{total} = {file_hit_count / max(total, 1):.2%}')
    print(f'Non-empty answers: {nonempty_answer_count}/{total} = {nonempty_answer_count / max(total, 1):.2%}')


if __name__ == '__main__':
    main()
