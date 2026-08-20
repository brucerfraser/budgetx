# ServerTxn — v1
# Budget X transactions write path: categorise / update / create / archive / restore.
# History:
#   v1  2026-08-20  Session 03 — created. The app's FIRST write path to a business table
#                   (spec_03 §3.1, contract §4.2–4.5).
#
# DESIGN NOTES (read before editing)
#
# - Self-contained: this module declares its own ApiError / api_http / require_session /
#   require_auth, copied in SHAPE from ServerApi (which is frozen). It imports nothing from
#   another Budget X server module — the standing pattern.
# - NO module-level app_tables access. Every table reference lives inside a function body so
#   this module imports cleanly whatever the schema state; a module-level table reference
#   would take /build/version down with it (S01's lesson).
# - A non-200 is always RETURNED as an HttpResponse, never raised out of the wrapper. A raised
#   exception becomes an Anvil 500 error page.
# - ApiError here carries an optional `detail`, which ServerApi's does not: spec_03 §4.5
#   requires 400s to say WHICH FIELD failed. `detail` names the field and a short reason and
#   NEVER echoes a caller-supplied value — a value in an error body is an echo channel.
# - Headers are read case-insensitively; Anvil returns lowercase header names over HTTP/2.
# - Every auth failure returns the identical uniform 401 body — {"ok": false,
#   "error": "unauthorized"} — with no data key anywhere in it.
#
# THE FOUR WRITE RULES (spec_03 §3.1) — every endpoint below obeys all four:
#   1. THE SERVER OWNS IDENTITY AND DERIVED FIELDS. transaction_id and hash are computed here
#      on every path. A caller-supplied transaction_id on create, or a caller-supplied hash
#      anywhere, is ignored and never stored: neither name appears in ACCEPTED_FIELDS.
#   2. WHITELIST, NEVER BLACKLIST. Each endpoint reads an exact set of keys; every other key in
#      the body is dropped before anything reaches a column. There is no "store what you sent".
#   3. EVERY WRITE RETURNS AN INDEPENDENT READ-BACK. The row returned is re-fetched from the
#      table with a DIFFERENT query method than the one that produced the write handle
#      (search() to write, get() to read back). Anvil Row handles cache per handle, so echoing
#      the handle you just wrote through proves nothing. With no audit log on this app, the
#      read-back IS the proof a write landed.
#   4. NO HARD REMOVAL EXISTS IN THIS MODULE. There is no row-removal call anywhere in this
#      file — spec_03 AC-2.6 proves it by an AST walk of the pushed source. Soft-delete only:
#      /txn/archive sets active False, /txn/restore sets it back, and an archived row is still
#      a row, so /build/counts is unchanged by an archive.
#
# `active` — THE HIGHEST-RISK RULE IN THIS ROUND (spec_03 §4.3)
#   Bruce's schema click adds `active` (bool) without touching the ~1,300 existing rows, so
#   they read None, not False. None means "predates soft-delete", which is to say ACTIVE.
#     * Serialisation:  active = (row['active'] is not False)  -> None and True both give true.
#     * Querying:       the active set is filtered on `is not False` in Python. NEVER `is True`
#                       — an `is True` test would hide all ~1,300 of Bruce's transactions.
#     * Writes always set a real boolean. This module never writes None to that column.
#   _active_raw() also tolerates the column being ABSENT (pre-click), returning None, so every
#   endpoint here behaves sanely on either side of the migration.
#
# MONEY — INTEGER CENTS, AND NEVER A MULTIPLY (spec_03 §0.1, §4.2)
#   The `amount` column ALREADY HOLDS CENTS: csv_handler.make_ready does
#   int(math.trunc(d['amount']*100)) on import, and the Forms UI divides by 100 to display.
#   So the wire conversion is a TYPE cast, not a SCALE conversion: int(round(stored)).
#   A multiply by 100 anywhere here would inflate every figure in the app 100x.
#   The legacy float name `amount` never appears on the wire; the wire name is amount_cents.
#
# THE HASH, AND THE FLOAT/INT TRAP (spec_03 §4.4)
#   Formula, reproduced from csv_handler.py:161 and transaction_work.py:25:
#       hash = str(day) + str(month) + str(year) + str(amount) + account
#   day and month are NOT zero-padded; `amount` is the stored cents value; `account` is acc_id.
#
#   The trap: Anvil number columns are float-typed. The importer built its hash from a Python
#   int, so every stored hash renders the amount as "12345". If Anvil hands the same value back
#   as 12345.0, a naive str() yields "12345.0" and the recomputation cannot match.
#
#   _hash_amount() therefore renders an INTEGRAL value through int() first, so an int and an
#   integral float both render "12345". This is not a guess about what Anvil returns — it is
#   forced by the CONTRACT, and would be right either way:
#     * csv_handler.make_ready ALWAYS computes its candidate hash from a Python int, and
#       csv_handler.save_transactions / duplicate_check match a new import against stored
#       hashes by exact string equality. A row this module writes with a "12345.0"-style hash
#       would be invisible to the Forms app's duplicate detection for ever.
#     * If Anvil returns ints anyway, both renderings coincide and nothing is lost.
#   A NON-integral stored value (a pre-existing data defect) is rendered by plain str(), which
#   is what the legacy code would have produced for it, and the row is reported as an anomaly.
#
#   WHAT IS STILL OPEN: whether the ~1,300 STORED hashes match this recomputation could not be
#   tested while writing this module, because no /txn/* endpoint was deployed and bootstrap did
#   not yet return transactions. scratch/s03/verify_hash.py settles it against live data the
#   moment ServerAppData v2 is deployed. That is spec_03 AC-4.3.

