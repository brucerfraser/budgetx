# ServerApi — v1
# Budget X API spine: ApiError / api_http / require_auth, session tokens over Anvil Users.
# History:
#   v1  2026-08-19  Session 01 — created. login/me/logout, 12h absolute token expiry.
#
# DESIGN NOTES (read before editing)
# - Self-contained: this module declares its own ApiError / api_http / require_auth. It imports
#   nothing from another Budget X server module.
# - NO module-level app_tables access. Every table reference lives inside a function body so this
#   module imports cleanly before the api_sessions table exists (spec_01 AC-1.4). A module-level
#   table reference would take /build/version down with it.
# - Anvil serves these at https://budget-x.anvil.app/_/api/<path>. The /_/api prefix is the
#   platform's, not ours. The app root keeps serving the Forms app and is not touched.
# - A non-200 is always RETURNED as an HttpResponse, never raised. A raised exception becomes an
#   Anvil 500 error page, which fails AC-1.3 / AC-3 / AC-5.5.
# - The raw token is never stored: api_sessions holds sha256(token) only.
# - Anvil Users remains the credential store. This module never reads or writes password_hash.

import anvil.server
import anvil.users
from anvil.tables import app_tables

import hashlib
import json
import re
import secrets
import traceback
import uuid
from datetime import datetime, timedelta, timezone

MODULE_VERSION = "v1"

# Absolute token lifetime. Does NOT extend on use.
TOKEN_TTL = timedelta(hours=12)

_TOKEN_RE = re.compile(r"^[0-9a-f]{64}$")


class ApiError(Exception):
    """Carries an HTTP status and a short machine-readable code."""

    def __init__(self, status, code):
        super().__init__("%s:%s" % (status, code))
        self.status = int(status)
        self.code = str(code)


def _now():
    return datetime.now(timezone.utc)


def _as_utc(value):
    """Anvil may hand back a naive datetime; treat naive as UTC rather than crashing."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value):
    value = _as_utc(value)
    return None if value is None else value.isoformat()


def _json_response(status, body):
    resp = anvil.server.HttpResponse(int(status), json.dumps(body))
    resp.headers["Content-Type"] = "application/json"
    return resp


def _header(name):
    """Case-insensitive header lookup. A missing header is None, never a KeyError/500."""
    try:
        headers = anvil.server.request.headers or {}
        target = str(name).lower()
        for key, value in dict(headers).items():
            if str(key).lower() == target:
                return value
    except Exception:
        return None
    return None


def _request_json():
    """The POST body as a dict, or ApiError(400) — never a 500."""
    try:
        body = anvil.server.request.body_json
    except Exception:
        raise ApiError(400, "bad_request")
    if not isinstance(body, dict):
        raise ApiError(400, "bad_request")
    return body


def api_http(path, methods=("GET",)):
    """Wraps @anvil.server.http_endpoint with uniform JSON encoding and error mapping.

    The body never contains a traceback, a stack frame, a module path or a table name; the
    traceback is printed so it reaches the Anvil app logs instead.
    """

    def decorator(fn):
        @anvil.server.http_endpoint(path, methods=list(methods))
        def wrapper(*args, **kwargs):
            try:
                return _json_response(200, fn(*args, **kwargs))
            except ApiError as err:
                return _json_response(err.status, {"ok": False, "error": err.code})
            except Exception:
                traceback.print_exc()
                return _json_response(500, {"ok": False, "error": "server_error"})

        wrapper.__name__ = fn.__name__
        return wrapper

    return decorator


def require_session():
    """The authenticated api_sessions row, or ApiError(401).

    Every 401 carries the identical body and no account data, so nothing leaks which check failed.
    """
    raw = _header("Authorization")
    if not raw:
        raise ApiError(401, "unauthorized")
    parts = str(raw).split(" ")
    if len(parts) != 2 or parts[0] != "Bearer":
        raise ApiError(401, "unauthorized")
    token = parts[1]
    if not _TOKEN_RE.match(token):
        raise ApiError(401, "unauthorized")

    row = app_tables.api_sessions.get(
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest()
    )
    if row is None:
        raise ApiError(401, "unauthorized")
    if row["revoked_at"] is not None:
        raise ApiError(401, "unauthorized")
    if row["active"] is not True:
        raise ApiError(401, "unauthorized")
    expires_at = _as_utc(row["expires_at"])
    if expires_at is None or expires_at <= _now():
        raise ApiError(401, "unauthorized")
    return row


def require_auth():
    """The authenticated users row, per spec_01 §3.1. Called explicitly inside each handler body,
    never relied on through decorator ordering."""
    return require_session()["user"]


@api_http("/auth/login", methods=["POST"])
def api_auth_login(**kwargs):
    body = _request_json()
    email = body.get("email")
    password = body.get("password")
    if not isinstance(email, str) or not email.strip():
        raise ApiError(400, "bad_request")
    if not isinstance(password, str) or not password:
        raise ApiError(400, "bad_request")

    # Credential check against the Anvil Users service. The broad except is deliberate and is
    # scoped to this block only: anvil.users raises a family of failures (bad password, unconfirmed
    # email, disabled account, too many failures, MFA). Every one maps to the same 401 so no
    # response distinguishes "no such account" from "wrong password".
    try:
        anvil.users.login_with_email(email.strip(), password)
        user = anvil.users.get_user()
    except Exception:
        try:
            anvil.users.logout()
        except Exception:
            pass
        raise ApiError(401, "invalid_credentials")
    finally:
        # Keep the HTTP API stateless: no Anvil session leaks between requests.
        try:
            anvil.users.logout()
        except Exception:
            pass

    if user is None:
        raise ApiError(401, "invalid_credentials")

    token = secrets.token_hex(32)
    issued_at = _now()
    expires_at = issued_at + TOKEN_TTL
    app_tables.api_sessions.add_row(
        record_uid=str(uuid.uuid4()),
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        user=user,
        issued_at=issued_at,
        expires_at=expires_at,
        revoked_at=None,
        active=True,
        source="api",
    )
    # The raw token is returned once, in this response only.
    return {
        "ok": True,
        "token": token,
        "expires_at": _iso(expires_at),
        "email": user["email"],
    }


@api_http("/me", methods=["GET"])
def api_me(**kwargs):
    session = require_session()
    return {
        "ok": True,
        "email": session["user"]["email"],
        "expires_at": _iso(session["expires_at"]),
    }


@api_http("/auth/logout", methods=["POST"])
def api_auth_logout(**kwargs):
    session = require_session()
    session["revoked_at"] = _now()
    session["active"] = False
    # A second call with the same token returns 401: the token is already dead. That is correct.
    return {"ok": True, "revoked": True}
