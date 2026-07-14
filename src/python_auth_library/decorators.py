from __future__ import annotations

import functools
from typing import Callable

from flask import abort, g, redirect, request, url_for


def login_required(view: Callable) -> Callable:
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if getattr(g, "user", None) is None:
            login_url = url_for("keycloak_auth.login", next=request.url)
            return redirect(login_url)
        return view(*args, **kwargs)

    return wrapper


def roles_required(*roles: str, require_all: bool = True) -> Callable:
    def decorator(view: Callable) -> Callable:
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            user = getattr(g, "user", None)
            if user is None:
                login_url = url_for("keycloak_auth.login", next=request.url)
                return redirect(login_url)

            ok = user.has_role(*roles) if require_all else user.has_any_role(*roles)
            if not ok:
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator
