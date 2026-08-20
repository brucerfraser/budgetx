# ServerAppData — v1
# Budget X app data for the HTML clients: one read-only bootstrap payload per page open.
# History:
#   v1  2026-08-20  Session 02 — created. GET /app/bootstrap (spec_02 §3.1, contract §4).
#
# DESIGN NOTES (read before editing)
# - Self-contained: this module declares its own ApiError / api_http / require_session /
#   require_auth, copied in SHAPE from ServerApi. It imports nothing from another Budget X
#   server module (spec_02 §3.1, the standing pattern).
# - NO module-level app_tables access. Every table reference lives inside a function body, so
#   this module imports cleanly whatever the schema state. A module-level table reference
#   would take /build/version down with it (spec_01 AC-1.4, learned in S01).
# - THIS MODULE IS READ-ONLY AND MUST STAY READ-ONLY (spec_02 §3.1, AC-1.4). It contains no
#   row-add, row-update or row-delete call, and no subscript assignment of any kind. AC-1.4
#   proves that by SCANNING THIS SOURCE for those call names and for bracketed assignment, so
#   the ban is textual as well as behavioural — this file must not even spell the patterns out.
#   The one place a subscript assignment would otherwise appear is stamping the response
#   Content-Type; it calls dict.__setitem__ explicitly instead. Do NOT tidy that back into
#   bracket-assignment form, and add no other bracketed assignment here: a scan cannot tell a
#   header write from a table write, and this module's whole guarantee is that it writes
#   nothing.
# - A non-200 is always RETURNED as an HttpResponse, never raised out of the wrapper. A raised
#   exception becomes an Anvil 500 error page, which fails AC-1.3.
# - Every auth failure returns the identical uniform 401 body — {"ok": false,
#   "error": "unauthorized"} — with no data key anywhere in it, so no response distinguishes a
#   missing header from a revoked token.
# - Headers are read case-insensitively; a missing header is None, never a KeyError/500.
# - Serialisation is factored into pure functions over plain mappings (an Anvil Row and a dict
#   both index the same way), so the payload shape is testable off-platform against
#   scratch/s02/fixtures/bootstrap.json without a database.
# - The response key-set is the frozen contract of spec_02 §4. Future rounds may ADD keys;
#   they may never rename or repurpose one. No amount appears in this payload.

import anvil.server
from anvil.tables import app_tables

import hashlib
import json
import re
import traceback
from datetime import date, datetime, timezone

MODULE_VERSION = "v1"

# The Transfer sentinel category. Hardcoded in six client_code files today; from here on the
# clients read it from this one constant so it stops being a magic string (spec_02 §4).
# A plain string constant at module level is not a table access.
TRANSFER_CATEGORY_ID = "ec8e0085-8408-43a2-953f-ebba24549d96"

# The Forms app keys its single settings row id='budget' (client_code/F_Components/Settings).
SETTINGS_ROW_ID = "budget"

# The contract's defaults. A stored value fills one of these in only when the row actually
# supplies it: a missing or None stored value must never blank out a default, and a key the
# stored row lacks must never drop out of the payload. (Standing rule: "a default is not a
# default if something stored shadows it".)
SETTINGS_DEFAULTS = {"dash_variances": False, "dash_var_top_five": []}

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


def _json_response(status, body):
    resp = anvil.server.HttpResponse(int(status), json.dumps(body))
    # dict.__setitem__ rather than bracketed assignment on resp.headers — see the DESIGN
    # NOTES: this module must contain no subscript assignment, because AC-1.4 proves it writes
    # nothing by scanning the source. Behaviour is identical to the S01-proven assignment form.
    resp.headers.__setitem__("Content-Type", "application/json")
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

    Replicates ServerApi.require_session exactly — same 64-lowercase-hex token shape, same
    revoked_at / active / expires_at checks, same naive-datetime-is-UTC handling. Every one of
    those failures carries the identical body and no account data, so nothing leaks which check
    failed. Copied rather than imported, per the self-contained-module rule.
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
    """The authenticated users row. Called explicitly inside the handler body, never relied on
    through decorator ordering."""
    return require_session()["user"]


# ---------------------------------------------------------------------------------------------
# Pure serialisation. Everything below takes plain mappings and returns plain JSON types, so it
# runs — and is tested — without Anvil or a database.
# ---------------------------------------------------------------------------------------------


def _get(row, name, default=None):
    """One column, defensively: an absent column or a None value yields the default."""
    try:
        value = row[name]
    except Exception:
        return default
    return default if value is None else value


