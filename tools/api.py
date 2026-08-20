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


def api_base(cfg):
    return cfg.get("APP_BASE", "").rstrip("/") + "/_/api"


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
        secret = cfg.get("BUILD_SECRET")
        if not secret:
            die("BUILD_SECRET missing from .secrets/budgetx.env")
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

    elif args.cmd == "session":
        status, payload = call(cfg, "GET", "/build/session", build_secret=True,
                               params={"token_hash": args.token_hash})
        require_ok(status, payload)
        print(json.dumps(payload.get("session"), indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
