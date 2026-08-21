# ServerBudget — v1
# Budget X budget + structure write path, and GET /budget/summary, the money verification
# instrument.
# History:
#   v1  2026-08-21  Session 04 — created. The app's FIRST write path to its STRUCTURE
#                   (categories / sub_categories), the budget write path, and the read-only
#                   recomputation instrument (spec_04 §3.2, contract §4.2–4.7).
#
# =============================================================================================
# DESIGN NOTES — read the whole block before editing. Every rule here cost something.
# =============================================================================================
#
# SELF-CONTAINED
# - This module declares its own ApiError / api_http / require_session / require_auth, copied in
#   SHAPE from ServerApi (frozen) and ServerTxn. It imports nothing from another Budget X server
#   module. That is the standing pattern and it is why the same twelve helpers appear in four
#   files: a cross-import makes one module's failure every module's failure.
# - NO module-level app_tables access. Every table reference lives inside a function body, so
#   this module imports cleanly whatever the schema state. A module-level table reference would
#   take /build/version down with it (S01's lesson).
# - Do NOT reach for q.fetch_only(): it returns TableError app-wide on this app — Accelerated
#   Tables is not enabled (spec_04 §0.1, measured in S03).
#
# NO SUBSCRIPT ASSIGNMENT, ANYWHERE IN THIS FILE (spec_04 §3.2, AC-3.10)
# - AC-3.10 proves "no hard removal" by a MODULE-WIDE AST walk for row-removal calls and for
#   subscript assignment of any kind. A walk cannot tell a table-row subscript write from a
#   header write or a dict write, so the ban is total: every row write goes through
#   row.update(**fields), every dict is built as a literal / comprehension, and every
#   accumulator uses .__setitem__ or .setdefault. The response Content-Type is stamped with
#   headers.__setitem__ for the same reason. DO NOT tidy any of those back into bracket form.
# - There is likewise no row-removal call in this file. Archival is SOFT: active False plus the
#   §3.8 order mirror, and every archive endpoint has a restore endpoint.
#
# THE SIX WRITE RULES (spec_03 §3.1 + spec_04 §3.2) — every endpoint below obeys all six:
#   1. THE SERVER OWNS IDENTITY AND DERIVED FIELDS. category_id / sub_category_id are minted
#      here (uuid4) and `order` is computed here, on every path. A caller-supplied id or order
#      is ignored and never stored: neither name is in an accepted-field tuple.
#   2. WHITELIST, NEVER BLACKLIST. Each endpoint reads an exact key set; every other key in the
#      body is dropped before anything reaches a column. There is no "store what you sent".
#   3. EVERY WRITE RETURNS AN INDEPENDENT READ-BACK. A single-row response is re-fetched with
#      get() after being written through a handle obtained from search(); a whole-set response
#      is re-fetched with a FRESH search() after the writes. Anvil Row handles cache per handle,
#      so echoing the handle you just wrote through proves nothing. With no audit log on this
#      app, the read-back IS the proof a write landed.
#   4. NO HARD REMOVAL. See above.
#   5. ORDER IS WRITTEN, NEVER NUDGED. No endpoint shifts a sibling by ±1. A reorder submits the
#      COMPLETE desired sequence and the server rewrites the whole set; an archive rewrites the
#      remaining siblings contiguous. This deletes the entire class of defect in fact 15 rather
#      than porting it. (Rows already holding their target value are not re-written — the final
#      state is what "rewrites the whole set" means, and a no-op write on one of Bruce's real
#      rows buys nothing.)
#   6. ARCHIVE AND RESTORE ARE SYMMETRIC. Every archive endpoint has a restore endpoint.
#
# THE ARCHIVE MIRROR (spec_04 §3.8) — DECLARED, TEMPORARY, ROUND 08 REMOVES IT
#   `active` is the authority. The Forms app cannot see it and reads order == -1 (fact 4). So
#   every archive here writes BOTH — active False AND order -1 — and every restore clears both,
#   in the SAME call, never as a follow-up request and never by a client. _archive_state()
#   returns the pair so the two can never drift apart in one place and not the other.
#
# MONEY — INTEGER CENTS, AND NEVER A MULTIPLY (spec_04 §0.1, §4.3)
#   budgets.budget_amount ALREADY HOLDS CENTS (Sub_category:96 does `text * 100` on save; every
#   display site divides by 100). So the wire conversion is a TYPE cast — int(round(stored)) —
#   and NEVER a multiply by 100. A stray *100 at a boundary inflates every figure in the app
#   100x. No float arithmetic is performed on money anywhere in this file; the only floats are
#   the progress meter's `fraction` / `over_ratio`, which are ratios, not amounts.
#
# THE SIGN RULE IS THE SERVER'S (fact 7, spec_04 §3.2)
#   /budget/amount stores abs(amount_cents) for a sub-category of the income category and
#   -abs(amount_cents) for anything else; 0 stays 0. The client's sign is never trusted. This is
#   the legacy `neg_pos` moved to where authority lives.
#
# THE INCOME CATEGORY — ONE PLACE, AND ROUND 08 REPLACES IT
#   _is_income_name() is the ONLY place the magic string appears in this module, and
#   _income_category_id() is the only place a category is identified as income. It mirrors
#   bxIncomeCategoryId exactly: the category whose TRIMMED name equals it CASE-INSENSITIVELY,
#   else None. (The legacy test is byte-exact, fact 6; §3.1 measurement 2 proved the widening
#   safe — exactly one live category matches and there are zero near-misses.) Round 08 replaces
#   the body of _income_category_id with a flag lookup and nothing else changes.
#
# GET /budget/summary IS THE VERIFICATION INSTRUMENT AND NOTHING ELSE (spec_04 §3.2, §4.4)
# - It is NOT on any interactive path. No client may call it; AC-13.1 asserts the budget screens
#   make exactly one data request per page open and this is not it.
# - It was written from the §4.4 / §4.5 / §4.5A / §4.6 prose, INDEPENDENTLY of bx_calc.js, which
#   was deliberately not read while it was written. A port would agree with itself while both
#   were wrong, and agreement between the two is the whole point of AC-5.4.
# - It is READ-ONLY and provably so: no function reachable from api_budget_summary contains a
#   row-add, row-update or row-removal call (AC-3.11).
# - It reads month M-1 for the pool AND every month of a sub-category's roll-over window for
#   `rollover`, which can be a year or more. An implementation that scoped its query to two
#   months would return carried_in: 0 everywhere and prove nothing. Every table is therefore
#   loaded ONCE and every figure computed from memory — no query per month, no query per row.
#
# TRANSFER EXCLUSION HAPPENS ON THE TRANSACTION SIDE (§3.1 measurement 3)
#   The sentinel ec8e0085-… IS a `categories` row (name Transfer, order -1, so legacy-archived)
#   and is NOT a `sub_categories` row; 12 transactions point straight at it. So a transaction is
#   a transfer when its `category` IS the sentinel, or names a sub-category that is the sentinel
#   or hangs off the sentinel category — the same test GET /build/budget-audit used to take the
#   round-start measurements, so the two instruments agree by construction.
#
# SIX ALIGNMENT RULINGS TAKEN BY THE ORCHESTRATOR, 2026-08-21 (spec_04 §12 addenda), on clauses
# where the spec was genuinely ambiguous and this module and bx_calc.js could each have picked a
# defensible side. All six are implemented here and each is commented at its own site:
#   1. an ARCHIVED CATEGORY contributes nothing to `totals` (but keeps its own figures in
#      categories[]) — build_summary's category loop;
#   2. ORPHANS reach the POOL but not the category roll-ups — §4.5A rule 3 enumerates its own
#      exclusions and orphans are not among them, so an orphan is an expense for pool purposes;
#   3. the transfer sentinel is excluded on the TRANSACTION side — _transfer_sub_ids;
#   4. `budget_present` carries the null/zero distinction and `budget_cents` is ALWAYS an int;
#   5. `over_fraction` is CLAMPED to [0, 1] on both meter tables while `over_ratio` stays
#      uncapped — _clamp01;
#   6. a duplicate (belongs_to, period) pair resolves to the SMALLEST cents value on the read
#      path — _budget_for.
#
# TWO DEFINITIONS THIS MODULE HAD TO CHOOSE — both flagged to the orchestrator for an addendum:
#   1. DUPLICATE (belongs_to, period) BUDGET PAIRS (fact 3). The write path REFUSES them (400,
#      nothing written) as §3.2 requires. The READ path cannot refuse, so it takes the SMALLEST
#      cents value of the pair — deterministic, never repaired, and identical to the rule
#      GET /build/budget-audit already used for the round-start measurements. §3.1 measurement 5
#      found zero live duplicates, so no live figure depends on the choice.
#   2. "A MONTH WITH NO DATA -> 200 with zero-filled totals and EMPTY ARRAYS" (§3.2, AC-5.12).
#      A month holding no budget row and no active non-transfer transaction returns empty
#      sub_categories[] and categories[]; any month with data lists EVERY sub-category and
#      EVERY category row, flagged. `available` is always the full thirteen-field object, as
#      §3.2 requires, because it reads M-1 and prev_month_has_data says why its figures are 0.

import anvil.server
from anvil.tables import app_tables

import hashlib
import json
import re
import traceback
import uuid
from datetime import date, datetime, timezone

MODULE_VERSION = "v1"

# The Transfer sentinel. A `categories` row on this app, not a `sub_categories` row, and a
# transaction may carry it directly as its `category`. A plain string constant is not a table
# access, so it is safe at module level.
TRANSFER_CATEGORY_ID = "ec8e0085-8408-43a2-953f-ebba24549d96"

