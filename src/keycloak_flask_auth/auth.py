"""Core Keycloak/OIDC integration for Flask, built on Authlib."""

from __future__ import annotations

import os
from typing import Any

from authlib.integrations.flask_client import OAuth
from flask import Flask, g, session

from .routes import build_blueprint
from .user import User

# Session keys (kept private to avoid collisions with app data)
SESSION_USER_KEY = "_kfa_user"
SESSION_ID_TOKEN_KEY = "_kfa_id_token"


class KeycloakAuth:
    """Wires Keycloak OIDC login into a Flask app.

    All configuration is read from environment variables by default, so the
    integrating developer usually only needs::

        auth = KeycloakAuth(app)

    Required environment variables
    ------------------------------
    KEYCLOAK_SERVER_URL   e.g. https://auth.example.com
    KEYCLOAK_REALM        e.g. my-realm
    KEYCLOAK_CLIENT_ID    e.g. my-flask-app
    KEYCLOAK_CLIENT_SECRET the confidential client's secret

    Optional
    --------
    KEYCLOAK_SCOPES         default "openid email profile"
    KEYCLOAK_URL_PREFIX     default "/auth" (mounts /login, /callback, /logout)
    KEYCLOAK_POST_LOGIN     path to redirect to after login (default "/")
    KEYCLOAK_POST_LOGOUT    absolute URL Keycloak returns to after logout
    """

    def __init__(
        self,
        app: Flask | None = None,
        *,
        server_url: str | None = None,
        realm: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        scopes: str | None = None,
        url_prefix: str | None = None,
        post_login_redirect: str | None = None,
        post_logout_redirect: str | None = None,
    ):
        self._explicit = {
            "server_url": server_url,
            "realm": realm,
            "client_id": client_id,
            "client_secret": client_secret,
            "scopes": scopes,
            "url_prefix": url_prefix,
            "post_login_redirect": post_login_redirect,
            "post_logout_redirect": post_logout_redirect,
        }
        self.oauth: OAuth | None = None
        self.client = None  # Authlib remote app
        self.client_id: str | None = None
        self.server_metadata_url: str | None = None
        self.end_session_endpoint: str | None = None
        self.url_prefix: str = "/auth"
        self.post_login_redirect: str = "/"
        self.post_logout_redirect: str | None = None

        if app is not None:
            self.init_app(app)

    # -- Setup ------------------------------------------------------------------
    def init_app(self, app: Flask) -> None:
        cfg = self._resolve_config()

        realm_base = f"{cfg['server_url'].rstrip('/')}/realms/{cfg['realm']}"
        self.server_metadata_url = f"{realm_base}/.well-known/openid-configuration"
        self.client_id = cfg["client_id"]
        self.url_prefix = cfg["url_prefix"]
        self.post_login_redirect = cfg["post_login_redirect"]
        self.post_logout_redirect = cfg["post_logout_redirect"]

        oauth = OAuth(app)
        self.client = oauth.register(
            name="keycloak",
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            server_metadata_url=self.server_metadata_url,
            client_kwargs={"scope": cfg["scopes"]},
        )
        self.oauth = oauth

        # Make the current user available as ``g.user`` on every request.
        app.before_request(self._load_user)

        # Expose helpers to Jinja templates: current_user, is_authenticated.
        app.context_processor(self._template_context)

        # Register /login, /callback, /logout.
        app.register_blueprint(build_blueprint(self), url_prefix=self.url_prefix)

        # Keep a handle for extensions / debugging.
        app.extensions = getattr(app, "extensions", {})
        app.extensions["keycloak_flask_auth"] = self

    def _resolve_config(self) -> dict[str, Any]:
        def pick(key: str, env: str, default: Any = None, required: bool = False) -> Any:
            value = self._explicit.get(key)
            if value is None:
                value = os.environ.get(env, default)
            if required and not value:
                raise RuntimeError(
                    f"keycloak-flask-auth: missing required config '{key}'. "
                    f"Set the {env} environment variable or pass {key}=... to KeycloakAuth()."
                )
            return value

        return {
            "server_url": pick("server_url", "KEYCLOAK_SERVER_URL", required=True),
            "realm": pick("realm", "KEYCLOAK_REALM", required=True),
            "client_id": pick("client_id", "KEYCLOAK_CLIENT_ID", required=True),
            "client_secret": pick("client_secret", "KEYCLOAK_CLIENT_SECRET", required=True),
            "scopes": pick("scopes", "KEYCLOAK_SCOPES", "openid email profile"),
            "url_prefix": pick("url_prefix", "KEYCLOAK_URL_PREFIX", "/auth"),
            "post_login_redirect": pick("post_login_redirect", "KEYCLOAK_POST_LOGIN", "/"),
            "post_logout_redirect": pick("post_logout_redirect", "KEYCLOAK_POST_LOGOUT", None),
        }

    # -- Request lifecycle ------------------------------------------------------
    def _load_user(self) -> None:
        g.user = User.from_session(session.get(SESSION_USER_KEY), client_id=self.client_id)

    def _template_context(self) -> dict[str, Any]:
        user = getattr(g, "user", None)
        return {"current_user": user, "is_authenticated": user is not None}

    # -- Session helpers (used by routes) --------------------------------------
    def save_user(self, claims: dict[str, Any], id_token: str | None) -> User:
        user = User(claims, client_id=self.client_id)
        session[SESSION_USER_KEY] = user.to_session()
        if id_token:
            session[SESSION_ID_TOKEN_KEY] = id_token
        g.user = user
        return user

    def clear_session(self) -> str | None:
        id_token = session.pop(SESSION_ID_TOKEN_KEY, None)
        session.pop(SESSION_USER_KEY, None)
        g.user = None
        return id_token

    # -- Discovery helpers ------------------------------------------------------
    def load_server_metadata(self) -> dict[str, Any]:
        """Fetch (and cache on the Authlib client) the OIDC discovery document."""
        return self.client.load_server_metadata()

    @property
    def current_user(self) -> User | None:
        return getattr(g, "user", None)
