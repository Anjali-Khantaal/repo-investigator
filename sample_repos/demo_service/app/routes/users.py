from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from ..auth import get_current_user
from ..db import list_users

router = APIRouter(prefix='/users', tags=['users'])


@router.get('')
def get_users(authorization: str | None = Header(default=None)):
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail='Unauthorized')
    return {"requested_by": user, "users": list_users()}
