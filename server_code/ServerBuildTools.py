# ServerBuildTools — v1
# Budget X build pipeline: upload/promote/list of app_versions, the /x serving route, and the
# read-back instruments (/build/session, /build/counts) that prove a write actually landed.
# History:
#   v1  2026-08-19  Session 01 — created. upload/promote/list/version/session/counts and /x.
#
# DESIGN NOTES (read before editing)
# - Self-contained: this module declares its own ApiError / api_http rather than importing
#   ServerApi's. The ONE sanctioned cross-module reference is reading ServerApi.MODULE_VERSION
#   inside _module_versions(), because /build/version must report both stamps and spec_01 §3.4
#   requires each stamp to come from a single in-module constant so header and endpoint cannot
#   drift. It is imported INSIDE the function, never at module level.
# - NO module-level app_tables access, so this module imports cleanly before api_sessions and
#   app_versions exist (AC-1.4).
# - /build/version deliberately touches NO table: it must answer on the near side of the schema
#   migration, which is what makes AC-1 judgeable before Bruce's migrate click. Do not add a
#   table read to it.
# - Every /build/* endpoint is gated by the X-Build-Secret header compared with hmac.compare_digest
#   against the Anvil App Secret named build_secret. The secret is never a query parameter, never
#   in a response body, never in a log line.
# - /x is the ONLY ungated route (a browser fetches it) and is NOT the app root. It returns the
#   stored bytes verbatim: no templating, no wrapping, no injected banner.

import anvil.server
import anvil.secrets
from anvil.tables import app_tables

import hashlib
import hmac
import json
import traceback
import uuid
from datetime import datetime, timezone

MODULE_VERSION = "v1"

DEFAULT_SLUG = "x"
DEFAULT_KIND = "html"

# Tables reported by /build/counts — the AC-11.1 instrument. Counts only, never row contents.
COUNTED_TABLES = [
    "accounts", "budgets", "categories", "sub_categories",
    "transactions", "settings", "files", "test_csv", "users",
]


class ApiError(Exception):
    def __init__(self, status, code):
        super().__init__("%s:%s" % (status, code))
        self.status = int(status)
        self.code = str(code)


def _now():
    return datetime.now(timezone.utc)


def _as_utc(value):
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
    """Case-insensitive header lookup. Missing is None, never a KeyError/500."""
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
    try:
        body = anvil.server.request.body_json
    except Exception:
        raise ApiError(400, "bad_request")
    if not isinstance(body, dict):
        raise ApiError(400, "bad_request")
    return body


def require_build_secret():
    """Constant-time check of X-Build-Secret against the build_secret App Secret."""
    supplied = _header("X-Build-Secret")
    if supplied is None:
        raise ApiError(401, "unauthorized")
    try:
        expected = anvil.secrets.get_secret("build_secret")
    except Exception:
        traceback.print_exc()
        raise ApiError(401, "unauthorized")
    if not expected:
        raise ApiError(401, "unauthorized")
    if not hmac.compare_digest(str(supplied).encode("utf-8"), str(expected).encode("utf-8")):
        raise ApiError(401, "unauthorized")
    return True


def api_http(path, methods=("GET",)):
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


def _module_versions():
    """Both module stamps, each read from that module's single in-module constant."""
    versions = {"ServerBuildTools": MODULE_VERSION}
    try:
        import ServerApi
        versions["ServerApi"] = ServerApi.MODULE_VERSION
    except Exception:
        traceback.print_exc()
        versions["ServerApi"] = "unavailable"
    return versions


def _manifest(row):
    """One build row WITHOUT its html column — the list is a manifest, not a payload."""
    return {
        "record_uid": row["record_uid"],
        "slug": row["slug"],
        "kind": row["kind"],
        "version": row["version"],
        "sha256": row["sha256"],
        "bytes": row["bytes"],
        "is_current": row["is_current"],
        "uploaded_at": _iso(row["uploaded_at"]),
        "promoted_at": _iso(row["promoted_at"]),
    }


@api_http("/build/version", methods=["GET"])
def api_build_version(**kwargs):
    require_build_secret()
    return {"ok": True, "modules": _module_versions()}


