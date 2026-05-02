from __future__ import annotations

from .services.token_service import decode_token


def get_current_user(authorization_header: str | None) -> str | None:
    """Authenticate a request using a very small bearer-token format."""
    if not authorization_header:
        return None
    if not authorization_header.startswith('Bearer '):
        return None
    token = authorization_header.replace('Bearer ', '', 1).strip()
    payload = decode_token(token)
    if not payload.get('valid'):
        return None
    return payload.get('user')
