from __future__ import annotations

import os
import unittest
from pathlib import Path

from backend.app.agent import RepoInvestigatorService
from backend.app.config import Settings
from backend.app.schemas import AskRequest


class HeuristicAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ['AGENT_MODE'] = 'heuristic'
        os.environ['ENABLE_MLFLOW'] = 'false'
        os.environ['DEFAULT_REPO'] = 'sample_repos/demo_service'
        self.settings = Settings()
        self.service = RepoInvestigatorService(self.settings)

    def test_auth_question_returns_auth_file(self) -> None:
        response = self.service.ask(AskRequest(
            question='Where is authentication handled?',
            repo_path='sample_repos/demo_service',
            developer_mode=True,
        ))
        cited = {item.file_path for item in response.citations}
        self.assertIn('app/auth.py', cited)
        self.assertIn(response.mode, {'heuristic', 'dspy'})
        self.assertGreaterEqual(response.latency_ms, 0)


if __name__ == '__main__':
    unittest.main()
