# Budget X — Spec 01: the API spine

**Status:** APPROVED AND LOCKED — Bruce, 2026-08-19. Build against this text as written. **Do not edit
the approved text in place**; corrections go in §10 as dated addenda.

**Round:** 01 · **Written:** 2026-08-19 · **Source:** `scratch/brief_for_spec_01.md` (Code, 2026-08-19)

**Build model: Opus.** This is the auth and token spine — the carve-out the migration-phase
cheap-model exception explicitly names. Do not build it on Sonnet.

---

## 1. WHY

Budget X is a classic Anvil app: Forms calling `@anvil.server.callable`, with the business logic on the
client. The target is IAMS's shape — HTTP endpoints, authority server-side, one responsive HTML client
served from the database and versioned through build/promote.

**Nothing in that migration can be verified until the spine exists.** There are no HTTP endpoints today,
so there is no `tools/api.py`, no version ping, and no way to prove an acceptance criterion by observed
API behaviour. Round 01 buys the ability to test every round after it.

**This round is deliberately invisible to users.** The existing Forms app keeps serving at
`https://budget-x.anvil.app` untouched for the whole round. If a user would notice this round happened,
it has gone wrong.

---

## 2. WHAT MUST NOT CHANGE

Every item here is a hard boundary. AC-8 and AC-11 exist to prove it.

1. **The app root.** `https://budget-x.anvil.app` keeps serving the existing Forms app. Register no HTTP
   endpoint at path `/`, and do not change the startup form (`Frame`).
2. **`client_code/`** — not one byte. Neither UI tree is touched this round.
3. **The five existing server modules** — `ServerModule1`, `account_work`, `budget_work`, `csv_handler`,
   `transaction_work`. No edits, no refactors, no "while I'm here".
4. **The nine existing tables** — `accounts`, `budgets`, `categories`, `files`, `settings`,
   `sub_categories`, `test_csv`, `transactions`, `users`. No column added, renamed, retyped or removed.
   The two new tables in §4 are additions and nothing else.
5. **Business data.** This round writes to `api_sessions` and `app_versions` only.
   **One carve-out, and only one:** the Anvil Users service performs its own bookkeeping on the test
   account's `users` row when it authenticates — `last_login` on success, `n_password_failures` on
   failure. That is the platform writing, is expected, and is permitted. **Every other business-table
   write is forbidden**, live or throwaway. There is no audit log on this app to reconstruct from.
6. **The GitHub↔Anvil sync stays UNLINKED.** Do not relink it. Deploy is `git push anvil master`,
   mirrored to `origin`. Never force-push, to either remote.
7. **The Anvil Users service stays the credential store.** The API issues session tokens *on top of* it;
   it does not replace it and never reads or writes `users.password_hash` directly.
8. **Bruce's schema-migrate click.** Never click through a schema-mismatch migration. See §6.

---

## 3. SCOPE

Two new server modules, one new CLI tool, two new tables. Nothing else.

### 3.0 Rules that apply to both modules

1. **All `app_tables` access happens inside function bodies.** No module-level table reference, no
   module-level `app_tables.x` lookup, no import-time query. Both modules must import cleanly **before
   the new tables exist** — AC-1.4 depends on it, and a module-level reference takes `/build/version`
   down with it.
2. **Header lookups are case-insensitive.** Anvil normalises header names (observed as lowercase), so
   `headers["X-Build-Secret"]` may raise `KeyError` → 500. Look headers up case-insensitively and
   default to `None`; never let a missing header become a 500. AC-1.3 and AC-5.5 both fail on a 500.
3. **JSON responses are explicit.** Serialise with `json.dumps` and set
   `Content-Type: application/json` on the response object yourself rather than relying on Anvil to
   infer it. AC-1 and AC-6 read the response headers.
4. **Self-contained modules.** Each module declares its own `ApiError` / `api_http` (and `ServerApi` its
   own `require_auth`) rather than importing across modules, per `CLAUDE.md` "Architectural intent".

### 3.1 `server_code/ServerApi.py` — the spine

**`ApiError`** — an exception carrying `status` (int) and `code` (short machine string, e.g.
`invalid_credentials`).

**`api_http(path, methods)`** — a decorator wrapping `@anvil.server.http_endpoint`. It must:

1. Call the handler and, on success, **return** `anvil.server.HttpResponse(200, json.dumps(body))` with
   `Content-Type: application/json`.
2. Catch `ApiError` and **return** `HttpResponse(err.status, {"ok": false, "error": err.code})`.
   **A non-200 from an Anvil http_endpoint must be RETURNED, never raised** — a raised exception becomes
   a 500 with an Anvil error page, which fails AC-1.3, AC-3 and AC-5.5.
3. Catch any other `Exception` and return `HttpResponse(500, {"ok": false, "error": "server_error"})`.
   **The response body never contains a traceback, a stack frame, a module path or a table name.** Log
   the traceback server-side (`print`) so it reaches the Anvil app logs.
4. Never emit a body containing a token, a password, a password hash, or the build secret, on any path.

