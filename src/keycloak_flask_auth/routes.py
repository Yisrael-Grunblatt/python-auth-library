"""Auth blueprint: /login, /callback, /logout.

These are registered automatically by :class:`KeycloakAuth` under the configured
``url_prefix`` (default ``/auth``).
"""

from __future__ import annotations

from urllib.parse import urlencode

from flask import Blueprint, redirect, request, session, url_for

SESSION_NEXT_KEY = "_kfa_next"


def build_blueprint(auth) -> Blueprint:
    bp = Blueprint("keycloak_auth", __name__)

    @bp.route("/login")
    def login():
        # Remember where to send the user back to after a successful login.
        next_url = request.args.get("next") or auth.post_login_redirect
        session[SESSION_NEXT_KEY] = next_url

        redirect_uri = url_for("keycloak_auth.callback", _external=True)
        return auth.client.authorize_redirect(redirect_uri)

    @bp.route("/callback")
    def callback():
        # Exchange the authorization code for tokens (back-channel, signature
        # verified against Keycloak's JWKS by Authlib).
        token = auth.client.authorize_access_token()
        claims = token.get("userinfo")
        if claims is None:
            # Fallback if the provider didn't return parsed id_token claims.
            claims = auth.client.userinfo(token=token)

        auth.save_user(dict(claims), token.get("id_token"))

        next_url = session.pop(SESSION_NEXT_KEY, None) or auth.post_login_redirect
        return redirect(next_url)

    @bp.route("/logout")
    def logout():
        # Clear the local session, then redirect to Keycloak's end-session
        # endpoint so single sign-out works across all apps in the realm.
        id_token = auth.clear_session()

        try:
            metadata = auth.load_server_metadata()
            end_session = metadata.get("end_session_endpoint")
        except Exception:  # pragma: no cover - network hiccup shouldn't block logout
            end_session = None

        post_logout = auth.post_logout_redirect or url_for(
            "keycloak_auth.login", _external=True
        )

        if not end_session:
            return redirect(post_logout)

        params = {"post_logout_redirect_uri": post_logout, "client_id": auth.client_id}
        if id_token:
            params["id_token_hint"] = id_token
        return redirect(f"{end_session}?{urlencode(params)}")

    return bp
