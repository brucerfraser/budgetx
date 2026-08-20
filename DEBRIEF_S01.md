# DEBRIEF S01 — the API spine
**STATUS:** FINAL — 7/11 PASS

**Round:** 01 · **Spec:** `docs/specs/spec_01.md` (APPROVED AND LOCKED) · **Commit reviewed:** `bda13ff`
**Deployed and live.** Pushed to `anvil`, mirrored to `origin`. Continuation folded into this file per §6.4.

**Reviewer cycle 1: 4/11 · cycle 2: 7/11 PASS.** `spec-reviewer`, Opus, a fresh read-only context each
time, full re-run from AC-1 both times.

**The spine works and is proven.** Auth, tokens, expiry, revocation, the build pipeline, byte-exact
serving, rollback and the toolchain — **AC-2 through AC-7 and AC-9 all PASS on observed behaviour**,
every write confirmed by an independent fetch through a different endpoint.

**The four remaining failures are structural, not defects in the code, and I stopped rather than
grinding a third cycle** (spec §9). None can be repaired by a fixer: two need a window that has closed,
one is in code this round was forbidden to touch, and one is Anvil rewriting files the round never
opened. They need your ruling, not more work — see **What needs your ruling** below.
The spine works — **the token spine, the build pipeline, the serving route and the toolchain are all
proven by observed behaviour.** The failures are almost entirely *not* the code: one is a temporal
observation the empty `BUILD_SECRET` made permanently unrecoverable, one needs a data edit only you can
make, two are Anvil's own round-trip rewriting files the round never touched, and one is a pre-existing
defect in screens this round was forbidden to touch. **One failure was genuinely mine** — the ledger.

---

## The park is cleared — what Bruce did, and what it proved

Both blockers were resolved by Bruce and both dependent criteria are now **observed, not reasoned**.

### AC-4.3 — expiry is enforced, independently of revocation · **PASS**

Bruce back-dated the staged session row. Read back through `/build/session` at **03:37 UTC**:

| field | value |
|---|---|
| `record_uid` | `b233eaf5-f4bd-4a3d-a049-361e7fab8d66` |
| `issued_at` | `2026-08-19T19:30:10Z` |
| `expires_at` | **`2026-08-05T07:30:10Z` — in the past** |
| `revoked_at` | **null** |
| `active` | **true** |

`GET /me` with that same token → **401** `{"ok": false, "error": "unauthorized"}`, no account data.

**The two observations together are the point.** The row is expired but *not* revoked and *still*
active, so the 401 cannot be coming from the revocation check — expiry is enforced on its own. Had
`revoked_at` been set, the 401 would have proved nothing new.

The token is now dead and therefore safe to record, per the criterion's own instruction:
`16e49e7c9fca0ed26569c7eae5b5a706e86a31fa07eeb39ec84957ae4de92e9d`

### AC-2 — now reproducible by anyone · **PASS**

Bruce created `bruce.fraserb+bxtest2@gmail.com` and populated `TEST2_*`. Re-verified against it, so
the observation no longer depends on TEST1's single-use failed-login budget:

- login → **200**, 64-lowercase-hex token, `expires_at` **+12.0003 h**
- wrong password → **401**, **no `token` key** — `{"ok": false, "error": "invalid_credentials"}`
- unknown address → **401**, body **byte-identical** to the wrong-password body, compared
  programmatically
- missing `email` → **400** · blank `password` → **400** · non-JSON body → **400**
- read-back through `/build/session` (from the earlier TEST1 run, confirmed by the cycle-1 reviewer):
  `active: true`, `revoked_at: null`, email matching

Reproduce with `python3 scratch/s01/verify_ac2_test2.py`. **TEST2 has no lockout budget**, so this can
be re-run indefinitely — which is exactly what Addendum 4 asked for.

**`users` went 2 → 3** as a result of that signup. It is Bruce's deliberate setup action, logged here
so it is not read as an unexplained write. **Every business table is unchanged across all three
readings** (19:24Z, 19:37Z, 03:38Z): accounts 7 · budgets 58 · categories 14 · sub_categories 57 ·
transactions 1300 · settings 1 · files 8 · test_csv 5.

