"""keycloak-flask-auth

Drop-in Keycloak (OIDC) authentication for Flask apps.

Typical usage
-------------
    from flask import Flask, g, render_template
    from keycloak_flask_auth import KeycloakAuth, login_required

    app = Flask(__name__)
    app.secret_key = "change-me"

    auth = KeycloakAuth(app)  # reads config from environment variables

    @app.route("/")
    @login_required
    def home():
        return render_template("index.html", user=g.user)
"""

from .auth import KeycloakAuth
from .decorators import login_required, roles_required
from .user import User

__all__ = ["KeycloakAuth", "login_required", "roles_required", "User"]

__version__ = "0.1.0"
