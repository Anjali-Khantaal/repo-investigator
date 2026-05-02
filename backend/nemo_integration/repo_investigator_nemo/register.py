from __future__ import annotations

from pydantic import Field

try:
    from nat.builder.builder import Builder
    from nat.cli.register_workflow import register_function
    from nat.data_models.function import FunctionBaseConfig
except Exception as exc:  # pragma: no cover - only exercised in NeMo environments
    raise RuntimeError(
        'This plugin requires NVIDIA NeMo Agent Toolkit (nvidia-nat).'
    ) from exc


class RepoInvestigatorFunctionConfig(FunctionBaseConfig, name='repo_investigator'):
    backend_url: str = Field(default='http://localhost:8001', description='repo-investigator backend URL')
    repo_path: str = Field(default='sample_repos/demo_service', description='Default repository path passed to the backend')
    developer_mode: bool = Field(default=True, description='Whether to request developer diagnostics from the backend')
    timeout_seconds: int = Field(default=120, description='Request timeout in seconds')


@register_function(config_type=RepoInvestigatorFunctionConfig)
async def repo_investigator_function(config: RepoInvestigatorFunctionConfig, builder: Builder):
    import httpx

    async def _repo_investigator(question: str) -> str:
        """Answer a repository question by delegating to the repo-investigator backend."""
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                f'{config.backend_url.rstrip("/")}/ask',
                json={
                    'question': question,
                    'repo_path': config.repo_path,
                    'developer_mode': config.developer_mode,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload['answer']

    yield _repo_investigator
