# keycloak-flask-auth

Drop-in **Keycloak (OIDC) authentication for Flask** apps that render HTML
templates server-side. Built on [Authlib](https://authlib.org/). Designed so any
Python developer can add SSO to a Flask project in **three lines**.

- Standard OIDC **Authorization Code** flow (confidential client)
- **Server-side session** (signed cookie) — no tokens in the browser
- `@login_required` and `@roles_required` decorators
- `g.user` in views, `current_user` / `is_authenticated` in templates
- Single sign-on **and single sign-out** across all your apps in the realm
- Config entirely via environment variables → identical setup for every app

---

## Install

```bash
pip install keycloak-flask-auth
# from source:
pip install -e .
```

## Quickstart

```python
from flask import Flask, g, render_template
from keycloak_flask_auth import KeycloakAuth, login_required

app = Flask(__name__)
app.secret_key = "change-me"          # signs the session cookie

KeycloakAuth(app)                     # 1 line: wires up login/callback/logout

@app.route("/")
@login_required                       # protect any route
def home():
    return render_template("home.html", user=g.user)
```

Set these environment variables (per app):

```bash
KEYCLOAK_SERVER_URL=https://auth.example.com
KEYCLOAK_REALM=my-realm
KEYCLOAK_CLIENT_ID=my-flask-app
KEYCLOAK_CLIENT_SECRET=your-confidential-client-secret
```

That's it. The library adds these routes automatically:

| Route          | Purpose                                    |
| -------------- | ------------------------------------------ |
| `/auth/login`  | Start the Keycloak login                   |
| `/auth/callback` | OIDC redirect URI (register this in Keycloak) |
| `/auth/logout` | Local logout + Keycloak single sign-out    |

---

## Protecting routes

```python
from keycloak_flask_auth import login_required, roles_required

@app.route("/dashboard")
@login_required
def dashboard():
    ...

@app.route("/admin")
@roles_required("admin")               # must have the Keycloak "admin" role
def admin():
    ...

@app.route("/reports")
@roles_required("analyst", "manager", require_all=False)  # any of these
def reports():
    ...
```

## Using the user in templates

`current_user` and `is_authenticated` are injected into every template:

```html
{% if is_authenticated %}
  Hello {{ current_user.username }} ({{ current_user.email }})
  <a href="{{ url_for('keycloak_auth.logout') }}">Log out</a>
{% else %}
  <a href="{{ url_for('keycloak_auth.login') }}">Log in</a>
{% endif %}
```

The `user` object (`g.user`) exposes: `sub`, `username`, `email`,
`email_verified`, `name`, `given_name`, `family_name`, `roles`, `realm_roles`,
`client_roles`, plus `has_role(...)` / `has_any_role(...)`. The raw token claims
are always at `user.claims`.

---

## Configuring Keycloak (once per app)

In your realm, create a **client** for each Flask app:

1. **Client ID**: e.g. `my-flask-app`
2. **Client authentication**: ON (confidential)
3. **Standard flow**: enabled (Authorization Code)
4. **Valid redirect URIs**: `https://your-app.example.com/auth/callback`
5. **Valid post logout redirect URIs**: your app's home URL
6. Copy the client secret → `KEYCLOAK_CLIENT_SECRET`

Because all apps live in the same realm, logging into one signs the user into
the others (SSO), and `/auth/logout` signs them out everywhere.

## Reusing across many apps

Every app uses the **same code and the same env-var names** — only the values
differ (`KEYCLOAK_CLIENT_ID` / `KEYCLOAK_CLIENT_SECRET` per client). Pin this
package as a dependency in each project and you're done.

Optional environment variables:

| Variable                | Default               | Purpose                                  |
| ----------------------- | --------------------- | ---------------------------------------- |
| `KEYCLOAK_SCOPES`       | `openid email profile`| Requested OIDC scopes                    |
| `KEYCLOAK_URL_PREFIX`   | `/auth`               | Where login/callback/logout are mounted  |
| `KEYCLOAK_POST_LOGIN`   | `/`                   | Fallback redirect after login            |
| `KEYCLOAK_POST_LOGOUT`  | login page            | Where Keycloak returns after logout      |

You can also pass any of these directly instead of via env vars:

```python
KeycloakAuth(
    app,
    server_url="https://auth.example.com",
    realm="my-realm",
    client_id="my-flask-app",
    client_secret="...",
)
```

---

## Run the example

```bash
pip install -e ".[example]"
cp example/.env.example example/.env   # fill in your Keycloak details
python example/app.py                   # http://localhost:5000
```

## Security notes

- Uses server-side sessions — tokens never reach the browser.
- Authlib validates the ID token signature against Keycloak's JWKS and checks
  `state` / `nonce` automatically.
- Always set a strong `app.secret_key` and serve over HTTPS in production.
- For high-traffic apps or shared logout state, back the Flask session with
  Redis via `Flask-Session`.

## License

MIT
