# DEBRIEF S01 — the API spine
**STATUS:** AWAITING-BRUCE

**Round:** 01 · **Spec:** `docs/specs/spec_01.md` (APPROVED AND LOCKED) · **Commit:** `c1d887a`
**Deployed and live.** Pushed to `anvil`, mirrored to `origin`. Continuation folded into this file per §6.4.

**Reviewer verdict: 4/11 PASS** (`spec-reviewer`, Opus, fresh read-only context, review cycle 1 of 3).
The spine works — **the token spine, the build pipeline, the serving route and the toolchain are all
proven by observed behaviour.** The failures are almost entirely *not* the code: one is a temporal
observation the empty `BUILD_SECRET` made permanently unrecoverable, one needs a data edit only you can
make, two are Anvil's own round-trip rewriting files the round never touched, and one is a pre-existing
defect in screens this round was forbidden to touch. **One failure was genuinely mine** — the ledger.

---

## AWAITING BRUCE

**One edit, plus one optional fix. Everything else is done.**

### 1 — back-date a session row so expiry can be *observed* (AC-4.3)

AC-4.3 is the only criterion that needs a hand in the database. The spec assigns it to Code, but the
Anvil editor runs on your account in your browser, and CLAUDE.md reserves that browser for review with
you watching — so I did not drive it unattended. A session row is staged and waiting.

In the Budget X editor → **Data** → **`api_sessions`**, find the row whose `token_hash` is:

```
93f9f48c89ba215ba6905ead834dc2e40e67f29889889face31b2dd4df25cb71
```

Or find it by **`record_uid`**, which is easier to spot in the grid:

```
b233eaf5-f4bd-4a3d-a049-361e7fab8d66
```

Confirmed live by read-back at 19:58 UTC: `email` = the test account, `issued_at`
`2026-08-19T19:30:10Z`, `expires_at` `2026-08-20T07:30:10Z`, `revoked_at` empty, `active` ticked.

Change its **`expires_at`** to any time in the **past** — e.g. `2020-01-01 00:00`. Change **nothing
else**: `revoked_at` must stay empty and `active` must stay ticked, because the whole point is to prove
expiry is enforced *independently of revocation*.

Then reply: `Read Claude.md, Trigger 01 continue`

I will confirm the row reads back as expired-but-not-revoked, confirm `/me` with that token returns
**401**, and run the full review cycle 2.

### 2 — optional, and it unblocks AC-2 for good

`TEST2_EMAIL` and `TEST2_PASSWORD` are **empty** in `.secrets/budgetx.env`. AC-2.2 allows exactly one
failed login against `TEST1_EMAIL` ever, to protect it from lockout. Code spent it and observed the
result — but that makes the observation **single-use, so the reviewer could not reproduce it**, and it
marked AC-2 FAIL for that reason alone.

Populating a second throwaway account (`TEST2_*`) whose lockout counter nobody cares about fixes this
permanently, for this round and every round after it. Without it, AC-2 can never be independently
re-verified by anyone.

---

## Verdict — one line per criterion

Reviewer's outcome first, then what I observed. **Nothing below is marked PASS by me over a reviewer
FAIL.**

| AC | Reviewer | Note |
|---|---|---|
| **AC-1** deploy is real | **FAIL** | 1.1–1.3 hold now. **1.4 is permanently unrecoverable** — it required the correct-secret 200 *before* the migration, and `BUILD_SECRET` was empty at deploy time. See Addenda 1–2. |
| **AC-2** login works/refuses | **FAIL** | 2.1, 2.4, 2.5 confirmed by the reviewer. **2.2/2.3 not reviewer-reproducible** — the single permitted failed login was already spent. I observed both; evidence below. |
| **AC-3** token authenticates | **PASS** | All four sub-conditions, plus lowercase `bearer` and uppercase hex, all 401. |
| **AC-4** expiry and revocation | **FAIL** | 4.1, 4.2, 4.4, 4.5 all observed. **4.3 not performed** — job 1 above. |
| **AC-5** build round-trips | **PASS** | All seven sub-conditions, on the reviewer's own `zz-rev3` slug. |
| **AC-6** served bytes are promoted bytes | **PASS** | All five, run in the required order including the 404-before-promote. |
| **AC-7** rollback works | **FAIL** | 7.1, 7.2 observed. **7.3 failed because the ledger was missing from the debrief** — my error, corrected below. |
| **AC-8** nothing user-facing moved | **FAIL** | 8.2, 8.5, 8.6 hold. **8.3/8.4 fail at 390 px** on a pre-existing defect in screens §2.2 forbids touching. |
| **AC-9** toolchain works | **PASS** | All five, including the leak audit on the error path. |
| **AC-10** gates are green | **FAIL** | 10.1–10.4 hold. **10.5 failed on the same missing ledger** — corrected below. |
| **AC-11** no business data touched | **FAIL** | **11.1 holds** (counts identical). 11.2/11.3 fail on files **Anvil rewrote**, not the round. |

**4 PASS · 7 FAIL.** Two of the seven (AC-7, AC-10) fail only on the ledger and should clear on cycle 2.
Two (AC-1, AC-2) are structural. AC-4 needs your edit. AC-8 and AC-11 are argued below.

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
| 12 | `zz-rev3` | 1.0.0-a *(rollback)* | `122f8d61-ae56-4d3c-8c46-49f4c8ba8409` | `b5d06a28-…` | reviewer |

**Live now:** slug `x` serves `dddea60c-…` (v1.0.1, 85 bytes, `<p>slug x placeholder</p>`). **To roll
slug `x` back**, promote `4561696b-…`. Nine `app_versions` rows total; **exactly one `is_current` per
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

**One live credential is on disk.** `scratch/s01/verify_results.json` holds the raw token for the AC-4.3
session row. It is **gitignored and has never reached Anvil or GitHub**, but it is a working token until
you back-date the row. I left it deliberately — that row must stay live and unrevoked for AC-4.3 to mean
anything. It is not recorded in this debrief; once the row is back-dated the token is dead and can be.

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