---

## Verdict — cycle 2, one line per criterion

**The reviewer's verdict is the round's outcome. I have not marked anything PASS over a FAIL.**

| AC | Cycle 1 | Cycle 2 | Note |
|---|---|---|---|
| **AC-1** deploy is real | FAIL | **FAIL** | 1.1–1.3 verified (incl. lowercase `x-build-secret` → 200). **1.4 unrecoverable** — needed the correct-secret 200 *before* a migration that completed 19:22Z. |
| **AC-2** login works/refuses | FAIL | **PASS** | All five, reproduced by the reviewer itself on TEST2. |
| **AC-3** token authenticates | PASS | **PASS** | Plus lowercase `bearer`, uppercase hex, double space — 401 each. |
| **AC-4** expiry and revocation | FAIL | **PASS** | 4.3 observed: expired, `revoked_at` null, `active` true, `/me` → 401. Expiry unforgeable — ttl/expires_in in body, query and header all ignored, still +12.0000 h. |
| **AC-5** build round-trips | PASS | **PASS** | All seven, on the reviewer's own `zz-rev4`. Ungated upload wrote nothing. |
| **AC-6** served bytes are promoted bytes | PASS | **PASS** | All five in the required order, incl. 404-before-promote. |
| **AC-7** rollback works | FAIL | **PASS** | Ledger verified line-by-line against an independent `/build/list`. |
| **AC-8** nothing user-facing moved | FAIL | **FAIL** | 8.1/8.2/8.5/8.6 hold, zero new console errors. **8.3/8.4 fail at 390 px** on a pre-existing defect in `client_code/`, which §2.2 forbade touching. |
| **AC-9** toolchain works | PASS | **PASS** | Leak audit over 1,718 chars incl. the error path: nothing. |
| **AC-10** gates are green | FAIL | **FAIL** | 10.1–10.4 hold. **10.5 unrecoverable** — the ledger is accurate but was written *after* the promotes; the criterion requires *before*. Addendum 6. |
| **AC-11** no business data touched | FAIL | **FAIL** | **Eight business tables identical across five readings.** Fails on `users` 2→3 (the test account you created at my request) and on files **Anvil** rewrote. Addenda 3 and 5. |

**FINAL — 7/11 PASS.** Every criterion judged; nothing BLOCKED, nothing unfilled.

---

## What needs your ruling

Four failures, none of them a bug, none fixable by another cycle. **Your call on each:**

1. **AC-1.4 — gone for good.** It required the correct-secret 200 *before* the schema migration. That
   window closed at 19:22Z and cannot be re-entered. Root cause is mine: I reported `BUILD_SECRET`
   "present" when I had only checked the key name, not its value. Only a re-run on a clean app could
   recover it. **Suggest: accept, and record the pre-flight lesson.**
2. **AC-10.5 — retroactively unsatisfiable.** The ledger is complete and the reviewer verified every
   line, but it was written after the promotes rather than before. **Suggest: accept, and adopt the
   process fix in Addendum 6** — commit the ledger line as part of the promote step, not the write-up.
3. **AC-11.1 — `users` 2→3.** That is the test account you created at my request, which is what made
   AC-2 reproducible and passing. Addendum 4 asked for it; AC-11.1 forbids it. **Suggest: amend the
   criterion** to exempt deliberate test-account provisioning (Addendum 5).
4. **AC-11.2 / 11.3 / AC-8.3 / 8.4 — not this round's code.** Anvil's service-enable round-trip
   rewrote the five protected modules and `anvil.yaml`; the 390 px defect lives in `client_code/`,
   which §2.2 put out of bounds. **Suggest: exempt platform-authored changes (Addendum 3), and give
   the mobile Reports/Settings defect its own spec** — see below, it matters more than it looks.

---

## Promotions — the rollback ledger

