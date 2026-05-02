from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

TEXT_EXTENSIONS = {
    '.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.env', '.sh',
    '.js', '.ts', '.tsx', '.jsx', '.css', '.html', '.sql', '.csv', '.rst'
}

STOPWORDS = {
    'the', 'a', 'an', 'to', 'for', 'and', 'or', 'of', 'in', 'on', 'is', 'are', 'be', 'with',
    'where', 'which', 'what', 'how', 'why', 'does', 'do', 'did', 'this', 'that', 'these',
    'those', 'add', 'change', 'changes', 'flow', 'trace', 'summarize', 'summary', 'likely',
    'would', 'need', 'repo', 'repository', 'file', 'files', 'code', 'module', 'function',
    'class', 'service', 'user', 'handled', 'handling'
}

SYNONYM_MAP = {
    'authentication': ['auth', 'token', 'bearer'],
    'authenticate': ['auth', 'token', 'bearer'],
    'authorization': ['auth', 'token', 'bearer'],
    'login': ['auth', 'token', 'bearer'],
    'users': ['user'],
    'routes': ['route'],
    'routing': ['route'],
}

MAX_FILE_BYTES = 500_000


@dataclass(slots=True)
class SearchHit:
    path: Path
    score: float
    matched_terms: list[str] = field(default_factory=list)
    matching_lines: list[int] = field(default_factory=list)
    reason: str = ''


@dataclass(slots=True)
class EvidenceRecord:
    file_path: str
    summary: str
    snippet: str
    score: float
    matched_terms: list[str]


def list_repo_files(repo_path: Path, max_files: int = 200, include_hidden: bool = False) -> list[Path]:
    files: list[Path] = []
    for path in sorted(repo_path.rglob('*')):
        if len(files) >= max_files:
            break
        if path.is_dir():
            continue
        relative_parts = path.relative_to(repo_path).parts
        if not include_hidden and any(part.startswith('.') for part in relative_parts):
            continue
        if '__pycache__' in relative_parts or path.suffix == '.pyc':
            continue
        files.append(path)
    return files


def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    try:
        with path.open('rb') as handle:
            sample = handle.read(512)
        return b'\x00' not in sample
    except OSError:
        return False


def summarize_repo_tree(repo_path: Path, max_files: int = 200) -> str:
    lines = [f'Repository root: {repo_path}']
    for path in list_repo_files(repo_path, max_files=max_files):
        rel = path.relative_to(repo_path)
        lines.append(f'- {rel}')
    if len(lines) == 1:
        lines.append('- <empty repository>')
    return '\n'.join(lines)


def extract_question_keywords(question: str) -> list[str]:
    lowered = question.lower()
    tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_\-/.:]*', lowered)
    keywords: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        cleaned = token.strip('._:-/')
        if not cleaned or cleaned in STOPWORDS:
            continue
        if len(cleaned) <= 2 and cleaned not in {'db', 'ui', 'ux', 'id'}:
            continue
        if cleaned not in seen:
            seen.add(cleaned)
            keywords.append(cleaned)
    return keywords[:12]


def expand_search_terms(search_terms: Iterable[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for raw_term in search_terms:
        term = raw_term.strip().lower()
        if not term:
            continue
        candidates = [term]
        if term in SYNONYM_MAP:
            candidates.extend(SYNONYM_MAP[term])
        if term.endswith('s') and len(term) > 3:
            candidates.append(term[:-1])
        if '_' in term:
            candidates.extend(part for part in term.split('_') if part)
        if '-' in term:
            candidates.extend(part for part in term.split('-') if part)
        for candidate in candidates:
            cleaned = candidate.strip().lower()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                expanded.append(cleaned)
    return expanded


def _read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='ignore')


def python_ast_overview(path: Path) -> str:
    if path.suffix.lower() != '.py':
        return 'Non-Python file.'
    try:
        tree = ast.parse(_read_text(path))
    except Exception:
        return 'Python AST could not be parsed.'

    functions: list[str] = []
    classes: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.AsyncFunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

    parts: list[str] = []
    if classes:
        parts.append(f"Classes: {', '.join(sorted(set(classes))[:8])}")
    if functions:
        parts.append(f"Functions: {', '.join(sorted(set(functions))[:12])}")
    return ' | '.join(parts) if parts else 'No top-level classes or functions detected.'


def read_file_snippet(path: Path, line_no: int | None = None, context: int = 5, max_chars: int = 1500) -> str:
    try:
        text = _read_text(path)
    except OSError:
        return '<unable to read file>'

    lines = text.splitlines()
    if not lines:
        return '<empty file>'

    if line_no is None:
        snippet_lines = lines[: min(len(lines), 30)]
        snippet = '\n'.join(f'{idx + 1:04d}: {line}' for idx, line in enumerate(snippet_lines))
        return snippet[:max_chars]

    start = max(0, line_no - context - 1)
    end = min(len(lines), line_no + context)
    snippet_lines = [f'{idx + 1:04d}: {lines[idx]}' for idx in range(start, end)]
    return '\n'.join(snippet_lines)[:max_chars]


def _matching_line_numbers(text: str, term: str, max_matches: int) -> list[int]:
    matches: list[int] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if term in line.lower():
            matches.append(index)
            if len(matches) >= max_matches:
                break
    return matches


def search_repo(
    repo_path: Path,
    search_terms: Iterable[str],
    max_candidate_files: int = 8,
    max_matches_per_file: int = 5,
) -> list[SearchHit]:
    terms = expand_search_terms([term.lower().strip() for term in search_terms if term and term.strip()])
    if not terms:
        return []

    hits: list[SearchHit] = []
    for path in repo_path.rglob('*'):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(repo_path).parts
        if '__pycache__' in relative_parts or path.suffix == '.pyc':
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue

        rel = str(path.relative_to(repo_path)).lower()
        score = 0.0
        matched_terms: list[str] = []
        matching_lines: list[int] = []

        for term in terms:
            if term in rel:
                score += 5.0
                if term not in matched_terms:
                    matched_terms.append(term)

        if is_text_file(path):
            try:
                text = _read_text(path).lower()
            except OSError:
                text = ''
            for term in terms:
                if term in text:
                    score += 2.0
                    if term not in matched_terms:
                        matched_terms.append(term)
                    for line_no in _matching_line_numbers(text, term, max_matches=max_matches_per_file):
                        if line_no not in matching_lines:
                            matching_lines.append(line_no)

        if score > 0:
            reason = 'filename match' if any(term in rel for term in terms) else 'content match'
            hits.append(SearchHit(path=path, score=score, matched_terms=matched_terms, matching_lines=matching_lines[:max_matches_per_file], reason=reason))

    hits.sort(key=lambda item: (-item.score, str(item.path)))
    return hits[:max_candidate_files]


def build_evidence(
    repo_path: Path,
    hits: list[SearchHit],
    max_snippet_chars: int = 1500,
) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for hit in hits:
        rel_path = str(hit.path.relative_to(repo_path))
        line_no = hit.matching_lines[0] if hit.matching_lines else None
        snippet = read_file_snippet(hit.path, line_no=line_no, max_chars=max_snippet_chars)
        ast_summary = python_ast_overview(hit.path)
        summary = f'{hit.reason}; matched terms: {", ".join(hit.matched_terms) or "n/a"}; {ast_summary}'
        records.append(EvidenceRecord(
            file_path=rel_path,
            summary=summary,
            snippet=snippet,
            score=hit.score,
            matched_terms=hit.matched_terms,
        ))
    return records