# The legacy archive sentinel (fact 4). Written as the §3.8 mirror alongside `active`, and
# removed at round 08 when the Forms app stops serving.
ARCHIVED_ORDER = -1

# Name bounds, after trimming (spec_04 §3.2).
NAME_MIN = 3
NAME_MAX = 40

# A defensive bound on the §4.5 branch-D rollover walk. A roll_over_date a century in the past
# is a data defect, not a plan; without a bound one such row walks the endpoint into a timeout.
# 1200 months = 100 years, far beyond any real window, and the same cap GET /build/budget-audit
# applies. `months` is still REPORTED uncapped — only the walk is bounded.
MAX_ROLLOVER_MONTHS = 1200

# Rule 2 — the whitelists. `category_id`, `sub_category_id`, `order` and `active` are ABSENT
# deliberately: rule 1 reserves all four to the server.
CAT_ACCEPTED_FIELDS = ("name", "colour_back", "colour_text")
SUB_ACCEPTED_FIELDS = ("name", "icon", "roll_over", "roll_over_date", "belongs_to")

_TOKEN_RE = re.compile(r"^[0-9a-f]{64}$")
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COLOUR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ApiError(Exception):
    """An HTTP status, a short machine-readable code, and an optional field-level detail.

    `detail` names a FIELD and a reason and NEVER echoes a caller-supplied value — a value in an
    error body is an echo channel (spec_04 §4.7).
    """

    def __init__(self, status, code, detail=None):
        super().__init__("%s:%s" % (status, code))
        self.status = int(status)
        self.code = str(code)
        self.detail = None if detail is None else str(detail)


def _bad_request(detail):
    return ApiError(400, "bad_request", detail)


def _not_found():
    return ApiError(404, "not_found")


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
    # dict.__setitem__ rather than bracketed assignment — see the DESIGN NOTES. Behaviour is
    # identical to the assignment form proven in S01.
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


def _request_json():
    """The POST body as a dict, or ApiError(400) — never a 500."""
    try:
        body = anvil.server.request.body_json
    except Exception:
        raise _bad_request("body: must be a JSON object")
    if not isinstance(body, dict):
        raise _bad_request("body: must be a JSON object")
    return body


def api_http(path, methods=("GET",)):
    """Wraps @anvil.server.http_endpoint with uniform JSON encoding and error mapping.

    The body never contains a traceback, a stack frame, a module path or a table name; the
    traceback is printed so it reaches the Anvil app logs instead. A 400 additionally carries
    `detail`; a 401 and a 404 carry NO data key of any kind (spec_04 §3.2's error table).
    """

    def decorator(fn):
        @anvil.server.http_endpoint(path, methods=list(methods))
        def wrapper(*args, **kwargs):
            try:
                return _json_response(200, fn(*args, **kwargs))
            except ApiError as err:
                body = {"ok": False, "error": err.code}
                if err.detail is not None:
                    body = {"ok": False, "error": err.code, "detail": err.detail}
                return _json_response(err.status, body)
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
    """The authenticated users row. Called explicitly inside each handler body, never relied on
    through decorator ordering."""
    return require_session()["user"]


# =============================================================================================
# PURE HELPERS. Everything from here to the "TABLE ACCESS" banner takes plain mappings and
# returns plain JSON types, so it runs — and is tested — without Anvil or a database. An Anvil
# Row and a dict index the same way, which is how S02 and S03 tested their serialisers.
# =============================================================================================


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
    """A JSON number. Whole floats collapse to int so the payload reads 1, not 1.0. A bool is
    not a number here."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _cents(value, default=0):
    """A stored money column as integer cents.

    A TYPE cast, not a SCALE conversion — the column already holds cents. NEVER multiply by 100.
    A non-integral stored value is a pre-existing data defect (fact 11): it is rounded here, and
    the caller collects the row so the round can list it.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return int(round(value))