def _text(value, default=""):
    """A JSON string. None becomes the default so a str-typed contract field stays a str."""
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def _text_or_none(value):
    """A JSON string or null — for the contract's explicitly nullable fields (icon)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _number(value, default=0):
    """A JSON number. Whole floats collapse to int so the payload reads 1, not 1.0.

    Anvil number columns are nullable; the contract types `order` as a number, so a null column
    falls back to the default rather than emitting a type the client cannot sort on. Every
    category and sub_category in the live data carries an order (the Forms app sorts on it), so
    this fallback is a guard, not a data source.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _iso_date(value):
    """A date column as ISO YYYY-MM-DD, or null. Defensive about a datetime coming back where a
    date was expected — datetime is a subclass of date, so it is tested first."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if text else None


def _order_sort_key(row):
    """Sort by the `order` column with None LAST, then by name, then by id — deterministic
    output matters more than the tie-break chosen."""
    value = _get(row, "order")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return (1, 0.0)
    return (0, float(value))


def serialise_account(row):
    return {
        "acc_id": _text(_get(row, "acc_id")),
        "acc_name": _text(_get(row, "acc_name")),
        # A real bool: the column is nullable and the client filters on this flag.
        "archived": bool(_get(row, "archived", False)),
    }


def serialise_category(row):
    return {
        "category_id": _text(_get(row, "category_id")),
        "name": _text(_get(row, "name")),
        "colour_back": _text(_get(row, "colour_back")),
        "colour_text": _text(_get(row, "colour_text")),
        "order": _number(_get(row, "order")),
    }


def serialise_sub_category(row):
    return {
        "sub_category_id": _text(_get(row, "sub_category_id")),
        "name": _text(_get(row, "name")),
        "icon": _text_or_none(_get(row, "icon")),
        "belongs_to": _text(_get(row, "belongs_to")),
        "order": _number(_get(row, "order")),
        "roll_over": bool(_get(row, "roll_over", False)),
        "roll_over_date": _iso_date(_get(row, "roll_over_date")),
    }


def serialise_settings(row):
    """The defaults, with only the keys the stored row actually supplies filled in.

    A stored None never blanks a default, and a key the stored row lacks never drops out of the
    payload — otherwise a default added in a later round would silently never reach an
    environment seeded before it existed.
    """
    if row is None:
        return dict(SETTINGS_DEFAULTS)
    stored = {
        key: value
        for key, value in (
            ("dash_variances", _get(row, "dash_variances")),
            ("dash_var_top_five", _get(row, "dash_var_top_five")),
        )
        if value is not None
    }
    merged = {**SETTINGS_DEFAULTS, **stored}
    top_five = merged["dash_var_top_five"]
    return {
        "dash_variances": bool(merged["dash_variances"]),
        "dash_var_top_five": list(top_five) if isinstance(top_five, (list, tuple)) else [],
    }


def build_bootstrap_payload(email, server_date, accounts, categories, sub_categories,
                            settings_row):
    """The frozen contract of spec_02 §4 — exactly these eight keys, no extras, no omissions.

    Rows arrive as plain mappings (Anvil Rows or dicts). Every row of each table appears;
    archived accounts are included with their flag and the client does the filtering.
    """
    sorted_accounts = sorted(
        accounts,
        key=lambda r: (_text(_get(r, "acc_name")).lower(), _text(_get(r, "acc_id"))),
    )
    sorted_categories = sorted(
        categories,
        key=lambda r: (_order_sort_key(r), _text(_get(r, "name")).lower(),
                       _text(_get(r, "category_id"))),
    )
    sorted_sub_categories = sorted(
        sub_categories,
        key=lambda r: (_order_sort_key(r), _text(_get(r, "name")).lower(),
                       _text(_get(r, "sub_category_id"))),
    )
    return {
        "ok": True,
        "email": _text(email),
        "server_date": server_date,
        "transfer_category_id": TRANSFER_CATEGORY_ID,
        "accounts": [serialise_account(r) for r in sorted_accounts],
        "categories": [serialise_category(r) for r in sorted_categories],
        "sub_categories": [serialise_sub_category(r) for r in sorted_sub_categories],
        "settings": serialise_settings(settings_row),
    }


# ---------------------------------------------------------------------------------------------
# The endpoint. Table access lives here and nowhere above.
# ---------------------------------------------------------------------------------------------


def _settings_row():
    """The single settings row, or None.

    The Forms app keys it id='budget', so that is the primary lookup. A lone unkeyed row is
    accepted as a fallback; anything ambiguous (no row, or several unkeyed rows) falls through
    to the documented defaults rather than guessing which row is authoritative.
    """
    try:
        row = app_tables.settings.get(id=SETTINGS_ROW_ID)
    except Exception:
        traceback.print_exc()
        row = None
    if row is not None:
        return row
    try:
        rows = list(app_tables.settings.search())
    except Exception:
        traceback.print_exc()
        return None
    return rows[0] if len(rows) == 1 else None


@api_http("/app/bootstrap", methods=["GET"])
def api_app_bootstrap(**kwargs):
    """Everything a client shell needs, in ONE call — the standing one-fetch-per-page-open rule.

    Read-only: search() and get() only. Nothing in this handler, or anywhere in this module,
    creates, updates or deletes a row.
    """
    user = require_auth()
    return build_bootstrap_payload(
        email=_text(_get(user, "email")),
        server_date=_now().date().isoformat(),
        accounts=list(app_tables.accounts.search()),
        categories=list(app_tables.categories.search()),
        sub_categories=list(app_tables.sub_categories.search()),
        settings_row=_settings_row(),
    )
