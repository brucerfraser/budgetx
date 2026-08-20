# Budget X — Spec 02: the shell — login, entry, and the two-client pattern

**Status:** APPROVED AND LOCKED — Bruce, 2026-08-20. Build against this text as written.
**Do not edit the approved text in place**; corrections go in §11 as dated addenda.

**Round:** 02 · **Written:** 2026-08-20 · **Source:** Migration Blueprint (Cowork, 2026-08-20)

**Build models:** Opus orchestrator. Builder S (server) on **Opus** — it touches the auth
surface and the build pipeline, which the migration-phase exception explicitly carves out.
Builders D and M (HTML clients) on **Sonnet** — localised client work, the exception's home
ground. Record who actually ran each role in the debrief.

---

## 1. WHY

Session 01 proved the spine: tokens, build/promote, byte-exact serving. Nothing yet uses it.
This round makes the pipeline real for users-to-be: a login page served from the database, a
desktop shell and a phone-first shell that authenticate, fetch real data through the API, and
navigate — the pattern every screen round after this copies.

It also locks in **Bruce's ruling of 2026-08-20: every screen ships as TWO clients** — a
desktop client and a mobile client designed just for phones — replacing the earlier
"single responsive client" target. This spec instructs the CLAUDE.md amendment so the repo
and the specs never disagree.

This round is still invisible to anyone visiting the app root. The Forms app keeps serving at
`https://budget-x.anvil.app` untouched.

**This round is also the multi-agent template.** Three builders work in parallel from this
spec: the API contract in §4 is fixed before any of them starts, the fixtures in §5 let the
client builders finish without the server existing, and the ownership table in §3.0 means no
two builders can touch the same file or slug.

