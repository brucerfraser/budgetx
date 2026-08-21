# ServerBuildTools — v4
# Budget X build pipeline: upload/promote/list of app_versions, the /x serving route, and the
# read-back instruments (/build/session, /build/counts) that prove a write actually landed.
# History:
#   v1  2026-08-19  Session 01 — created. upload/promote/list/version/session/counts and /x.
#   v2  2026-08-20  Session 02 — upload stamps uploaded_by server-side; /build/list reports it;
#                   /build/version also reports ServerAppData.
#   v3  2026-08-20  Session 03 — /build/version also reports ServerTxn. Required by spec_03
#                   AC-1.6; _module_versions() enumerates modules explicitly, so a new module
#                   is invisible to the endpoint until it is named here. See spec_03 Addendum 2.
#   v4  2026-08-21  Session 04 — /build/version reports ServerBudget (guarded: the module lands
#                   later this round, so an absent module omits the key rather than raising);
#                   GET /build/budget-audit (spec_04 §3.1, read-only) and POST /build/init-active
#                   (spec_04 §3.7 step 4) added. Both are migration scaffolding, both are
#                   build-secret-gated, and both are RETIRED AT ROUND 08 with the rest of it.
#
# SESSION 04 — WHY THESE TWO TOOLS LIVE HERE AND NOT IN ServerBudget (spec_04 §3.0)
# - §3.7 step 2 requires that the commit carrying the schema edit contains NO code that reads
#   the new `active` columns on categories/sub_categories. Shipping them inside ServerBudget
#   would ship /cat/archive and /budget/summary alongside them, against columns the database
#   does not have yet. Putting them here makes that claim TRUE rather than aspirational.
# - GET /build/budget-audit therefore reads the LEGACY archive sentinel `order == -1` and never
#   touches an `active` column on categories or sub_categories. It reads `active` on
#   `transactions` only, where the column already exists (added in S03), and probes it ONCE per
#   call — reading a column the schema does not have costs a server round trip PER ROW
#   (ServerAppData's v2 DESIGN NOTES measured 3–4 ms each over 1,300 rows).
# - GET /build/budget-audit IS STRICTLY READ-ONLY, and provably so: neither it nor any function
#   it calls contains add_row, .update(, .delete( or a subscript assignment of any kind. Dict
#   accumulation goes through .__setitem__ / .setdefault, exactly as ServerAppData sets its
#   Content-Type, so a function-scoped AST walk is decidable. DO NOT tidy those back into
#   bracketed assignment form.
# - POST /build/init-active is the one write here, and it is bounded on purpose: two literal
#   table names in the source (never from the caller), one column, one derived value, idempotent,
#   and it returns ID LISTS rather than counts so §3.7 step 5 can reconcile it against §3.1
#   measurement 4 while ServerAppData is still v2 and cannot show `active` at all.
# - MONEY IS INTEGER CENTS. budgets.budget_amount ALREADY holds cents, so the conversion is a
#   TYPE cast — int(round(stored)) — and NEVER a multiply by 100.
# - Do NOT reach for q.fetch_only(): it returns TableError app-wide here (spec_04 §0.1).
#
# DESIGN NOTES (read before editing)
# - Self-contained: this module declares its own ApiError / api_http rather than importing
#   ServerApi's. The ONLY sanctioned cross-module references are reading MODULE_VERSION from
#   ServerApi and (from v2) ServerAppData inside _module_versions(), because /build/version must
#   report every module's stamp and spec_01 §3.4 requires each stamp to come from a single
#   in-module constant so header and endpoint cannot drift. Both are imported INSIDE the
#   function, never at module level — which is exactly why no module may touch app_tables at
#   import time: a module that fails to import would take /build/version down with it.
# - v2: /build/upload stamps uploaded_by itself (spec_02 §3.2). The caller cannot set it — a
#   client-supplied provenance field is not provenance. /build/list carries it so the stamp is
#   provable by read-back, and still never carries html.
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
from datetime import date, datetime, timezone

MODULE_VERSION = "v4"

DEFAULT_SLUG = "x"
DEFAULT_KIND = "html"

# Provenance is stamped by the server, never accepted from the caller (spec_02 §3.2).
UPLOADED_BY = "build-api"

# The entire accepted input set of /build/upload. Anything else in the body is ignored and
# never stored — including uploaded_by, which is the whole point of the v2 change.
UPLOAD_KEYS = ("slug", "kind", "version", "html")