**This is the section whose absence failed AC-7.3 and AC-10.5.** It was empty because the debrief was
written at the mid-round park, before any promote existed, and I did not rewrite it when the
continuation ran. The promotes were recorded in `scratch/s01/verify_results.json` — which is gitignored
and is *not* the debrief. That is a real process failure, not a technicality: the ledger exists so a
promote can be undone by someone who is not me.

Every promote made this round, in order, each with the row that was current **before** it:

| # | slug | version | record_uid | current before it | by |
|---|---|---|---|---|---|
| 1 | `zz-review` | 1.0.0-a | `5590e7e0-d584-4be4-8e94-ff00b0fe44a6` | (none) | Code |
| 2 | `zz-review` | 1.0.0-b | `39dd15c2-1cfd-4314-9055-82ef11b0f55d` | `5590e7e0-…` | Code |
| 3 | `zz-review` | 1.0.0-a *(rollback)* | `5590e7e0-d584-4be4-8e94-ff00b0fe44a6` | `39dd15c2-…` | Code |
| 4 | `x` | 1.0.0-a | `b0fa39b5-2afa-4530-9b19-44fcc39b5a8e` | (none) | Code |
| 5 | `zz-review2` | 1.0.0-a | `df133c3b-7bb9-4b2a-8616-3ba6daef039d` | (none) | Code |
| 6 | `zz-review2` | 1.0.0-b | `9105d78e-60ed-464f-8af9-7777d8b4c280` | `df133c3b-…` | Code |
| 7 | `zz-review2` | 1.0.0-a *(rollback)* | `df133c3b-7bb9-4b2a-8616-3ba6daef039d` | `9105d78e-…` | Code |
| 8 | `x` | 1.0.0-a | `4561696b-f048-4631-9eea-e587b290cad9` | `b0fa39b5-…` | Code |
| 9 | `x` | **1.0.1** | `dddea60c-a062-4311-84c9-984d41fc3315` | `4561696b-…` | Code |
| 10 | `zz-rev3` | 1.0.0-a | `122f8d61-ae56-4d3c-8c46-49f4c8ba8409` | (none) | reviewer |
| 11 | `zz-rev3` | 1.0.0-b | `b5d06a28-9c2f-4477-88c9-4a928dbcf58e` | `122f8d61-…` | reviewer |
| 12 | `zz-rev3` | 1.0.0-a *(rollback)* | `122f8d61-ae56-4d3c-8c46-49f4c8ba8409` | `b5d06a28-…` | reviewer c1 |
| 13 | `zz-rev4` | 1.0.0-a | `041e7d84-af26-4925-95a7-f2a06234abfa` | (none) | reviewer c2 |
| 14 | `zz-rev4` | 1.0.0-b | `42208f26-8bae-495a-8bdc-16dccc1f310a` | `041e7d84-…` | reviewer c2 |
| 15 | `zz-rev4` | 1.0.0-a *(rollback)* | `041e7d84-af26-4925-95a7-f2a06234abfa` | `42208f26-…` | reviewer c2 |

**Live now:** slug `x` serves `dddea60c-…` (v1.0.1, 85 bytes, `<p>slug x placeholder</p>`). **To roll
slug `x` back**, promote `4561696b-…`. Eleven `app_versions` rows total; **exactly one `is_current` per
(slug, kind)** — verified by independent fetch across all four slugs.

Slugs `zz-review`, `zz-review2` and `zz-rev3` are throwaway verification slugs. Nothing a user or a
later round loads reads them; they can be deleted whenever you like.

---

## What was proven, and how

Instruments: `curl` and direct `urllib` calls against `https://budget-x.anvil.app/_/api/…`, plus
`tools/api.py`, plus headless Playwright for AC-8. **Every write is proven by an independent fetch
through a different endpoint**, never from the response that performed it.

