from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .agent import RepoInvestigatorService
from .config import Settings, get_settings
from .schemas import AskRequest, AskResponse, HealthResponse, RepoInfo
from .tracing import configure_mlflow


@lru_cache(maxsize=1)
def get_service() -> RepoInvestigatorService:
    settings = get_settings()
    configure_mlflow(settings)
    return RepoInvestigatorService(settings)


app = FastAPI(title='repo-investigator', version='0.1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/', include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url='/docs', status_code=307)


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    service = get_service()
    repos = [RepoInfo(name=path.name, path=str(path)) for path in settings.list_known_repos()]
    return HealthResponse(
        status='ok',
        agent_mode=settings.agent_mode,
        effective_mode='dspy' if service.effective_mode == 'dspy' else 'heuristic',
        dspy_available=service.llm_status.dspy_available,
        mlflow_enabled=settings.enable_mlflow,
        backend_public_url=settings.backend_public_url,
        frontend_public_url=settings.frontend_public_url,
        default_repo=str(settings.resolve_user_path(settings.default_repo)),
        known_repos=repos,
        warnings=service.warnings,
    )


@app.get('/repos', response_model=list[RepoInfo])
def repos() -> list[RepoInfo]:
    settings = get_settings()
    return [RepoInfo(name=path.name, path=str(path)) for path in settings.list_known_repos()]


@app.post('/ask', response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    service = get_service()
    try:
        return service.ask(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get('/runs/{run_id}', response_model=AskResponse)
def get_run(run_id: str) -> AskResponse:
    response = get_service().store.load(run_id)
    if response is None:
        raise HTTPException(status_code=404, detail=f'Run not found: {run_id}')
    return response


@app.get('/recent')
def recent(limit: int = 20):
    return get_service().store.list_recent(limit=limit)
