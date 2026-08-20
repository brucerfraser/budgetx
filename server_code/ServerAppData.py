# ServerAppData — v2
# Budget X app data for the HTML clients: one read-only bootstrap payload per page open.
# History:
#   v1  2026-08-20  Session 02 — created. GET /app/bootstrap (spec_02 §3.1, contract §4).
#   v2  2026-08-20  Session 03 — GET /app/bootstrap gains the optional ?include=transactions
#                   parameter and, only then, one new top-level key (spec_03 §3.2, §4.1–4.3).
#   v2  2026-08-20  Session 03, in-round repair — whether the `active` column is READABLE is
#                   now decided once per call instead of being rediscovered on every row, which
#                   took ?include=transactions from p50 10,457 ms to the figure in the debrief
#                   (spec_03 AC-13.6). No key, type, value or order change. The stamp stays v2
#                   on purpose: AC-1.6 pins /build/version to ServerAppData v2.
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
#   they may never rename or repurpose one.
#
# v2 — THE ONE ADDITIVE CHANGE (spec_03 §3.2, AC-1.1/1.2/1.3)
# - GET /app/bootstrap gains ONE optional query parameter, `include`. Only the exact value
#   "transactions" does anything; ANY other value, and no query string at all, returns a body
#   whose key-set is EXACTLY v1's, with no `transactions` key present. AC-1.1 and AC-1.3 check
#   that programmatically, and it is what keeps d-dash / m-dash honest.
# - The extra key is added by rebuilding the payload as a NEW dict literal, never by assigning
#   into the existing one — see the subscript-assignment ban above.
# - The set returned is every row where `active` IS NOT FALSE (spec_03 §4.3). Bruce's schema
#   click adds `active` without touching the ~1,300 existing rows, so they read None, and None
#   means "predates soft-delete", which is to say ACTIVE. A `is True` test here would hide all
#   ~1,300 of Bruce's transactions; it is the single most likely serious defect in round 03 and
#   it has its own criterion. is_active() is the ONE place the test is written.
# - There is no windowing: the whole history goes in one call, because the clients do all
#   display maths locally and every later screen needs the same set (spec_03 §11.3).
# - MONEY IS INTEGER CENTS. The `amount` column ALREADY holds cents (csv_handler.make_ready
#   does int(math.trunc(x*100)) on import; the Forms UI divides by 100 to display), so the
#   wire conversion is a TYPE cast — int(round(stored)) — and NEVER a multiply by 100. The
#   legacy float name `amount` does not appear on the wire; the wire name is amount_cents.
# - The transaction serialiser is DUPLICATED here and in ServerTxn rather than imported, per
#   the self-contained-module rule. scratch/s03/shape_check.py asserts the two agree.
#
# READING A COLUMN THE SCHEMA DOES NOT HAVE COSTS A SERVER ROUND TRIP, EVERY TIME
# (measured on live 2026-08-20, and the whole of the AC-13.6 defect)
# - ?include=transactions ran p50 10,457 ms (7,838–14,826) for 1,300 rows. Server-side timing
#   of the legs put 390 ms in the search and 10,350 ms in the SERIALISER, so the body size and
#   the query were never the problem. Instrumenting a 200-row sample settled the rest:
#       reading one existing column on 200 rows ......   0 ms
#       reading nine existing columns on 200 rows ...    1 ms
#       reading them all a second time ..............    1 ms
#       reading the MISSING `active` column, 200 rows  577–804 ms   (~3–4 ms EACH)
#   search() already hands back every stored column, so column access is free. A column the
#   schema does not have is not free: Anvil goes and asks the data layer before it raises.
# - is_active() was called TWICE per row — once to filter, once to fill the `active` key — so
#   the pre-click set cost 2 × 1,300 ≈ 2,600 round trips ≈ 10 s. That is the entire defect.
# - THE FIX: readability of `active` is a property of the SCHEMA, not of a row. It is therefore
#   probed ONCE per call (_active_readable, which tries at most three rows) and threaded through
#   as a flag. Not readable => the column reads None for every row, and None is exactly what the
#   per-row lookup returned anyway — same answer, O(1) lookups instead of O(2n).
# - This is why _active_raw/is_active take the flag rather than consulting a module-level cache:
#   a cached "missing" would survive Bruce's schema click inside a warm server process and go on
#   hiding archived rows after the column existed. The flag is re-derived on every request.
# - AFTER the click the flag is True, every row is read exactly as before, and the cost is the
#   ~0 ms that reading a real column costs. The repair needs no edit on the day of the click.
# - NOT the fix: q.fetch_only(). It was tried and deployed first, and this app's data tables
#   reject it outright — `TableError: Invalid argument to table query` on every table, including
#   ones with no missing column (Accelerated Tables is not enabled; anvil.yaml's tables service
#   carries an empty server_config). It also could not have helped, because the measurements
#   above show stored columns are already resolved by search().

import anvil.server
from anvil.tables import app_tables

import hashlib
import json
import re
import traceback
from datetime import date, datetime, timezone

MODULE_VERSION = "v2"

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


# ---------------------------------------------------------------------------------------------
# v2 — the transaction object (spec_03 §4.2). Pure over plain mappings, like everything above.
# ---------------------------------------------------------------------------------------------


def _nullable_text(value):
    """A JSON string or null, for `category` and `transfer_account` — the transaction object's
    only nullable fields. An empty stored string normalises to null: the Forms app writes both
    None and "" for "no category", and the contract has one spelling for absent."""
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    return text if text != "" else None


