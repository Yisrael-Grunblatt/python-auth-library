"""Route protection decorators."""

from __future__ import annotations

import functools
from typing import Callable

from flask import abort, g, redirect, request, url_for


def login_required(view: Callable) -> Callable:
    """Require an authenticated user.

    Unauthenticated requests are redirected to the Keycloak login flow and, on
    success, returned to the originally requested URL.

        @app.route("/dashboard")
        @login_required
        def dashboard():
            return render_template("dashboard.html", user=g.user)
    """

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if getattr(g, "user", None) is None:
            login_url = url_for("keycloak_auth.login", next=request.url)
            return redirect(login_url)
        return view(*args, **kwargs)

    return wrapper


def roles_required(*roles: str, require_all: bool = True) -> Callable:
    """Require the authenticated user to have the given Keycloak role(s).

    By default the user must have *all* listed roles. Pass ``require_all=False``
    to allow access when the user has *any* of them. Missing authentication
    triggers a login redirect; insufficient roles returns HTTP 403.

        @app.route("/admin")
        @roles_required("admin")
        def admin():
            ...

        @app.route("/reports")
        @roles_required("analyst", "manager", require_all=False)
        def reports():
            ...
    """

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