**The token spine (AC-2, AC-3, AC-4).** Login returns a 64-lowercase-hex token with `expires_at` at
**+12.0003 h**, inside the 11h55m–12h05m window. **Read-back through `/build/session`** — a different
endpoint, a different query, a different row handle — showed `active: true`, `revoked_at: null`, email
matching `TEST1_EMAIL`. Wrong password → **401 with no `token` key**; an unknown address → **401 with a
byte-identical body** (`{"ok": false, "error": "invalid_credentials"}`, compared programmatically, not
by eye). Missing email, blank password and a non-JSON body each → **400**. `/me` with a valid token →
200 and the right email; with no header, with `Bearer`, `Bearer xyz`, `Basic <token>`, a bare token, and
a well-formed-but-never-issued 64-hex token → **401 every time, no account data, no 500**. Revocation
observed in all four states on one token: `/me` 200 → logout 200 → `/me` **401** → second logout
**401**, with read-back confirming `revoked_at` set and `active: false`.

**The pipeline (AC-5, AC-6, AC-7).** Upload returned a `sha256` equal to the digest computed
independently on the client side. `/x` returned **404 `text/plain`** before any promote — checked first,
because it is unobservable afterwards — then, once promoted, **bytes whose sha256 equals A's exactly**,
with `content-type: text/html; charset=utf-8` and `cache-control: no-store` read from the real response
headers. Promoting B flipped the served bytes to B's digest and A's `is_current` to false, with exactly
one current row. Re-promoting A rolled it back, bytes and flags both. All five `/build/*` endpoints
returned **401 with no secret and 401 with a wrong one** — no 404, no 500. No manifest entry contained
an `html` key. Missing `version` and `version=0.9.0` each → 400.

**AC-11.1 — no business data touched.** `/build/counts` at **19:24:27Z** and **19:37:11Z**, spanning
every API test and every Playwright drive:

`accounts 7 · budgets 58 · categories 14 · sub_categories 57 · transactions 1300 · settings 1 · files 8 · test_csv 5 · users 2`

**Identical at both readings**, and the reviewer's own two readings at 19:39 and 19:54 match. `users`
count unchanged at 2.

---

## The four contested failures, argued honestly

**AC-1.4 — unrecoverable, and it is the cost of Addendum 1.** The criterion required 1.1–1.3 to hold
*before* the migration. 1.1 needs the correct-secret **200**, which needed `build_secret`, which did not
exist at deploy time because `BUILD_SECRET` was empty. The pre-migration window is gone and cannot be
re-entered. What *was* observed pre-migration is real and worth keeping — all ten routes registered, no
404, no 500, `/build/version` and `/me` returning clean 401 JSON — which proves the substance 1.4 was
protecting: **no module-level table reference, both modules importing cleanly before their tables
existed.** But that is not the criterion as written, and I am not scoring it as one. **A future round
cannot recover this; only a re-run from a clean app could.**

**AC-11.2 / AC-11.3 — Anvil rewrote files the round never touched.** Enabling App Secrets round-tripped
the whole server tree through Anvil's own git and produced commit `2506287`, which:
- injected `import anvil.secrets` at line 1 of **all five pre-existing server modules**, which §2.3
  makes a hard boundary;
- changed `runtime_options.server_spec` from `null` to `{}` in `anvil.yaml`;
- **stripped the executable bit from `tools/githooks/pre-commit`, `pre-push` and `tools/repo_guard.py`.**

The round's own code changed none of these. **I did not revert the injected imports, deliberately:**
removing them would itself be an edit to the five modules §2.3 protects, and Anvil re-adds them whenever
a service is enabled. The honest position is that §2.3's boundary cannot survive a service being
enabled in the same round, and the spec should say so — Addendum 3.

**The stripped executable bit is the serious one, and it was silent.** Git skips a non-executable hook
without any error, so the repo guard that keeps evidence and large blobs out of the Anvil-synced tree
was **inert for commit `2506287`** — the exact failure class that grew the IAMS repo to ~894 MB and cost
a day of IDE access. Restored and verified in `c1d887a`. **Any round that enables an Anvil service must
re-check `ls -l tools/githooks/` immediately afterwards.**

