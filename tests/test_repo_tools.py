from __future__ import annotations

import unittest
from pathlib import Path

from backend.app.repo_tools import build_evidence, extract_question_keywords, search_repo, summarize_repo_tree


class RepoToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_path = Path('sample_repos/demo_service').resolve()

    def test_extract_question_keywords(self) -> None:
        keywords = extract_question_keywords('Where is authentication handled in the user routes?')
        self.assertIn('authentication', keywords)
        self.assertIn('routes', keywords)

    def test_summarize_repo_tree(self) -> None:
        tree = summarize_repo_tree(self.repo_path)
        self.assertIn('app/auth.py', tree)
        self.assertIn('app/main.py', tree)

    def test_search_repo_finds_auth(self) -> None:
        hits = search_repo(self.repo_path, ['authentication', 'token'])
        hit_paths = [str(hit.path.relative_to(self.repo_path)) for hit in hits]
        self.assertTrue(any(path.endswith('app/auth.py') for path in hit_paths))

    def test_build_evidence(self) -> None:
        hits = search_repo(self.repo_path, ['authentication'])
        evidence = build_evidence(self.repo_path, hits)
        self.assertGreater(len(evidence), 0)
        self.assertIn('app/auth.py', [item.file_path for item in evidence])


if __name__ == '__main__':
    unittest.main()