**And it sets the design language and the speed bar** (Bruce's rulings, 2026-08-20). This app
talks to a person about their money — it must be beautiful, not merely correct: layered dark
surfaces, 16–20 px radii, soft shadows, 150–250 ms motion, no browser `alert()` anywhere. And
it must be fast: no interaction a user feels waits on the network, loads over one second need
naming and justifying. The login page and the two shells are where both standards are
established; every screen round copies them. The current Forms app is a floor, not a ceiling.

---

## 2. WHAT MUST NOT CHANGE

1. **The app root.** `https://budget-x.anvil.app` keeps serving the Forms app. No endpoint at
   `/`, startup form stays `Frame`.
2. **`client_code/`** — not one byte. Both Forms UI trees stay untouched.
3. **The five original server modules** — `ServerModule1`, `account_work`, `budget_work`,
   `csv_handler`, `transaction_work`. No edits. **Exemption (learned in S01, now standing):**
   changes Anvil itself writes when a service is enabled or its git round-trips (injected
   imports, `runtime_options` rewrites, permission-bit changes) are platform-authored and do
   not count as edits — but they must be listed in the debrief, and
   `ls -l tools/githooks/` must be re-checked immediately after any service change (Anvil
   silently strips the executable bit, disabling the repo guard).
4. **`ServerApi.py` is frozen this round.** The token spine passed review in S01; nothing here
   needs it changed. If a builder believes it does, STOP and park — do not edit it.
5. **Schema.** Zero schema changes. No table, no column. **This round must close unattended.**
6. **Business data.** No business-table row is created, edited or deleted. Reads are expected
   (`/app/bootstrap` reads accounts, categories, sub_categories, settings). The Anvil Users
   service's own bookkeeping on the test accounts' `users` rows (`last_login`,
   `n_password_failures`) is the platform writing and is permitted. **Standing exemption
   (S01 Addendum 5):** deliberate, logged test-account provisioning requested of Bruce is
   never counted as a business-data violation — but none is expected this round.
7. **The GitHub↔Anvil sync stays UNLINKED.** Deploy = `git push anvil master`, mirrored to
   `origin`. Never force-push. `git fetch anvil && git merge --ff-only anvil/master` first.
8. **Slug `x` currently serves the S01 placeholder (v1.0.1, record `dddea60c-…`).** It is
   replaced this round through the normal upload → ledger-line → promote path, never by
   editing rows in the editor.

---

## 3. SCOPE

One new server module, two edited files, three HTML clients, one CLAUDE.md amendment.
Nothing else.

### 3.0 Builder ownership — the parallel plan

| Builder | Model | Owns (nobody else may touch) |
|---|---|---|
| **S** — server | Opus | `server_code/ServerAppData.py` (new) · `server_code/ServerBuildTools.py` (v2) · `tools/api.py` |
| **D** — desktop client | Sonnet | `client_src/bx_core.css` + `client_src/bx_core.js` (the canon, new) · slug `x` (login/entry page) · slug `d-dash` |
| **M** — mobile client | Sonnet | slug `m-dash` (embeds Builder D's canon verbatim once it exists; works from the fixtures and the token block meanwhile) |
| **Orchestrator** | Opus | `CLAUDE.md` amendment · `docs/specs/spec_02.md` addenda · integration, deploy, ledger, debrief |

Order of work: all three builders start together. D and M build and self-test against the §5
fixtures (served locally from a file, or from a `zz-` slug); S builds the endpoint to match
the fixtures byte-shape-exactly. The orchestrator integrates only when each builder's own
gate is clean (§3.5), then deploys, basic-tests, and dispatches the review cycle on the round
as a whole. **The review gate never fragments per builder.**

Upload/promote discipline during the build: builders may round-trip drafts on `zz-b02-d`,
`zz-b02-m`, `zz-b02-x` slugs freely. The real slugs `x`, `d-dash`, `m-dash` are promoted by
the orchestrator only, each with its ledger line written into the debrief **as part of the
promote step** (S01 Addendum 6 — never afterwards).

### 3.1 `server_code/ServerAppData.py` — new module (Builder S)

Self-contained per the standing pattern: declares its own `ApiError` / `api_http` /
`require_auth` (copy the shapes from `ServerApi`, do not import across modules), `vN` header
stamp + history line, all `app_tables` access inside function bodies, JSON explicit, non-200s
returned never raised, headers read case-insensitively.

One endpoint:

**`GET /app/bootstrap`** — Bearer-gated via `require_auth()`. Returns everything a client
shell needs in one call. Response shape is **the contract in §4** — exact keys, no extras, no
omissions. Read-only: it must contain no `add_row`, no `update`, no `delete`, and no write to
any table. Failure paths: any auth failure → the uniform 401
`{"ok": false, "error": "unauthorized"}` with no data keys present.

### 3.2 `server_code/ServerBuildTools.py` — v2 (Builder S)

Two changes, both carried from S01's reviewer findings:

1. **`POST /build/upload` ignores any caller-supplied `uploaded_by`.** The server stamps the
   constant `"build-api"`. The accepted input set is exactly `{"slug","kind","version","html"}`;
   unknown keys are ignored, never stored.
2. **`GET /build/list` entries now include `uploaded_by`** — this is what makes 1 provable by
   read-back. No other change to the list shape; it still never returns `html`.

Bump the header stamp to `v2` with a one-line history entry; `/build/version` must report it.

### 3.3 `tools/api.py` (Builder S)

- `login` no longer prints the full `token_hash` (S01 finding 6). Any hash or token printed on
  any path, success or error, is masked to first-6-chars + `…`.
- Stop sending `uploaded_by` in `build-upload` (matches §3.2).
- Everything else unchanged.

### 3.4 The three clients (Builders D and M)

All three are **complete, self-contained HTML files**: inline CSS and JS, no external
resource except the Google Fonts stylesheet already used by the app
(`fonts.googleapis.com` — Eczar 400/600 + Roboto Condensed 300/400/700). No framework, no
CDN script, no build step — the file is the artefact, easy to open and easy to modify.

**The canon: `client_src/bx_core.css` and `client_src/bx_core.js`** (Builder D authors,
everyone embeds). These two repo files are the single source of the look and the client
plumbing; each HTML client embeds both **verbatim** inside its own `<style>`/`<script>` tags,
and AC-7 asserts every embedded copy is byte-identical to the canonical file in the pushed
commit. `bx_core.css` opens with these tokens exactly:

```css
:root {
  --surface-0: #191C1A;        /* page */
  --surface-1: #212925;        /* raised card */
  --surface-2: #2A332E;        /* higher card / sheet */
  --surface-variant: #404943;
  --on-surface: #E1E3DF;
  --on-surface-variant: #C0C9C1;
  --primary: #1EB980;          /* Rally green */
  --primary-container: #005235;
  --on-primary-container: #73FBBC;
  --outline: #8A938C;
  --negative: #B87C4C;         /* Amount Negative — amber, not red */
  --error: #D64D47;
  --radius: 18px;
  --radius-sm: 12px;
  --shadow-1: 0 2px 12px rgba(0,0,0,.35);
  --shadow-2: 0 8px 30px rgba(0,0,0,.45);
  --motion: 200ms cubic-bezier(.2,.7,.3,1);
  --font-head: 'Eczar', serif;
  --font-body: 'Roboto Condensed', sans-serif;
}
```

**The design language these pages establish** (every later screen copies it):

- Layered dark surfaces — cards on `--surface-1`/`--surface-2` with `--radius` corners and
  `--shadow-1`; the login card sits centred on `--surface-0` with `--shadow-2`.
- Motion: content fades-and-rises ~12 px on load over `--motion`; buttons and cards lift
  slightly on hover/press; the shell-proof rows stagger in (~40 ms apart). All motion
  collapses to instant under `prefers-reduced-motion: reduce`.
- While the bootstrap fetch is in flight, the shells show **skeleton shimmer rows**, never a
  spinner or a blank page.
- Errors are inline text or a toast in the page's own style — **no browser `alert()`,
  `confirm()` or `prompt()` anywhere** in any client, this round or ever.
- Dark theme only, matching the running app: dark sidebar with uppercase letter-spaced items
  (desktop), fixed top bar + fixed bottom bar (mobile), pill-shaped primary buttons, Eczar
  for headings and amounts.

`bx_core.js` carries the auth/api pattern below, plus `fmtR()` money formatting
(`R1,234.56`, negatives in parentheses) ready for later rounds.

**Client-side auth pattern** (identical in all three files, ~30 lines of JS, part of this
contract). Two IAMS lessons are inherited deliberately: on success the login page
**NAVIGATES** to the shell's URL — never an in-place HTML swap, which broke on Safari and
clashed global scopes on the sibling project — and the served-from-database login page is
the only login surface (bookmarkable, same-origin with the API, auto-updating). One IAMS rule
is **deliberately diverged from**: the token lives in `localStorage`, not `sessionStorage`
(Bruce's ruling, 2026-08-20 — single-user personal app on his own devices; re-entering a
password on every phone visit is the wrong trade here; expiry and logout still kill the token
server-side). Token in `localStorage` under `bx_token`, expiry ISO string under `bx_expires`;
`api(path, opts)` helper prefixes `/_/api`, sends `Authorization: Bearer <token>`, and on any
401 clears both keys and navigates to `/_/api/x`. Sign out = `POST /auth/logout`, clear both
keys, navigate to `/_/api/x`. The client stores nothing else and decides nothing the server
does not re-check.

**Slug `x` — login + entry (Builder D).** Replaces the S01 placeholder.

- Renders at 1280 px and at 390 px (this one page serves both form factors).
- Email + password form → `POST /_/api/auth/login`. On 401 shows exactly
  "Email or password incorrect" — one message for both causes, mirroring the API's uniform
  body. On 400 (blank field) shows "Enter your email and password". Never echoes the password,
  never distinguishes unknown-address from wrong-password.
- On 200: store token + expiry, then redirect — `matchMedia("(max-width: 998px)")` →
  `?slug=m-dash`, else `?slug=d-dash` (breakpoint matches the Forms app's `Responsive.py`).
  Below the fold of each shell's nav there is a plain link to the other form factor, so the
  redirect is a default, not a cage.
- If a stored token already exists on load, ping `GET /me`; a 200 skips the form and redirects
  as above; a 401 clears storage and shows the form.
- Wordmark "Budget X" in Eczar; no image assets this round.

**Slug `d-dash` — desktop shell (Builder D).** 1280-first.

- Left sidebar: BUDGET X wordmark, then DASHBOARD · BUDGET · TRANSACTIONS · REPORTS ·
  SETTINGS · SIGN OUT, uppercase, spaced, current item highlighted with `--primary-container`.
  Dashboard links to itself; the four unbuilt screens render as visibly disabled items
  (reduced opacity, `aria-disabled="true"`, no navigation) — they gain hrefs in their own
  rounds. Sign out follows the auth pattern.
- Content area, this round: a "shell proof" panel driven by live data — the signed-in email
  and the list of active (non-archived) account names, all from **one** `GET /app/bootstrap`
  call (the standing rule: one data fetch per page open; the page never calls `/me` itself).
  Plus one quiet line: "Screens arrive in rounds 03–07." Nothing invented, nothing hardcoded:
  every rendered fact must come from that call.
- If the content overflows the viewport it scrolls normally; nothing is ever fixed except the
  sidebar.

**Slug `m-dash` — phone shell (Builder M).** 390-first, designed for thumbs, not a squeezed
desktop.

- Fixed top bar (56 px): "Dashboard: Budget X".
- Fixed bottom bar (72 px): a SIGN OUT button (44 px+ touch target) — the bar that later
  rounds fill with per-screen actions.
- Scrollable content between the bars: the same shell proof (email + active account rows as
  cards), plus the link to the desktop version. Content must never be hidden under either bar.
- No hamburger this round; navigation arrives with the screens themselves.

**Versions:** all three uploaded as `version` **1.1.0** (`0.x` never promotes; `x` is already
at 1.0.1).

### 3.5 Gates per builder, before integration

- Builder S: pyflakes clean on all three Python files; fixtures-conformance self-check
  (the live-shape test happens post-deploy).
- Builders D and M: each HTML file's inline JS extracted verbatim to a temp `.js` file and
  passed through `node --check`, output recorded; file opens locally with fixtures and
  renders; the embedded `bx_core.css`/`bx_core.js` blocks are byte-identical to the canonical
  files (self-checked with a hash before handing back).
- Orchestrator: `python3 tools/repo_guard.py` exit 0 and `git config core.hooksPath` =
  `tools/githooks`, **before the round's first commit**.

The HTML files themselves are **not committed to the repo** — they are uploaded to
`app_versions` (that is the point of the pipeline). Keep working copies in `scratch/s02/`
(gitignored). The repo diff for this round is Python + `CLAUDE.md` + this spec's addenda only.

### 3.6 The CLAUDE.md amendment (Orchestrator)

Amend the "WHERE THIS APP IS GOING" section: the target is **two HTML clients per screen —
desktop (`d-<screen>`) and phone-first (`m-<screen>`) slugs — plus the `x` entry/login
client**, replacing the "single responsive client" wording. Add the slug table from the
blueprint. Add these standing rules, each one or two sentences:

- *(from S01)* platform-authored changes are exempt from no-edit criteria but logged;
  deliberate logged test-account provisioning is exempt from `users`-count criteria; the
  rollback-ledger line is written into the debrief as part of the promote step; re-check
  `tools/githooks/` permissions after any service change.
- *(Bruce, 2026-08-20 — the 1-second rule)* no interaction a user feels waits on the
  network; loads over one second are named and justified in the debrief. Display maths runs
  client-side (it holds no secrets); **authority and verification stay server-side**, and
  every money figure must remain reproducible by independent recomputation from raw rows.
- *(Bruce, 2026-08-20 — the beauty mandate)* the clients must be beautiful, not merely
  correct: the `bx_core` design language, motion, no browser `alert()`/`confirm()`, skeleton
  states. Feel criteria are first-class ACs driven by the visual reviewer.
- *(shared code)* canonical `client_src/` files are embedded verbatim in every client;
  embedded copies must be byte-identical to the canon in the same commit.

Nothing else in CLAUDE.md changes.

---

## 4. THE CONTRACT — `GET /app/bootstrap`

Response, 200, `Content-Type: application/json`. Exactly these keys:

```json
{
  "ok": true,
  "email": "<authenticated account email>",
  "server_date": "YYYY-MM-DD",
  "transfer_category_id": "ec8e0085-8408-43a2-953f-ebba24549d96",
  "accounts": [
    {"acc_id": "str", "acc_name": "str", "archived": false}
  ],
  "categories": [
    {"category_id": "str", "name": "str", "colour_back": "str",
     "colour_text": "str", "order": 0}
  ],
  "sub_categories": [
    {"sub_category_id": "str", "name": "str", "icon": "str|null",
     "belongs_to": "str", "order": 0, "roll_over": false,
     "roll_over_date": "YYYY-MM-DD|null"}
  ],
  "settings": {"dash_variances": false, "dash_var_top_five": []}
}
```

Rules: every row of each table appears (archived accounts included, with their flag — the
client filters); dates serialise as ISO `YYYY-MM-DD` strings or null; **no amounts appear
anywhere in this payload** (money arrives with the domain rounds); no other keys. Future
rounds may only ADD keys, never rename or repurpose these. `transfer_category_id` is read
from a single module-level constant — the sentinel UUID stops being a magic string from here
on.

---

## 5. FIXTURES — what client builders build against

`scratch/s02/fixtures/bootstrap.json` (gitignored), constructed by the orchestrator at round
start **from the shapes above with ZZ-synthetic values** (e.g. `ZZ Cheque`, `ZZ Savings`,
three categories, five sub-categories), plus `me.json` (`{"ok":true,"email":"…","expires_at":"…"}`)
and the uniform 401 body. Builders D and M must render correctly from these fixtures alone.
Builder S's endpoint must match the fixture shapes key-for-key against the real tables — the
reviewer compares the live response's key-set and types against §4, not against the fixture
values.

---

## 6. SECRETS AND TEST ACCOUNTS

- `.secrets/budgetx.env` holds `APP_BASE`, `BUILD_SECRET`, `TEST1_*`, `TEST2_*` — all
  populated as of S01's close. If any needed value is empty, park AWAITING-BRUCE; never
  generate or hardcode.
- **Drive everything as TEST2** (`TEST2_EMAIL` / `TEST2_PASSWORD`) — it exists for repeatable
  verification. **After any deliberate failed-login test, immediately log in successfully with
  TEST2** so Anvil's `n_password_failures` counter resets and the account cannot creep toward
  lockout. Unknown-address cases use a synthetic address not in `users`. At most one failed
  login may ever target TEST1 this round, and none is expected.
- Never Bruce's own login; never a live business record. No secret, password or live token in
  any commit, debrief, log line or CLI output.

---

## 7. INSTRUMENTS — what proves what

| What | Instrument |
|---|---|
| API shapes, auth failures, build pipeline | `curl` / `urllib` against `https://budget-x.anvil.app/_/api/…`, plus `tools/api.py` |
| Served bytes = promoted bytes | sha256 of `GET /x?slug=…` vs `/build/list` |
| Write read-back (`uploaded_by`) | `GET /build/list` (which now carries the field) |
| Login flow, redirects, rendering, scroll, tokens in storage | Playwright headless against the published URL, at **1280×800 and 390×844**, driving the real pages — never Bruce's Chrome |
| No business writes | `GET /build/counts` before/after, UTC-stamped |
| CLAUDE.md amendment, module stamps, canonical embeds | `Read` of the repo + `/build/version` + sha256 of embedded blocks vs `client_src/` files |
| Speed | timed `curl` (≥20 requests per endpoint, p50/p95) and Playwright navigation timing at both widths |

Everything below is reproducible by anyone holding `.secrets/budgetx.env`, including the
reviewers, with no reliance on the builder's transcript.

---

## 8. ACCEPTANCE CRITERIA

Each numbered sub-condition is a separate proof. Partial credit does not exist.

### AC-1 — the bootstrap contract holds

1. `GET /_/api/app/bootstrap` with a valid TEST2 Bearer token returns **200**,
   `application/json`, and a body whose key-set **exactly equals** §4 — no missing keys, no
   extras, verified programmatically against the schema, not by eye.
2. Every `accounts` / `categories` / `sub_categories` row count in the payload equals the
   table's row count from `GET /build/counts`, fetched independently in the same minute.
3. With no `Authorization` header, a malformed header, and a never-issued 64-hex token:
   **401** each time, body byte-identical to the uniform
   `{"ok": false, "error": "unauthorized"}`, and **no data key** (`accounts`, `email`, …)
   anywhere in any of those bodies.
4. The module contains **no table write call** (`add_row`, `update`, `delete`) — proven by
   reading the pushed source — and `/build/counts` is identical before and after a bootstrap
   call.

### AC-2 — `uploaded_by` is server-stamped

1. `POST /build/upload` (on slug `zz-rev-s02`) with `"uploaded_by": "EVIL"` in the body
   returns 200, and the **read-back** through `GET /build/list` shows that row's
   `uploaded_by` = `"build-api"` — not `"EVIL"`.
2. An upload without the key shows the same `"build-api"`.
3. `/build/list` entries carry `uploaded_by` and still carry **no `html` key**.
4. `/build/version` reports `ServerBuildTools` at `v2`, matching the pushed header stamp.

### AC-3 — the toolchain leaks nothing

1. Captured stdout+stderr of `tools/api.py login`, `whoami`, `build-list`, **and one
   deliberately failing command**, searched programmatically for: the literal `BUILD_SECRET`,
   `TEST2_PASSWORD`, any 64-lowercase-hex string. **Zero matches** — tokens and hashes appear
   masked (6 chars + `…`) or not at all.
2. After the deliberate failure, a successful TEST2 login is performed (lockout hygiene, §6).

### AC-4 — the login page works, and refuses

1. `GET /_/api/x` serves bytes whose sha256 equals the promoted v1.1.0 build's `sha256` from
   `/build/list` — byte-exact, headers `text/html; charset=utf-8`.
2. Playwright at **both** 1280×800 and 390×844: the form renders (email, password, submit all
   visible and enabled) with the dark palette (§AC-7).
3. Wrong password (TEST2 + garbage): the page shows exactly "Email or password incorrect", no
   token lands in `localStorage`, and the same message appears for a synthetic unknown
   address — indistinguishable. *(Follow each with a successful login, per §6.)*
4. Correct TEST2 login at 390×844 lands on `?slug=m-dash`; at 1280×800 lands on
   `?slug=d-dash`; in both cases `localStorage.bx_token` is 64 lowercase hex and a direct
   `GET /me` with that token returns 200 with TEST2's email.
5. Visiting `x` with a valid stored token skips the form (redirects); with a garbage stored
   token shows the form and the garbage token is cleared.

### AC-5 — the desktop shell is real

At 1280×800, logged in as TEST2 via the page itself:

1. The sidebar shows exactly the six items in §3.4 order; DASHBOARD is highlighted; BUDGET,
   TRANSACTIONS, REPORTS, SETTINGS are visibly disabled (`aria-disabled="true"`) and clicking
   them navigates nowhere.
2. The shell proof renders TEST2's email **equal to** `GET /me`'s answer, and one row per
   **non-archived** account whose names equal exactly the `archived: false` names in an
   independent `GET /app/bootstrap` — compared programmatically.
3. SIGN OUT: after clicking it, `localStorage` holds no `bx_token`, the browser is back on the
   login page, and the old token now gets **401** from `/me` (revoked server-side, not just
   forgotten client-side).
4. **Scroll is driven, not photographed:** the content region's `scrollTop` is pushed and
   MOVES when content overflows (force overflow with a 1280×500 viewport if the content fits at
   1280×800 — record the method), and no element is clipped or unreachable at 1280×800.

### AC-6 — the mobile shell is designed for a phone

At 390×844, logged in as TEST2 via the page itself:

1. Top bar and bottom bar are fixed (their bounding boxes do not move when the content
   scrolls — asserted from the DOM, not a tall screenshot).
2. The SIGN OUT touch target is ≥44×44 px and works as AC-5.3.
3. The shell proof renders between the bars: email + non-archived account cards matching the
   API exactly (as AC-5.2), and **no content is occluded by either bar** — the last card's
   bottom edge is reachable above the bottom bar after scrolling.
4. **Scroll is driven:** the content region's `scrollTop` MOVES and the content below the
   first viewport is reached at 390×844. Tall-viewport captures are not evidence.
5. The link to the desktop version exists and navigates to `?slug=d-dash`.

### AC-7 — one look, self-contained files

For each of the three served pages (`x`, `d-dash`, `m-dash`), on the **served bytes**:

1. No `<script src=` at all, and the only external `<link` targets are
   `fonts.googleapis.com` / `fonts.gstatic.com` — the file is otherwise self-contained.
2. The embedded `bx_core.css` and `bx_core.js` blocks in each served page are **byte-identical**
   to `client_src/bx_core.css` / `client_src/bx_core.js` at the reviewed commit — compared by
   hash, all three pages.
3. The §3.4 token block is present verbatim (every custom property, those exact values).
4. Playwright computed styles: `body` background is `rgb(25, 28, 26)` and the primary action
   element resolves to `rgb(30, 185, 128)` — the Rally palette is live, not just declared.

### AC-8 — a dead token cannot use a shell

1. Playwright plants a well-formed but never-issued 64-hex `bx_token`, then opens `d-dash`:
   the page ends at the login form with storage cleared. Same for `m-dash`.
2. During the bounce, no API response containing a data key was received (asserted from the
   network log — the 401 body is the uniform one).

### AC-9 — nothing user-facing moved

1. Baseline captured **before the round's first push**: the Forms app as TEST2 at 1280×800
   and 390×844 across Dashboard, Transactions, Budget, Reports, Settings, with console
   output, kept in `scratch/s02/` (never committed).
2. After the final deploy the root still serves the Forms app (startup `Frame`), and the five
   screens show their observables at both widths **except** mobile Reports and mobile
   Settings, which are the pre-existing S01-documented defects — listed, compared against
   baseline (must be no worse), and not counted against this round.
3. Each judged Forms view is actually scrolled (scrollTop MOVES), both widths.
4. No new console error against the baseline of 1.

### AC-10 — the gates are green

1. pyflakes clean on `ServerAppData.py`, `ServerBuildTools.py`, `tools/api.py` — commands and
   empty output recorded.
2. `node --check` clean on the extracted inline JS of all three HTML clients — recorded.
3. `python3 tools/repo_guard.py` exits 0 and `git config core.hooksPath` = `tools/githooks`,
   verified **before the round's first commit**.
4. The round's git diff touches only: `server_code/ServerAppData.py`,
   `server_code/ServerBuildTools.py`, `tools/api.py`, `client_src/bx_core.css`,
   `client_src/bx_core.js`, `CLAUDE.md`, `docs/specs/spec_02.md` (addenda only) — and
   **nothing under `client_code/`**. File list shown.
5. `ServerAppData` carries `v1` + history line; both stamps match `/build/version` (ties to
   AC-2.4).
6. **The rollback ledger is written as part of each promote** — for `x`, `d-dash`, `m-dash`:
   slug · version · `record_uid` · the row that was current before (for `x`: `dddea60c-…`) —
   present in the debrief with the promote, not reconstructed after (S01 Addendum 6).

### AC-11 — no business data was touched

1. `GET /build/counts` at round start and round end: **all nine counts identical**, both
   readings UTC-stamped. (`users` included — no provisioning is planned; if Bruce is asked to
   provision anything, it is logged and exempt per §2.6.)
2. `anvil.yaml` byte-identical for the whole round except nothing — no schema section may
   change at all. Show the diff (expected: empty, or platform-authored `runtime_options`
   noise only, listed).

### AC-12 — CLAUDE.md now tells the truth

1. The migration section names the two-client target and the slug scheme (`x`, `d-*`, `m-*`),
   and the "single responsive client" wording is gone.
2. The standing rules of §3.6 are present — the S01 four, the 1-second rule with compute
   placement, the beauty mandate, and the canonical-embed rule.
3. No other section changed — diff shown.

### AC-13 — it is fast, and the truth about speed is on record

1. **Page discipline:** each shell makes exactly **one** data request per open
   (`/app/bootstrap`), asserted from Playwright's network log; the login page makes exactly
   one (`/auth/login`) per attempt.
2. **Page weight:** each of the three served HTML files is **≤ 200 KB** (`bytes` from
   `/build/list`).
3. **Render speed:** with the bootstrap response mocked to resolve instantly (Playwright
   route fulfilment), tap-to-rendered-shell-proof is **< 300 ms** at both widths — what the
   page itself costs, isolated from the network.
4. **The network, measured honestly:** p50 and p95 over ≥ 20 timed requests each for
   `GET /x?slug=d-dash`, `POST /auth/login`, `GET /app/bootstrap`, warm (and one recorded
   cold-start figure after ≥ 10 min idle). All figures go in the debrief. **Any p50 over
   1 000 ms is named with its cause** — page behaviour is this round's to fix; platform
   latency is reported to Bruce with options, not silently accepted.
5. While the real bootstrap is in flight, the shells show the skeleton state (asserted by
   throttling the route), never a blank page or a browser spinner alone.

### AC-14 — it feels good (driven, not admired)

At both 1280×800 and 390×844:

1. **Motion exists and plays:** the shell-proof content's entry animation actually runs —
   computed `transition`/`animation` properties are non-`none` on the animated elements, and
   two timestamped screenshots ≤ 150 ms apart during load differ in the animated region.
2. **Reduced motion is honoured:** with `prefers-reduced-motion: reduce` emulated, the same
   content appears instantly (no animation frames) and nothing is hidden or broken.
3. **No native dialogs:** the served bytes of all three pages contain no `alert(`,
   `confirm(` or `prompt(` calls; errors render as in-page styled elements (observed on the
   wrong-password path, AC-4.3).
4. **Surfaces are the design language:** cards render with non-zero `border-radius`
   (≥ 12 px) and a non-`none` `box-shadow`, read from computed styles on the login card and
   the shell-proof cards.
5. **Nothing janks:** during a driven scroll of `m-dash` content, the top and bottom bars'
   bounding boxes are stable (AC-6.1's assertion, re-checked while animating content is
   present).

---

## 9. THE REVIEW

- **Both reviewers run.** This round changes what humans look at, so: **visual-reviewer
  first** (AC-4.2, AC-5, AC-6, AC-7.4, AC-9, AC-13.1/3/5, AC-14 — the driven-interaction and
  feel criteria), its verdict committed, **then spec-reviewer** on everything (fresh
  read-only context, full AC-1…AC-14).
- **Freeze promotes on `x`, `d-dash`, `m-dash` while any reviewer is running.** Reviewers may
  upload/promote freely on `zz-rev-s02*` slugs — that is throwaway-record creation their
  charters allow.
- Reviewer logins use TEST2 with the §6 lockout hygiene.
- On any FAIL: `fixer` (Opus, own context) repairs, full re-review from AC-1, three cycles
  maximum, then stop and report.
- If cycle 2 still fails structurally, split cleanly: `02a` = server (AC-1/2/3/10/11) ·
  `02b` = clients (AC-4…9, 12, 13, 14). The seam is the §4 contract.
- Debrief `DEBRIEF_S02.md`, STATUS line rules unchanged. Never FINAL with anything unjudged.

---

## 10. ROUND CLOSE — what this round leaves behind

The template every screen round copies: a contract-first spec, three parallel builders with
disjoint ownership, fixtures that decouple them, two designed clients per screen, and a
review cycle on the integrated whole. Round 03 (Transactions domain) starts from this
pattern plus the blueprint's §4.

---

## 11. ADDENDA

### Addendum 1 — 2026-08-20 (Code, Session 02)

**§3.3 and §6 conflict over which account `tools/api.py login` uses.** §3.3 lists exactly two
changes to the tool and says "everything else unchanged"; the S01 tool reads `TEST1_EMAIL` /
`TEST1_PASSWORD` and nothing else. §6 says "**Drive everything as TEST2**". Both cannot hold: as
written, every login through the toolchain drives TEST1.

**Resolved in favour of §6**, which is the safety rule (TEST1 has a single-use failed-login budget;
TEST2 exists precisely to be driven repeatedly). `login` now takes `--account {1,2}`, **defaulting
to `2`**, and reads that pair from the env. `--email` still overrides the address. Nothing else
about the CLI changed. AC-3.1's capture is therefore of a TEST2 login, which is also what §6 asks
for.

### Addendum 2 — 2026-08-20 (Code, Session 02)

**§3.6 says "add the slug table from the blueprint", but the Migration Blueprint is not in this
repo.** `docs/` holds only `anvil_schema_panel.md`, `cowork_project_instructions.md` and
`specs/`; the blueprint lives in Cowork's vault, which Code cannot reach. Rather than park the
round on a document it cannot read, the slug table added to `CLAUDE.md` was **derived from
spec_02's own contents** — `x`, `d-dash`/`m-dash` (§3.4), the five sidebar screens (§3.4), "screens
arrive in rounds 03–07" (§3.4), round 03 = Transactions (§10), and the `zz-*` throwaway convention
(§3.0/§9). **If the blueprint's table differs, CLAUDE.md's is the one to correct** — it is a
reconstruction, not a transcription, and is flagged as such here and in the debrief.

### Addendum 3 — 2026-08-20 (Code, Session 02)

**AC-10.2's instrument: there is no `node` on this machine's PATH.** No Homebrew node, no nvm, no
system node. The `node --check` gate is run with the **real node binary Playwright ships in its
driver** — `…/site-packages/playwright/driver/node`, **v24.15.0**, verified to accept `--check`
and to reject a syntax error. This is genuine node, not a substitute parser, so the criterion is
met as written; the path is recorded here because the command in the debrief will not look like a
bare `node`.

### Addendum 4 — 2026-08-20 (Code, Session 02)

**§3.2 says ServerBuildTools gets "two changes"; AC-10.5 requires a third.** AC-10.5 reads
"`ServerAppData` carries `v1` + history line; **both stamps match `/build/version`**" — which is
unprovable unless `/build/version` reports `ServerAppData` at all, and at v1 it reported only
`ServerApi` and `ServerBuildTools`. `_module_versions()` therefore gained a third entry.
**Authorised by the orchestrator**: `/build/version` still touches no table (so it still answers
on the near side of any migration), and the import stays inside the function body. The module's
DESIGN NOTES now record two sanctioned cross-module references rather than one.

**§4 does not state what a NULL column serialises to, and three of its columns are nullable in the
live schema.** Resolved, and recorded so a reviewer reads the payload the same way:

- `order` is typed as a number but the column is nullable → **null becomes `0`**, and rows with a
  null order sort **last**. This is a type guard, not a data source: every live category and
  sub_category carries an order because the Forms app sorts on it.
- The `str`-typed fields (`acc_id`, `acc_name`, `category_id`, `name`, `colour_back`,
  `colour_text`, `belongs_to`) → **null becomes `""`**, so a strict type check of §4 holds.
- Only `icon` and `roll_over_date` are nullable in the payload, which is what §4's explicit
  `str|null` / `YYYY-MM-DD|null` already say.
- Anvil returns number columns as floats; **whole floats collapse to int**, so `order` serialises
  as `1`, not `1.0`.
- `roll_over_date` accepts a `datetime` as well as a `date` (datetime is a subclass of date and is
  tested first).

**Row ORDER is not part of the contract.** The endpoint sorts `accounts` by `acc_name` and the two
category tables by `order`; `scratch/s02/fixtures/bootstrap.json` is not in that order. §5 already
says the reviewer compares the live response's **key-set and types** against §4, not the fixture's
values — flagged here so a reviewer diffing row order against the fixture does not misread it.

**Secret discipline was widened beyond §3.3, deliberately.** `tools/api.py` now also masks the
sha256 digests printed by `build-upload`, and `die()` masks any run of 32+ lowercase hex before it
reaches stderr (the `session` command puts a `token_hash` in a query string, and some urllib
failures stringify the URL — precisely the "deliberately failing command" AC-3.1 captures). The
MATCH/MISMATCH verdict is still computed on the **full** digests, so the evidence survives.
**Consequence, and it matters for AC-4.1:** no full sha256 reaches CLI output anywhere, so the
served-bytes comparison reads `sha256` from `/build/list`'s JSON directly (urllib), never from the
CLI table — which is itself scanned by AC-3.1.
