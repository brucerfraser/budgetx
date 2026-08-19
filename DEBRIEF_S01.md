# DEBRIEF S01 — the API spine
**STATUS:** AWAITING-BRUCE

**Round:** 01 · **Spec:** `docs/specs/spec_01.md` (APPROVED AND LOCKED) · **Commit:** `ab4518c`
**Deployed:** `git push anvil master` → `b48ce8f..ab4518c`, mirrored to `origin`. Live on the app.

**Verdict: 0 PASS · 0 FAIL · 9 BLOCKED · 2 judged-with-findings.** The round parked as §6 predicted —
but **twice over, not once**. The schema click was planned. The second blocker was not: `BUILD_SECRET`
is an **empty key** in `.secrets/budgetx.env`, so no `/build/*` endpoint can return 200 and **AC-1,
which the spec designed to be judgeable before the migration, is blocked too.**

---

## AWAITING BRUCE

Two jobs, both in the Anvil editor, one visit. **Do them in this order.**

### 1 — the build secret (new; this is why AC-1 could not be judged)

`.secrets/budgetx.env` contains the line `BUILD_SECRET=` with **nothing after the `=`**. Spec §5 says
never generate one, never hardcode one, never leave an endpoint ungated — so I stopped.

Whoever holds this secret can promote arbitrary HTML and JavaScript served from
`budget-x.anvil.app/_/api/x` — the **same origin** as your Forms app. It is an origin-level
code-execution capability. Generate it yourself and keep it out of chat.

**a.** Generate a value (any 32+ random chars), e.g. in Terminal:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**b.** Put it in `.secrets/budgetx.env`, replacing the empty line, so it reads `BUILD_SECRET=<value>`.

**c.** In the Budget X editor, enable the **App Secrets** service (left rail → **`+`** beside Services
→ **App Secrets**), then add a secret named exactly **`build_secret`** with that same value.

*I did not do (c) myself. Creating it means typing a credential into a web form, which I do not do —
that limit holds regardless of the spec's authorisation, and §5 anticipated it ("If it cannot be done
unattended, park AWAITING-BRUCE with the exact click and the exact secret name"). The secret name is
`build_secret`. Note enabling the service writes a `services:` entry into Anvil's own git copy, so I
will `git fetch anvil && git merge --ff-only` before touching anything on continuation.*

### 2 — the schema migration (planned; §6)

Open the Budget X editor. In the left icon rail, click the **Data** icon (third: App · Build with AI ·
**Data**). A **`Schema Mismatch`** banner appears — *"Your app is expecting a schema that does not
match this database."* Click **`Resolve...`**.

The two-column panel opens: **Source Code Schema** on the left, **'Default Database' Schema** on the
right. Take the **RED / LEFT** side — *"The schema of the source code is correct"*.

The confirmation dialog enumerates the operations in plain text. It must read exactly
**`Create tables: api_sessions, app_versions`** (or one `Create tables:` line naming both) **and
nothing else**. If it proposes any `Delete column`, `Delete table`, or `Add column` to an existing
table — **Cancel, and tell me.** Otherwise click **`Migrate`**. The ⚠ beside `Default Database`
becomes a green ✓.

### Then reply: `Read Claude.md, Trigger 01 continue`

That resumes the round, judges AC-1 through AC-7, AC-9 and AC-11.1, dispatches the reviewer, and folds
everything into this same file.

---

## Verdict, one line per criterion

| AC | Outcome | Evidence |
|---|---|---|
| **AC-1** deploy is real | **BLOCKED** | Routes registered and both modules import cleanly with no tables (1.4 substance proven — see below). **1.1 unprovable: no `build_secret` exists, so the correct-secret call cannot return 200.** |
| **AC-2** login works/refuses | **BLOCKED** | `api_sessions` does not exist until the migrate click. |
| **AC-3** token authenticates | **BLOCKED** | Same. |
| **AC-4** expiry and revocation | **BLOCKED** | Same. **4.5 alone is proven statically** — see below. |
| **AC-5** build round-trips | **BLOCKED** | `app_versions` does not exist; `/build/*` also needs the secret. |
| **AC-6** served bytes are promoted bytes | **BLOCKED** | Same. |
| **AC-7** rollback works | **BLOCKED** | Same. |
| **AC-8** nothing user-facing moved | **JUDGED — 5 of 6 met, 8.3 not met at 390 px (pre-existing)** | Full comparison below. |
| **AC-9** toolchain works | **BLOCKED** | `tools/api.py login` needs `api_sessions`; `version`/`counts` need the secret. |
| **AC-10** gates are green | **JUDGED — 4 of 5 met, 10.3 half-blocked** | Below. |
| **AC-11** no business data touched | **11.2 PASS · 11.3 PASS · 11.1 BLOCKED** | Below. |