import anvil.server
from anvil.tables import app_tables

import hashlib
import json
import re
import traceback
import uuid
from datetime import date, datetime, timezone

MODULE_VERSION = "v1"

# The Transfer sentinel category, as hardcoded across the Forms app and pinned by ServerAppData.
# A transaction may carry it as its `category` even though it is not a sub_categories row.
TRANSFER_CATEGORY_ID = "ec8e0085-8408-43a2-953f-ebba24549d96"

# Batch bounds for /txn/categorise, /txn/archive, /txn/restore.
BATCH_MIN = 1
BATCH_MAX = 200

# Rule 2 — the whitelist. These, and nothing else, may reach a column from a request body.
# transaction_id and hash are ABSENT deliberately: rule 1 says the server owns both.
ACCEPTED_FIELDS = ("date", "description", "amount_cents", "notes", "category", "account",
                   "transfer_account")

# Required on create.
REQUIRED_ON_CREATE = ("date", "amount_cents", "account")

_TOKEN_RE = re.compile(r"^[0-9a-f]{64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ApiError(Exception):
    """Carries an HTTP status, a short machine-readable code, and an optional field-level
    detail. `detail` names a FIELD and a reason; it never carries a caller-supplied value."""

    def __init__(self, status, code, detail=None):
        super().__init__("%s:%s" % (status, code))
        self.status = int(status)
        self.code = str(code)
        self.detail = None if detail is None else str(detail)


def _bad_request(detail):
    return ApiError(400, "bad_request", detail)


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
        raise _bad_request("body: must be a JSON object")
    if not isinstance(body, dict):
        raise _bad_request("body: must be a JSON object")
    return body


def api_http(path, methods=("GET",)):
    """Wraps @anvil.server.http_endpoint with uniform JSON encoding and error mapping.

    The body never contains a traceback, a stack frame, a module path or a table name; the
    traceback is printed so it reaches the Anvil app logs instead. A 400 additionally carries
    `detail`; a 401 and a 404 carry NO data key of any kind (spec_03 §4.5).
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
    revoked_at / active / expires_at checks, same naive-datetime-is-UTC handling. Copied
    rather than imported, per the self-contained-module rule.
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


# ---------------------------------------------------------------------------------------------
# Pure helpers. Everything in this block takes plain mappings and returns plain JSON types, so
# it runs — and is tested — without Anvil or a database. An Anvil Row and a dict index the same
# way, which is how S02 tested its serialiser off-platform.
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
    """A JSON string or null — for `category` and `transfer_account`, the only nullable fields.

    An empty stored string is normalised to null: the Forms app writes both None and "" for
    "no category", and the contract has exactly one spelling for absent.
    """
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    return text if text != "" else None


def _iso_date(value):
    """A date column as ISO YYYY-MM-DD, or "". datetime is a subclass of date, so it is tested
    first."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if text else ""


def _active_raw(row):
    """The raw `active` column value: True, False, or None.

    None covers BOTH "the column exists and this legacy row was never touched" and "the column
    does not exist yet" (pre-click). Both mean active — see the DESIGN NOTES.
    """
    try:
        value = row["active"]
    except Exception:
        return None
    return value if value is True or value is False else None


def is_active(row):
    """The active test, in ONE place so it cannot drift. `is not False` — NEVER `is True`."""
    return _active_raw(row) is not False


def _amount_cents(value, anomalies=None, transaction_id=None):
    """The stored `amount` column as the contract's integer cents.

    A TYPE cast, not a SCALE conversion — the column already holds cents. NEVER multiply by
    100 here. A non-integral stored value is a pre-existing data defect: it is rounded, and the
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


def _hash_amount(value):
    """The `amount` component of the legacy hash string — see the DESIGN NOTES on the trap.

    An integral value (int OR integral float) renders through int(), reproducing exactly what
    csv_handler wrote and what its duplicate detection still computes. A non-integral value
    falls through to plain str(), which is what the legacy code would have produced for it.
    """
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value)


def compute_hash(day, month, year, amount, account):
    """The legacy formula, reproduced exactly (spec_03 §4.4):

        str(date.day) + str(date.month) + str(date.year) + str(amount) + account

    day and month are NOT zero-padded — that is the formula, not an oversight.
    """
    return "%s%s%s%s%s" % (int(day), int(month), int(year), _hash_amount(amount),
                           _text(account))


def hash_for_row(row):
    """compute_hash over a row mapping, taking the date/amount/account exactly as stored."""
    stored_date = _get(row, "date")
    if isinstance(stored_date, datetime):
        stored_date = stored_date.date()
    if not isinstance(stored_date, date):
        return ""
    return compute_hash(stored_date.day, stored_date.month, stored_date.year,
                        _get(row, "amount", 0), _get(row, "account"))


def serialise_transaction(row, anomalies=None):
    """The spec_03 §4.2 transaction object — exactly these ten keys, no extras, no omissions.

    Pure over a plain mapping. `amount_cents` is always an int; `active` is always a real
    bool; `category` and `transfer_account` are the only nullable fields; every other string
    field serialises None to "".
    """
    transaction_id = _text(_get(row, "transaction_id"))
    return {
        "transaction_id": transaction_id,
        "date": _iso_date(_get(row, "date")),
        "description": _text(_get(row, "description")),
        "amount_cents": _amount_cents(_get(row, "amount", 0), anomalies, transaction_id),
        "account": _text(_get(row, "account")),
        "category": _text_or_none(_get(row, "category")),
        "transfer_account": _text_or_none(_get(row, "transfer_account")),
        "notes": _text(_get(row, "notes")),
        "hash": _text(_get(row, "hash")),
        "active": is_active(row),
    }


def _sort_key(txn):
    """Row order IS part of the contract: `date` descending, then `transaction_id` ascending.

    A total order, so two calls are diffable. Dates are compared as the integer YYYYMMDD and
    negated for the descending leg; a blank date sorts last rather than crashing.
    """
    iso = txn["date"]
    if len(iso) == 10 and iso[4] == "-" and iso[7] == "-":
        try:
            return (0, -int(iso[0:4] + iso[5:7] + iso[8:10]), txn["transaction_id"])
        except ValueError:
            pass
    return (1, 0, txn["transaction_id"])


def sort_transactions(txns):
    return sorted(txns, key=_sort_key)


def report_amount_anomalies(anomalies):
    """Non-integral stored cents are a pre-existing data defect worth knowing about. They go to
    the Anvil app log — never into the payload, which has a frozen key-set."""
    for transaction_id, value in anomalies or []:
        print("ServerTxn: non-integral stored amount on transaction_id=%s value=%r"
              % (transaction_id, value))


# ---------------------------------------------------------------------------------------------
# Validation. Pure where it can be; the two that need the database take their valid-id sets as
# arguments so the rules themselves stay testable off-platform.
# ---------------------------------------------------------------------------------------------


def _require_transaction_id(value, field="transaction_id"):
    if not isinstance(value, str) or not value.strip():
        raise _bad_request("%s: must be a non-empty string" % field)
    return value.strip()


def _validate_category(value, valid_sub_ids):
    """A sub_category_id that exists, or the transfer sentinel, or null. Anything else is a 400
    naming the field — never echoing the offending value."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise _bad_request("category: must be a string or null")
    candidate = value.strip()
    if candidate == "":
        return None
    if candidate == TRANSFER_CATEGORY_ID:
        return candidate
    if candidate not in valid_sub_ids:
        raise _bad_request("category: unknown sub_category_id")
    return candidate


def _validate_account(value, valid_acc_ids, field="account"):
    if not isinstance(value, str) or not value.strip():
        raise _bad_request("%s: must be a non-empty string" % field)
    candidate = value.strip()
    if candidate not in valid_acc_ids:
        raise _bad_request("%s: unknown acc_id" % field)
    return candidate


def _validate_date(value):
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise _bad_request("date: must be ISO YYYY-MM-DD")
    try:
        return date(int(value[0:4]), int(value[5:7]), int(value[8:10]))
    except ValueError:
        raise _bad_request("date: must be a real calendar date")


def _validate_amount_cents(value):
    """An integer number of cents. A bool is not an int here, and a float is accepted only if
    it is exactly integral — the client is contractually sending an integer."""
    if isinstance(value, bool):
        raise _bad_request("amount_cents: must be an integer")
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise _bad_request("amount_cents: must be an integer")


def _validate_text(value, field):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise _bad_request("%s: must be a string" % field)
    return value


def validate_fields(fields, valid_sub_ids, valid_acc_ids, require=()):
    """Rule 2 in one place: read ONLY the whitelisted keys, validate each, return the column
    values to write. Unknown keys are dropped here and are silently ignored — including
    transaction_id and hash, which rule 1 reserves to the server.
    """
    if not isinstance(fields, dict):
        raise _bad_request("fields: must be an object")

    supplied = [key for key in ACCEPTED_FIELDS if key in fields]
    for key in require:
        if key not in supplied:
            raise _bad_request("%s: required" % key)
    if not supplied:
        raise _bad_request("fields: no accepted field supplied")

    out = {}
    for key in supplied:
        value = fields[key]
        if key == "date":
            out = {**out, "date": _validate_date(value)}
        elif key == "amount_cents":
            out = {**out, "amount": _validate_amount_cents(value)}
        elif key == "account":
            out = {**out, "account": _validate_account(value, valid_acc_ids)}
        elif key == "transfer_account":
            out = {**out, "transfer_account":
                   None if value is None or value == ""
                   else _validate_account(value, valid_acc_ids, "transfer_account")}
        elif key == "category":
            out = {**out, "category": _validate_category(value, valid_sub_ids)}
        elif key == "description":
            out = {**out, "description": _validate_text(value, "description")}
        elif key == "notes":
            out = {**out, "notes": _validate_text(value, "notes")}
    return out


def _validate_batch(raw, field):
    if not isinstance(raw, list):
        raise _bad_request("%s: must be a list" % field)
    if len(raw) < BATCH_MIN:
        raise _bad_request("%s: at least %d item required" % (field, BATCH_MIN))
    if len(raw) > BATCH_MAX:
        raise _bad_request("%s: at most %d items per call" % (field, BATCH_MAX))
    return raw


# ---------------------------------------------------------------------------------------------
# Table access. Everything below this line touches the database and nothing above it does.
# ---------------------------------------------------------------------------------------------


def _valid_sub_ids():
    return {r["sub_category_id"] for r in app_tables.sub_categories.search()
            if isinstance(r["sub_category_id"], str)}


def _valid_acc_ids():
    return {r["acc_id"] for r in app_tables.accounts.search()
            if isinstance(r["acc_id"], str)}


def _row_for_write(transaction_id):
    """The handle a write goes through — obtained via search().

    Deliberately a DIFFERENT query method from _read_back()'s get(), so the read-back cannot be
    served from the same cached handle. Anvil Row handles cache per handle.
    """
    for row in app_tables.transactions.search(transaction_id=transaction_id):
        return row
    return None


def _read_back(transaction_id):
    """Rule 3 — an independent re-fetch through get(), after the write. Returns the serialised
    §4.2 object, or None if the row cannot be found (which would mean the write did not land)."""
    row = app_tables.transactions.get(transaction_id=transaction_id)
    if row is None:
        return None
    anomalies = []
    payload = serialise_transaction(row, anomalies)
    report_amount_anomalies(anomalies)
    return payload


def _require_rows(transaction_ids):
    """Every id must resolve to a row BEFORE anything is written — so a batch carrying an
    unknown id writes nothing at all. Returns {transaction_id: write handle}.

    ONE search() pass over the table, not one query per id. A 200-item batch resolved with 200
    indexed lookups is 200 round trips, and the standing 1-second rule applies to the inbox
    flush as much as to a page load. The read-back afterwards is still one independent get()
    per row — that is rule 3 and it is not negotiable for speed.
    """
    wanted = set(transaction_ids)
    handles = {}
    for row in app_tables.transactions.search():
        key = row["transaction_id"]
        if key in wanted and key not in handles:
            handles = {**handles, key: row}
            if len(handles) == len(wanted):
                break
    for transaction_id in wanted:
        if transaction_id not in handles:
            raise ApiError(404, "not_found")
    return handles


def _recompute_hash(row, changes):
    """The hash after `changes` are applied, taking unchanged components from the stored row."""
    new_date = changes["date"] if "date" in changes else _get(row, "date")
    if isinstance(new_date, datetime):
        new_date = new_date.date()
    new_amount = changes["amount"] if "amount" in changes else _get(row, "amount", 0)
    new_account = changes["account"] if "account" in changes else _get(row, "account")
    if not isinstance(new_date, date):
        return None
    return compute_hash(new_date.day, new_date.month, new_date.year, new_amount, new_account)


# ---------------------------------------------------------------------------------------------
# The five endpoints.
# ---------------------------------------------------------------------------------------------


@api_http("/txn/categorise", methods=["POST"])
def api_txn_categorise(**kwargs):
    """The inbox's endpoint, and the only batch write. 1–200 items.

    ATOMIC ON REJECTION: every item is validated, and every row resolved, BEFORE the first
    write. A batch carrying one bad category changes nothing at all (spec_03 AC-2.2).
    """
    require_auth()
    body = _request_json()
    items = _validate_batch(body.get("items"), "items")

    valid_sub_ids = _valid_sub_ids()
    planned = []
    for item in items:
        if not isinstance(item, dict):
            raise _bad_request("items: each item must be an object")
        transaction_id = _require_transaction_id(item.get("transaction_id"))
        category = _validate_category(item.get("category"), valid_sub_ids)
        planned.append((transaction_id, category))

    handles = _require_rows([pair[0] for pair in planned])

    # Nothing above this line wrote anything.
    for transaction_id, category in planned:
        handles[transaction_id].update(category=category)

    updated = []
    for transaction_id, _category in planned:
        fresh = _read_back(transaction_id)
        if fresh is None:
            raise ApiError(404, "not_found")
        updated.append(fresh)
    return {"ok": True, "updated": updated}


@api_http("/txn/update", methods=["POST"])
def api_txn_update(**kwargs):
    """A single row. Whitelisted fields only; hash is recomputed when date, amount_cents or
    account changes, so the Forms app's duplicate detection keeps working."""
    require_auth()
    body = _request_json()
    transaction_id = _require_transaction_id(body.get("transaction_id"))
    changes = validate_fields(body.get("fields"), _valid_sub_ids(), _valid_acc_ids())

    row = _row_for_write(transaction_id)
    if row is None:
        raise ApiError(404, "not_found")

    if "date" in changes or "amount" in changes or "account" in changes:
        recomputed = _recompute_hash(row, changes)
        if recomputed is not None:
            changes = {**changes, "hash": recomputed}

    row.update(**changes)

    fresh = _read_back(transaction_id)
    if fresh is None:
        raise ApiError(404, "not_found")
    return {"ok": True, "transaction": fresh}


@api_http("/txn/create", methods=["POST"])
def api_txn_create(**kwargs):
    """A single new row. date, amount_cents and account are required.

    The server mints transaction_id (uuid4) and computes hash. A transaction_id or hash in the
    body is not in ACCEPTED_FIELDS, so it is dropped by validate_fields and never stored.
    """
    require_auth()
    body = _request_json()
    fields = body.get("fields")
    if fields is None:
        fields = body
    changes = validate_fields(fields, _valid_sub_ids(), _valid_acc_ids(),
                              require=REQUIRED_ON_CREATE)

    new_date = changes["date"]
    transaction_id = str(uuid.uuid4())
    columns = {
        "transaction_id": transaction_id,
        "date": new_date,
        "description": changes.get("description", ""),
        "amount": changes["amount"],
        "notes": changes.get("notes", ""),
        "account": changes["account"],
        "category": changes.get("category"),
        "transfer_account": changes.get("transfer_account"),
        "hash": compute_hash(new_date.day, new_date.month, new_date.year,
                             changes["amount"], changes["account"]),
        # A real boolean, always. This module never writes None to `active`.
        "active": True,
    }
    app_tables.transactions.add_row(**columns)

    fresh = _read_back(transaction_id)
    if fresh is None:
        raise ApiError(404, "not_found")
    return {"ok": True, "transaction": fresh}


def _set_active(target, key):
    """The shared body of /txn/archive and /txn/restore.

    Auth is checked BEFORE the body is parsed, so an unauthenticated caller sending rubbish
    gets the uniform 401 and never a 400 that would confirm the endpoint parsed anything.

    The ids returned are the ones CONFIRMED by re-reading each row and testing the column —
    never the ids that were sent.
    """
    require_auth()
    body = _request_json()
    ids = _validate_batch(body.get("transaction_ids"), "transaction_ids")
    wanted = []
    for value in ids:
        transaction_id = _require_transaction_id(value)
        if transaction_id not in wanted:
            wanted.append(transaction_id)

    handles = _require_rows(wanted)
    for transaction_id in wanted:
        handles[transaction_id].update(active=target)

    confirmed = []
    for transaction_id in wanted:
        row = app_tables.transactions.get(transaction_id=transaction_id)
        if row is not None and _active_raw(row) is target:
            confirmed.append(transaction_id)
    return {"ok": True, key: confirmed}


@api_http("/txn/archive", methods=["POST"])
def api_txn_archive(**kwargs):
    """Soft delete. Sets active False. An archived row is STILL A ROW — /build/counts does not
    move — and /txn/restore puts it back."""
    return _set_active(False, "archived")


@api_http("/txn/restore", methods=["POST"])
def api_txn_restore(**kwargs):
    """The inverse of /txn/archive. Every write this round makes is reversible from the API."""
    return _set_active(True, "restored")
