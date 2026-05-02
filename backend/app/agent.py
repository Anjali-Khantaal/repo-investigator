from __future__ import annotations

import textwrap
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import Settings
from .dspy_programs import DSPyPrograms, build_programs
from .llm import LLMStatus, configure_dspy
from .repo_tools import EvidenceRecord, build_evidence, extract_question_keywords, search_repo, summarize_repo_tree
from .run_store import RunStore
from .schemas import AgentStep, AskRequest, AskResponse, Citation, EvidenceChunk
from .tracing import log_metric, set_tags, start_span


class RepoInvestigatorService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = RunStore(settings.runs_dir)
        self.warnings: list[str] = []
        self.llm_status: LLMStatus = configure_dspy(settings) if settings.agent_mode in {'auto', 'dspy'} else LLMStatus(False, False, 'DSPy disabled.')
        self.programs: DSPyPrograms | None = None
        self.effective_mode: str = 'heuristic'

        if settings.agent_mode == 'heuristic':
            self.effective_mode = 'heuristic'
        elif settings.agent_mode == 'dspy':
            if not self.llm_status.configured:
                raise RuntimeError(self.llm_status.message)
            self.programs = build_programs()
            self.effective_mode = 'dspy'
        else:
            if self.llm_status.configured:
                self.programs = build_programs()
                self.effective_mode = 'dspy'
            else:
                self.warnings.append(self.llm_status.message)
                self.effective_mode = 'heuristic'

    def _record_step(self, steps: list[AgentStep], stage: str, summary: str, **details) -> None:
        steps.append(AgentStep(stage=stage, summary=summary, details=details))

    def _keywords_from_planner(self, question: str, repo_map: str) -> tuple[list[str], str, str]:
        if not self.programs:
            keywords = extract_question_keywords(question)
            return keywords, '', 'heuristic keyword extraction'

        with start_span('planner', inputs={'question': question}) as span:
            plan = self.programs.planner(question=question, repo_map=repo_map)
            search_terms_raw = getattr(plan, 'search_terms', '') or ''
            file_hints = getattr(plan, 'file_hints', '') or ''
            rationale = getattr(plan, 'search_rationale', '') or ''
            keywords = []
            for item in str(search_terms_raw).replace('\n', ',').split(','):
                cleaned = item.strip().lower()
                if cleaned and cleaned not in keywords:
                    keywords.append(cleaned)
            if not keywords:
                keywords = extract_question_keywords(question)
            span.set_outputs({'search_terms': keywords, 'file_hints': file_hints})
            return keywords[:12], str(file_hints), str(rationale)

    def _format_evidence_text(self, evidence: list[EvidenceRecord]) -> str:
        blocks: list[str] = []
        for item in evidence:
            blocks.append(
                f"FILE: {item.file_path}\nSUMMARY: {item.summary}\nSNIPPET:\n{item.snippet}"
            )
        return '\n\n'.join(blocks)

    def _answer_with_dspy(self, question: str, evidence: list[EvidenceRecord]) -> tuple[str, list[str], str]:
        if not self.programs:
            raise RuntimeError('DSPy programs are unavailable.')
        evidence_text = self._format_evidence_text(evidence)
        with start_span('answerer', inputs={'question': question}) as span:
            answer_pred = self.programs.answerer(question=question, evidence=evidence_text)
            answer = str(getattr(answer_pred, 'answer', '')).strip()
            cited = str(getattr(answer_pred, 'cited_file_paths', '')).strip()
            confidence = str(getattr(answer_pred, 'confidence_summary', '')).strip()
            span.set_outputs({'cited_file_paths': cited, 'confidence_summary': confidence})

        with start_span('critic', inputs={'question': question, 'answer': answer}) as span:
            critique = self.programs.critic(question=question, answer=answer, evidence=evidence_text)
            grounded = str(getattr(critique, 'grounded', '')).strip().lower()
            revised = str(getattr(critique, 'revised_answer', '')).strip()
            if grounded and grounded not in {'yes', 'true', 'grounded'} and revised:
                answer = revised
            span.set_outputs({'grounded': grounded})

        cited_files: list[str] = []
        for item in cited.replace('\n', ',').split(','):
            cleaned = item.strip()
            if cleaned and cleaned not in cited_files:
                cited_files.append(cleaned)
        return answer or self._heuristic_answer(question, evidence), cited_files, confidence

    def _heuristic_answer(self, question: str, evidence: list[EvidenceRecord]) -> str:
        if not evidence:
            return (
                'I could not find relevant files for that question in the selected repository. '
                'Try using more specific keywords such as a function name, module name, or route.'
            )
        intro = (
            f'Based on the most relevant files I found for "{question}", the answer appears to center on '
            f'{", ".join(item.file_path for item in evidence[:3])}. '
        )
        details: list[str] = []
        for item in evidence[:3]:
            first_snippet_line = item.snippet.splitlines()[0] if item.snippet else ''
            details.append(f'- `{item.file_path}`: {item.summary}. First visible line: {first_snippet_line}')
        return intro + '\n' + '\n'.join(details)

    def _build_citations(self, evidence: list[EvidenceRecord], cited_files: list[str]) -> list[Citation]:
        citations: list[Citation] = []
        preferred = set(cited_files)
        for item in evidence:
            if preferred and item.file_path not in preferred:
                continue
            citations.append(Citation(file_path=item.file_path, reason=item.summary))
        if citations:
            return citations
        for item in evidence[:3]:
            citations.append(Citation(file_path=item.file_path, reason=item.summary))
        return citations

    def ask(self, request: AskRequest) -> AskResponse:
        started = time.perf_counter()
        steps: list[AgentStep] = []
        warnings = list(self.warnings)
        run_id = uuid.uuid4().hex
        repo_path = self.settings.resolve_repo_path(request.repo_path)
        set_tags({'repo_investigator_run_id': run_id, 'repo_path': str(repo_path), 'mode': self.effective_mode})

        with start_span('repo_investigator.ask', inputs={'question': request.question, 'repo_path': str(repo_path)}) as span:
            repo_map = summarize_repo_tree(repo_path, max_files=self.settings.max_files_in_map)
            self._record_step(steps, 'repo_map', 'Built repository map', total_lines=len(repo_map.splitlines()))

            keywords, file_hints, rationale = self._keywords_from_planner(request.question, repo_map)
            self._record_step(steps, 'planner', 'Planned repository search', keywords=keywords, file_hints=file_hints, rationale=rationale)

            hits = search_repo(
                repo_path=repo_path,
                search_terms=keywords,
                max_candidate_files=self.settings.max_candidate_files,
                max_matches_per_file=self.settings.max_matches_per_file,
            )
            self._record_step(
                steps,
                'search',
                'Ranked candidate files',
                candidates=[str(hit.path.relative_to(repo_path)) for hit in hits],
            )

            evidence_records = build_evidence(
                repo_path=repo_path,
                hits=hits,
                max_snippet_chars=self.settings.max_snippet_chars,
            )
            self._record_step(steps, 'evidence', 'Extracted evidence snippets', evidence_files=[item.file_path for item in evidence_records])

            if self.effective_mode == 'dspy' and self.programs is not None:
                try:
                    answer, cited_files, confidence = self._answer_with_dspy(request.question, evidence_records)
                    self._record_step(steps, 'answer', 'Generated DSPy answer', cited_files=cited_files, confidence=confidence)
                except Exception as exc:
                    warnings.append(f'DSPy answering failed, falling back to heuristic mode: {exc}')
                    answer = self._heuristic_answer(request.question, evidence_records)
                    cited_files = []
                    self._record_step(steps, 'answer', 'Fell back to heuristic answer', error=str(exc))
            else:
                answer = self._heuristic_answer(request.question, evidence_records)
                cited_files = []
                self._record_step(steps, 'answer', 'Generated heuristic answer')

            citations = self._build_citations(evidence_records, cited_files)
            evidence_models = [
                EvidenceChunk(
                    file_path=item.file_path,
                    summary=item.summary,
                    snippet=item.snippet,
                    score=item.score,
                    matched_terms=item.matched_terms,
                )
                for item in evidence_records
            ]

            latency_ms = int((time.perf_counter() - started) * 1000)
            response = AskResponse(
                run_id=run_id,
                timestamp_utc=datetime.now(timezone.utc),
                mode='dspy' if self.effective_mode == 'dspy' else 'heuristic',
                repo_path=str(repo_path),
                question=request.question,
                answer=answer,
                citations=citations,
                evidence=evidence_models,
                steps=steps if request.developer_mode else [],
                warnings=warnings,
                latency_ms=latency_ms,
            )
            self.store.save(response)
            span.set_outputs({'run_id': run_id, 'latency_ms': latency_ms, 'mode': response.mode})
            log_metric('latency_ms', float(latency_ms))
            log_metric('evidence_count', float(len(evidence_models)))
            return response