**Nothing is marked PASS on a criterion I could not observe.** Per §9 and CLAUDE.md, BLOCKED is not
FAIL and is not "should work".

### What *is* proven, pre-migration

All ten routes are registered and answering — no 404 anywhere, no 500 on a gated path:

| Call | Observed |
|---|---|
| `GET /_/api/build/version` (no header) | `401` · `application/json` · `{"ok": false, "error": "unauthorized"}` |
| `GET /_/api/build/version` (wrong secret) | `401`, identical body |
| `GET /_/api/me` (no header) | `401`, identical body, **no `email` key** |
| `GET /_/api/build/counts` (no header) | `401`, identical body |
| `POST /_/api/auth/login` (non-JSON body) | `400` · `{"ok": false, "error": "bad_request"}` |

This is **AC-1.4's substance**: both modules imported cleanly *before* `api_sessions` and
`app_versions` exist, proving no module-level table reference. It is not AC-1 itself, which needs the
200. **AC-4.5 is proven statically** — the registered paths are exactly the spec's ten, no extras, no
backdoor; `@anvil.server.callable` count is unchanged at 22; nothing is registered at `/`; startup form
is still `Frame`.

`GET /_/api/x` currently returns **500 `text/plain`**, not the 404 AC-6.1 expects, because
`app_versions` does not exist yet. Expected to become 404 after the migration; **AC-6.1 is judged on
the continuation, not now.**

---

## AC-8 — nothing user-facing moved

Baseline captured **before the first push** (2026-08-19 18:11 UTC, `scratch/s01/baseline_LOCKED.json`,
sha `6bbe9339c788504c…`, 12 screenshots), as the test account, headless Playwright 1.60 against
`https://budget-x.anvil.app`. Never Bruce's login, never his Chrome. Evidence stayed in gitignored
`scratch/` and **was not committed**.

**Every metric is identical before and after the deploy**, on all ten screen×viewport combinations:

| Screen | 1280×800 textLen / elems | 390×844 textLen / elems | scroll moved (both) |
|---|---|---|---|
| Dashboard | 327 / 1135 → **unchanged** | 293 / 1119 → **unchanged** | yes / yes |
| Transactions | 331 / 674 → **unchanged** | 278 / 653 → **unchanged** | yes / not scrollable |
| Budget | 797 / 2321 → **unchanged** | 784 / 1635 → **unchanged** | yes / yes |
| Reports | 471 / 930 → **unchanged** | 87 / 997 → **unchanged** | yes / not scrollable |
| Settings | 354 / 878 → **unchanged** | 87 / 946 → **unchanged** | yes / not scrollable |

- **8.1 met** — baseline pre-push, evidence uncommitted.
- **8.2 met** — root still serves the Forms app (startup form `Frame`) at both widths; login succeeded
  and the nav rendered at both.
- **8.3 NOT met at 390 px, from a pre-existing defect.** **Mobile Reports and mobile Settings render
  an Anvil error banner — "This app has experienced an error" — and almost no content (textLen 87).**
  The screenshots captured **before the first push** show the identical banner, so **this round did not
  cause it**; but the criterion as written asks each screen to show its stated observable at *both*
  widths, and at 390 px two of them do not. I am not marking that PASS. Desktop: all five render
  correctly. See `## Findings I did not fix`.
- **8.4 met on every scrollable view** — scrollTop reset to 0 then driven to max; movement asserted, and
  below-fold content reached where a below-fold element existed (desktop Budget/Settings; mobile
  Dashboard/Budget, the latter 0 → 1718 px). **Four views were not scrollable at all** (desktop none
  after correction; mobile Transactions, Reports, Settings) because `scrollHeight ≤ clientHeight` —
  there is nothing below the fold to reach. No tall-viewport capture was used as evidence anywhere.
- **8.5 met** — console errors: desktop 0 → 0; mobile 1 → 1 (a pre-existing 404 on a resource).
  **Zero new console errors.**
- **8.6 met** — driven as the test account throughout; navigation and scrolling only. No create, edit or
  delete was performed. AC-11.1 will confirm this independently once `/build/counts` is reachable.

**Two corrections to my own instrument, both found and fixed before judging** — recorded because the
first one would have hidden a real defect:

1. My error detector matched `/an error has occurred/` and missed Anvil's actual wording, *"This app has
   experienced an error"*. It reported mobile Reports/Settings as clean. I caught it by opening the
   screenshots rather than trusting the metric, then fixed the detector and re-measured. **This is the
   "verify the artefact, not your model of it" trap, and I fell into it once.**
2. My scroll test read `scrollTop` without resetting it, so desktop Reports showed `moved=False` purely
   because a previous screen had left the container at its maximum. Fixed to force `scrollTop = 0`
   first; all five desktop views then demonstrably move.

Because the fixes landed after the push, the corrected detector could not be re-run against a true
pre-push baseline. The pre-existing-ness of the mobile error banner therefore rests on the **pre-push
screenshots** (`scratch/s01/baseline/mobile_390x844_Reports.png`), which show it plainly, plus the
identical textLen/elems counts. I regard that as sound, and I am flagging the limitation rather than
papering over it.

---

## AC-10 — the gates

1. **10.1 met — pyflakes clean**, empty output, on every touched `.py`:
   `python3 -m pyflakes server_code/ServerApi.py server_code/ServerBuildTools.py tools/api.py` → exit 0,
   no output. No JS touched, so no `node --check`.
2. **10.2 met, verified before the round's first commit** — `git config core.hooksPath` = `tools/githooks`;
   `python3 tools/repo_guard.py` → **exit 0**.
3. **10.3 half-blocked** — both modules carry a `vN` header stamp and a one-line history entry, and each
   stamp is read from a single in-module `MODULE_VERSION = "v1"` constant so header and endpoint cannot
   drift. **That the endpoint *reports* them is unproven** (ties to AC-1.2, blocked on the secret).
4. **10.4 met** — the round's committed file list is exactly `anvil.yaml`, `docs/specs/spec_01.md`,
   `server_code/ServerApi.py`, `server_code/ServerBuildTools.py`, `tools/api.py`. Nothing under
   `scratch/` or `docs/evidence/`; largest blob 37 KB (the spec).
5. **10.5 met, vacuously** — see `## Promotions`. No promote has been made, so the ledger is empty. It
   is not empty because I forgot; it is empty because `/build/promote` is unreachable.

## AC-11 — no business data touched

- **11.2 PASS** — the round's diff touches **no file under `client_code/`** (count 0) and **none of the
  five existing server modules** (count 0). File list as in 10.4.
- **11.3 PASS** — `anvil.yaml` differs by **71 insertions, 0 deletions**, and every inserted line belongs
  to the two new `db_schema` entries. Validated read-only after a **textual** insert (no
  `yaml.safe_load`→`dump` round-trip, per §4.1(1)): **11 entries**; the **nine existing entries
  byte-identical** both structurally and as raw text; **`services:` and `startup:` unchanged** — so this
  push carries no App Secrets change, which is why job 1 above is yours.
- **11.1 BLOCKED** — `/build/counts` needs the secret and the migration. **No baseline count exists yet.**
  Per §8 the baseline is taken *after* the test account's first Forms login, which has now happened, so
  the first reading on continuation is a valid baseline.

---

## Promotions

*(rollback ledger — one line per promote, written before the promote)*

**None. No build was uploaded or promoted this round**; `/build/upload` and `/build/promote` are gated
by a secret that does not exist. Slug `x` and slug `zz-review` both hold **no rows at all**, so there is
nothing to roll back to and nothing to roll back from. The placeholder promote on slug `x` that §9
requires *before* dispatching a reviewer has **not** been made — it is the first act of the continuation.

## Anvil editor actions

**None.** I did not open the Anvil editor at any point this round — no exploratory run, no run that did
nothing. Both editor jobs are handed to you above.

## Live data touched

**None.** No business record was created, edited or deleted. The test account logged into the Forms app
(read-only navigation and scrolling), which causes the Anvil Users service to stamp `last_login` on its
own `users` row — the single carve-out §2.5 permits. **No failed login was aimed at `TEST1_EMAIL`**, so
`n_password_failures` is untouched and the account is not at risk of lockout; AC-2.2's one permitted
failure is still unspent.

## Reviewers

**Not dispatched at this park, deliberately, and this is not a skipped gate.** Nine of eleven criteria
are unprovable until you have done the two jobs above; a reviewer dispatched now could only re-report
BLOCKED, and would be certifying a build that is about to change. §9 requires promotes frozen while a
reviewer runs and the placeholder promoted *before* dispatch — neither is possible yet.

**The gate runs in full on the continuation, before anything is marked FINAL**, in a fresh read-only
context, one line per AC.

