from __future__ import annotations


def decode_token(token: str) -> dict:
    """Very fake token decoder for the demo service."""
    parts = token.split(':')
    if len(parts) != 2:
        return {"valid": False, "user": None}
    _, username = parts
    return {"valid": True, "user": username}
