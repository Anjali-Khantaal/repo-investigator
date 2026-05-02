FAKE_USERS = [
    {"id": 1, "name": "Anita", "role": "admin"},
    {"id": 2, "name": "Rohan", "role": "analyst"},
]


def list_users() -> list[dict]:
    return FAKE_USERS