**`require_auth()`** — called explicitly inside the body of every protected handler, not relied on
through decorator ordering. It:

1. Reads the `Authorization` header case-insensitively from `anvil.server.request.headers`.
2. Requires the exact form `Bearer <token>` where `<token>` is 64 lowercase hex characters. Anything
   else — absent, wrong scheme, no space, wrong length, non-hex — is `ApiError(401, "unauthorized")`.
3. Looks up `api_sessions` by `token_hash = sha256(token.encode()).hexdigest()`. **The raw token is
   never stored.** No row → 401.
4. Requires `revoked_at is None` **and** `expires_at > now (UTC)` **and** `active is True`. Otherwise 401.
5. Returns the linked `users` row.

Every 401 from `require_auth` returns the **same** body — `{"ok": false, "error": "unauthorized"}` — and
carries no account data, no email, and no hint about which check failed.

**Endpoints.** Anvil serves `@anvil.server.http_endpoint("/foo")` at
`https://budget-x.anvil.app/_/api/foo`. That prefix is the platform's, not ours.

| Method | Path | Auth | Body in | 200 body out |
|---|---|---|---|---|
| POST | `/auth/login` | none | `{"email","password"}` | `{"ok":true,"token","expires_at","email"}` |
| GET | `/me` | Bearer | — | `{"ok":true,"email","expires_at"}` |
| POST | `/auth/logout` | Bearer | — | `{"ok":true,"revoked":true}` |

**`POST /auth/login`** — checks the credentials against the **Anvil Users service**. Expected shape:
`anvil.users.login_with_email(email, password)` inside a `try`, followed immediately by
`anvil.users.logout()` so the HTTP API stays stateless and no Anvil session leaks between requests.

- **Catch the whole `anvil.users` failure family, not just `AuthenticationFailed`.** `anvil.users` also
  raises for unconfirmed email, disabled accounts, too many password failures and (if configured) MFA.
  **Every one of them maps to the same 401 `invalid_credentials`.** Left uncaught they become 500s and
  fail AC-2.3's identical-body comparison. If the platform's exception names differ from what you
  expect, catch the base `anvil.users.AuthenticationFailed` **plus** a broad `Exception` inside the
  credential-check block only, map it to 401, and record the correction as a §10 addendum.
- On success, mint a token with `secrets.token_hex(32)` (64 hex chars), store its sha256 in a new
  `api_sessions` row, and return the raw token **once, in this response only**.
- **Expiry: 12 hours absolute from issue.** `expires_at = issued_at + 12h`, UTC, and it **does not
  extend on use**. Return `expires_at` as an ISO-8601 UTC string.
- **Failure is uniform.** Wrong password and unknown email both return **HTTP 401** with the body
  `{"ok": false, "error": "invalid_credentials"}` — byte-identical, with no `token` key present and
  nothing distinguishing "no such account" from "wrong password".
- Missing/blank `email` or `password`, and a non-JSON body, return **400**
  `{"ok": false, "error": "bad_request"}`.
- **Deliberately deferred, not overlooked:** there is no rate limit and no timing equalisation on this
  endpoint this round. Anvil Users' own `n_password_failures` is the only brake. This is a stated
  decision so the reviewer does not raise it as a finding; it is Session 02+ work.

**`GET /me`** — `require_auth()`, then return the authenticated account's email and the session's
`expires_at`. On any auth failure: 401, and **no `email` key anywhere in the body**.

**`POST /auth/logout`** — `require_auth()`, then set `revoked_at = now` and `active = False` on that
session row. Returns 200 once. A second call with the same token returns 401 — the token is already
dead. That is correct behaviour, not a bug.

### 3.2 `server_code/ServerBuildTools.py` — the pipeline

**Gate.** Every `/build/*` endpoint requires the header `X-Build-Secret` to equal the Anvil App Secret
named **`build_secret`** (`anvil.secrets.get_secret("build_secret")`). Look the header up
case-insensitively, treat absent as `None`, and compare with `hmac.compare_digest` on encoded bytes
(guarding the `None` case first). Missing or wrong → **401** `{"ok": false, "error": "unauthorized"}`.
**The build secret is never a query parameter, never in a response body, never in a log line.**

| Method | Path | Gate | In | 200 body out |
|---|---|---|---|---|
| GET | `/build/version` | `X-Build-Secret` | — | `{"ok":true,"modules":{...}}` |
| POST | `/build/upload` | `X-Build-Secret` | `{"slug","kind","version","html"}` | `{"ok":true,"record_uid","sha256","bytes"}` |
| POST | `/build/promote` | `X-Build-Secret` | `{"record_uid"}` | `{"ok":true,"record_uid","slug","version"}` |
| GET | `/build/list` | `X-Build-Secret` | `?slug=&kind=` | `{"ok":true,"builds":[…]}` |
| GET | `/build/session` | `X-Build-Secret` | `?token_hash=` | `{"ok":true,"session":{…}}` or `{"ok":true,"session":null}` |
| GET | `/build/counts` | `X-Build-Secret` | — | `{"ok":true,"counts":{table:n,…}}` |
| GET | `/x` | **none** | `?slug=` | the promoted HTML |