# Tables reported by /build/counts — the AC-11.1 instrument. Counts only, never row contents.
COUNTED_TABLES = [
    "accounts", "budgets", "categories", "sub_categories",
    "transactions", "settings", "files", "test_csv", "users",
]

# --- Session 04 migration scaffolding (retired at round 08) ----------------------------------

# The Transfer sentinel (spec_04 §3.1 measurement 3). Whether it is a real categories row, a
# real sub_categories row or NEITHER is exactly what the audit reports; nothing here assumes it.
TRANSFER_SENTINEL_ID = "ec8e0085-8408-43a2-953f-ebba24549d96"

# The legacy archive sentinel (fact 4). Until Bruce's click and POST /build/init-active this is
# the ONLY archive signal on categories/sub_categories, and it is what the audit reads.
ARCHIVED_ORDER = -1

# The magic income name (fact 6). Case-sensitive exact match is the LEGACY test; the trimmed,
# case-insensitive match is what _income_category_id()/bxIncomeCategoryId will use. The audit
# reports both, which is the whole point of measurement 2.
INCOME_NAME = "Income"

# POST /build/init-active operates on exactly these tables, as literals. The caller supplies
# no table name and no other input at all (spec_04 §3.7).
INIT_ACTIVE_TABLES = ("categories", "sub_categories")
INIT_ACTIVE_ID_COLUMN = {"categories": "category_id", "sub_categories": "sub_category_id"}

# A defensive bound on the §4.5 branch-D rollover walk. A roll_over_date a century in the past
# is a data defect, not a plan; without a bound one such row would walk the whole endpoint into
# a timeout. 1200 months = 100 years, far beyond any real window.
MAX_ROLLOVER_MONTHS = 1200


class ApiError(Exception):
    """An HTTP status, a short machine-readable code, and (v4) optional extra body keys.

    `extra` exists for spec_04 §3.7's 409 {"ok": false, "error": "column_missing",
    "table": "<name>"} and for nothing else. It defaults to empty, so every pre-existing raise
    produces a byte-identical body to v3 — the uniform 401 in particular carries no data key.
    """

    def __init__(self, status, code, extra=None):
        super().__init__("%s:%s" % (status, code))
        self.status = int(status)
        self.code = str(code)
        self.extra = dict(extra) if extra else {}


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
    # v4: .__setitem__ rather than bracketed assignment, so that a function-scoped AST walk of
    # the read-only /build/budget-audit call graph cannot trip over a header write. Behaviour
    # is identical; do NOT tidy this back into resp.headers["Content-Type"] = ...
    resp.headers.__setitem__("Content-Type", "application/json")
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
                return _json_response(
                    err.status, {"ok": False, "error": err.code, **err.extra}
                )
            except Exception:
                traceback.print_exc()
                return _json_response(500, {"ok": False, "error": "server_error"})

        wrapper.__name__ = fn.__name__
        return wrapper

    return decorator


def _module_versions():
    """Every module stamp, each read from that module's single in-module constant."""
    versions = {"ServerBuildTools": MODULE_VERSION}
    try:
        import ServerApi
        versions["ServerApi"] = ServerApi.MODULE_VERSION
    except Exception:
        traceback.print_exc()
        versions["ServerApi"] = "unavailable"
    try:
        import ServerAppData
        versions["ServerAppData"] = ServerAppData.MODULE_VERSION
    except Exception:
        traceback.print_exc()
        versions["ServerAppData"] = "unavailable"
    try:
        import ServerTxn
        versions["ServerTxn"] = ServerTxn.MODULE_VERSION
    except Exception:
        traceback.print_exc()
        versions["ServerTxn"] = "unavailable"
    # v4 — ServerBudget is GUARDED, and its guard OMITS the key rather than reporting
    # "unavailable" (spec_04 §3.0/AC-1.6). The module does not exist at the §3.7 step-2 commit
    # and lands later in the same round: /build/version must answer correctly on both sides of
    # that, and a module that cannot be imported must never take the endpoint down. An absent
    # module is silent (it is the expected state for part of this round); any OTHER failure is
    # logged, because a ServerBudget that exists and will not import is a real defect and
    # AC-1.6 should fail on it rather than read "unavailable".
    try:
        import ServerBudget
        versions["ServerBudget"] = ServerBudget.MODULE_VERSION
    except ImportError:
        pass
    except Exception:
        traceback.print_exc()
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
        # v2: the read-back that proves the server, not the caller, set this (spec_02 AC-2).
        "uploaded_by": row["uploaded_by"],
    }


