#!/usr/bin/env python3
"""Budget X API CLI — the round-01 toolchain.

Reads .secrets/budgetx.env (gitignored) for APP_BASE, BUILD_SECRET, TEST1_*, TEST2_*.

SECRET DISCIPLINE (spec_01 §3.3, AC-9.4; spec_02 §3.3, AC-3): no secret, password, full token
or full hash is ever written to stdout or stderr, on success OR on error. Error paths are where
secrets leak, so nothing here prints a request header, a repr of the config, or a URL carrying
credentials. Anything token- or digest-shaped goes through mask() first — spec_02 AC-3.1 scans
this tool's captured output for any 64-lowercase-hex string and expects none. A password is
never accepted as a command-line argument either: it would land in shell history and in ps.

Logins default to TEST2 (spec_02 §6 — TEST2 is the account everything is driven as).

  login [--account {1,2}] [--email E] | whoami | logout | version | counts
  build-upload <file> --version V [--slug S] [--kind K]
  build-promote <record_uid> | build-list [--slug S] [--kind K] | session <token_hash>

Round 03 verification commands (spec_03 §3.1, §4):
  bootstrap [--include transactions,budgets] [--out FILE]
  txn-categorise (--id ID --category CAT | --batch FILE)     CAT may be the literal `null`
  txn-update --id ID --field K=V [--field K=V ...]           amount_cents is cast to int
  txn-create --date D --amount-cents N --account A [--description X] [--category C]
             [--notes N] [--transfer-account A]
  txn-archive --id ID [--id ID ...] | txn-restore --id ID [--id ID ...]

Round 04 verification commands (spec_04 §3.2, §4):
  budget-summary --month YYYY-MM [--out FILE]
  budget-amount --sub S --month M --amount-cents N
  budget-notes  --sub S --month M --notes TEXT
  budget-open-month --month M --copy-from M
  cat-create --name N --colour-back #RRGGBB --colour-text #RRGGBB
  cat-update --id C --field K=V [...]          | cat-reorder --id C [--id C ...]
  cat-archive --id C                           | cat-restore --id C
  subcat-create --name N --belongs-to C [--icon I] [--roll-over] [--roll-over-date YYYY-MM]
  subcat-update --id S --field K=V [...]       | subcat-reorder --belongs-to C --id S [--id S..]
  subcat-archive --id S                        | subcat-restore --id S
  budget-audit [--out FILE]                    | init-active

EVERY round-04 write command accepts `--raw K=JSON` (repeatable). The value is parsed as JSON
and merged into the body LAST, so a reviewer can post a float, a string or a null where an
integer is contracted, or a forged `category_id` / `order`, without a second tool. That is what
AC-2.1, AC-2.8 and AC-3.1 need to drive.

Every one prints the PARSED response, routed through emit() so the redaction that covers the
older commands covers these too — including their error paths. --out writes the raw response
body to a file (a file is not stdout); the bootstrap payload carries no secret, only app data.

BUILD_SECRET (spec_04 §3.11 fix 8, AC-12.6): an environment variable of that name OVERRIDES the
value in .secrets/budgetx.env. Which source was used is announced on stderr — by NAME, never by
value — so an override is demonstrable without a secret reaching captured output.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".secrets", "budgetx.env")
TOKEN_PATH = os.path.join(ROOT, ".secrets", ".token")


# Any long lowercase-hex run in an error message is a token, a digest or a token_hash that has
# no business on stderr. `session` puts a token_hash in a query string, and some urllib failures
# stringify the URL — so the failure path is redacted rather than trusted (spec_02 AC-3.1).
_HEXISH = re.compile(r"[0-9a-f]{32,}")

# A bare integer in a --field value. Money never passes through here (budget amounts have their
# own typed flag), so this only ever coerces things like an `order` a reviewer is forging.
_INTISH = re.compile(r"^-?\d+$")


def die(msg, code=1):
    """Fail with a short reason. Never echoes a secret, a token or a full hash."""
    sys.stderr.write("error: %s\n" % _HEXISH.sub(lambda m: mask(m.group(0)), str(msg)))
    sys.exit(code)


def load_env():
    if not os.path.exists(ENV_PATH):
        die("missing .secrets/budgetx.env — ask Bruce; never hardcode a value")
    cfg = {}
    with open(ENV_PATH) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def mask(token):
    """First 6 characters then an ellipsis. Never the whole token, hash or digest.

    Six characters is enough to correlate two lines of output with each other and far too few
    to be used as a credential.
    """
    if not token:
        return "(none)"
    return token[:6] + "…"


def redact(text):
    """Every long lowercase-hex run masked. The single funnel for anything printed by the
    round-03 commands, so a digest cannot reach captured output down ANY path, including an
    unexpected server message echoed inside a response body (spec_02 AC-3.1)."""
    return _HEXISH.sub(lambda m: mask(m.group(0)), str(text))


def emit(obj):
    """Print a parsed response. A transaction `hash` is a short numeric-ish string like
    "3082026-66981ZZ-ACC-CHEQUE" and a transaction_id is a uuid4 whose longest hex run is 12
    characters, so neither trips the 32+-lowercase-hex rule — but the output still goes through
    redact() rather than relying on that, because the rule is the contract, not the shape."""
    print(redact(json.dumps(obj, indent=1, sort_keys=True)))


def api_base(cfg):
    return cfg.get("APP_BASE", "").rstrip("/") + "/_/api"


def build_secret_from(cfg):
    """(secret, source-name). The ENVIRONMENT WINS (spec_04 §3.11 fix 8, AC-12.6).

    An override in the environment lets a reviewer drive a build endpoint with a deliberately
    wrong secret — AC-4.3 needs exactly that — without editing the gitignored env file. The
    source is a NAME, never a value; nothing here returns or prints the secret itself.
    """
    env_value = os.environ.get("BUILD_SECRET")
    if env_value:
        return env_value, "environment override (BUILD_SECRET)"
    return cfg.get("BUILD_SECRET"), ".secrets/budgetx.env"


def parse_raw(pairs):
    """`--raw K=JSON` -> {K: parsed}. A value that is not valid JSON is kept as a plain string,
    so `--raw name=hello` works as well as `--raw amount_cents=null`."""
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            die("--raw expects K=JSON")
        key, value = pair.split("=", 1)
        try:
            out[key.strip()] = json.loads(value)
        except ValueError:
            out[key.strip()] = value
    return out


def parse_fields(pairs, field="--field"):
    """`K=V` -> {K: V}, with the JSON literals `null`, `true` and `false` and a bare integer
    recognised. Anything else stays a string, which is what a name or a colour wants."""
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            die("%s expects K=V" % field)
        key, value = pair.split("=", 1)
        key = key.strip()
        if value in ("null", "true", "false") or _INTISH.match(value):
            out[key] = json.loads(value)
        else:
            out[key] = value
    return out


def with_raw(body, args):
    """Merge --raw overrides in LAST, so they win over the typed flags."""
    return {**body, **parse_raw(getattr(args, "raw", []))}


def add_raw(parser):
    parser.add_argument("--raw", dest="raw", action="append", default=[], metavar="K=JSON",
                        help="repeatable; parsed as JSON and merged into the body last — the "
                             "escape hatch for negative tests (a float where an int is "
                             "contracted, a forged id, an unknown key)")
    return parser


def report(status, payload, out=None):
    """The round-03/04 house style: HTTP status, the parsed body through emit(), exit 2 on a
    non-2xx so a shell loop can tell a refusal from a success."""
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
        print("wrote %s" % out)
    print("HTTP %s" % status)
    emit(payload)
    if not (200 <= status < 300):
        sys.exit(2)
    return payload


def call(cfg, method, path, body=None, params=None, token=None, build_secret=False):
    """Returns (status, parsed_or_text). Raises nothing that would print a secret."""
    url = api_base(cfg) + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer %s" % token)
    if build_secret:
        secret, source = build_secret_from(cfg)
        if not secret:
            die("BUILD_SECRET missing from the environment and from .secrets/budgetx.env")
        # The SOURCE is announced, never the value — that is what makes AC-12.6's override
        # demonstrable without a secret reaching captured output. stderr, so --out and every
        # JSON-parsing caller are unaffected.
        sys.stderr.write("build secret: %s\n" % source)
        req.add_header("X-Build-Secret", secret)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", "replace")
        status = err.code
    except Exception as exc:
        # Deliberately narrow: the class name and message only, never the request or its headers.
        die("request failed (%s): %s" % (type(exc).__name__, str(exc)[:160]))
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


def require_ok(status, payload):
    if not (200 <= status < 300):
        code = payload.get("error") if isinstance(payload, dict) else None
        die("HTTP %s%s" % (status, (" — %s" % code) if code else ""), 2)
    return payload


def read_token():
    if not os.path.exists(TOKEN_PATH):
        die("no cached token — run: python3 tools/api.py login")
    with open(TOKEN_PATH) as fh:
        return fh.read().strip()


def write_token(token):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    # Create with 0600 from the outset rather than chmod-ing afterwards.
    fd = os.open(TOKEN_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(token)
    os.chmod(TOKEN_PATH, 0o600)


def main():
    ap = argparse.ArgumentParser(prog="tools/api.py", description="Budget X API CLI")
    sub = ap.add_subparsers(dest="cmd")
    lg = sub.add_parser("login")
    lg.add_argument("--email", default=None, help="override the address; password still comes "
                                                  "from the selected account's env pair")
    lg.add_argument("--account", choices=["1", "2"], default="2",
                    help="which TESTn_* pair to use (default 2 — spec_02 §6)")
    sub.add_parser("whoami")
    sub.add_parser("logout")
    sub.add_parser("version")
    sub.add_parser("counts")
    up = sub.add_parser("build-upload")
    up.add_argument("file")
    up.add_argument("--version", required=True)
    up.add_argument("--slug", default="x")
    up.add_argument("--kind", default="html")
    sub.add_parser("build-promote").add_argument("record_uid")
    bl = sub.add_parser("build-list")
    bl.add_argument("--slug", default=None)
    bl.add_argument("--kind", default=None)
    sub.add_parser("session").add_argument("token_hash")

    # ---- round 03 --------------------------------------------------------------------------
    bs = sub.add_parser("bootstrap")
    bs.add_argument("--include", default=None,
                    help="pass `transactions` for the §4.2 array; anything else is ignored "
                         "by the server and must leave the v1 key-set intact")
    bs.add_argument("--out", default=None, help="write the RAW response JSON to this file")

    tc = sub.add_parser("txn-categorise")
    tc.add_argument("--id", dest="ids", action="append", default=[])
    tc.add_argument("--category", default=None,
                    help="a sub_category_id, the transfer sentinel, or the literal `null`")
    tc.add_argument("--batch", default=None, help="a JSON file: a list of §3.1 items, or an "
                                                  "object with an `items` key")

    tu = sub.add_parser("txn-update")
    tu.add_argument("--id", required=True)
    tu.add_argument("--field", dest="fields", action="append", default=[], metavar="K=V",
                    help="repeatable; amount_cents is cast to int, `null` means JSON null")

    tn = sub.add_parser("txn-create")
    tn.add_argument("--date", required=True, help="ISO YYYY-MM-DD")
    tn.add_argument("--amount-cents", required=True, type=int,
                    help="INTEGER CENTS — the column already holds cents; never multiply by 100")
    tn.add_argument("--account", required=True)
    tn.add_argument("--description", default=None)
    tn.add_argument("--category", default=None)
    tn.add_argument("--notes", default=None)
    tn.add_argument("--transfer-account", default=None)

    for name in ("txn-archive", "txn-restore"):
        pr = sub.add_parser(name)
        pr.add_argument("--id", dest="ids", action="append", default=[], required=True)

    # ---- round 04 --------------------------------------------------------------------------
    bsum = sub.add_parser("budget-summary")
    bsum.add_argument("--month", required=True, help="YYYY-MM")
    bsum.add_argument("--out", default=None, help="write the RAW response JSON to this file")

    bam = add_raw(sub.add_parser("budget-amount"))
    bam.add_argument("--sub", dest="sub_category_id", required=True)
    bam.add_argument("--month", required=True, help="YYYY-MM")
    bam.add_argument("--amount-cents", type=int, default=None,
                     help="INTEGER CENTS — the column already holds cents; never multiply by "
                          "100. Omit and use --raw amount_cents=<json> to send a bad type.")

    bno = add_raw(sub.add_parser("budget-notes"))
    bno.add_argument("--sub", dest="sub_category_id", required=True)
    bno.add_argument("--month", required=True, help="YYYY-MM")
    bno.add_argument("--notes", default="", help="an EMPTY string clears the note (fact 10)")

    bom = add_raw(sub.add_parser("budget-open-month"))
    bom.add_argument("--month", default=None, help="YYYY-MM — the month being opened")
    bom.add_argument("--copy-from", dest="copy_from", default=None, help="YYYY-MM")

    cc = add_raw(sub.add_parser("cat-create"))
    cc.add_argument("--name", default=None)
    cc.add_argument("--colour-back", dest="colour_back", default=None, help="#RRGGBB")
    cc.add_argument("--colour-text", dest="colour_text", default=None, help="#RRGGBB")

    cu = add_raw(sub.add_parser("cat-update"))
    cu.add_argument("--id", dest="category_id", required=True)
    cu.add_argument("--field", dest="fields", action="append", default=[], metavar="K=V",
                    help="repeatable; a value of `null` means JSON null")

    cr = add_raw(sub.add_parser("cat-reorder"))
    cr.add_argument("--id", dest="ids", action="append", default=[],
                    help="repeatable, in the DESIRED order — the COMPLETE non-archived set")

    for name in ("cat-archive", "cat-restore"):
        pr = add_raw(sub.add_parser(name))
        pr.add_argument("--id", dest="category_id", required=True)

    sc = add_raw(sub.add_parser("subcat-create"))
    sc.add_argument("--name", default=None)
    sc.add_argument("--belongs-to", dest="belongs_to", default=None)
    sc.add_argument("--icon", default=None)
    sc.add_argument("--roll-over", dest="roll_over", action="store_true")
    sc.add_argument("--roll-over-date", dest="roll_over_date", default=None,
                    help="YYYY-MM (or YYYY-MM-DD)")

    su = add_raw(sub.add_parser("subcat-update"))
    su.add_argument("--id", dest="sub_category_id", required=True)
    su.add_argument("--field", dest="fields", action="append", default=[], metavar="K=V",
                    help="repeatable; `null` means JSON null, `true`/`false` mean booleans")

    sr = add_raw(sub.add_parser("subcat-reorder"))
    sr.add_argument("--belongs-to", dest="belongs_to", required=True)
    sr.add_argument("--id", dest="ids", action="append", default=[],
                    help="repeatable, in the DESIRED order — the COMPLETE non-archived set")

    for name in ("subcat-archive", "subcat-restore"):
        pr = add_raw(sub.add_parser(name))
        pr.add_argument("--id", dest="sub_category_id", required=True)

    ba = sub.add_parser("budget-audit")
    ba.add_argument("--out", default=None, help="write the RAW response JSON to this file")
    ia = sub.add_parser("init-active")
    ia.add_argument("--out", default=None, help="write the RAW response JSON to this file")

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        sys.exit(1)

    cfg = load_env()

    if args.cmd == "login":
        # spec_02 §6: everything is driven as TEST2, so TEST2 is the default. (spec_02 §3.3
        # said only "login"; the S01 tool read TEST1_* — filed as spec_02 Addendum 1.)
        prefix = "TEST%s" % getattr(args, "account", "2")
        email = getattr(args, "email", None) or cfg.get(prefix + "_EMAIL")
        password = cfg.get(prefix + "_PASSWORD")
        if not email or not password:
            die("%s_EMAIL / %s_PASSWORD missing from .secrets/budgetx.env" % (prefix, prefix))
        status, payload = call(cfg, "POST", "/auth/login",
                               body={"email": email, "password": password})
        require_ok(status, payload)
        token = payload.get("token")
        if not token:
            die("login returned no token", 2)
        write_token(token)
        print("logged in as %s" % payload.get("email"))
        print("token %s (cached at .secrets/.token, mode 0600)" % mask(token))
        print("expires_at %s" % payload.get("expires_at"))
        # Masked, not full (spec_02 §3.3, S01 finding 6). The full hash is a lookup key for
        # /build/session and belongs in a request, never in captured output.
        print("token_hash %s" % mask(hashlib.sha256(token.encode("utf-8")).hexdigest()))

    elif args.cmd == "whoami":
        status, payload = call(cfg, "GET", "/me", token=read_token())
        require_ok(status, payload)
        print(payload.get("email"))

    elif args.cmd == "logout":
        status, payload = call(cfg, "POST", "/auth/logout", token=read_token())
        require_ok(status, payload)
        print("revoked")

    elif args.cmd == "version":
        status, payload = call(cfg, "GET", "/build/version", build_secret=True)
        require_ok(status, payload)
        print(json.dumps(payload.get("modules"), indent=1))

    elif args.cmd == "counts":
        status, payload = call(cfg, "GET", "/build/counts", build_secret=True)
        require_ok(status, payload)
        print(json.dumps(payload.get("counts"), indent=1, sort_keys=True))

    elif args.cmd == "build-upload":
        with open(args.file, encoding="utf-8") as fh:
            html = fh.read()
        local = hashlib.sha256(html.encode("utf-8")).hexdigest()
        status, payload = call(cfg, "POST", "/build/upload", build_secret=True,
                               body={"slug": args.slug, "kind": args.kind,
                                     "version": args.version, "html": html})
        require_ok(status, payload)
        remote = payload.get("sha256")
        print("record_uid %s" % payload.get("record_uid"))
        print("sha256     %s" % mask(remote))
        print("bytes      %s" % payload.get("bytes"))
        # The verdict is computed on the FULL digests; only the display is masked, so no
        # 64-hex string reaches captured output (spec_02 AC-3.1). The full digest stays
        # available from /build/list's JSON for the served-bytes comparison (spec_02 §7).
        print("local sha  %s  %s" % (mask(local), "MATCH" if local == remote else "MISMATCH"))
        if local != remote:
            sys.exit(3)

    elif args.cmd == "build-promote":
        status, payload = call(cfg, "POST", "/build/promote", build_secret=True,
                               body={"record_uid": args.record_uid})
        require_ok(status, payload)
        print("promoted %s (slug %s, version %s)" % (payload.get("record_uid"),
                                                     payload.get("slug"), payload.get("version")))

    elif args.cmd == "build-list":
        status, payload = call(cfg, "GET", "/build/list", build_secret=True,
                               params={"slug": args.slug, "kind": args.kind})
        require_ok(status, payload)
        builds = payload.get("builds", [])
        row_fmt = "%-38s %-10s %-10s %-8s %-5s %-26s %s"
        # uploaded_by is the read-back that proves the server stamped it (spec_02 AC-2.1/2.3).
        print(row_fmt % ("record_uid", "slug", "version", "bytes", "cur", "uploaded_at",
                         "uploaded_by"))
        for b in builds:
            print(row_fmt % (b["record_uid"], b["slug"], b["version"], b["bytes"],
                             b["is_current"], b["uploaded_at"], b.get("uploaded_by")))
        print("(%d build(s))" % len(builds))

    elif args.cmd == "bootstrap":
        params = {"include": args.include} if args.include is not None else None
        status, payload = call(cfg, "GET", "/app/bootstrap", params=params,
                               token=read_token())
        require_ok(status, payload)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1, sort_keys=True)
            print("wrote %s" % args.out)
        # A compact summary: the KEY-SET is the thing AC-1.1/1.3 turn on, so it is printed in
        # full and in sorted order; the arrays are reported by length, never dumped.
        keys = sorted(payload.keys()) if isinstance(payload, dict) else []
        print("keys (%d): %s" % (len(keys), ", ".join(keys)))
        print("transactions key present: %s" % ("transactions" in keys))
        for key in ("accounts", "categories", "sub_categories", "transactions"):
            if isinstance(payload.get(key), list):
                print("%-16s %d" % (key, len(payload[key])))
        txns = payload.get("transactions")
        if isinstance(txns, list) and txns:
            non_int = [t for t in txns
                       if not isinstance(t.get("amount_cents"), int)
                       or isinstance(t.get("amount_cents"), bool)]
            print("amount_cents all int: %s" % (not non_int))
            print("active all bool:      %s"
                  % all(isinstance(t.get("active"), bool) for t in txns))
            print("sum(amount_cents):    %d" % sum(t["amount_cents"] for t in txns
                                                   if isinstance(t.get("amount_cents"), int)))
            print("first row:")
            emit(txns[0])

    elif args.cmd == "txn-categorise":
        if args.batch:
            with open(args.batch, encoding="utf-8") as fh:
                loaded = json.load(fh)
            items = loaded["items"] if isinstance(loaded, dict) else loaded
        else:
            if not args.ids:
                die("txn-categorise needs --id (repeatable) or --batch FILE")
            category = None if args.category in (None, "null") else args.category
            items = [{"transaction_id": i, "category": category} for i in args.ids]
        status, payload = call(cfg, "POST", "/txn/categorise", body={"items": items},
                               token=read_token())
        print("HTTP %s" % status)
        emit(payload)
        if not (200 <= status < 300):
            sys.exit(2)

    elif args.cmd == "txn-update":
        fields = {}
        for pair in args.fields:
            if "=" not in pair:
                die("--field expects K=V")
            key, value = pair.split("=", 1)
            key = key.strip()
            if value == "null":
                fields[key] = None
            elif key == "amount_cents":
                try:
                    fields[key] = int(value)
                except ValueError:
                    die("amount_cents must be an integer number of cents")
            else:
                fields[key] = value
        if not fields:
            die("txn-update needs at least one --field K=V")
        status, payload = call(cfg, "POST", "/txn/update",
                               body={"transaction_id": args.id, "fields": fields},
                               token=read_token())
        print("HTTP %s" % status)
        emit(payload)
        if not (200 <= status < 300):
            sys.exit(2)

    elif args.cmd == "txn-create":
        # amount_cents goes over the wire exactly as typed. NO multiply by 100 anywhere in this
        # tool: the column already holds cents (spec_03 §0.1), and a multiply here would inflate
        # the figure 100x just as surely as one on the server.
        body = {"date": args.date, "amount_cents": args.amount_cents, "account": args.account}
        for key, value in (("description", args.description), ("category", args.category),
                           ("notes", args.notes),
                           ("transfer_account", getattr(args, "transfer_account", None))):
            if value is not None:
                body[key] = None if value == "null" else value
        status, payload = call(cfg, "POST", "/txn/create", body=body, token=read_token())
        print("HTTP %s" % status)
        emit(payload)
        if not (200 <= status < 300):
            sys.exit(2)

    elif args.cmd in ("txn-archive", "txn-restore"):
        path = "/txn/archive" if args.cmd == "txn-archive" else "/txn/restore"
        status, payload = call(cfg, "POST", path, body={"transaction_ids": args.ids},
                               token=read_token())
        print("HTTP %s" % status)
        emit(payload)
        if not (200 <= status < 300):
            sys.exit(2)

    # ---- round 04 ----------------------------------------------------------------------------

    elif args.cmd == "budget-summary":
        status, payload = call(cfg, "GET", "/budget/summary",
                               params={"month": args.month}, token=read_token())
        report(status, payload, out=args.out)

    elif args.cmd == "budget-amount":
        body = {"sub_category_id": args.sub_category_id, "month": args.month}
        if args.amount_cents is not None:
            # Straight over the wire as typed. NO multiply by 100 anywhere in this tool: the
            # column already holds cents, and a multiply here would inflate the figure 100x
            # just as surely as one on the server.
            body = {**body, "amount_cents": args.amount_cents}
        status, payload = call(cfg, "POST", "/budget/amount", body=with_raw(body, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd == "budget-notes":
        body = {"sub_category_id": args.sub_category_id, "month": args.month,
                "notes": args.notes}
        status, payload = call(cfg, "POST", "/budget/notes", body=with_raw(body, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd == "budget-open-month":
        # Neither key is defaulted here either: an omitted flag sends no key at all, so the
        # server's "both are required" rule is drivable from the CLI.
        body = {}
        if args.month is not None:
            body = {**body, "month": args.month}
        if args.copy_from is not None:
            body = {**body, "copy_from": args.copy_from}
        status, payload = call(cfg, "POST", "/budget/open-month", body=with_raw(body, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd == "cat-create":
        body = {}
        for key, value in (("name", args.name), ("colour_back", args.colour_back),
                           ("colour_text", args.colour_text)):
            if value is not None:
                body = {**body, key: value}
        status, payload = call(cfg, "POST", "/cat/create", body=with_raw(body, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd == "cat-update":
        body = {"category_id": args.category_id, "fields": parse_fields(args.fields)}
        status, payload = call(cfg, "POST", "/cat/update", body=with_raw(body, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd == "cat-reorder":
        status, payload = call(cfg, "POST", "/cat/reorder",
                               body=with_raw({"order": args.ids}, args), token=read_token())
        report(status, payload)

    elif args.cmd in ("cat-archive", "cat-restore"):
        path = "/cat/archive" if args.cmd == "cat-archive" else "/cat/restore"
        status, payload = call(cfg, "POST", path,
                               body=with_raw({"category_id": args.category_id}, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd == "subcat-create":
        body = {"roll_over": bool(args.roll_over)}
        for key, value in (("name", args.name), ("belongs_to", args.belongs_to),
                           ("icon", args.icon), ("roll_over_date", args.roll_over_date)):
            if value is not None:
                body = {**body, key: None if value == "null" else value}
        status, payload = call(cfg, "POST", "/subcat/create", body=with_raw(body, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd == "subcat-update":
        body = {"sub_category_id": args.sub_category_id, "fields": parse_fields(args.fields)}
        status, payload = call(cfg, "POST", "/subcat/update", body=with_raw(body, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd == "subcat-reorder":
        body = {"belongs_to": args.belongs_to, "order": args.ids}
        status, payload = call(cfg, "POST", "/subcat/reorder", body=with_raw(body, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd in ("subcat-archive", "subcat-restore"):
        path = "/subcat/archive" if args.cmd == "subcat-archive" else "/subcat/restore"
        status, payload = call(cfg, "POST", path,
                               body=with_raw({"sub_category_id": args.sub_category_id}, args),
                               token=read_token())
        report(status, payload)

    elif args.cmd == "budget-audit":
        status, payload = call(cfg, "GET", "/build/budget-audit", build_secret=True)
        report(status, payload, out=args.out)

    elif args.cmd == "init-active":
        # The one bounded write in the migration scaffolding. It takes NO input: the two table
        # names are literals in the server's source (spec_04 §3.7).
        status, payload = call(cfg, "POST", "/build/init-active", body={}, build_secret=True)
        report(status, payload, out=args.out)

    elif args.cmd == "session":
        status, payload = call(cfg, "GET", "/build/session", build_secret=True,
                               params={"token_hash": args.token_hash})
        require_ok(status, payload)
        session = payload.get("session")
        if session is None:
            # spec_04 §3.11 fix 8 / AC-12.6: v1 printed `null` and exited 0, so a typo in a
            # token_hash was indistinguishable from a genuine lookup. The message names the
            # outcome and the exit code differs from both success (0) and an HTTP failure (2).
            die("no session found for that token_hash", 4)
        print(json.dumps(session, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
