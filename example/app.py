"""Minimal example: protecting a Flask app with Keycloak in a few lines.

Run it:
    1. copy .env.example to .env and fill in your Keycloak client details
    2. pip install -e ".[example]"
    3. python example/app.py
    4. open http://localhost:5000
"""

import os

from dotenv import load_dotenv
from flask import Flask, g, render_template

from python_auth_library import KeycloakAuth, login_required, roles_required

load_dotenv()

app = Flask(__name__)
# Required so Flask can sign the session cookie. Use a long random value in prod.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

# This single line wires up login/callback/logout and g.user. Config comes from
# the KEYCLOAK_* environment variables.
KeycloakAuth(app)


@app.route("/")
def index():
    # Public page. `current_user` / `is_authenticated` are available in templates.
    return render_template("index.html")


@app.route("/profile")
@login_required
def profile():
    # Protected: unauthenticated visitors are redirected to Keycloak.
    return render_template("profile.html", user=g.user)


@app.route("/admin")
@roles_required("admin")
def admin():
    # Protected AND requires the "admin" Keycloak role.
    return render_template("admin.html", user=g.user)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