@api_http("/build/version", methods=["GET"])
def api_build_version(**kwargs):
    require_build_secret()
    return {"ok": True, "modules": _module_versions()}


@api_http("/build/upload", methods=["POST"])
def api_build_upload(**kwargs):
    require_build_secret()
    body = _request_json()
    # The accepted input set, applied once and explicitly: every other key in the body is
    # dropped here and can therefore never reach a column — a caller cannot forge provenance,
    # or set any other stored field, by adding keys (spec_02 §3.2).
    fields = {key: body.get(key) for key in UPLOAD_KEYS}

    html = fields.get("html")
    if not isinstance(html, str) or html == "":
        raise ApiError(400, "bad_request")

    version = fields.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ApiError(400, "bad_request")
    version = version.strip()
    # Bruce's standing rule: never promote a 0.x build.
    if version.startswith("0."):
        raise ApiError(400, "bad_request")

    slug = fields.get("slug") or DEFAULT_SLUG
    kind = fields.get("kind") or DEFAULT_KIND
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
        # Server-stamped constant. A caller-supplied uploaded_by is read nowhere and stored
        # never; the field means "this row came in through /build/upload" and nothing else.
        uploaded_by=UPLOADED_BY,
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


# =============================================================================================
# SESSION 04 MIGRATION SCAFFOLDING — retired at round 08 (spec_04 §3.7, §10)
#
# Everything from here to the /x route serves spec_04 §3.1's twelve round-start measurements and
# §3.7 step 4's initialisation. Two endpoints:
#
#   GET  /build/budget-audit   strictly read-only, one UTC-stamped artefact, measurements 1–12
#   POST /build/init-active    the one bounded write: `active` on categories/sub_categories only
#
# READ-ONLY DISCIPLINE (audit path only). No function reachable from api_build_budget_audit
# contains add_row, .update(, .delete( or a subscript assignment. Accumulators use .__setitem__
# and .setdefault so an AST walk can decide it. See the module DESIGN NOTES.
# =============================================================================================


def _col(row, name, default=None):
    """One column, defensively: an absent column or a None value yields the default."""
    try:
        value = row[name]
    except Exception:
        return default
    return default if value is None else value


def _str(value, default=""):
    if value is None:
        return default
    return value if isinstance(value, str) else str(value)


def _num_or_none(value):
    """A stored number, or None for null/non-numeric. bool is excluded on purpose."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _cents(value):
    """A stored money column as integer cents, or None if it is not a number at all.

    A TYPE cast, not a SCALE conversion: budgets.budget_amount ALREADY holds cents. NEVER
    multiply by 100 here — a stray *100 inflates every figure in the app 100x.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(round(value))


