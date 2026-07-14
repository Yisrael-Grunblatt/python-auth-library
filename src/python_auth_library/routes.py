from __future__ import annotations

import base64
import binascii
import json
from typing import Any
from urllib.parse import urlencode

from flask import Blueprint, redirect, request, session, url_for

SESSION_NEXT_KEY = "_kfa_next"

_ROLE_CLAIMS = ("realm_access", "resource_access")


def _decode_jwt_payload(token: str) -> dict[str, Any]:

    try:
        payload_segment = token.split(".")[1]
        padding = "=" * (-len(payload_segment) % 4)
        decoded = base64.urlsafe_b64decode(payload_segment + padding)
        return json.loads(decoded)
    except (IndexError, ValueError, binascii.Error):
        return {}


def _merge_role_claims(claims: dict[str, Any], access_token: str | None) -> dict[str, Any]:
    if not access_token:
        return claims
    access_claims = _decode_jwt_payload(access_token)
    for key in _ROLE_CLAIMS:
        if key not in claims and key in access_claims:
            claims[key] = access_claims[key]
    return claims


def build_blueprint(auth) -> Blueprint:
    bp = Blueprint("keycloak_auth", __name__)

    @bp.route("/login")
    def login():
        next_url = request.args.get("next") or auth.post_login_redirect
        session[SESSION_NEXT_KEY] = next_url

        redirect_uri = url_for("keycloak_auth.callback", _external=True)
        return auth.client.authorize_redirect(redirect_uri)

    @bp.route("/callback")
    def callback():
        token = auth.client.authorize_access_token()
        claims = token.get("userinfo")
        if claims is None:
            claims = auth.client.userinfo(token=token)

        claims = _merge_role_claims(dict(claims), token.get("access_token"))
        auth.save_user(claims, token.get("id_token"))

        next_url = session.pop(SESSION_NEXT_KEY, None) or auth.post_login_redirect
        return redirect(next_url)

    @bp.route("/logout")
    def logout():
        id_token = auth.clear_session()

        try:
            metadata = auth.load_server_metadata()
            end_session = metadata.get("end_session_endpoint")
        except Exception:
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