def _is_integral(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        return value.is_integer()
    return True


def _iso_date(value):
    """A date column as ISO YYYY-MM-DD, or null. datetime subclasses date, so it is tested
    first."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else None


def _month_index(year, month):
    return year * 12 + (month - 1)


def _month_key(year, month):
    return "%04d-%02d" % (year, month)


def _month_from_index(index):
    return (index // 12, index % 12 + 1)


def _month_key_from_index(index):
    return _month_key(*_month_from_index(index))


def _split_month(month_key):
    """"YYYY-MM" (or a longer ISO string) -> (year, month), or None."""
    if not isinstance(month_key, str) or len(month_key) < 7:
        return None
    try:
        year, month = int(month_key[0:4]), int(month_key[5:7])
    except ValueError:
        return None
    if month < 1 or month > 12:
        return None
    return (year, month)


def _month_of_stored(value):
    """The "YYYY-MM" of a stored date/datetime column, or None."""
    iso = _iso_date(value)
    return None if iso is None or len(iso) < 7 else iso[0:7]


def _bump(counter, key, delta=1):
    """Accumulate into a plain dict WITHOUT a subscript assignment — see the DESIGN NOTES."""
    counter.__setitem__(key, counter.get(key, 0) + delta)


def _collect(store, key, value):
    """Append into a dict-of-lists WITHOUT a subscript assignment."""
    store.setdefault(key, []).append(value)


def _is_income_name(name):
    """The ONLY place the magic income name appears in this module (fact 6).

    Trimmed, case-insensitive — mirroring bxIncomeCategoryId. Round 08 replaces this and
    _income_category_id with a flag lookup.
    """
    return _text(name).strip().lower() == "income"


# --- the active flag -------------------------------------------------------------------------


def _active_readable(rows):
    """Whether the `active` column can be read at all on this table — decided ONCE per call.

    Presence is a property of the SCHEMA, not of a row: rediscovering it per row costs a server
    round trip PER ROW (ServerAppData v2's DESIGN NOTES measured 3–4 ms each over 1,300 rows).
    Up to three rows are tried and ANY success means readable; an empty set is readable by
    definition. The bias toward True is deliberate — a transient failure on one row must not be
    mistaken for "no such column", because that answer reports an archived row as active.

    It is NEVER cached across calls: a cached "missing" would survive Bruce's migrate click
    inside a warm server process and go on hiding rows after the column existed.
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
    return True


def _active_raw(row, readable=True):
    """The raw `active` column: True, False or None (column absent, or never set)."""
    if not readable:
        return None
    try:
        value = row["active"]
    except Exception:
        return None
    return value if value is True or value is False else None


def is_active(row, readable=True):
    """The active test, in ONE place so it cannot drift: `is not False` — NEVER `is True`.

    None means "the column is not there yet, or this legacy row was never touched", and both
    mean active. After §3.7's initialisation every row on both tables carries a real boolean.
    """
    return _active_raw(row, readable) is not False


# --- serialisation (spec_04 §4.2, §4.3) -------------------------------------------------------


def serialise_category(row, readable=True):
    """The §4.2 category object — exactly these six keys, no extras, no omissions."""
    return {
        "category_id": _text(_get(row, "category_id")),
        "name": _text(_get(row, "name")),
        "colour_back": _text(_get(row, "colour_back")),
        "colour_text": _text(_get(row, "colour_text")),
        "order": _number(_get(row, "order")),
        "active": is_active(row, readable),
    }


def serialise_sub_category(row, readable=True):
    """The §4.2 sub-category object — exactly these eight keys, no extras, no omissions."""
    return {
        "sub_category_id": _text(_get(row, "sub_category_id")),
        "name": _text(_get(row, "name")),
        "icon": _text_or_none(_get(row, "icon")),
        "belongs_to": _text(_get(row, "belongs_to")),
        "order": _number(_get(row, "order")),
        "roll_over": bool(_get(row, "roll_over", False)),
        "roll_over_date": _iso_date(_get(row, "roll_over_date")),
        "active": is_active(row, readable),
    }


def serialise_budget(row, anomalies=None):
    """The §4.3 budget object — exactly these four keys.

    The legacy column names belongs_to / period / budget_amount never appear on the wire.
    `amount_cents` is int(round(stored)) — a TYPE cast; the column already holds cents. A
    non-integral stored value or a period that is not the first of a month is collected in
    `anomalies` so the round can list it, and no key is added to the payload for either.
    """
    sub_category_id = _text(_get(row, "belongs_to"))
    stored_amount = _get(row, "budget_amount", 0)
    stored_period = _get(row, "period")
    iso = _iso_date(stored_period)
    month = "" if iso is None else iso[0:7]
    if anomalies is not None:
        if not _is_integral(stored_amount):
            _collect(anomalies, "non_integral_amount", (sub_category_id, month, stored_amount))
        if iso is not None and iso[8:10] != "01":
            _collect(anomalies, "period_not_first_of_month", (sub_category_id, iso))
        if iso is None:
            _collect(anomalies, "period_missing", (sub_category_id, None))
    return {
        "sub_category_id": sub_category_id,
        "month": month,
        "amount_cents": _cents(stored_amount),
        "notes": _text(_get(row, "notes")),
    }


def _order_sort_key(row):
    """Sort by the `order` column with None LAST — the tie-break ServerAppData already uses."""
    value = _get(row, "order")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return (1, 0.0)
    return (0, float(value))


def _category_sort_key(row):
    return (_order_sort_key(row), _text(_get(row, "name")).lower(),
            _text(_get(row, "category_id")))


def _sub_category_sort_key(row):
    return (_order_sort_key(row), _text(_get(row, "name")).lower(),
            _text(_get(row, "sub_category_id")))


def _budget_sort_key(obj):
    """§4.3 row order: month ascending, then sub_category_id ascending — a total order, so two
    calls are diffable."""
    return (obj["month"], obj["sub_category_id"])


def _income_category_id(categories):
    """The category_id of the income category, or None. THE ONLY PLACE income is identified.

    Mirrors bxIncomeCategoryId: trimmed name, case-insensitive. Archived rows are NOT excluded —
    the definition in §3.3 has no active clause, and the live income category is active anyway
    (§3.1 measurement 2: exactly one match, zero near-misses). If more than one row somehow
    matched, the first in the module's standard order wins, so the answer is deterministic.
    """
    matches = [r for r in categories if _is_income_name(_get(r, "name"))]
    if not matches:
        return None
    return _text(_get(sorted(matches, key=_category_sort_key)[0], "category_id"))


# --- validation (pure; the two that need the database take their id sets as arguments) --------


def _require_id(value, field):
    if not isinstance(value, str) or not value.strip():
        raise _bad_request("%s: must be a non-empty string" % field)
    return value.strip()


def _validate_month(value, field="month"):
    """"YYYY-MM" -> (year, month). Unknown or malformed -> 400, never a 500 and never a 404."""
    if not isinstance(value, str) or not _MONTH_RE.match(value):
        raise _bad_request("%s: must be YYYY-MM" % field)
    parsed = _split_month(value)
    if parsed is None:
        raise _bad_request("%s: must be a real calendar month" % field)
    return parsed


def _validate_amount_cents(value):
    """An INTEGER number of cents. Stricter than ServerTxn's, deliberately: §3.2 says a float,
    a string or a null is a 400, because fact 11 is how float cents got into this very table."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise _bad_request("amount_cents: must be an integer")
    return int(value)


def _validate_colour(value, field):
    if not isinstance(value, str) or not _COLOUR_RE.match(value.strip()):
        raise _bad_request("%s: must be #RRGGBB" % field)
    return value.strip()


def _validate_name(value, field="name"):
    """Trimmed FIRST, then length-tested — AC-3.2 requires the trim to precede both tests."""
    if not isinstance(value, str):
        raise _bad_request("%s: must be a string" % field)
    trimmed = value.strip()
    if len(trimmed) < NAME_MIN:
        raise _bad_request("%s: must be at least %d characters after trimming"
                           % (field, NAME_MIN))
    if len(trimmed) > NAME_MAX:
        raise _bad_request("%s: must be at most %d characters after trimming"
                           % (field, NAME_MAX))
    return trimmed


def _reject_duplicate_name(trimmed, existing_names, field="name"):
    """`existing_names` is the set of TRIMMED, LOWER-CASED names already taken by non-archived
    peers, with the row being edited removed by the caller."""
    if trimmed.strip().lower() in existing_names:
        raise _bad_request("%s: already used by another non-archived record" % field)
    return trimmed


def _validate_roll_over_date(value, field="roll_over_date"):
    """None, "YYYY-MM" or "YYYY-MM-DD" -> a date or None.

    §3.2 types the wire field "YYYY-MM|null", but §4.2 SERIALISES the stored column as
    YYYY-MM-DD, so a client that reads a row and writes it straight back would otherwise be
    rejected by its own payload. Both spellings are therefore accepted; a month is stored as the
    first of that month, which is the shape every live row already has. Flagged to the
    orchestrator as a §3.2/§4.2 mismatch.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise _bad_request("%s: must be YYYY-MM, YYYY-MM-DD or null" % field)
    text = value.strip()
    if _MONTH_RE.match(text):
        year, month = _split_month(text)
        return date(year, month, 1)
    if _DAY_RE.match(text):
        try:
            return date(int(text[0:4]), int(text[5:7]), int(text[8:10]))
        except ValueError:
            raise _bad_request("%s: must be a real calendar date" % field)
    raise _bad_request("%s: must be YYYY-MM, YYYY-MM-DD or null" % field)


def _validate_sequence(submitted, expected_ids, field="order"):
    """The complete-set rule (write rule 5), in one place.

    The submitted list must be EXACTLY the set of ids given — no additions, no omissions, no
    duplicates, all strings. Anything else is a 400 and NOTHING is written. The detail names the
    failure and never echoes an id.
    """
    if not isinstance(submitted, list):
        raise _bad_request("%s: must be a list of ids" % field)
    cleaned = []
    for item in submitted:
        if not isinstance(item, str) or not item.strip():
            raise _bad_request("%s: every entry must be a non-empty string" % field)
        cleaned.append(item.strip())
    if len(set(cleaned)) != len(cleaned):
        raise _bad_request("%s: contains a repeated id" % field)
    if set(cleaned) != set(expected_ids):
        raise _bad_request(
            "%s: must be exactly the complete set of non-archived ids (%d expected, %d supplied)"
            % (field, len(set(expected_ids)), len(cleaned)))
    return cleaned


def _accepted(fields, whitelist, field="fields"):
    """Rule 2 in one place: read ONLY the whitelisted keys. Unknown keys are dropped here and
    are silently ignored — including any id or order, which rule 1 reserves to the server."""
    if not isinstance(fields, dict):
        raise _bad_request("%s: must be an object" % field)
    supplied = {key: fields[key] for key in whitelist if key in fields}
    if not supplied:
        raise _bad_request("%s: no accepted field supplied" % field)
    return supplied


# =============================================================================================
# §4.5 / §4.5A / §4.6 — THE ARITHMETIC.
#
# Written from the spec prose, independently of bx_calc.js (see the DESIGN NOTES). Integer cents
# throughout; the only floats are the meter's ratios. Everything here is pure over plain
# indexes, so the whole of /budget/summary is testable off-platform and provably read-only.
# =============================================================================================


def _budget_for(budget_index, sub_category_id, month_key):
    """The stored cents for (S, month), or None when there is no row.

    A duplicate (belongs_to, period) pair (fact 3) resolves to the SMALLEST value — deterministic
    and never repaired. The write path refuses to touch such a pair at all.
    """
    values = budget_index.get((sub_category_id, month_key))
    if not values:
        return None
    return min(values)


def _spend_for(spend_index, sub_category_id, month_key):
    """The month's actual for S, in integer cents, transfers already excluded upstream."""
    return spend_index.get((sub_category_id, month_key), 0)


def rollover(sub_category_id, is_income, roll_over, roll_over_start, budget_index, spend_index,
             year, month):
    """The §4.5 object — ALL NINE FIELDS, on every branch.

    `roll_over_start` is (year, month) or None. Branch order: income FIRST, because §4.5's
    closing rule splits `remaining` from `overspent` on the assumption that expense figures are
    stored NEGATIVE; applied to income's positive figures it would report an under-earning line
    as "overspent", which §4.5A rule 4 forbids and which the shortfall reports under its own
    name. The legacy left this branch as `pass  # what do we actually do here???` (fact 13).
    """
    month_key = _month_key(year, month)
    month_budget = _budget_for(budget_index, sub_category_id, month_key)
    month_budget = 0 if month_budget is None else month_budget
    spent = _spend_for(spend_index, sub_category_id, month_key)

    if is_income:
        # Branch C — income does not carry, and no number is invented for it.
        available = month_budget
        return {
            "supported": False, "start_missing": False, "months": 0, "carried_in": 0,
            "month_budget": month_budget, "available": available, "spent": spent,
            "remaining": available - spent, "overspent": 0,
        }

    if not roll_over:
        # Branch A.
        return _rollover_close(0, month_budget, spent, supported=True, start_missing=False,
                               months=0)
    if roll_over_start is None:
        # Branch B — a DEFINED state, not a crash (fact 14).
        return _rollover_close(0, month_budget, spent, supported=True, start_missing=True,
                               months=0)

    # Branch D — walk every month of the window, D .. M-1.
    target_index = _month_index(year, month)
    start_index = _month_index(roll_over_start[0], roll_over_start[1])
    months = max(0, target_index - start_index)
    walk_from = max(start_index, target_index - MAX_ROLLOVER_MONTHS)
    carried = 0
    for index in range(walk_from, target_index):
        key = _month_key_from_index(index)
        budget_p = _budget_for(budget_index, sub_category_id, key)
        budget_p = 0 if budget_p is None else budget_p
        available_p = carried + budget_p
        remaining_p = available_p - _spend_for(spend_index, sub_category_id, key)
        carried = remaining_p if remaining_p <= 0 else 0
    return _rollover_close(carried, month_budget, spent, supported=True, start_missing=False,
                           months=months)


def _rollover_close(carried_in, month_budget, spent, supported, start_missing, months):
    """The §4.5 closing rule, applied on every non-income branch.

        available = carried_in + month_budget
        raw       = available - spent
        overspent = raw if raw > 0 else 0
        remaining = 0   if raw > 0 else raw

    Expense budgets and actuals are stored NEGATIVE, which is why a POSITIVE `raw` is the
    overspend: it is the amount by which the (negative) spend has passed the (negative) pot.
    `carried` clamps at 0 on the way in, so no category ever carries a debt — and the clamped-off
    amount is returned as `overspent` rather than discarded (fact 12, §0 ruling 5). It is
    accounted for one level up, in §4.5A's month pool.
    """
    available = carried_in + month_budget
    raw = available - spent
    return {
        "supported": bool(supported),
        "start_missing": bool(start_missing),
        "months": int(months),
        "carried_in": int(carried_in),
        "month_budget": int(month_budget),
        "available": int(available),
        "spent": int(spent),
        "remaining": 0 if raw > 0 else int(raw),
        "overspent": int(raw) if raw > 0 else 0,
    }


def progress(budget_cents, actual_cents, is_income):
    """The §4.6 meter. `budget_cents` is None when there is no budget row.

    `fraction` and `over_fraction` are capped at 1 for layout; `over_ratio` is UNCAPPED (or null
    when the state is not `over`), which is what makes a 3x and a 30x overspend distinguishable —
    the legacy's saturated third branch was not (fact 16). Guards are evaluated in the spec's
    order and the first match wins; the ordering is load-bearing in both tables.
    """
    if is_income:
        return _progress_income(budget_cents, actual_cents)
    return _progress_expense(budget_cents, actual_cents)


def _clamp01(value):
    """§4.6's "capped at 1 for layout", read as a CLAMP rather than a one-sided cap.

    Taken literally, min(ratio, 1) on income row 7 with an anomalous NEGATIVE target yields
    -1 — which is not a cap and would drive a meter backwards. `over_ratio` stays uncapped and
    may be negative on such an input; it is the diagnostic value. §3.1 measurement 11 found zero
    sign anomalies live, so nothing reachable hits this today. (Orchestrator ruling, spec_04 §12
    addendum, 2026-08-21.)
    """
    return max(0, min(value, 1))


def _meter(state, fraction, over_fraction, over_ratio, label_cents, label_kind):
    return {
        "state": state,
        "fraction": fraction,
        "over_fraction": over_fraction,
        "over_ratio": over_ratio,
        "label_cents": int(label_cents),
        "label_kind": label_kind,
    }


def _progress_expense(budget, actual):
    if budget is None:                                                          # row 1
        return _meter("none", 0, 0, None, abs(actual),
                      "over" if actual < 0 else "remaining")
    if actual > 0:                                                              # row 2 — refund
        return _meter("under", 0, 0, None, abs(budget) + actual, "remaining")
    if budget == 0 and actual == 0:                                             # row 3
        return _meter("none", 0, 0, None, 0, "remaining")
    if budget == 0 and actual < 0:                                              # row 4
        return _meter("over", 1, 1, None, abs(actual), "over")
    b, s = abs(budget), abs(actual)
    if s < b:                                                                   # row 5
        return _meter("under", s / b, 0, None, b - s, "remaining")
    if s == b:                                                                  # row 6
        return _meter("at", 1, 0, None, 0, "remaining")
    return _meter("over", 1, _clamp01((s - b) / b), (s - b) / b, s - b, "over")  # row 7


def _progress_income(budget, actual):
    t, e = budget, actual
    if t is None:                                                               # row 1
        return _meter("none", 0, 0, None, e, "earned")
    if t == 0 and e == 0:                                                       # row 2
        return _meter("none", 0, 0, None, 0, "short")
    if t == 0 and e > 0:                                                        # row 3
        return _meter("over", 1, 1, None, e, "earned")
    if e < 0:                                                                   # row 4 — reversal
        # Evaluated BEFORE `e < t` deliberately: any negative e also satisfies e < t for a
        # non-negative target, so a later reversal row could never fire — and e / t would then
        # hand back a NEGATIVE fraction, breaking the capped-for-layout contract.
        return _meter("under", 0, 0, None, t + abs(e), "short")
    if e < t:                                                                   # row 5
        return _meter("under", e / t, 0, None, t - e, "short")
    if e == t:                                                                  # row 6
        return _meter("at", 1, 0, None, 0, "short")
    return _meter("over", 1, _clamp01((e - t) / t), (e - t) / t, e - t, "earned")  # row 7


def overspend_for_month(sub_rows, budget_index, spend_index, income_category_id,
                        transfer_sub_ids, year, month):
    """§4.5A's `bxOverspend` twin: {total, by_sub}, positive magnitudes.

    The sum of rollover(...)["overspent"] over every ACTIVE, NON-TRANSFER, EXPENSE sub-category
    THAT HAS A BUDGET ROW for that month (§4.5A rule 3). Without that last clause an unbudgeted
    month makes every sub-category 100% overspent and wipes out the following month's pool.

    Underspend nets off NOTHING: only the positive `overspent` values are summed (rule 2).
    It is rollover-AWARE — a roll-over sub-category that blows its cumulative pot reaches the
    pool through the same field.
    """
    month_key = _month_key(year, month)
    by_sub = {}
    total = 0
    for sub in sub_rows:
        sub_id = sub["sub_category_id"]
        if not sub["active"] or sub_id in transfer_sub_ids:
            continue
        if income_category_id is not None and sub["belongs_to"] == income_category_id:
            continue
        if _budget_for(budget_index, sub_id, month_key) is None:
            continue
        result = rollover(sub_id, False, sub["roll_over"], sub["roll_over_start"],
                          budget_index, spend_index, year, month)
        if result["overspent"] > 0:
            by_sub.__setitem__(sub_id, result["overspent"])
            total += result["overspent"]
    return {"total": total, "by_sub": by_sub}


def income_shortfall_for_month(sub_rows, budget_index, spend_index, income_category_id,
                               transfer_sub_ids, year, month):
    """§4.5A's `bxIncomeShortfall` twin: {total, by_sub}, positive magnitudes.

    Per ACTIVE income sub-category THAT HAS a budget row for that month (rule 11),
    max(0, budget - actual), summed. The per-sub-category max(0, …) is what stops an income line
    that over-earns from offsetting one that falls short — the same no-netting rule as the
    expense side. The exact structural twin of overspend_for_month, because §0 ruling 6 makes
    them the same mechanism.
    """
    month_key = _month_key(year, month)
    by_sub = {}
    total = 0
    if income_category_id is None:
        return {"total": 0, "by_sub": by_sub}
    for sub in sub_rows:
        sub_id = sub["sub_category_id"]
        if not sub["active"] or sub_id in transfer_sub_ids:
            continue
        if sub["belongs_to"] != income_category_id:
            continue
        budget = _budget_for(budget_index, sub_id, month_key)
        if budget is None:
            continue
        short = budget - _spend_for(spend_index, sub_id, month_key)
        if short > 0:
            by_sub.__setitem__(sub_id, short)
            total += short
    return {"total": total, "by_sub": by_sub}


def available_to_budget(sub_rows, budget_index, spend_index, income_category_id,
                        transfer_sub_ids, month_has_data, year, month):
    """The §4.5A pool — the THIRTEEN-field object, always complete.

    §0 ruling 5 in arithmetic: no category ever carries a debt, and the overspend is not
    discarded either — it is deducted ONCE from the following month's pool, it does not chain,
    and underspend never nets it off. §0 ruling 6 makes an income shortfall the same mechanism,
    named separately.

    `income_planned` is the month's PLANNED income, IN FULL, whatever has actually arrived. It is
    NEVER built from actual receipts — late money is not lost money (rule 10), and this is the
    clause an implementation is most likely to "improve" away.

    `month_has_data` is a callable (year, month) -> bool, so rule 6's prev_month_has_data is
    answered from the same raw indexes as everything else.
    """
    month_str = _month_key(year, month)
    prev_index = _month_index(year, month) - 1
    prev_year, prev_month = _month_from_index(prev_index)

    income_planned = 0
    assigned = 0
    for sub in sub_rows:
        sub_id = sub["sub_category_id"]
        if not sub["active"] or sub_id in transfer_sub_ids:
            continue
        amount = _budget_for(budget_index, sub_id, month_str)
        if amount is None:
            # Rule 9: a sub-category with no budget row is UNBUDGETED, not budgeted at zero.
            continue
        if income_category_id is not None and sub["belongs_to"] == income_category_id:
            # max(0, …): a pre-existing negative income budget row would silently make the whole
            # pool wrong while every internal comparison stayed self-consistent (fact 7 only ran
            # on a legacy save). §3.1 measurement 11 found none live; the guard stays.
            income_planned += max(0, amount)
        else:
            assigned += abs(amount)

    over = overspend_for_month(sub_rows, budget_index, spend_index, income_category_id,
                               transfer_sub_ids, prev_year, prev_month)
    short = income_shortfall_for_month(sub_rows, budget_index, spend_index, income_category_id,
                                       transfer_sub_ids, prev_year, prev_month)
    carried_total = over["total"] + short["total"]
    starting_available = income_planned - carried_total
    return {
        "month": month_str,
        "prev_month": _month_key(prev_year, prev_month),
        "prev_month_has_data": bool(month_has_data(prev_year, prev_month)),
        "income_category": income_category_id is not None,
        "income_planned": int(income_planned),
        "carried_overspend": int(over["total"]),
        "carried_shortfall": int(short["total"]),
        "carried_total": int(carried_total),
        "starting_available": int(starting_available),
        "assigned": int(assigned),
        # May be NEGATIVE, and that is a real state, not an error (rule 5). Never clamped.
        "unassigned": int(starting_available - assigned),
        "overspend_by_sub": dict(over["by_sub"]),
        "shortfall_by_sub": dict(short["by_sub"]),
    }


# --- the summary payload ----------------------------------------------------------------------


def transfer_sub_ids(sub_rows_raw, sentinel=TRANSFER_CATEGORY_ID):
    """Sub-category ids that are transfer rows: the sentinel itself, or anything hanging off the
    sentinel CATEGORY.

    §3.1 measurement 3 found NEITHER live — the sentinel is a `categories` row with no children
    — which is exactly why the exclusion that actually bites happens on the TRANSACTION side: a
    transaction whose `category` is the sentinel is dropped from every spend figure by
    build_spend_index. The sentinel is a parameter rather than only the module constant so the
    golden runner can drive it, mirroring bx_calc.js's `transferCategoryId` argument.
    """
    ids = {sentinel}
    for row in sub_rows_raw:
        sub_id = _text(_get(row, "sub_category_id"))
        if sub_id == sentinel or _text(_get(row, "belongs_to")) == sentinel:
            ids.add(sub_id)
    return ids


def build_budget_index(budgets_raw, anomalies=None):
    """({(sub_category_id, "YYYY-MM"): [cents, ...]}, {months present}).

    A LIST per key, not a value: a duplicate (belongs_to, period) pair (fact 3) is preserved
    here and resolved by _budget_for, so the resolution rule lives in exactly one place.
    """
    index = {}
    months = set()
    for row in budgets_raw:
        sub_id = _text(_get(row, "belongs_to"))
        key = _month_of_stored(_get(row, "period"))
        if key is None:
            if anomalies is not None:
                _collect(anomalies, "budget_period_missing", sub_id)
            continue
        stored = _get(row, "budget_amount", 0)
        if anomalies is not None and not _is_integral(stored):
            _collect(anomalies, "non_integral_budget", (sub_id, key, stored))
        _collect(index, (sub_id, key), _cents(stored))
        months.add(key)
    return index, months


def build_spend_index(transactions_raw, transfer_subs, readable=True):
    """({(sub_category_id, "YYYY-MM"): cents}, {months holding a non-transfer transaction}).

    Archived transactions are excluded — the clients only ever receive the active set, so a
    figure computed here from the inactive ones could never be reproduced client-side.
    Transfers are excluded from every `spent` figure (§4.5), on the TRANSACTION side.
    """
    index = {}
    months = set()
    for row in transactions_raw:
        if not is_active(row, readable):
            continue
        category = _text(_get(row, "category"))
        key = _month_of_stored(_get(row, "date"))
        if key is None or category in transfer_subs:
            continue
        months.add(key)
        _bump(index, (category, key), _cents(_get(row, "amount", 0)))
    return index, months


def apply_sign(is_income, amount_cents):
    """The `neg_pos` sign rule (fact 7), moved to where authority lives.

    Income -> abs, everything else -> -abs, and 0 stays 0. The client's sign is NEVER trusted;
    /budget/amount calls this on every write.
    """
    if amount_cents == 0:
        return 0
    return abs(amount_cents) if is_income else -abs(amount_cents)


def _project_sub(row, readable):
    """A sub-category reduced to what the arithmetic needs — a plain dict, so every function
    above runs off-platform against fixtures."""
    start = _iso_date(_get(row, "roll_over_date"))
    parsed = None if start is None else _split_month(start)
    return {
        "sub_category_id": _text(_get(row, "sub_category_id")),
        "belongs_to": _text(_get(row, "belongs_to")),
        "active": is_active(row, readable),
        "roll_over": bool(_get(row, "roll_over", False)),
        "roll_over_start": parsed,
    }


def build_summary(categories_raw, sub_categories_raw, budgets_raw, transactions_raw, month_key,
                  cat_readable=True, sub_readable=True, txn_readable=True, anomalies=None):
    """GET /budget/summary's whole body (§4.4), computed from raw rows.

    Pure over plain mappings and therefore READ-ONLY BY CONSTRUCTION: nothing reachable from
    here can write, which is half of AC-3.11's proof (the other half is the AST walk).

    Every table is walked ONCE into an index; the rollover window walk and the M-1 pool then run
    entirely in memory. Scoping the query to two months would return carried_in: 0 everywhere.
    """
    parsed = _split_month(month_key)
    year, month = parsed

    income_id = _income_category_id(categories_raw)
    transfer_subs = transfer_sub_ids(sub_categories_raw)
    sub_rows = [_project_sub(r, sub_readable) for r in sub_categories_raw]
    category_ids = {_text(_get(r, "category_id")) for r in categories_raw}

    # --- indexes: every table walked ONCE, then all arithmetic runs in memory -------------------
    budget_index, budget_months = build_budget_index(budgets_raw, anomalies)
    spend_index, txn_months = build_spend_index(transactions_raw, transfer_subs, txn_readable)

    def month_has_data(y, m):
        key = _month_key(y, m)
        return key in budget_months or key in txn_months

    available = available_to_budget(sub_rows, budget_index, spend_index, income_id,
                                    transfer_subs, month_has_data, year, month)

    if not month_has_data(year, month):
        # §3.2: a month with no data is a 200 with zero-filled totals and EMPTY arrays — never a
        # 404 — and `available` is still the full thirteen-field object, with prev_month_has_data
        # saying why its figures are zero.
        zero = {"budget_cents": 0, "actual_cents": 0, "variance_cents": 0}
        return {
            "ok": True,
            "month": month_key,
            "income_category_id": income_id,
            "sub_categories": [],
            "categories": [],
            "totals": {"income": dict(zero), "expense": dict(zero)},
            "available": available,
            "excluded": {"transfers": 0, "archived_sub_categories": 0, "orphans": 0},
        }

    # --- per sub-category ----------------------------------------------------------------------
    # ROW ORDER IS `sub_category_id` ASCENDING, and `category_id` ascending below. §4.4 does not
    # state one, so it is chosen to be a TOTAL order (ids are unique) and therefore diffable —
    # and to match the two independent implementations this endpoint is compared against, so a
    # three-way diff shows arithmetic disagreements rather than sort noise. It is deliberately
    # NOT the bootstrap's (order, name, id) display order: the summary is an instrument, not a
    # render list, and `order` moves under a reorder while an id does not.
    ordered_subs = sorted(sub_categories_raw,
                          key=lambda r: _text(_get(r, "sub_category_id")))
    projected = {s["sub_category_id"]: s for s in sub_rows}
    sub_payload = []
    cat_totals = {}
    excluded_archived = 0
    excluded_orphans = 0
    excluded_transfers = 0
    for raw in ordered_subs:
        sub_id = _text(_get(raw, "sub_category_id"))
        sub = projected[sub_id]
        is_income = income_id is not None and sub["belongs_to"] == income_id
        budget = _budget_for(budget_index, sub_id, month_key)
        actual = _spend_for(spend_index, sub_id, month_key)
        budget_cents = 0 if budget is None else budget
        sub_payload.append({
            "sub_category_id": sub_id,
            "belongs_to": sub["belongs_to"],
            "active": sub["active"],
            "budget_cents": int(budget_cents),
            "budget_present": budget is not None,
            "actual_cents": int(actual),
            "variance_cents": int(actual - budget_cents),
            "rollover": rollover(sub_id, is_income, sub["roll_over"], sub["roll_over_start"],
                                 budget_index, spend_index, year, month),
            "progress": progress(budget, actual, is_income),
        })
        # The rollups exclude archived rows (fact 5 is a defect, not a convention), transfer
        # rows, and orphans — and `excluded` counts each, so a reviewer sees what was dropped
        # rather than inferring it from a difference.
        if not sub["active"]:
            excluded_archived += 1
            continue
        if sub_id in transfer_subs:
            excluded_transfers += 1
            continue
        if sub["belongs_to"] not in category_ids:
            excluded_orphans += 1
            continue
        bucket = cat_totals.setdefault(sub["belongs_to"], {"budget": 0, "actual": 0})
        bucket.__setitem__("budget", bucket["budget"] + budget_cents)
        bucket.__setitem__("actual", bucket["actual"] + actual)

    # --- per category and the two header totals -------------------------------------------------
    cat_payload = []
    income_totals = {"budget": 0, "actual": 0}
    expense_totals = {"budget": 0, "actual": 0}
    for raw in sorted(categories_raw, key=lambda r: _text(_get(r, "category_id"))):
        cat_id = _text(_get(raw, "category_id"))
        cat_active = is_active(raw, cat_readable)
        if cat_id == TRANSFER_CATEGORY_ID:
            # The transfer sentinel is not a spending category and is not listed at all. §4.4
            # excludes "transfer-sentinel rows" from categories[] and totals; on this app the
            # sentinel IS a categories row (§3.1 measurement 3), so that clause bites here.
            continue
        bucket = cat_totals.get(cat_id, {"budget": 0, "actual": 0})
        cat_payload.append({
            "category_id": cat_id,
            "active": cat_active,
            "budget_cents": int(bucket["budget"]),
            "actual_cents": int(bucket["actual"]),
            "variance_cents": int(bucket["actual"] - bucket["budget"]),
        })
        if not cat_active:
            # An ARCHIVED CATEGORY contributes nothing to the header totals (§3.9: "Archived
            # categories and sub-categories are hidden by default and excluded from every
            # total", fact 5). §4.4 names only archived SUB-categories, transfers and orphans,
            # which is why this is stated explicitly rather than inferred. It is a live-
            # reachable state, not a fixture artefact: /cat/archive deliberately leaves the
            # sub-categories active: true, so an archived category can hold active children
            # with real budgets and real spend. The category's OWN figures are still emitted
            # above — the "Archived (n)" affordance needs them; only the roll-up excludes it.
            # (Orchestrator ruling, spec_04 §12 addendum, 2026-08-21.)
            continue
        target = income_totals if (income_id is not None and cat_id == income_id) \
            else expense_totals
        target.__setitem__("budget", target["budget"] + bucket["budget"])
        target.__setitem__("actual", target["actual"] + bucket["actual"])

    return {
        "ok": True,
        "month": month_key,
        "income_category_id": income_id,
        "sub_categories": sub_payload,
        "categories": cat_payload,
        "totals": {
            "income": {"budget_cents": int(income_totals["budget"]),
                       "actual_cents": int(income_totals["actual"]),
                       "variance_cents": int(income_totals["actual"]
                                             - income_totals["budget"])},
            "expense": {"budget_cents": int(expense_totals["budget"]),
                        "actual_cents": int(expense_totals["actual"]),
                        "variance_cents": int(expense_totals["actual"]
                                              - expense_totals["budget"])},
        },
        "available": available,
        "excluded": {
            # ALL THREE COUNT SUB-CATEGORY ROWS dropped from categories[] and totals — the
            # symmetric reading, and the one the two implementations this endpoint is compared
            # against also took. NOTE that `transfers` is therefore structurally 0 on this app:
            # the sentinel is a `categories` row with no children (§3.1 measurement 3), so the
            # transfer exclusion that actually bites happens on the TRANSACTION side and is not
            # counted here. Flagged to the orchestrator for an addendum.
            "transfers": int(excluded_transfers),
            "archived_sub_categories": int(excluded_archived),
            "orphans": int(excluded_orphans),
        },
    }


def build_open_month_plan(budget_index_keys, sub_rows, from_key, to_key):
    """The ids a month-open would create rows for — the server's twin of bxOpenMonthPlan.

    Every ACTIVE sub-category that has a row in `from_key` and none in `to_key`. Archived rows
    are skipped (fact 2's other half, corrected), and a budget row whose sub-category no longer
    exists cannot be judged active, so it is skipped too.
    """
    have_from = {sub_id for (sub_id, key) in budget_index_keys if key == from_key}
    have_to = {sub_id for (sub_id, key) in budget_index_keys if key == to_key}
    return sorted(
        sub["sub_category_id"] for sub in sub_rows
        if sub["active"]
        and sub["sub_category_id"] in have_from
        and sub["sub_category_id"] not in have_to
    )


# =============================================================================================
# TABLE ACCESS. Everything below this line touches the database and nothing above it does.
# =============================================================================================


def _report_anomalies(anomalies):
    """Pre-existing data defects worth knowing about go to the Anvil app log — never into a
    payload, whose key-set is frozen."""
    for kind, items in (anomalies or {}).items():
        for item in items:
            print("ServerBudget: %s %r" % (kind, item))


def _load_categories():
    rows = list(app_tables.categories.search())
    return rows, _active_readable(rows)


def _load_sub_categories():
    rows = list(app_tables.sub_categories.search())
    return rows, _active_readable(rows)


def _category_handle(category_id):
    """The handle a write goes through — obtained via search(), deliberately a DIFFERENT query
    method from the read-back's get(), so the read-back cannot be served from the same cached
    handle. Anvil Row handles cache per handle."""
    for row in app_tables.categories.search(category_id=category_id):
        return row
    return None


def _sub_category_handle(sub_category_id):
    for row in app_tables.sub_categories.search(sub_category_id=sub_category_id):
        return row
    return None


def _read_back_category(category_id):
    """Rule 3 — an independent re-fetch through get(), after the write."""
    row = app_tables.categories.get(category_id=category_id)
    if row is None:
        raise _not_found()
    return serialise_category(row, _active_readable([row]))


def _read_back_sub_category(sub_category_id):
    row = app_tables.sub_categories.get(sub_category_id=sub_category_id)
    if row is None:
        raise _not_found()
    return serialise_sub_category(row, _active_readable([row]))


def _read_back_categories():
    """Rule 3 for a whole-set response: a FRESH search() after the writes, never the handles the
    writes went through. Returns the non-archived set, in stored order."""
    rows, readable = _load_categories()
    live = sorted([r for r in rows if is_active(r, readable)], key=_category_sort_key)
    return [serialise_category(r, readable) for r in live]


def _read_back_sub_categories(belongs_to):
    rows, readable = _load_sub_categories()
    live = sorted([r for r in rows
                   if is_active(r, readable) and _text(_get(r, "belongs_to")) == belongs_to],
                  key=_sub_category_sort_key)
    return [serialise_sub_category(r, readable) for r in live]


def _budget_rows_for(sub_category_id):
    """Every stored budget row for one sub-category, with its month key. One indexed search, not
    a scan of the table."""
    out = []
    for row in app_tables.budgets.search(belongs_to=sub_category_id):
        out.append((_month_of_stored(_get(row, "period")), row))
    return out


def _budget_matches(sub_category_id, month_key):
    return [row for key, row in _budget_rows_for(sub_category_id) if key == month_key]


def _read_back_budget(sub_category_id, month_key, period):
    """Rule 3 for a budget row. get() first — a genuinely independent fetch — with a fresh
    search() fallback in case the stored `period` does not compare equal to the date written
    (a datetime in a date column would do that). Both are independent of the write handle.
    """
    anomalies = {}
    row = None
    try:
        row = app_tables.budgets.get(belongs_to=sub_category_id, period=period)
    except Exception:
        traceback.print_exc()
        row = None
    if row is None:
        matches = _budget_matches(sub_category_id, month_key)
        if len(matches) != 1:
            raise _not_found()
        row = matches[0]
    payload = serialise_budget(row, anomalies)
    _report_anomalies(anomalies)
    return payload


def _existing_names(rows, readable, exclude_id=None, id_column="category_id"):
    """The TRIMMED, LOWER-CASED names already taken by non-archived peers."""
    return {
        _text(_get(r, "name")).strip().lower()
        for r in rows
        if is_active(r, readable) and _text(_get(r, id_column)) != exclude_id
    }


def _next_order(rows, readable, exclude_id=None, id_column="category_id"):
    """max(order among non-archived) + 1, or 0 when there are none."""
    values = [
        _number(_get(r, "order"), None) for r in rows
        if is_active(r, readable) and _text(_get(r, id_column)) != exclude_id
    ]
    numeric = [v for v in values if isinstance(v, (int, float))]
    return int(max(numeric)) + 1 if numeric else 0


def _archive_state(archived):
    """The §3.8 mirror, in ONE place so `active` and `order` can never drift apart.

    The order half is a DECLARED, TEMPORARY compatibility shim for the Forms app, which reads
    order == -1 as its archive signal and knows nothing about `active`. ROUND 08 REMOVES IT.
    """
    return {"active": False, "order": ARCHIVED_ORDER} if archived else {"active": True}


def _write_order(row, target):
    """Write rule 5's primitive: set an absolute position, never a ±1 nudge. A row already
    holding its target is left alone — the final state is what matters, and a no-op write on one
    of Bruce's real rows buys nothing."""
    if _number(_get(row, "order"), None) == target:
        return 0
    row.update(order=target)
    return 1


def _rewrite_category_order(rows, readable, income_id, requested=None):
    """Rewrite the WHOLE non-archived category sequence (write rule 5).

    Income is pinned to `order` 0 wherever it was submitted — the invariant the Forms app's own
    reorder depends on (Global.py:126-128's `count = -1` seed) — and the remainder are written
    1 … n. With no income category the sequence is written 0 … n-1 and everything else is
    identical. `requested` is the caller's complete id sequence, or None to keep stored order.
    """
    live = [r for r in rows if is_active(r, readable)]
    by_id = {_text(_get(r, "category_id")): r for r in live}
    if requested is None:
        sequence = [_text(_get(r, "category_id"))
                    for r in sorted(live, key=_category_sort_key)]
    else:
        sequence = list(requested)
    income_row = by_id.get(income_id) if income_id is not None else None
    written = 0
    if income_row is not None:
        written += _write_order(income_row, 0)
    position = 1 if income_row is not None else 0
    for cat_id in sequence:
        if income_row is not None and cat_id == income_id:
            continue
        row = by_id.get(cat_id)
        if row is None:
            continue
        written += _write_order(row, position)
        position += 1
    return written


def _rewrite_sub_category_order(rows, readable, belongs_to, requested=None):
    """The sub-category twin: the whole non-archived sibling set written 0 … n-1."""
    live = [r for r in rows
            if is_active(r, readable) and _text(_get(r, "belongs_to")) == belongs_to]
    by_id = {_text(_get(r, "sub_category_id")): r for r in live}
    if requested is None:
        sequence = [_text(_get(r, "sub_category_id"))
                    for r in sorted(live, key=_sub_category_sort_key)]
    else:
        sequence = list(requested)
    written = 0
    position = 0
    for sub_id in sequence:
        row = by_id.get(sub_id)
        if row is None:
            continue
        written += _write_order(row, position)
        position += 1
    return written


# --- READS -------------------------------------------------------------------------------------


@api_http("/budget/summary", methods=["GET"])
def api_budget_summary(month=None, **kwargs):
    """THE VERIFICATION INSTRUMENT (§3.2, §4.4). Read-only, and on no interactive path.

    A server-side recomputation, in integer cents, of every figure the clients compute locally,
    from raw rows — written independently of bx_calc.js so that agreement between the two is
    evidence rather than a tautology.

    Unknown or malformed `month` -> 400. A month with no data -> 200 with zero-filled totals and
    empty arrays, never a 404, and `available` is still a full thirteen-field object.
    """
    require_auth()
    year, month_number = _validate_month(month)
    categories_raw, cat_readable = _load_categories()
    sub_raw, sub_readable = _load_sub_categories()
    budgets_raw = list(app_tables.budgets.search())
    transactions_raw = list(app_tables.transactions.search())
    anomalies = {}
    payload = build_summary(
        categories_raw, sub_raw, budgets_raw, transactions_raw,
        _month_key(year, month_number),
        cat_readable=cat_readable, sub_readable=sub_readable,
        txn_readable=_active_readable(transactions_raw), anomalies=anomalies)
    _report_anomalies(anomalies)
    return payload


# --- BUDGET WRITES -------------------------------------------------------------------------------


def _resolve_sub_for_budget(sub_category_id):
    """The sub-category row a budget write targets, plus whether it is an income sub-category.

    An unknown id is a 404 — the id names the resource being addressed, not a field value.
    """
    rows, readable = _load_sub_categories()
    target = None
    for row in rows:
        if _text(_get(row, "sub_category_id")) == sub_category_id:
            target = row
            break
    if target is None:
        raise _not_found()
    categories_raw, _cat_readable = _load_categories()
    income_id = _income_category_id(categories_raw)
    is_income = income_id is not None and _text(_get(target, "belongs_to")) == income_id
    return target, is_income


def _single_budget_row(sub_category_id, month_key):
    """The one budget row for (S, month), or None.

    MORE THAN ONE (fact 3) is a 400 and NOTHING is written. It never picks one and it never adds
    a third — which is exactly what the legacy does (BUDGET.py:160-165), turning one duplicate
    pair into three.
    """
    matches = _budget_matches(sub_category_id, month_key)
    if len(matches) > 1:
        raise _bad_request("duplicate budget rows for that sub-category and month")
    return matches[0] if matches else None


@api_http("/budget/amount", methods=["POST"])
def api_budget_amount(**kwargs):
    """Set one sub-category's budget for one month.

    THE SIGN RULE IS THE SERVER'S, not the client's (fact 7): income -> abs, everything else ->
    -abs, and 0 stays 0. amount_cents must be an INTEGER; a float, a string or a null is a 400,
    because fact 11 is how float cents got into this table in the first place.
    """
    require_auth()
    body = _request_json()
    sub_category_id = _require_id(body.get("sub_category_id"), "sub_category_id")
    year, month_number = _validate_month(body.get("month"))
    amount = _validate_amount_cents(body.get("amount_cents"))

    _sub, is_income = _resolve_sub_for_budget(sub_category_id)
    stored = apply_sign(is_income, amount)

    month_key = _month_key(year, month_number)
    period = date(year, month_number, 1)
    row = _single_budget_row(sub_category_id, month_key)
    if row is None:
        app_tables.budgets.add_row(belongs_to=sub_category_id, period=period,
                                   budget_amount=stored, notes="")
    else:
        row.update(budget_amount=stored)

    return {"ok": True, "budget": _read_back_budget(sub_category_id, month_key, period)}


@api_http("/budget/notes", methods=["POST"])
def api_budget_notes(**kwargs):
    """Set or CLEAR one sub-category's note for one month.

    An empty string CLEARS the note — fact 10 is a defect, not a convention. The row is created
    with budget_amount 0 if it does not exist, retained from the legacy deliberately so a note
    can exist before a budget does.
    """
    require_auth()
    body = _request_json()
    sub_category_id = _require_id(body.get("sub_category_id"), "sub_category_id")
    year, month_number = _validate_month(body.get("month"))
    notes = body.get("notes")
    if not isinstance(notes, str):
        raise _bad_request("notes: must be a string")

    _resolve_sub_for_budget(sub_category_id)

    month_key = _month_key(year, month_number)
    period = date(year, month_number, 1)
    row = _single_budget_row(sub_category_id, month_key)
    if row is None:
        app_tables.budgets.add_row(belongs_to=sub_category_id, period=period,
                                   budget_amount=0, notes=notes)
    else:
        row.update(notes=notes)

    return {"ok": True, "budget": _read_back_budget(sub_category_id, month_key, period)}


@api_http("/budget/open-month", methods=["POST"])
def api_budget_open_month(**kwargs):
    """The explicit, idempotent replacement for fact 1 — the read that wrote the database.

    Both `month` and `copy_from` are REQUIRED and neither defaults: a read never writes, and
    neither does an under-specified write. `budget_amount` is copied; `notes` are NOT (fact 2,
    retained — a note is commentary about a month). Archived sub-categories get no row (fact 2's
    other half, corrected). A second identical call creates nothing.
    """
    require_auth()
    body = _request_json()
    if "month" not in body:
        raise _bad_request("month: required")
    if "copy_from" not in body:
        raise _bad_request("copy_from: required")
    to_year, to_month = _validate_month(body.get("month"))
    from_year, from_month = _validate_month(body.get("copy_from"), "copy_from")
    to_key = _month_key(to_year, to_month)
    from_key = _month_key(from_year, from_month)

    sub_raw, sub_readable = _load_sub_categories()
    sub_rows = [_project_sub(r, sub_readable) for r in sub_raw]

    budget_index = {}
    for row in app_tables.budgets.search():
        key = _month_of_stored(_get(row, "period"))
        if key in (from_key, to_key):
            _collect(budget_index, (_text(_get(row, "belongs_to")), key),
                     _cents(_get(row, "budget_amount", 0)))

    plan = build_open_month_plan(set(budget_index.keys()), sub_rows, from_key, to_key)
    have_from = {sub_id for (sub_id, key) in budget_index if key == from_key}
    have_to = {sub_id for (sub_id, key) in budget_index if key == to_key}
    skipped = len(have_from & have_to)

    period = date(to_year, to_month, 1)
    for sub_id in plan:
        amount = _budget_for(budget_index, sub_id, from_key)
        app_tables.budgets.add_row(belongs_to=sub_id, period=period,
                                   budget_amount=0 if amount is None else amount, notes="")

    created = sorted([_read_back_budget(sub_id, to_key, period) for sub_id in plan],
                     key=_budget_sort_key)
    return {
        "ok": True,
        "created": created,
        "skipped": int(skipped),
        # month <= copy_from is legitimate (back-filling a past month) and is FLAGGED so the
        # client can confirm before it happens.
        "direction": "backfill" if _month_index(to_year, to_month)
        <= _month_index(from_year, from_month) else "forward",
    }


# --- CATEGORY WRITES -------------------------------------------------------------------------


@api_http("/cat/create", methods=["POST"])
def api_cat_create(**kwargs):
    """A new category. The server mints category_id and computes `order`; a caller-supplied
    category_id or order is dropped by the whitelist and never stored (rule 1)."""
    require_auth()
    body = _request_json()
    rows, readable = _load_categories()

    name = _validate_name(body.get("name"))
    if _is_income_name(name):
        raise _bad_request("name: reserved for the income category")
    _reject_duplicate_name(name, _existing_names(rows, readable))
    colour_back = _validate_colour(body.get("colour_back"), "colour_back")
    colour_text = _validate_colour(body.get("colour_text"), "colour_text")

    category_id = str(uuid.uuid4())
    app_tables.categories.add_row(
        category_id=category_id, name=name, colour_back=colour_back, colour_text=colour_text,
        order=_next_order(rows, readable), active=True)
    return {"ok": True, "category": _read_back_category(category_id)}


@api_http("/cat/update", methods=["POST"])
def api_cat_update(**kwargs):
    """Rename or recolour a category. Accepted fields: name, colour_back, colour_text — nothing
    else. THE INCOME CATEGORY MAY BE RECOLOURED BUT NOT RENAMED: fact 6 makes its name
    load-bearing until round 08, and renaming it would detach every income rule in the Forms
    app."""
    require_auth()
    body = _request_json()
    category_id = _require_id(body.get("category_id"), "category_id")
    supplied = _accepted(body.get("fields"), CAT_ACCEPTED_FIELDS)

    rows, readable = _load_categories()
    if category_id not in {_text(_get(r, "category_id")) for r in rows}:
        raise _not_found()
    income_id = _income_category_id(rows)

    changes = {}
    if "name" in supplied:
        if income_id is not None and category_id == income_id:
            raise _bad_request("name: the income category cannot be renamed")
        name = _validate_name(supplied["name"])
        if _is_income_name(name):
            raise _bad_request("name: reserved for the income category")
        _reject_duplicate_name(name, _existing_names(rows, readable, exclude_id=category_id))
        changes.__setitem__("name", name)
    for field in ("colour_back", "colour_text"):
        if field in supplied:
            changes.__setitem__(field, _validate_colour(supplied[field], field))

    handle = _category_handle(category_id)
    if handle is None:
        raise _not_found()
    handle.update(**changes)
    return {"ok": True, "category": _read_back_category(category_id)}


@api_http("/cat/reorder", methods=["POST"])
def api_cat_reorder(**kwargs):
    """Write rule 5: the caller submits the COMPLETE desired sequence and the server rewrites the
    whole set. No endpoint here ever nudges a sibling by ±1 (fact 15). An incomplete, padded or
    repeating sequence is a 400 and NOTHING is written."""
    require_auth()
    body = _request_json()
    rows, readable = _load_categories()
    live_ids = [_text(_get(r, "category_id")) for r in rows if is_active(r, readable)]
    requested = _validate_sequence(body.get("order"), live_ids)

    _rewrite_category_order(rows, readable, _income_category_id(rows), requested=requested)
    return {"ok": True, "categories": _read_back_categories()}


def _set_category_archived(archived):
    """The shared body of /cat/archive and /cat/restore — symmetric by construction (rule 6).

    Archive writes the §3.8 mirror (active False AND order -1) and then rewrites the remaining
    non-archived set contiguous, income still at 0. Restore clears both and APPENDS at
    max(order among non-archived) + 1: the original position is not recovered, because the
    legacy archive destroyed it and this round does not invent one.

    It does NOT touch the category's sub-categories. They remain active and simply become
    unreachable in the UI, which is reversible; cascading would not be.
    """
    require_auth()
    body = _request_json()
    category_id = _require_id(body.get("category_id"), "category_id")
    rows, readable = _load_categories()
    if category_id not in {_text(_get(r, "category_id")) for r in rows}:
        raise _not_found()
    income_id = _income_category_id(rows)
    if archived and income_id is not None and category_id == income_id:
        raise _bad_request("category_id: the income category cannot be archived")
    if category_id == TRANSFER_CATEGORY_ID:
        # NOT IN THE SPEC — an added guard, declared in the round report. The transfer sentinel
        # is a structural constant of the app that happens to be stored as a legacy-archived
        # `categories` row (§3.1 measurement 3). RESTORING it would hand the Forms app a live
        # spending category called "Transfer" with a real order, on Bruce's own budget screen,
        # from one unremarkable-looking call. It is not a user category and neither half of the
        # archive pair applies to it.
        raise _bad_request("category_id: the transfer sentinel is not an archivable category")

    handle = _category_handle(category_id)
    if handle is None:
        raise _not_found()
    if archived:
        handle.update(**_archive_state(True))
        fresh, fresh_readable = _load_categories()
        _rewrite_category_order(fresh, fresh_readable, income_id)
    else:
        handle.update(order=_next_order(rows, readable, exclude_id=category_id),
                      **_archive_state(False))
    return {"ok": True, "categories": _read_back_categories()}


@api_http("/cat/archive", methods=["POST"])
def api_cat_archive(**kwargs):
    """Soft, mirrored and reversible. An archived category is STILL A ROW — /build/counts does
    not move — and /cat/restore puts it back."""
    return _set_category_archived(True)


@api_http("/cat/restore", methods=["POST"])
def api_cat_restore(**kwargs):
    """The inverse of /cat/archive. Every write this round makes is reversible from the API."""
    return _set_category_archived(False)


# --- SUB-CATEGORY WRITES ------------------------------------------------------------------------


def _require_live_parent(belongs_to, categories_raw, readable, field="belongs_to"):
    """A parent that exists AND is non-archived. Both failures are a 400 naming the field: here
    the id is a FIELD VALUE being validated, not the resource being addressed."""
    for row in categories_raw:
        if _text(_get(row, "category_id")) == belongs_to:
            if not is_active(row, readable):
                raise _bad_request("%s: category is archived" % field)
            return belongs_to
    raise _bad_request("%s: unknown category_id" % field)


def _sibling_names(sub_rows, readable, belongs_to, exclude_id=None):
    return {
        _text(_get(r, "name")).strip().lower()
        for r in sub_rows
        if is_active(r, readable)
        and _text(_get(r, "belongs_to")) == belongs_to
        and _text(_get(r, "sub_category_id")) != exclude_id
    }


def _next_sibling_order(sub_rows, readable, belongs_to, exclude_id=None):
    values = [
        _number(_get(r, "order"), None) for r in sub_rows
        if is_active(r, readable)
        and _text(_get(r, "belongs_to")) == belongs_to
        and _text(_get(r, "sub_category_id")) != exclude_id
    ]
    numeric = [v for v in values if isinstance(v, (int, float))]
    return int(max(numeric)) + 1 if numeric else 0


def _validate_roll_over_pair(roll_over, roll_over_date):
    """`roll_over: true` with a null date is REJECTED. Fact 14 is a crash the legacy toggle
    creates deliberately (`while cd <= ld` against None); this makes the state
    unrepresentable."""
    if roll_over and roll_over_date is None:
        raise _bad_request("roll_over_date: required when roll_over is true")


@api_http("/subcat/create", methods=["POST"])
def api_subcat_create(**kwargs):
    """A new sub-category under an existing, non-archived parent. The server mints
    sub_category_id and computes `order`."""
    require_auth()
    body = _request_json()
    categories_raw, cat_readable = _load_categories()
    sub_raw, sub_readable = _load_sub_categories()

    belongs_to = _require_live_parent(
        _require_id(body.get("belongs_to"), "belongs_to"), categories_raw, cat_readable)
    name = _validate_name(body.get("name"))
    _reject_duplicate_name(name, _sibling_names(sub_raw, sub_readable, belongs_to))

    icon = body.get("icon")
    if icon is not None and not isinstance(icon, str):
        raise _bad_request("icon: must be a string or null")
    roll_over = body.get("roll_over", False)
    if not isinstance(roll_over, bool):
        raise _bad_request("roll_over: must be a boolean")
    roll_over_date = _validate_roll_over_date(body.get("roll_over_date"))
    _validate_roll_over_pair(roll_over, roll_over_date)

    sub_category_id = str(uuid.uuid4())
    app_tables.sub_categories.add_row(
        sub_category_id=sub_category_id, name=name, icon=icon, belongs_to=belongs_to,
        order=_next_sibling_order(sub_raw, sub_readable, belongs_to),
        roll_over=roll_over, roll_over_date=roll_over_date, active=True)
    return {"ok": True, "sub_category": _read_back_sub_category(sub_category_id)}


@api_http("/subcat/update", methods=["POST"])
def api_subcat_update(**kwargs):
    """Accepted fields: name, icon, roll_over, roll_over_date, belongs_to — nothing else.

    THE ROLL-OVER PAIR IS VALIDATED AFTER THE MERGE, not per field: the resulting row may never
    have roll_over true with a null date, however the two arrived. Re-parenting places the row at
    the END of the new parent's order.
    """
    require_auth()
    body = _request_json()
    sub_category_id = _require_id(body.get("sub_category_id"), "sub_category_id")
    supplied = _accepted(body.get("fields"), SUB_ACCEPTED_FIELDS)

    categories_raw, cat_readable = _load_categories()
    sub_raw, sub_readable = _load_sub_categories()
    current = None
    for row in sub_raw:
        if _text(_get(row, "sub_category_id")) == sub_category_id:
            current = row
            break
    if current is None:
        raise _not_found()

    parent = _text(_get(current, "belongs_to"))
    changes = {}
    if "belongs_to" in supplied:
        new_parent = _require_live_parent(
            _require_id(supplied["belongs_to"], "belongs_to"), categories_raw, cat_readable)
        if new_parent != parent:
            changes.__setitem__("belongs_to", new_parent)
            changes.__setitem__(
                "order",
                _next_sibling_order(sub_raw, sub_readable, new_parent,
                                    exclude_id=sub_category_id))
            parent = new_parent
    if "name" in supplied:
        name = _validate_name(supplied["name"])
        _reject_duplicate_name(
            name, _sibling_names(sub_raw, sub_readable, parent, exclude_id=sub_category_id))
        changes.__setitem__("name", name)
    if "icon" in supplied:
        icon = supplied["icon"]
        if icon is not None and not isinstance(icon, str):
            raise _bad_request("icon: must be a string or null")
        changes.__setitem__("icon", icon)

    merged_roll_over = bool(_get(current, "roll_over", False))
    if "roll_over" in supplied:
        if not isinstance(supplied["roll_over"], bool):
            raise _bad_request("roll_over: must be a boolean")
        merged_roll_over = supplied["roll_over"]
        changes.__setitem__("roll_over", merged_roll_over)
    merged_date = _get(current, "roll_over_date")
    if isinstance(merged_date, datetime):
        merged_date = merged_date.date()
    if "roll_over_date" in supplied:
        merged_date = _validate_roll_over_date(supplied["roll_over_date"])
        changes.__setitem__("roll_over_date", merged_date)
    _validate_roll_over_pair(merged_roll_over, merged_date)

    handle = _sub_category_handle(sub_category_id)
    if handle is None:
        raise _not_found()
    handle.update(**changes)
    return {"ok": True, "sub_category": _read_back_sub_category(sub_category_id)}


@api_http("/subcat/reorder", methods=["POST"])
def api_subcat_reorder(**kwargs):
    """Write rule 5, scoped to one parent: the complete non-archived sibling set, written
    0 … n-1. An incomplete, padded or repeating sequence is a 400 and nothing is written."""
    require_auth()
    body = _request_json()
    belongs_to = _require_id(body.get("belongs_to"), "belongs_to")
    categories_raw, _cat_readable = _load_categories()
    if belongs_to not in {_text(_get(r, "category_id")) for r in categories_raw}:
        raise _not_found()

    sub_raw, sub_readable = _load_sub_categories()
    live_ids = [_text(_get(r, "sub_category_id")) for r in sub_raw
                if is_active(r, sub_readable) and _text(_get(r, "belongs_to")) == belongs_to]
    requested = _validate_sequence(body.get("order"), live_ids)

    _rewrite_sub_category_order(sub_raw, sub_readable, belongs_to, requested=requested)
    return {"ok": True, "sub_categories": _read_back_sub_categories(belongs_to)}


def _set_sub_category_archived(archived):
    """The shared body of /subcat/archive and /subcat/restore — symmetric by construction.

    BUDGET ROWS AND TRANSACTIONS POINTING AT AN ARCHIVED SUB-CATEGORY ARE LEFT EXACTLY AS THEY
    ARE. That is what makes the archive reversible.
    """
    require_auth()
    body = _request_json()
    sub_category_id = _require_id(body.get("sub_category_id"), "sub_category_id")
    sub_raw, sub_readable = _load_sub_categories()
    current = None
    for row in sub_raw:
        if _text(_get(row, "sub_category_id")) == sub_category_id:
            current = row
            break
    if current is None:
        raise _not_found()
    belongs_to = _text(_get(current, "belongs_to"))

    handle = _sub_category_handle(sub_category_id)
    if handle is None:
        raise _not_found()
    if archived:
        handle.update(**_archive_state(True))
        fresh, fresh_readable = _load_sub_categories()
        _rewrite_sub_category_order(fresh, fresh_readable, belongs_to)
    else:
        handle.update(
            order=_next_sibling_order(sub_raw, sub_readable, belongs_to,
                                      exclude_id=sub_category_id),
            **_archive_state(False))
    return {"ok": True, "sub_categories": _read_back_sub_categories(belongs_to)}


@api_http("/subcat/archive", methods=["POST"])
def api_subcat_archive(**kwargs):
    """Soft, mirrored and reversible, scoped to one parent."""
    return _set_sub_category_archived(True)


@api_http("/subcat/restore", methods=["POST"])
def api_subcat_restore(**kwargs):
    """The inverse of /subcat/archive."""
    return _set_sub_category_archived(False)