- **`GET /build/version` touches no table.** It returns only the module version stamps read from
  in-module constants, e.g. `{"ok":true,"modules":{"ServerApi":"v1","ServerBuildTools":"v1"}}`. This is
  deliberate: it is the one endpoint that must answer **before** the schema migration, so AC-1 is
  judgeable on the near side of the park. **Do not add a table read to it.**
- **`POST /build/upload`** — creates an `app_versions` row with `is_current = False`. Computes `sha256`
  and `bytes` over the HTML encoded as UTF-8. `slug` defaults to `"x"`, `kind` to `"html"`. **`version`
  is required** — absent, blank, or starting `0.` returns 400 `{"ok":false,"error":"bad_request"}`
  (Bruce's standing rule: never promote a `0.x` build). Empty `html` returns 400.
- **`POST /build/promote`** — sets `is_current = True` on the named row and `is_current = False` on
  **every other row with the same `slug` and `kind`**, and stamps `promoted_at`. **Exactly one row per
  (slug, kind) may have `is_current = True`** — the invariant AC-5.4 checks. Unknown `record_uid` → 404
  `{"ok": false, "error": "not_found"}`.
- **`GET /build/list`** — newest `uploaded_at` first. `slug` and `kind` are optional filters; with
  neither, return every row. Each entry carries `record_uid`, `slug`, `kind`, `version`, `sha256`,
  `bytes`, `is_current`, `uploaded_at`, `promoted_at`. **It never returns the `html` column** — the list
  is a manifest, not a payload.
- **`GET /build/session`** — the **read-back instrument** for AC-2.5, AC-4.2 and AC-4.3, and the reason
  those criteria are provable at all. Takes `token_hash` (the sha256 hex the caller computes from a
  token it already holds) and returns the matching `api_sessions` row as
  `{"record_uid","email","issued_at","expires_at","revoked_at","active"}`, or `"session": null` if
  there is none. **It never accepts a raw token, never returns `token_hash`, and cannot create,
  extend, revoke or modify anything.** It is read-only and gated by the build secret. It is *not* a test
  backdoor: it grants no capability a build-secret holder does not already have.
- **`GET /build/counts`** — the instrument for AC-11.1. Returns row counts for `accounts`, `budgets`,
  `categories`, `sub_categories`, `transactions`, `settings`, `files`, `test_csv` and `users`. Counts
  only — **no row contents, ever**. Read-only.
- **`GET /x`** — the serving route. **No auth, no secret**, because this is what a browser will fetch.
  Optional `?slug=` (default `"x"`); `kind` is always `html`. Returns the `html` of the current row for
  that slug as `HttpResponse(200, html)` with `Content-Type: text/html; charset=utf-8` and
  `Cache-Control: no-store`. **The bytes returned are the bytes stored — no templating, no wrapping, no
  injected banner.** No current row for that slug → **404**, body `no current build`, content type
  `text/plain`.
  - Full URL: `https://budget-x.anvil.app/_/api/x`. **This is not the app root and must not become it.**
  - The `?slug=` parameter exists so that the build round-trip can be proven on a throwaway slug without
    touching the slug a browser will one day load. See §9.

**The client HTML is out of scope this round.** Two one-line placeholder pages prove AC-5 → AC-7, and
they must differ from each other:

```
A  (version 1.0.0-a): <!doctype html><meta charset="utf-8"><title>Budget X</title><p>build A</p>
B  (version 1.0.0-b): <!doctype html><meta charset="utf-8"><title>Budget X</title><p>build B</p>
```

The first real screen is Session 02, deliberately.

### 3.3 `tools/api.py` — the CLI

A new file in this repo. It is modelled on IAMS's tool of the same name, but **this section is the
specification** — do not treat "like IAMS" as a source, because you cannot read that repo.

Reads `.secrets/budgetx.env` (gitignored) for `APP_BASE`, `BUILD_SECRET`, `TEST1_EMAIL`,
`TEST1_PASSWORD`. Subcommands:

`login` · `whoami` · `logout` · `version` · `build-upload <file> --version V [--slug S]` ·
`build-promote <record_uid>` · `build-list [--slug S]` · `session <token_hash>` · `counts`

- `login` caches the token at `.secrets/.token` (inside the gitignored `/.secrets/` directory, file mode
  `0600`) and prints it **masked** — first 6 characters then `…`, never in full.
- `whoami` calls `/me` with the cached token and prints the email.
- **No secret, password or full token is ever written to stdout or stderr**, on success or on error.
  **Error paths are where secrets leak** — check them: no request-header dump, no `repr` of the config,
  no full URL with credentials.
- Non-zero exit on any non-2xx response, with the HTTP status and the `error` code printed.

### 3.4 Module version stamps

Both new modules carry a header comment of exactly this shape, as the first lines of the file:

```python
# ServerApi — v1
# Budget X API spine: ApiError / api_http / require_auth, session tokens over Anvil Users.
# History:
#   v1  2026-08-__  Session 01 — created. login/me/logout, 12h absolute token expiry.
```

The `vN` string is also what `/build/version` reports for that module, **read from a single in-module
constant** so the header and the endpoint cannot drift.

---

## 4. SCHEMA ADDITIONS

Two new tables, both **`client: none`, `server: full`** — the client keeps no secrets, and
`api_sessions.token_hash` and `app_versions.html` must never be client-readable. Five of the nine
existing tables are `client: full`; **do not pattern-match a neighbour.** Anvil column types are
`string`, `number`, `bool`, `datetime`, `date`, `simpleObject`, `link_single` (with `target`).

**`api_sessions`** — title `api_sessions`

| Column | Anvil type | Notes |
|---|---|---|
| `record_uid` | string | stable UUID4 string, safe to expose |
| `token_hash` | string | sha256 hex of the raw token. **The raw token is never stored.** |
| `user` | link_single → `users` | |
| `issued_at` | datetime | UTC |
| `expires_at` | datetime | UTC, `issued_at + 12h` |
| `revoked_at` | datetime | null until logout |
| `active` | bool | `True` on issue, `False` on revoke |
| `source` | string | `"api"` |

**`app_versions`** — title `app_versions`

| Column | Anvil type | Notes |
|---|---|---|
| `record_uid` | string | stable UUID4 string |
| `slug` | string | `"x"` for the real client |
| `kind` | string | `"html"` |
| `version` | string | build label, required, never `0.x` |
| `html` | string | the served bytes, verbatim |
| `sha256` | string | hex digest of `html` as UTF-8 |
| `bytes` | number | byte length of `html` as UTF-8 |
| `is_current` | bool | exactly one `True` per (slug, kind) |
| `uploaded_at` | datetime | UTC |
| `promoted_at` | datetime | UTC, null until promoted |
| `uploaded_by` | string | free text, e.g. `"tools/api.py"` |
| `active` | bool | soft-delete flag; `True` |

### 4.1 How the schema change is made — order matters

`CLAUDE.md` says do not hand-edit `anvil.yaml`. **Adding these two `db_schema` entries is the one
sanctioned exception for this round**, under these constraints:

1. **Insert the two new entries textually** — a targeted edit that appends two blocks to `db_schema`.
   **Do not `yaml.safe_load` → `yaml.dump` the file**: a round-trip reorders keys and rewrites quoting
   across the whole file, which is exactly the silent-corruption case `CLAUDE.md` warns about.
2. **Then parse the result read-only to validate**: `db_schema` has exactly **eleven** entries, the nine
   existing entries are **byte-identical** to the pre-edit file, and the two new entries carry the
   columns, types, `client: none` and `server: full` above.
3. **Before pushing, diff the LIVE schema against `anvil.yaml` and declare every drifted column in the
   debrief.** A schema push forces reconciliation of the whole schema, not just the addition — Bruce's
   panel will show whatever else has drifted, and he must not be surprised by it.
4. **Do the editor work in §5 BEFORE the push, then re-fetch.** Enabling the App Secrets service writes
   a `services:` entry into Anvil's own git copy, creating an Anvil-side commit this clone does not
   have; pushing afterwards is rejected non-fast-forward, and force-pushing is forbidden. Order:
   editor action → `git fetch anvil && git merge --ff-only anvil/master` → commit → push. **If that
   merge is not fast-forwardable, stop and park AWAITING-BRUCE** — do not resolve it unattended.

---

## 5. SECRETS AND THE TEST ACCOUNT

- **`BUILD_SECRET` already exists in `.secrets/budgetx.env`.** Use that exact value. **If it is missing,
  park AWAITING-BRUCE** — never generate one, never hardcode one, never leave an endpoint ungated.
- **What this secret is:** whoever holds it can promote arbitrary HTML and JavaScript that is served from
  `budget-x.anvil.app/_/api/x` — the **same origin** as the Forms app, and from Session 02 the same
  origin as the client that holds session tokens. It is an origin-level code-execution capability, not a
  convenience password. It never reaches a client, a build artefact, a CI log, a commit or a debrief.
- The Anvil **App Secrets service is not currently enabled** (services at clone: Tables, Users, Files).
  Enabling it and creating the secret **`build_secret`** with the value from `.secrets/budgetx.env` is
  part of this round. It is an editor action, not a schema migration, so Code does it and **logs it in
  the debrief with a UTC timestamp**, then follows the re-fetch order in §4.1(4). If it cannot be done
  unattended, park **AWAITING-BRUCE** with the exact click and the exact secret name.
- **The test account exists.** Use `TEST1_EMAIL` / `TEST1_PASSWORD` from `.secrets/budgetx.env`.
  **Never Bruce's own login.** `TEST2_*` is not needed this round.
- **Protect the test account from lockout.** Anvil Users counts `n_password_failures`. Across a full
  verification pass, **at most one** failed login may be aimed at `TEST1_EMAIL` (AC-2.2); AC-2.3's
  unknown-address case must use a synthetic address that is not in `users`. If the account does lock,
  reset `n_password_failures` to 0 via the Anvil editor DATA tab and log the action with a UTC
  timestamp.
- **No secret value, password, or live token appears in a commit, a commit message, a debrief, a log
  line, or CLI output.**

---

## 6. THE KNOWN CHECKPOINT — this round WILL park

Both new tables are schema additions, and **a pushed schema change never applies on its own**: Anvil
parks it and waits for a human click. **Round 01 is expected to go AWAITING-BRUCE once, mid-round.**
That is planned, not a failure.

1. Do the §5 editor work, re-fetch per §4.1(4), implement everything, push to `anvil`, mirror to
   `origin`.
2. Judge and record every criterion that does **not** depend on the new tables — **AC-1, AC-8, AC-10 and
   AC-11.2/11.3** are all judgeable now. Do them before parking, not after.
3. Write `DEBRIEF_S01.md` with `**STATUS:** AWAITING-BRUCE` and an `## AWAITING BRUCE` section reading,
   in substance — he may be on a phone, so one instruction, no ambiguity:

   > Open the Budget X editor. In the left icon rail, click the **Data** icon (third: App · Build with
   > AI · **Data**). A **`Schema Mismatch`** banner appears — *"Your app is expecting a schema that does
   > not match this database."* Click **`Resolve...`**.
   > The two-column panel opens: **Source Code Schema** on the left, **'Default Database' Schema** on the
   > right. Take the **RED/LEFT** side — *"The schema of the source code is correct"*. Differences can be
   > resolved row by row, so apply **only** the two table additions.
   > The confirmation dialog enumerates the operations in plain text. It must read exactly
   > **`Create tables: api_sessions, app_versions`** (or one `Create tables:` line naming both) **and
   > nothing else**. If it proposes any `Delete column`, `Delete table`, or `Add column` to an existing
   > table — **Cancel, and tell Code.** Otherwise click **`Migrate`**.
   > The ⚠ beside `Default Database` becomes a green ✓. Then reply: `Read Claude.md, Trigger 01 continue`.

   Mark every schema-dependent criterion **BLOCKED**. **Never PASS, never FAIL, never "should work".**
4. On `Trigger 01 continue`, resume, judge the remaining criteria, and **fold the continuation into the
   same `DEBRIEF_S01.md`**.

`docs/anvil_schema_panel.md` holds the verbatim panel wording, captured on IAMS. **Re-capture it the
first time Budget X shows the panel and correct that file if it differs**, then say so in the debrief.

---

## 7. HOW THIS ROUND IS VERIFIED — the instruments

There is no `tools/api.py` and no version ping at the start, so the instrument changes mid-round. **State
in the debrief which instrument proved each criterion.**

| Stage | Available instrument |
|---|---|
| Before the first push | Playwright (AC-8 baseline) only. No API exists. |
| After deploy, before migration | `curl` against `/build/version` — AC-1. No table exists yet. |
| After migration | `curl` and `tools/api.py` against `https://budget-x.anvil.app/_/api/…` — everything else. |
| AC-8 | Playwright installed in the repo, headless, driving the published URL. **Not Bruce's own Chrome** — that is reserved for joint live review. |
| Read-back of a write | `GET /build/session` and `GET /build/counts`, both build-secret gated and read-only. |

**Read-back is the only proof of a write.** Budget X has no audit log. Every write criterion below is
proven by an **independent fetch** — a separate HTTP call through a different endpoint — never through
the handle or the response that performed the write, because Anvil Row handles cache per handle.

**Everything except AC-4.3 is reproducible by anyone holding `.secrets/budgetx.env`**, including the
reviewer, with no reliance on Code's transcript. AC-4.3 needs one editor action; see the criterion.

---

## 8. ACCEPTANCE CRITERIA

Eleven criteria. **Each numbered sub-condition is a separate thing to prove** — a criterion with four
sub-conditions is four proofs, and if three hold the criterion FAILS and the reviewer names the fourth.
Partial credit does not exist.

### AC-1 — the deploy is real *(judgeable BEFORE the migration)*

1. `GET /_/api/build/version` with the correct `X-Build-Secret` returns **200**, `Content-Type:
   application/json`, and a `modules` object.
2. The versions it reports **equal the `vN` header stamps in the pushed commit**, for both modules.
3. The same call with **no** `X-Build-Secret` returns **401**; with a **wrong** secret, **401**. Neither
   returns **404** (the route never registered) and neither returns **500**.
4. All of 1–3 hold **before** the schema migration, proving the endpoint reads no table and both modules
   import cleanly without the new tables.

### AC-2 — login works, and refuses *(BLOCKED until migration)*

1. `POST /_/api/auth/login` with `TEST1_EMAIL` / `TEST1_PASSWORD` returns **200**, a 64-hex-character
   `token`, and an `expires_at` **between 11h55m and 12h05m** after the request.
2. The same call with a **wrong password** returns **401** and a body with **no `token` key**. *(One
   attempt only — see §5, lockout.)*
3. A **non-existent** address returns **401** with a body **byte-identical** to 2's — compared
   programmatically, not by eye.
4. A missing `email`, a blank `password`, and a non-JSON body each return **400** — not 500, not 200.
5. **Read-back:** `GET /_/api/build/session?token_hash=<sha256 of the token>` returns a session with
   `active: true`, `revoked_at: null`, and `email` equal to `TEST1_EMAIL`. **`ok:true` from the login
   response is not evidence of this.**

### AC-3 — the token authenticates *(BLOCKED until migration)*

1. `GET /_/api/me` with a valid `Authorization: Bearer <token>` returns **200** and **that account's
   email address**.
2. With **no** `Authorization` header: **401**, and **no `email` key anywhere in the body**.
3. With a **malformed** header — each of `Bearer`, `Bearer xyz`, `Basic <token>`, and the bare token with
   no scheme — **401** each time, no account data, no 500.
4. With a **well-formed but never-issued** 64-hex token: **401**, no account data.

### AC-4 — the token expires and revokes *(BLOCKED until migration)*

1. **Revocation, both states of one token, observed:** issue a token → `/me` returns 200 → `POST
   /auth/logout` with it returns 200 → `/me` with **the same token** returns **401**. All four
   observations recorded.
2. **Read-back:** `GET /build/session?token_hash=…` for that token shows `revoked_at` set and
   `active: false`.
3. **Expiry, observed not reasoned:** issue a second token, confirm `/me` returns 200, then **back-date
   that session row's `expires_at` to the past via the Anvil editor's DATA tab** — a permitted data edit
   on a session row, logged in the debrief with a UTC timestamp; the schema-migrate click remains
   Bruce's alone. Then: `GET /build/session?token_hash=…` shows `expires_at` in the past with
   `revoked_at` still null and `active` still true, **and** `/me` with that same token returns **401**.
   The two observations together prove expiry is enforced independently of revocation.
   *Record that now-dead token's value in the debrief so the reviewer can reproduce both observations —
   an expired token is not a credential. Never record a live one.*
   **If the Anvil editor cannot be reached unattended, AC-4.3 is BLOCKED, not FAILED** — say so and hand
   Bruce the edit.
4. `POST /auth/logout` with an already-revoked token returns **401**.
5. **No test backdoor ships.** Enumerate every `@anvil.server.http_endpoint` path in the round's diff:
   the list equals exactly these **ten** paths and no others — `/auth/login`, `/me`, `/auth/logout`,
   `/build/version`, `/build/upload`, `/build/promote`, `/build/list`, `/build/session`,
   `/build/counts`, `/x`. **No new `@anvil.server.callable` is added.**
   No parameter, header or endpoint shortens, extends or bypasses expiry.

### AC-5 — a build round-trips *(BLOCKED until migration)*

*Run on slug `zz-review` so the round-trip is reproducible without touching the served client. §9 makes
this explicitly permitted for the reviewer.*

1. `POST /_/api/build/upload` with build **A** (`slug=zz-review`, `version=1.0.0-a`) returns **200**, a
   `record_uid`, and a `sha256` **equal to the sha256 of A computed independently on the client side**.
2. `POST /_/api/build/promote` with that `record_uid` returns **200**.
3. `GET /_/api/build/list?slug=zz-review` shows that row with `is_current: true` — an independent fetch,
   not the promote response.
4. After uploading and promoting a **second, different** build **B** (`version=1.0.0-b`): the list shows
   **B `is_current` true and A `is_current` false**, and **exactly one** row for (`zz-review`, `html`)
   has `is_current: true`.
5. `upload`, `promote`, `list`, `session` and `counts` each return **401** with no `X-Build-Secret` and
   **401** with a wrong one. No 404, no 500.
6. `build/list` responses contain **no `html` key**.
7. `upload` with no `version`, and with `version=0.9.0`, each return **400**.

### AC-6 — the served bytes are the promoted bytes *(BLOCKED until migration)*

*The artefact rule. A stale cache passes every other criterion in this list. **Run in this order** — 6.4
is unobservable once anything is promoted.*

1. **Before any promote on `zz-review`:** upload A, then `GET /_/api/x?slug=zz-review` returns **404**
   with `Content-Type: text/plain` — not 200 with an empty body. *(This is AC-6.4's condition, checked
   first because it cannot be re-created afterwards.)*
2. With A promoted, `GET /_/api/x?slug=zz-review` returns **200** and a body whose **sha256 equals A's**.
   Byte-for-byte, not "looks right".
3. Response `Content-Type` is `text/html; charset=utf-8` and `Cache-Control: no-store` is present, read
   from the actual response headers.
4. After promoting **B**, the same fetch — fresh connection, cache-busting query string — returns a body
   whose sha256 equals **B's**, and **not A's**.
5. `GET /_/api/x` with **no** `slug` parameter serves slug `x` — i.e. the round's own promoted
   placeholder, not `zz-review` — proving the default is correct and the two slugs are isolated.

### AC-7 — rollback works *(BLOCKED until migration)*

1. Re-promoting **A**'s `record_uid` returns 200, and `GET /_/api/x?slug=zz-review` then returns a body
   whose sha256 equals **A's**.
2. `build/list?slug=zz-review` shows A `is_current` true, B false, still exactly one current row.
3. Every promote in the round appears in the debrief's rollback ledger (see AC-10.5) — including these.

### AC-8 — nothing user-facing moved *(baseline BEFORE first push; comparison after)*

*This is the criterion that makes the round safe. It is not a formality.*

1. A **baseline** is captured **before the round's first push**: the app loaded as the test account at
   **1280×800** and **390×844**, the five screens of 8.3 visited, and console output recorded. Evidence
   stays in `scratch/` — **it is never committed**.
2. After the final deploy, `https://budget-x.anvil.app` still loads the existing Forms app (startup form
   `Frame`) at **1280×800** and **390×844**.
3. These five screens are still reachable and each shows its stated observable, at **both** widths:
   **Dashboard** (renders its content area with at least one populated element, not an empty shell) ·
   **Transactions** (the transaction list renders and is scrollable) · **Budget** (the budget view
   renders its category rows) · **Reports** (the report view renders without an error dialog) ·
   **Settings** (the settings form renders its controls). "Renders" means visible content, not merely a
   mounted component.
4. Each judged view is **actually scrolled** — `scrollTop` must MOVE and content below the fold must be
   REACHED — at both widths. **A tall-viewport capture is not acceptable as sole evidence.**
5. **No new console error** compared with the baseline of 1. Pre-existing errors are listed and not
   counted against the round.
6. Driven as the **test account**, never Bruce's own login, and **no business record created, edited or
   deleted** in the process — which AC-11.1 then confirms independently.

### AC-9 — the toolchain works from the repo *(BLOCKED until migration)*

1. `python3 tools/api.py login` succeeds against Budget X, reading `.secrets/budgetx.env`.
2. `python3 tools/api.py whoami` prints the test account's email.
3. `python3 tools/api.py build-list` succeeds and shows the current build.
4. **Nothing leaks:** the captured stdout+stderr of all three commands, plus one deliberately failing
   command (a wrong-password login), searched for the literal values of `BUILD_SECRET`,
   `TEST1_PASSWORD` and the full token, contains **none of them**. The token appears masked or not at
   all. **The error path is checked, because that is where secrets leak.**
5. `.secrets/.token` exists with mode `0600` and is not tracked by git.

### AC-10 — the gates are green

1. **pyflakes clean** on every touched `.py`, with the command and its empty output recorded.
2. `python3 tools/repo_guard.py` exits **0**, and `git config core.hooksPath` reads `tools/githooks` —
   **verified before the round's first commit**, not after.
3. Both new modules carry a `vN` stamp **and** a one-line history entry, and those stamps match what
   `/build/version` reports (ties to AC-1.2).
4. Nothing under `scratch/` or `docs/evidence/` is committed; no blob over 2 MB enters the tree. Show
   the round's file list.
5. **The rollback ledger exists.** `DEBRIEF_S01.md` carries a `## Promotions` section with one line per
   promote — slug · version · `record_uid` of the row that was current **before** it, written before the
   promote was made. Never promote before that line is written.

### AC-11 — no business data was touched

1. Row counts from `GET /_/api/build/counts` for `accounts`, `budgets`, `categories`, `sub_categories`,
   `transactions`, `settings`, `files` and `test_csv` are **identical** at the end of the round to the
   first reading taken after the migration. Both readings logged with UTC timestamps.
   *The baseline is taken **after** the test account has logged into the Forms app once (AC-8.1), so any
   first-run bootstrap row already exists and is not counted as a change.* `users` is read but **exempt
   from the identical-count requirement** only for its own Anvil bookkeeping columns per §2.5 — its row
   **count** must still be unchanged.
2. `git diff` for the whole round touches **no file under `client_code/`** and **none of the five
   existing server modules**. Show the diff's file list.
3. `anvil.yaml` differs from its pre-round state **only** by the two new `db_schema` entries — the nine
   existing entries byte-identical, and any `services:` change limited to enabling App Secrets. Show the
   diff.

---

## 9. ROUND CLOSE

- The debrief is `DEBRIEF_S01.md` at the repo root. **Second line exactly** `**STATUS:** INTERIM`,
  `**STATUS:** AWAITING-BRUCE`, or `**STATUS:** FINAL — n/n PASS`.
- **`spec-reviewer` is dispatched on every round, by default, without being asked** — the trigger line
  never carries a dispatch instruction. This round changes nothing a human looks at, so the **visual
  reviewer is not required**; AC-8 is driven by Code's own Playwright check. If the harness refuses to
  dispatch `spec-reviewer`, say so prominently, mark the review outcome **FAIL**, and quote the refusal
  verbatim.
- **What the reviewer may do here.** `spec-reviewer` is read-only about *code and about the served
  client*. Uploading and promoting rows on **slug `zz-review`** is explicitly permitted and expected —
  it is the throwaway-record creation its own charter allows, it is not application code, it is not live
  data, and it changes no build a user or a later round will load. **Slug `x` is frozen for the
  reviewer:** it must not upload or promote there.
- **Freeze promotes on slug `x` while a reviewer is running.** Promote the round's own placeholder before
  dispatching, not during.
- On any FAIL: the **`fixer`** repairs it in its own context, then the **full review re-runs from AC-1**.
  Three cycles maximum, then stop and report the outstanding FAILs with the reviewer's evidence.
- **If a second full cycle still leaves FAILs**, do not spend the third grinding: close **INTERIM** and
  defer the build pipeline to a round `01b`. The split point is clean — `01a` is `ServerApi` +
  `api_sessions` + AC-1/2/3/4/9; `01b` is `ServerBuildTools` + `app_versions` + AC-5/6/7 — because
  AC-5 → AC-7 depend on nothing in the auth spine. Say so in the debrief and stop.
- **AC-2 through AC-4 are the round.** If the token spine is wrong, everything built on it for the next
  month is wrong. They are not waved through on "the code checks the token".
- **Never report FINAL while any criterion is BLOCKED or unjudged.** An honest partial beats a confident
  overstatement.
- Corrections are expected output: if a stated fact here turns out wrong or a criterion turns out
  unprovable, **add a dated addendum in §10** and carry it into the debrief. Never edit the approved text
  in place, and never silently deviate.

---

## 10. ADDENDA

*(none — Code appends dated entries here)*

### Addendum 1 — 2026-08-19 (Code, Session 01)

**§5 first bullet is factually wrong.** It states "`BUILD_SECRET` already exists in
`.secrets/budgetx.env`. Use that exact value." The **key** exists; its **value is empty** (length 0).
`TEST2_EMAIL` and `TEST2_PASSWORD` are likewise empty, which is harmless — §5 says TEST2 is not needed
this round. `APP_BASE`, `TEST1_EMAIL` and `TEST1_PASSWORD` are populated.

Per §5's own instruction ("If it is missing, park AWAITING-BRUCE — never generate one, never hardcode
one, never leave an endpoint ungated") the round parked. No secret was generated or hardcoded.

**Additionally, §5's creation step could not be performed unattended.** Creating the App Secret means
typing a credential into a web form, which Code does not do. §5 anticipates this ("If it cannot be done
unattended, park AWAITING-BRUCE with the exact click and the exact secret name"). Both the value and the
`build_secret` App Secret are handed to Bruce in `DEBRIEF_S01.md`.

### Addendum 2 — 2026-08-19 (Code, Session 01)

**§7's instrument table assumes AC-1 is judgeable "after deploy, before migration".** That holds only if
`build_secret` exists at deploy time. Because of Addendum 1 it did not, so **AC-1 is gated on the secret
rather than on the schema migration**, and the round loses the pre-migration checkpoint §6 designed.

What *was* provable pre-migration, and is recorded in the debrief: all ten routes registered (no 404),
`/build/version` and `/me` returning `401 application/json` with identical bodies, `/auth/login`
returning `400` on a non-JSON body, and therefore **AC-1.4's substance** — both modules import cleanly
before `api_sessions` and `app_versions` exist. That is not AC-1, which requires the 200.

`GET /_/api/x` returns **500 `text/plain`** pre-migration rather than AC-6.1's 404, because
`app_versions` does not exist. AC-6.1 is judged on the continuation.

### Addendum 3 — 2026-08-19 (Code, Session 01, continuation)

**§2.3's "no edits to the five existing server modules" cannot hold in a round that also enables an
Anvil service.** Enabling App Secrets round-tripped the whole server tree through Anvil's own git
(commit `2506287`) and, without any involvement from the round's code:

- injected `import anvil.secrets` at line 1 of **all five pre-existing server modules**, which §2.3
  makes a hard boundary and AC-11.2 tests;
- changed `runtime_options.server_spec` from `null` to `{}` in `anvil.yaml`, which AC-11.3 tests;
- **cleared the executable bit on `tools/githooks/pre-commit`, `pre-push` and `tools/repo_guard.py`**,
  silently disabling the repo guard, since git skips a non-executable hook without error.

The injected imports were **not** reverted: removing them would itself be an edit to the five protected
modules, and Anvil re-adds them whenever a service is enabled. AC-11.2 and AC-11.3 should exempt
platform-authored changes, or enabling a service should be its own round.

### Addendum 4 — 2026-08-19 (Code, Session 01, continuation)

**§7's claim that "everything except AC-4.3 is reproducible by anyone holding `.secrets/budgetx.env`,
including the reviewer" is false for AC-2.2 and AC-2.3.** §5 caps failed logins against `TEST1_EMAIL`
at one for the whole verification pass, so that observation is **single-use**: once the builder makes
it, the reviewer cannot re-derive it, and cannot complete AC-2.3's byte-identity comparison either.

`spec-reviewer` failed AC-2 on exactly this ground in cycle 1. The fix is a second throwaway account —
`TEST2_EMAIL` / `TEST2_PASSWORD` exist as keys in `.secrets/budgetx.env` but are **empty**.
