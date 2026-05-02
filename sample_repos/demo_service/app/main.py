from __future__ import annotations

from fastapi import FastAPI

from .routes.users import router as users_router

app = FastAPI(title='demo_service')
app.include_router(users_router)


@app.get('/health')
def health() -> dict:
    return {"status": "ok"}