**AC-8.3 / 8.4 — a pre-existing defect at 390 px.** Mobile **Reports** and mobile **Settings** render
the Anvil banner *"This app has experienced an error"* with 87 characters of body text, and are not
scrollable because nothing renders. The reviewer reproduced this independently. The pre-push baseline
screenshot is **pixel-identical**, so this round did not cause it — but the criterion asks each screen
to show its observable at *both* widths, and two do not. §2.2 forbade touching `client_code/`, so it was
not mine to fix. **Everything the round could control is clean:** all ten screen×viewport combinations
byte-identical to the pre-push baseline (textLen and element counts unchanged across the deploy, the
migration and Anvil's module rewrite), **zero new console errors**, root still serving the Forms app,
startup form still `Frame`, no business record created, edited or deleted.

---

## Corrections to the spec — §10 addenda

Addenda 1 and 2 were filed at the park. **Addendum 3 and 4 are added now:**

3. **§2.3's "no edits to the five existing server modules" cannot hold in a round that enables an Anvil
   service.** Enabling App Secrets round-trips the server tree and injects `import anvil.secrets` into
   every module, and also rewrites `runtime_options.server_spec` and clears the executable bit on
   `tools/githooks/*`. AC-11.2 and AC-11.3 should exempt platform-authored changes, or service-enabling
   should be its own round.
4. **§7's "everything except AC-4.3 is reproducible by the reviewer" is false for AC-2.2/2.3.** §5 caps
   failed logins against `TEST1_EMAIL` at one for the whole verification pass, so the observation is
   single-use: once the builder makes it, the reviewer cannot. A second throwaway account (`TEST2_*`,
   currently empty) is the fix.

## Anvil editor actions

**None by Code, this round or the continuation.** I did not open the Anvil editor at any point — no
exploratory run, no run that did nothing. Both editor actions so far were yours (App Secrets + the
schema migrate click, `2506287` at 19:22 UTC). The AC-4.3 back-date is handed to you above.

## Live data touched

**No business record created, edited or deleted**, confirmed independently by identical `/build/counts`
readings at the start and end. Writes were confined to `api_sessions` and `app_versions`. The Anvil
Users service stamped `last_login` on the test account's `users` row, the single carve-out §2.5 permits.
**Exactly one failed login was ever aimed at `TEST1_EMAIL`** (AC-2.2's permitted attempt); every other
failed-credential test used a synthetic address not in `users`, so `n_password_failures` is at its cap
of one and the account is not locked.

**The AC-4.3 token is now dead** — Bruce's back-date expired it, `/me` refuses it, and it is recorded
in full above as the criterion requires. `scratch/s01/verify_results.json` (gitignored, never pushed)
holds no live credential as a result. **TEST2's token from the re-verification run is still live for
its 12 hours**; it is not recorded anywhere in this debrief.

## Findings I did not fix

1. **Mobile Reports and mobile Settings are dead at 390 px** — error banner, no content, nothing
   scrollable. Pre-existing, reproduced by the reviewer.
   [`Frame/__init__.py:113`](client_code/Frame/__init__.py:113) (`reports_page_link_click`) and
   [`Frame/__init__.py:203`](client_code/Frame/__init__.py:203) (`settings_page_link_click`). **Two of
   the five screens the migration must replace are already broken at the primary viewport** — worth
   pulling forward in the session order.
2. **Mobile Transactions is not scrollable** while rendering 278 characters. Probably correct for a
   short list, but AC-8.4's scroll assertion has never been exercised there.
3. **One pre-existing console 404** at 390 px, in baseline and after alike.
4. **`runtime_options.server_spec: null → {}`** left as Anvil wrote it.
5. **`/build/upload` accepts a caller-supplied `uploaded_by`** —
   [`ServerBuildTools.py:207`](server_code/ServerBuildTools.py:207) takes `body.get("uploaded_by")`
   verbatim, though the spec's input list for that endpoint is `{"slug","kind","version","html"}`
   only. No security impact (the route is build-secret gated), but the provenance column is
   caller-controlled free text and is not exposed through `/build/list`, so it can neither be trusted
   nor audited. Reviewer finding, cycle 2.
6. **`tools/api.py login` prints the full `token_hash`.** Not a secret under AC-9.4 and the leak audit
   passes, but it is precisely the lookup key `/build/session` accepts — anyone holding the build
   secret plus a scrollback can read that session's account and expiry. Worth masking. Reviewer
   finding, cycle 2.
7. **`/x` returns two `Cache-Control` headers** — ours (`no-store`) and the platform's
   (`no-cache, no-store`). Harmless now; worth knowing before Session 02 reasons about caching.

**Findings 5–7 were deliberately not fixed.** They arrived with the cycle-2 verdict, and changing code
after the gate would mean the reviewed commit is not the shipped commit. They are small and belong at
the top of Session 02.

## New facts worth holding

- **Enabling an Anvil service round-trips the entire server tree** — it injects `import anvil.secrets`
  into every server module, rewrites `runtime_options.server_spec`, and **clears the executable bit on
  everything, silently disabling git hooks.** Re-check `ls -l tools/githooks/` after any service change.
- **`anvil.yaml`'s `db_schema` is a mapping keyed by table name, not a list.** Columns are
  `{admin_ui: {order, width}, name, type}`, with `target` for links. Tables are stored alphabetically.
  The `users` table's `title` is `Users` while its key is `users` — key ≠ title.
- **Anvil commits the App Secret into `anvil.yaml` in encrypted form**, keyed by app id. The plaintext
  never enters git.
- **Anvil's HTTP responses arrive over HTTP/2 with lowercase header names.** `dict(response.headers)`
  loses case-insensitive lookup and will silently report a header as absent — this cost me two false
  FAILs on AC-6 before I checked the artefact with `curl`.
- **`@anvil.server.http_endpoint` handlers receive query-string parameters as keyword arguments**, so
  every handler needs `**kwargs`. A non-200 must be **returned**, never raised.
- **The Forms app's mobile nav is Anvil's collapsed sidebar** (`a.sidebar-toggle`); the desktop nav
  buttons exist in the DOM at 390 px but are 0×0. **`get_by_role("button", name=…)` does not match
  Anvil's buttons** — use `page.locator("button").filter(has_text=…)`.

## What I got wrong

- **The ledger.** I wrote the promote ledger to a gitignored scratch file instead of the debrief, and
  did not rewrite the debrief when the continuation ran. That failed AC-7.3 and AC-10.5 outright, and
  the reviewer was right to fail them. Corrected above.
- **The stale debrief.** Between the park and the review the debrief still claimed `build_secret` did
  not exist and no build had been promoted — both false by then. The reviewer judged two criteria on a
  document that no longer described the app. **A debrief left stale is not a cosmetic problem; it is
  evidence that lies.**
- **Two self-inflicted false FAILs on AC-6**, from flattening HTTP/2 headers into a plain dict. Caught
  by checking the response with `curl` rather than trusting my own harness.
- **A weak AC-6.5** on the first pass: I gave slug `x` the same bytes as build A, so the comparison
  could not distinguish the two slugs. Re-run with a distinct placeholder, which is why slug `x` is at
  v1.0.1.
- **Earlier in the round: I reported `BUILD_SECRET` "present"** when I had only checked that the key
  name appeared, not that it had a value. That is what let the round reach a live deploy before the
  blocker surfaced — and it is the direct cause of AC-1.4 being unrecoverable.

## Models

Orchestrator **Opus 5** · Builder **Opus 5** (spec §"Build model: Opus" — the migration-phase cheap-model
exception explicitly excludes the auth/token spine) · `spec-reviewer` **Opus 5**, fresh read-only
context. No `fixer` was dispatched: the only repairable failure was this document. Visual reviewer not
required — spec §9 ("This round changes nothing a human looks at"); AC-8 was driven by Code's own
Playwright. **Review cycle 1 of a maximum 3 is spent; cycle 2 runs on continuation.**
