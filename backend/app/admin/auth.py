from fastapi import Request

SESSION_KEY = "admin_logged_in"


def is_admin(request: Request) -> bool:
    return bool(request.session.get(SESSION_KEY))