@api_http("/build/upload", methods=["POST"])
def api_build_upload(**kwargs):
    require_build_secret()
    body = _request_json()

    html = body.get("html")
    if not isinstance(html, str) or html == "":
        raise ApiError(400, "bad_request")

    version = body.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ApiError(400, "bad_request")
    version = version.strip()
    # Bruce's standing rule: never promote a 0.x build.
    if version.startswith("0."):
        raise ApiError(400, "bad_request")

    slug = body.get("slug") or DEFAULT_SLUG
    kind = body.get("kind") or DEFAULT_KIND
    if not isinstance(slug, str) or not slug.strip():
        raise ApiError(400, "bad_request")
    if not isinstance(kind, str) or not kind.strip():
        raise ApiError(400, "bad_request")

    encoded = html.encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    record_uid = str(uuid.uuid4())

    app_tables.app_versions.add_row(
        record_uid=record_uid,
        slug=slug.strip(),
        kind=kind.strip(),
        version=version,
        html=html,
        sha256=digest,
        bytes=len(encoded),
        is_current=False,
        uploaded_at=_now(),
        promoted_at=None,
        uploaded_by=str(body.get("uploaded_by") or "tools/api.py"),
        active=True,
    )
    return {"ok": True, "record_uid": record_uid, "sha256": digest, "bytes": len(encoded)}


@api_http("/build/promote", methods=["POST"])
def api_build_promote(**kwargs):
    require_build_secret()
    body = _request_json()
    record_uid = body.get("record_uid")
    if not isinstance(record_uid, str) or not record_uid.strip():
        raise ApiError(400, "bad_request")

    target = app_tables.app_versions.get(record_uid=record_uid.strip())
    if target is None:
        raise ApiError(404, "not_found")

    slug, kind = target["slug"], target["kind"]
    # Exactly one row per (slug, kind) may be current: demote every sibling first.
    for row in app_tables.app_versions.search(slug=slug, kind=kind):
        if row["record_uid"] != target["record_uid"] and row["is_current"]:
            row["is_current"] = False
    target["is_current"] = True
    target["promoted_at"] = _now()
    return {"ok": True, "record_uid": target["record_uid"], "slug": slug, "version": target["version"]}


@api_http("/build/list", methods=["GET"])
def api_build_list(slug=None, kind=None, **kwargs):
    require_build_secret()
    rows = list(app_tables.app_versions.search())
    if slug:
        rows = [r for r in rows if r["slug"] == slug]
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    rows.sort(key=lambda r: _as_utc(r["uploaded_at"]) or datetime.min.replace(tzinfo=timezone.utc),
              reverse=True)
    return {"ok": True, "builds": [_manifest(r) for r in rows]}


@api_http("/build/session", methods=["GET"])
def api_build_session(token_hash=None, **kwargs):
    """Read-only read-back of an api_sessions row. Never accepts a raw token, never returns
    token_hash, and cannot create, extend, revoke or modify anything."""
    require_build_secret()
    if not token_hash or not isinstance(token_hash, str):
        raise ApiError(400, "bad_request")
    row = app_tables.api_sessions.get(token_hash=token_hash.strip())
    if row is None:
        return {"ok": True, "session": None}
    user = row["user"]
    return {
        "ok": True,
        "session": {
            "record_uid": row["record_uid"],
            "email": user["email"] if user else None,
            "issued_at": _iso(row["issued_at"]),
            "expires_at": _iso(row["expires_at"]),
            "revoked_at": _iso(row["revoked_at"]),
            "active": row["active"],
        },
    }


@api_http("/build/counts", methods=["GET"])
def api_build_counts(**kwargs):
    """Row counts only — no row contents, ever. The AC-11.1 instrument."""
    require_build_secret()
    counts = {}
    for name in COUNTED_TABLES:
        try:
            counts[name] = len(getattr(app_tables, name).search())
        except Exception:
            traceback.print_exc()
            counts[name] = None
    return {"ok": True, "counts": counts}


@anvil.server.http_endpoint("/x", methods=["GET"])
def serve_client(slug=None, **kwargs):
    """The serving route: no auth, no secret, because a browser fetches it.

    Returns the promoted bytes verbatim. NOT the app root — the Forms app keeps serving there.
    """
    try:
        wanted = slug or DEFAULT_SLUG
        row = None
        for candidate in app_tables.app_versions.search(slug=wanted, kind=DEFAULT_KIND):
            if candidate["is_current"]:
                row = candidate
                break
        if row is None:
            resp = anvil.server.HttpResponse(404, "no current build")
            resp.headers["Content-Type"] = "text/plain; charset=utf-8"
            resp.headers["Cache-Control"] = "no-store"
            return resp
        resp = anvil.server.HttpResponse(200, row["html"])
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except Exception:
        traceback.print_exc()
        resp = anvil.server.HttpResponse(500, "server error")
        resp.headers["Content-Type"] = "text/plain; charset=utf-8"
        resp.headers["Cache-Control"] = "no-store"
        return resp