def _iso_date_text(value):
    """A date column as ISO YYYY-MM-DD, or "" — the transaction contract types `date` as a
    string, so a null column must not emit null. datetime is a subclass of date and is tested
    first."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if text else ""


def _active_readable(rows):
    """Whether the `active` column can be read at all — decided ONCE for the whole set.

    Presence is a property of the SCHEMA, not of a row: if the column is not there, it is not
    there for any row. Rediscovering that per row costs a server round trip per row (see the
    DESIGN NOTES), which is what made ?include=transactions a ten-second call before the click.

    Up to three rows are tried and ANY success means readable. The bias is deliberate: a
    transient failure on one row must not be mistaken for "no such column", because that answer
    would report an archived row as active. Falling back to readable=True is always safe — it
    just pays the per-row lookup and reads the truth.
    """
    tried = 0
    for row in rows:
        try:
            row["active"]
            return True
        except Exception:
            tried += 1
            if tried >= 3:
                return False
    return tried == 0


def _active_raw(row, readable=True):
    """The raw `active` column: True, False or None.

    None covers BOTH "the column exists and this legacy row was never touched" and "the column
    is not there yet" (before Bruce's click). Both mean active.

    `readable=False` says the column is absent from the schema, which is precisely the case the
    except branch below used to discover — one row at a time, at a round trip each.
    """
    if not readable:
        return None
    try:
        value = row["active"]
    except Exception:
        return None
    return value if value is True or value is False else None


def is_active(row, readable=True):
    """The active test, in ONE place so it cannot drift: `is not False` — NEVER `is True`.

    The test runs on every path. `readable` only changes how the raw value is obtained, never
    how it is judged.
    """
    return _active_raw(row, readable) is not False


def _amount_cents(value, anomalies=None, transaction_id=None):
    """The stored `amount` column as the contract's integer cents.

    A TYPE cast, not a SCALE conversion — the column already holds cents. NEVER multiply by
    100 here. A non-integral stored value is a pre-existing data defect: it is rounded and the
    row is collected so the round can list it, but no key is added to the payload for it.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if anomalies is not None:
            anomalies.append((transaction_id, value))
        return 0
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        if anomalies is not None:
            anomalies.append((transaction_id, value))
        return int(round(value))
    return int(value)


def serialise_transaction(row, anomalies=None, readable=True):
    """The spec_03 §4.2 transaction object — exactly these ten keys, no extras, no omissions.

    `readable` is the caller's one-off answer to "is the `active` column in the schema?"; it
    defaults to True so a lone call behaves exactly as it always did.
    """
    transaction_id = _text(_get(row, "transaction_id"))
    return {
        "transaction_id": transaction_id,
        "date": _iso_date_text(_get(row, "date")),
        "description": _text(_get(row, "description")),
        "amount_cents": _amount_cents(_get(row, "amount", 0), anomalies, transaction_id),
        "account": _text(_get(row, "account")),
        "category": _nullable_text(_get(row, "category")),
        "transfer_account": _nullable_text(_get(row, "transfer_account")),
        "notes": _text(_get(row, "notes")),
        "hash": _text(_get(row, "hash")),
        "active": is_active(row, readable),
    }


def _transaction_sort_key(txn):
    """Row order IS part of the contract (spec_03 §4.2): `date` descending, then
    `transaction_id` ascending — a total order, so two calls are diffable. Dates compare as the
    integer YYYYMMDD, negated for the descending leg; a blank date sorts last."""
    iso = txn["date"]
    if len(iso) == 10 and iso[4] == "-" and iso[7] == "-":
        try:
            return (0, -int(iso[0:4] + iso[5:7] + iso[8:10]), txn["transaction_id"])
        except ValueError:
            pass
    return (1, 0, txn["transaction_id"])


def build_transactions_payload(rows, anomalies=None):
    """Every row where `active` is not False, serialised and sorted by the contract order.

    The rows are materialised first so the readability probe and the walk see the same set, and
    so a one-shot iterator is not consumed by the probe.
    """
    materialised = list(rows)
    readable = _active_readable(materialised)
    return sorted(
        [serialise_transaction(r, anomalies, readable)
         for r in materialised if is_active(r, readable)],
        key=_transaction_sort_key,
    )


def wants_transactions(include):
    """True only for the exact value "transactions". Any other value — and no query string at
    all — leaves the v1 key-set untouched (spec_03 AC-1.1/1.3)."""
    if not isinstance(include, str):
        return False
    return include.strip().lower() == "transactions"


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


def _report_amount_anomalies(anomalies):
    """Non-integral stored cents are a pre-existing data defect worth knowing about. They go to
    the Anvil app log — never into the payload, whose key-set is frozen."""
    for transaction_id, value in anomalies or []:
        print("ServerAppData: non-integral stored amount on transaction_id=%s value=%r"
              % (transaction_id, value))


@api_http("/app/bootstrap", methods=["GET"])
def api_app_bootstrap(include=None, **kwargs):
    """Everything a client shell needs, in ONE call — the standing one-fetch-per-page-open rule.

    Read-only: search() and get() only. Nothing in this handler, or anywhere in this module,
    creates, changes or removes a row.

    v2: with ?include=transactions the payload gains ONE extra top-level key. With any other
    include value, or none, the key-set is exactly v1's. The extra key is added by building a
    NEW dict from the old one, never by assigning into it.
    """
    user = require_auth()
    payload = build_bootstrap_payload(
        email=_text(_get(user, "email")),
        server_date=_now().date().isoformat(),
        accounts=list(app_tables.accounts.search()),
        categories=list(app_tables.categories.search()),
        sub_categories=list(app_tables.sub_categories.search()),
        settings_row=_settings_row(),
    )
    if not wants_transactions(include):
        return payload
    anomalies = []
    transactions = build_transactions_payload(
        list(app_tables.transactions.search()), anomalies)
    _report_amount_anomalies(anomalies)
    return {**payload, "transactions": transactions}