**One thing I need you to be aware of.** This session carries a standing instruction not to dispatch
subagents unless you ask for it, which sits against CLAUDE.md's rule that `spec-reviewer` is dispatched
every round without being asked. I read `Trigger 01` as carrying that authorisation through CLAUDE.md,
and I intend to dispatch on the continuation. **If the harness refuses**, I will say so prominently,
quote the refusal verbatim, and mark the review outcome **FAIL** — never PASS, never a silent
self-assessment.

---

## Corrections to the spec — §10 addenda

Two, both carried into `docs/specs/spec_01.md` §10 as dated addenda rather than edited into the
approved text.

1. **§5's first bullet is wrong.** It states "**`BUILD_SECRET` already exists in
   `.secrets/budgetx.env`.** Use that exact value." The key exists; **its value is empty** (length 0).
   `TEST2_EMAIL` and `TEST2_PASSWORD` are likewise empty — harmless, since §5 says TEST2 is not needed
   this round. `APP_BASE`, `TEST1_EMAIL` and `TEST1_PASSWORD` are all populated.
2. **§7's instrument table assumes AC-1 is judgeable "after deploy, before migration".** That holds only
   if `build_secret` exists at deploy time. Because §5's creation step could not be done unattended,
   **AC-1 is gated on the secret, not on the migration** — the round loses the pre-migration checkpoint
   the spec designed. Everything else about the staging is unaffected.

I also record my own error from the previous turn: my pre-flight check reported "`BUILD_SECRET` present"
when it had only tested that the **key name** appeared, not that it had a value. That is what let the
round get all the way to a deploy before the blocker surfaced.

## Findings I did not fix

1. **Mobile Reports and mobile Settings are broken at 390 px** — both render *"This app has experienced
   an error"* with essentially no content (textLen 87 against 471 and 354 on desktop). Reproduced in the
   pre-push baseline, so it is pre-existing and out of this round's scope (§2.2 forbids touching
   `client_code/`). Nav handlers: [`Frame/__init__.py:113`](client_code/Frame/__init__.py:113)
   (`reports_page_link_click`) and [`Frame/__init__.py:203`](client_code/Frame/__init__.py:203)
   (`settings_page_link_click`). Worth its own spec — these are two of the five screens the migration
   has to replace anyway.
2. **Mobile Transactions is not scrollable** (`scrollHeight ≤ clientHeight`) while rendering 278 chars.
   Probably correct — the list is short on the test account — but it means AC-8.4's scroll assertion has
   never been exercised on that screen at phone width. Worth re-checking against an account with more
   rows before the Transactions screen is migrated.
3. **One pre-existing console 404** on a resource at 390 px, in baseline and after alike. Not chased.

## New facts worth holding

- **`anvil.yaml`'s `db_schema` is a YAML *mapping keyed by table name*, not a list** — entries carry
  `client`, `columns`, `server`, `title`, and each column is `{admin_ui: {order, width}, name, type}`
  with `target` added for links. "Eleven entries" means eleven keys. Tables are stored alphabetically;
  `api_sessions` and `app_versions` sort between `accounts` and `budgets`.
- **The `users` table's `title` is `Users` (capital U) while its key is `users`.** Do not assume
  key == title when writing schema entries.
- **Anvil's own git accepted the push in well under 20 s**, consistent with the ≤16 s measured on IAMS.
- **The Forms app's mobile nav is Anvil's collapsed sidebar**, opened by `a.sidebar-toggle`; the desktop
  nav buttons are present in the DOM at 390 px but 0×0. Any future visual check at phone width **must**
  click that toggle first, or it will silently "verify" five screens while never leaving the first one —
  which is exactly what my first two baseline runs did.
- **`get_by_role("button", name=…)` does not match this app's Anvil buttons.** Use
  `page.locator("button").filter(has_text=…)`. My first run appeared to work only because it silently
  fell back to a text locator.
- Anvil serves these endpoints under `/_/api/…`; response headers arrive with
  `cache-control: no-cache, no-store` already set by the platform.

## What I could not reach or verify

- Anything requiring `build_secret`: AC-1, AC-5, AC-6, AC-7, AC-9, AC-11.1, and `/build/version`'s
  report of the module stamps (AC-10.3's second half).
- Anything requiring the two new tables: AC-2, AC-3, AC-4 (except 4.5), AC-5, AC-6, AC-7, AC-9.
- The Anvil schema-mismatch panel's verbatim wording. `docs/anvil_schema_panel.md` still holds the IAMS
  capture; **I have not been able to confirm it matches what Budget X shows**, because I have not opened
  the editor. If the panel differs from the §6 wording quoted above, tell me and I will correct the file
  on continuation.