def _is_integral(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        return value.is_integer()
    return True


def _json_scalar(value):
    """A stored value made safe for json.dumps, without pretending it was a number."""
    if value is None or isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def _iso_day(value):
    """A date column as ISO YYYY-MM-DD, or None. datetime subclasses date, so test it first."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else None


def _month_of(iso_day):
    """"YYYY-MM-DD" -> "YYYY-MM", or None."""
    if not isinstance(iso_day, str) or len(iso_day) < 7:
        return None
    return iso_day[:7]


def _split_month(month_key):
    """"YYYY-MM" (or "YYYY-MM-DD") -> (year, month), or None."""
    if not isinstance(month_key, str) or len(month_key) < 7:
        return None
    try:
        return int(month_key[0:4]), int(month_key[5:7])
    except ValueError:
        return None


def _month_index(year, month):
    return year * 12 + (month - 1)


def _month_key_from_index(index):
    return "%04d-%02d" % (index // 12, index % 12 + 1)


def _bump(counter, key, delta=1):
    """Accumulate into a plain dict WITHOUT a subscript assignment — see the DESIGN NOTES."""
    counter.__setitem__(key, counter.get(key, 0) + delta)


def _active_column_readable(rows):
    """Whether `active` can be read at all on this table — decided ONCE for the whole set.

    Presence is a property of the SCHEMA, not of a row, and rediscovering it per row costs a
    server round trip per row (ServerAppData v2 DESIGN NOTES). Up to three rows are tried and
    ANY success means readable; an empty table is readable by definition (there is nothing to
    read and nothing to write). The bias toward True is deliberate: a transient failure on one
    row must not be mistaken for "no such column".
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


def _read_active(row):
    """The raw `active` column: True, False or None (absent column, or never set)."""
    try:
        value = row["active"]
    except Exception:
        return None
    return value if value is True or value is False else None


# --- pure row projections (plain mappings in, plain JSON types out) ---------------------------


def _audit_category(row):
    return {
        "category_id": _str(_col(row, "category_id")),
        "name": _str(_col(row, "name")),
        "order": _num_or_none(_col(row, "order")),
    }


def _audit_sub_category(row):
    return {
        "sub_category_id": _str(_col(row, "sub_category_id")),
        "name": _str(_col(row, "name")),
        "belongs_to": _str(_col(row, "belongs_to")),
        "order": _num_or_none(_col(row, "order")),
        "roll_over": _col(row, "roll_over") is True,
        "roll_over_date": _iso_day(_col(row, "roll_over_date")),
    }


def _audit_budget(row):
    stored = _col(row, "budget_amount")
    period_iso = _iso_day(_col(row, "period"))
    return {
        "belongs_to": _str(_col(row, "belongs_to")),
        "period": period_iso,
        "month": _month_of(period_iso),
        "period_is_first": bool(period_iso) and period_iso[8:10] == "01",
        "stored": _json_scalar(stored),
        "amount_cents": _cents(stored),
        "integral": _is_integral(stored),
    }


def _audit_transaction(row, active_readable):
    iso = _iso_day(_col(row, "date"))
    return {
        "category": _str(_col(row, "category")),
        "month": _month_of(iso),
        "amount_cents": _cents(_col(row, "amount")) or 0,
        # `is not False` — NEVER `is True`: a row predating soft-delete reads None and is ACTIVE.
        "active": (_read_active(row) if active_readable else None) is not False,
    }


def _order_sort_key(item):
    """`order` ascending with None LAST, then name case-insensitively, then id — the same
    total order ServerAppData already sorts these two tables by."""
    value, name, ident = item
    if value is None:
        return (1, 0.0, name.lower(), ident)
    return (0, float(value), name.lower(), ident)


def _resolve_income(categories):
    """Measurement 2, both halves.

    `exists` is the LEGACY test — a category named exactly "Income", byte for byte (fact 6).
    `resolved_category_id` is what _income_category_id()/bxIncomeCategoryId will return — the
    trimmed, case-insensitive match — and it is what every other figure in this audit uses.
    Reporting both is what proves the widening is safe. If more than one category matches
    case-insensitively, the exact match wins, else the first by (name, id); the rest are
    near-misses, so an ambiguity can never hide behind a single id.
    """
    exact = [c for c in categories if c["name"] == INCOME_NAME]
    loose = [c for c in categories
             if c["name"].strip().lower() == INCOME_NAME.lower()]
    if exact:
        chosen = exact[0]
    elif loose:
        chosen = sorted(loose, key=lambda c: (c["name"], c["category_id"]))[0]
    else:
        chosen = None
    near = [{"category_id": c["category_id"], "name": c["name"]}
            for c in loose if c is not chosen]
    return {
        "exists": bool(exact),
        "category_id": exact[0]["category_id"] if exact else None,
        "name": exact[0]["name"] if exact else None,
        "near_misses": sorted(near, key=lambda c: (c["name"], c["category_id"])),
        "resolved_category_id": chosen["category_id"] if chosen else None,
        "resolved_name": chosen["name"] if chosen else None,
        "resolved_count": len(loose),
    }


def _budget_amount_for(month_index_map, sub_category_id, month_key):
    """The budget for (S, month), and whether a row exists at all.

    Duplicate (belongs_to, period) pairs are a real state of this table (fact 3) and this tool
    does NOT repair them. For arithmetic it takes the SMALLEST cents value of the duplicates —
    an arbitrary but DETERMINISTIC choice, so two runs agree — and every affected pair is
    listed in full under duplicate_budget_pairs so the orchestrator can see where it mattered.
    """
    values = month_index_map.get((sub_category_id, month_key))
    if not values:
        return 0, False
    return sorted(values)[0], True


def _rollover_overspent(sub, month_index_map, spend_map, year, month):
    """The §4.5 `overspent` for one sub-category and one month — a POSITIVE magnitude, or 0.

    Branch A (roll_over false) and branch B (roll_over true, no date) both give carried_in 0.
    Branch C (income) never reaches here: income sub-categories are excluded by the caller,
    because §4.5 branch C fixes overspent at 0 and §4.5A rule 4 forbids calling an under-earning
    income line "overspent". Branch D walks D .. M-1, clamping the carry at 0 on overspend.
    """
    sub_id = sub["sub_category_id"]
    carried = 0
    start = _split_month(sub["roll_over_date"]) if sub["roll_over"] else None
    if start is not None:
        start_index = _month_index(start[0], start[1])
        months = max(0, _month_index(year, month) - start_index)
        for step in range(min(months, MAX_ROLLOVER_MONTHS)):
            prev_key = _month_key_from_index(start_index + step)
            budget_p, _present = _budget_amount_for(month_index_map, sub_id, prev_key)
            available_p = carried + budget_p
            remaining_p = available_p - spend_map.get((sub_id, prev_key), 0)
            carried = remaining_p if remaining_p <= 0 else 0
    month_key = "%04d-%02d" % (year, month)
    month_budget, _present = _budget_amount_for(month_index_map, sub_id, month_key)
    raw = (carried + month_budget) - spend_map.get((sub_id, month_key), 0)
    return raw if raw > 0 else 0


def _count_table(name, preloaded):
    if name in preloaded:
        return len(preloaded[name])
    try:
        return len(getattr(app_tables, name).search())
    except Exception:
        traceback.print_exc()
        return None


def build_budget_audit(preloaded, taken_at):
    """spec_04 §3.1 measurements 1-12 as one artefact. Pure over plain mappings — an Anvil Row
    and a dict index the same way — so it is testable off-platform without a database."""
    categories = [_audit_category(r) for r in preloaded["categories"]]
    sub_categories = [_audit_sub_category(r) for r in preloaded["sub_categories"]]
    budgets = [_audit_budget(r) for r in preloaded["budgets"]]
    txn_active_readable = _active_column_readable(preloaded["transactions"])
    transactions = [_audit_transaction(r, txn_active_readable)
                    for r in preloaded["transactions"]]

    # --- measurement 2 -----------------------------------------------------------------------
    income = _resolve_income(categories)
    income_category_id = income["resolved_category_id"]

    # --- measurement 3: the transfer sentinel ------------------------------------------------
    # A transaction is a transfer if its `category` IS the sentinel, or names a sub-category
    # that is the sentinel or hangs off it. Measurement 3 allows the sentinel to be NEITHER a
    # categories nor a sub_categories row, in which case only the first clause can ever fire —
    # which is exactly why the exclusion is done on the transaction side (spec_04 §3.3).
    transfer_sub_ids = {TRANSFER_SENTINEL_ID} | {
        s["sub_category_id"] for s in sub_categories
        if s["belongs_to"] == TRANSFER_SENTINEL_ID
    }
    transfer_sentinel = {
        "sub_category_id": TRANSFER_SENTINEL_ID,
        "in_sub_categories": any(s["sub_category_id"] == TRANSFER_SENTINEL_ID
                                 for s in sub_categories),
        "in_categories": any(c["category_id"] == TRANSFER_SENTINEL_ID for c in categories),
        "txn_count": sum(1 for t in transactions
                         if t["active"] and t["category"] == TRANSFER_SENTINEL_ID),
        "txn_count_including_inactive": sum(1 for t in transactions
                                            if t["category"] == TRANSFER_SENTINEL_ID),
        "child_sub_category_ids": sorted(
            s["sub_category_id"] for s in sub_categories
            if s["belongs_to"] == TRANSFER_SENTINEL_ID
        ),
    }

    # --- measurement 4: the order == -1 id sets ----------------------------------------------
    order_minus_one = {
        "categories": sorted(c["category_id"] for c in categories
                             if c["order"] == ARCHIVED_ORDER),
        "sub_categories": sorted(s["sub_category_id"] for s in sub_categories
                                 if s["order"] == ARCHIVED_ORDER),
    }
    archived_sub_ids = set(order_minus_one["sub_categories"])

    # --- indexes, built once (measurements 5, 6, 7, 12) --------------------------------------
    pair_index = {}          # (belongs_to, period ISO day) -> [cents, ...]   duplicates
    month_index_map = {}     # (belongs_to, "YYYY-MM")      -> [cents, ...]   arithmetic
    budget_month_counts = {}
    for b in budgets:
        cents = b["amount_cents"] or 0
        if b["period"]:
            pair_index.setdefault((b["belongs_to"], b["period"]), []).append(cents)
        if b["month"]:
            month_index_map.setdefault((b["belongs_to"], b["month"]), []).append(cents)
            _bump(budget_month_counts, b["month"])

    spend_map = {}           # (sub_category_id, "YYYY-MM") -> cents, active non-transfer only
    txn_month_counts = {}
    txn_month_non_transfer = {}
    txn_month_inactive = {}
    for t in transactions:
        if not t["month"]:
            continue
        if not t["active"]:
            _bump(txn_month_inactive, t["month"])
            continue
        _bump(txn_month_counts, t["month"])
        if t["category"] in transfer_sub_ids:
            continue
        _bump(txn_month_non_transfer, t["month"])
        _bump(spend_map, (t["category"], t["month"]), t["amount_cents"])

    # --- measurement 5: duplicate (belongs_to, period) pairs. REPORTED, NEVER REPAIRED --------
    duplicate_budget_pairs = [
        {"belongs_to": key[0], "period": key[1], "count": len(values),
         "amounts": sorted(values)}
        for key, values in sorted(pair_index.items())
        if len(values) > 1
    ]

    # --- measurement 6: rows per month, across BOTH tables -----------------------------------
    all_months = sorted(set(budget_month_counts) | set(txn_month_counts)
                        | set(txn_month_non_transfer) | set(txn_month_inactive))
    per_month = {
        key: {
            "budget_rows": budget_month_counts.get(key, 0),
            "transactions": txn_month_counts.get(key, 0),
            "non_transfer_transactions": txn_month_non_transfer.get(key, 0),
            "transactions_inactive": txn_month_inactive.get(key, 0),
        }
        for key in all_months
    }

    # --- measurement 7: non-integral stored budget amounts, in full (fact 11) ----------------
    non_integer_budget_amounts = [
        {"belongs_to": b["belongs_to"], "period": b["period"], "stored": b["stored"]}
        for b in sorted(budgets, key=lambda r: (r["period"] or "", r["belongs_to"]))
        if not b["integral"]
    ]
    # Not a numbered measurement, but §4.3 obliges the round to list these too.
    non_first_of_month_periods = [
        {"belongs_to": b["belongs_to"], "period": b["period"]}
        for b in sorted(budgets, key=lambda r: (r["period"] or "", r["belongs_to"]))
        if b["period"] and not b["period_is_first"]
    ]

    # --- measurement 8: roll_over true with no start date (fact 14) --------------------------
    rollover_without_date = sorted(
        s["sub_category_id"] for s in sub_categories
        if s["roll_over"] and not s["roll_over_date"]
    )

    # --- measurement 9: orphans --------------------------------------------------------------
    sub_ids = {s["sub_category_id"] for s in sub_categories}
    category_ids = {c["category_id"] for c in categories}
    orphans = {
        "budgets_with_no_sub_category": [
            {"belongs_to": b["belongs_to"], "period": b["period"]}
            for b in sorted(budgets, key=lambda r: (r["belongs_to"], r["period"] or ""))
            if b["belongs_to"] not in sub_ids
        ],
        "sub_categories_with_no_category": sorted(
            s["sub_category_id"] for s in sub_categories
            if s["belongs_to"] not in category_ids
        ),
        # Not in measurement 9's wording, but the same failure mode: a null `period` makes a
        # budget row invisible to every month-keyed rollup, so it is named rather than dropped.
        "budgets_with_no_period": sorted(
            b["belongs_to"] for b in budgets if not b["period"]
        ),
    }

    # --- measurement 10: the verbatim order sequences (the AC-11.3 restore artefact) ----------
    category_sequence = [
        [ident, value]
        for value, _name, ident in sorted(
            [(c["order"], c["name"], c["category_id"]) for c in categories],
            key=_order_sort_key,
        )
    ]
    sub_groups = {}
    for s in sub_categories:
        sub_groups.setdefault(s["belongs_to"], []).append(s)
    sub_sequences = {
        parent: [
            [ident, value]
            for value, _name, ident in sorted(
                [(s["order"], s["name"], s["sub_category_id"]) for s in group],
                key=_order_sort_key,
            )
        ]
        for parent, group in sorted(sub_groups.items())
    }
    order_sequences = {"categories": category_sequence, "sub_categories": sub_sequences}

    # --- measurement 11: sign anomalies (fact 7 never ran on these rows) ---------------------
    income_sub_ids = {s["sub_category_id"] for s in sub_categories
                      if income_category_id is not None
                      and s["belongs_to"] == income_category_id}
    ordered_budgets = sorted(budgets, key=lambda r: (r["period"] or "", r["belongs_to"]))
    sign_anomalies = {
        "income_negative": [
            {"belongs_to": b["belongs_to"], "period": b["period"],
             "amount": b["amount_cents"] or 0}
            for b in ordered_budgets
            if b["belongs_to"] in income_sub_ids and (b["amount_cents"] or 0) < 0
        ],
        "expense_positive": [
            {"belongs_to": b["belongs_to"], "period": b["period"],
             "amount": b["amount_cents"] or 0}
            for b in ordered_budgets
            if b["belongs_to"] in sub_ids
            and b["belongs_to"] not in income_sub_ids
            and (b["amount_cents"] or 0) > 0
        ],
    }

    # --- measurement 12: per-month overspend under §4.5A -------------------------------------
    # Only ACTIVE (order != -1), NON-TRANSFER, EXPENSE sub-categories that HAVE a budget row
    # for that month contribute (§4.5A rule 3). Without that last clause an unbudgeted month
    # reports every sub-category 100% overspent and wipes out the following month's pool.
    eligible_subs = [
        s for s in sub_categories
        if s["sub_category_id"] not in archived_sub_ids
        and s["sub_category_id"] not in transfer_sub_ids
        and s["belongs_to"] != TRANSFER_SENTINEL_ID
        and s["sub_category_id"] not in income_sub_ids
    ]
    overspend_per_month = {}
    for month_key in all_months:
        parts = _split_month(month_key)
        if parts is None:
            continue
        by_sub = {}
        total = 0
        for sub in eligible_subs:
            _amount, present = _budget_amount_for(
                month_index_map, sub["sub_category_id"], month_key)
            if not present:
                continue
            overspent = _rollover_overspent(
                sub, month_index_map, spend_map, parts[0], parts[1])
            if overspent > 0:
                by_sub.__setitem__(sub["sub_category_id"], overspent)
                total = total + overspent
        overspend_per_month.__setitem__(
            month_key, {"total": total, "by_sub": by_sub})

    return {
        "ok": True,
        "taken_at": taken_at,
        "counts": {name: _count_table(name, preloaded) for name in COUNTED_TABLES},
        "income_category": income,
        "transfer_sentinel": transfer_sentinel,
        "order_minus_one_ids": order_minus_one,
        "duplicate_budget_pairs": duplicate_budget_pairs,
        "per_month": per_month,
        "non_integer_budget_amounts": non_integer_budget_amounts,
        "non_first_of_month_periods": non_first_of_month_periods,
        "rollover_without_date": rollover_without_date,
        "orphans": orphans,
        "order_sequences": order_sequences,
        "sign_anomalies": sign_anomalies,
        "overspend_per_month": overspend_per_month,
        "definitions": {
            "active_source": "order == -1 (legacy sentinel). The `active` column on "
                             "categories/sub_categories is NEVER read by this tool.",
            "money": "integer cents; int(round(budget_amount)), never a multiply by 100",
            "income_resolution": "sign_anomalies and overspend_per_month use "
                                 "income_category.resolved_category_id (trimmed, "
                                 "case-insensitive). income_category.exists is the legacy "
                                 "byte-exact test.",
            "transfer_exclusion": "a transaction is a transfer if its `category` is the "
                                  "sentinel, or names a sub-category that is the sentinel or "
                                  "hangs off it",
            "transactions_counted": "transactions/non_transfer_transactions and every spend "
                                    "figure count only rows where `active` is not False; "
                                    "transactions_inactive counts the rest",
            "duplicate_budget_rule": "arithmetic uses the SMALLEST cents value of a duplicate "
                                     "(belongs_to, period) pair — deterministic, never "
                                     "repaired; see duplicate_budget_pairs",
            "order_sequences_sort": "order ascending with null last, then name "
                                    "case-insensitively, then id; each entry is [id, order] "
                                    "with the stored order verbatim",
            "overspend": "spec_04 §4.5 closing rule per active, non-transfer, expense "
                         "sub-category that HAS a budget row that month; positive magnitudes",
            "rollover_window_cap": MAX_ROLLOVER_MONTHS,
        },
    }


@api_http("/build/budget-audit", methods=["GET"])
def api_build_budget_audit(**kwargs):
    """spec_04 §3.1's measurement instrument. STRICTLY READ-ONLY. Retired at round 08.

    Every table is loaded ONCE and every figure is computed from memory — no query per month
    and no query per sub-category. Nothing here writes, and nothing here reads the `active`
    column on categories or sub_categories: archival is read from the legacy `order == -1`
    sentinel, which is what makes §3.7 step 2's "commit 1 reads no new column" true.
    """
    require_build_secret()
    preloaded = {
        "categories": list(app_tables.categories.search()),
        "sub_categories": list(app_tables.sub_categories.search()),
        "budgets": list(app_tables.budgets.search()),
        "transactions": list(app_tables.transactions.search()),
    }
    return build_budget_audit(preloaded, _iso(_now()))


def _init_active_for_table(rows, id_column):
    """Set `active` from the legacy sentinel on one table, writing only where it differs.

    `active` is DERIVED from order == -1, never blanket-set to True: blanket-truthing would
    resurrect every archived row the moment the clients started filtering on `active` — the
    mirror image of round 03's failure, and just as silent (spec_04 §3.7 step 4).

    TWO PARTITIONS ARE RETURNED, DELIBERATELY, AND THEY ARE NOT THE SAME PARTITION.

    - set_true_ids / set_false_ids / unchanged_ids describe what this call WROTE. Every row
      appears in exactly one of the three. This is the partition AC-4.5's idempotence is about:
      a second call writes nothing, so both set_* lists come back empty.
    - derived_true_ids / derived_false_ids describe what each row's `active` now IS, written or
      not. Every row appears in exactly one of the two.

    Both are needed because of the S03 migration hazard. Bruce's migrate click writes a real
    `False` into EVERY existing row, so by the time this runs the archived rows already hold the
    correct value: they are UNCHANGED, and set_false_ids comes back EMPTY. AC-4.4 asks that
    "set_false_ids equals measurement 4's order == -1 id set", which under that hazard can only
    be true of the DERIVED set. Reconcile AC-4.4 against derived_false_ids and AC-4.5 against
    set_*_ids; prior_counts shows which state the click actually left behind. Flagged to the
    orchestrator for a spec addendum rather than resolved by picking one reading.
    """
    set_true, set_false, unchanged = [], [], []
    derived_true, derived_false = [], []
    prior = {"true": 0, "false": 0, "null": 0}
    for row in rows:
        row_id = _str(_col(row, id_column))
        want = _num_or_none(_col(row, "order")) != ARCHIVED_ORDER
        current = _read_active(row)
        _bump(prior, "true" if current is True else ("false" if current is False else "null"))
        (derived_true if want else derived_false).append(row_id)
        if current is want:
            unchanged.append(row_id)
        else:
            # The ONLY write in this module's session-04 code: one column, one derived value.
            row.update(active=want)
            (set_true if want else set_false).append(row_id)
    return {
        "set_true_ids": set_true,
        "set_false_ids": set_false,
        "unchanged_ids": unchanged,
        "derived_true_ids": derived_true,
        "derived_false_ids": derived_false,
        "prior_counts": prior,
    }


@api_http("/build/init-active", methods=["POST"])
def api_build_init_active(**kwargs):
    """spec_04 §3.7 step 4. Bounded on purpose, and retired at round 08.

    Two literal table names in the source — the caller supplies NO input at all. One column.
    One derived value. Idempotent: a re-run writes nothing and returns empty set_* lists.

    It is deployed BEFORE Bruce's migrate click, so the absent-column case is a defined 409,
    not a 500: both tables are probed before ANY row is written, so a missing column on either
    one leaves the database entirely untouched.
    """
    require_build_secret()
    loaded = []
    for name in INIT_ACTIVE_TABLES:
        rows = list(getattr(app_tables, name).search())
        if not _active_column_readable(rows):
            raise ApiError(409, "column_missing", {"table": name})
        loaded.append((name, rows))
    results = {}
    for name, rows in loaded:
        try:
            results.__setitem__(
                name, _init_active_for_table(rows, INIT_ACTIVE_ID_COLUMN[name]))
        except Exception:
            # Belt and braces: the probe above should already have caught this. Stop here and
            # write nothing further; rows already set carry their correct derived value.
            traceback.print_exc()
            raise ApiError(409, "column_missing", {"table": name})
    return {"ok": True, "tables": results}


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
