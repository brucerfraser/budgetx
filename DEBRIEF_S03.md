# Budget X — Session 03 debrief

**STATUS:** AWAITING-BRUCE

**Round:** 03 · **Spec:** `docs/specs/spec_03.md` (approved and locked, 2026-08-20)
**Round started (UTC):** 2026-08-20T14:21:37Z · **This debrief written (UTC):** 2026-08-20T14:35Z

> This is the **park** required by spec §3.8 and §11.4. The round does **not** close unattended
> because it needs one schema click that only Bruce can make. Work continues while this sits —
> all four builders are running. Nothing below is a final verdict; no acceptance criterion is
> judged yet.

---

## AWAITING BRUCE

**One thing, in the Anvil editor. (The two `ZZ` account rows are already done — see below.)**

On the **`transactions`** table, add **one column**:

| name | type |
|---|---|
| `active` | **bool** (True/False) |

**Do not set a value on any existing row — leave all 1,300 of them blank.** That is deliberate:
they will read as `None`, which the serialiser reads as *"predates soft-delete, therefore active"*
(spec §4.3). Setting them would not break anything, but leaving them blank is what the round is
built to prove.

Then say **done** and I resume with `Read Claude.md, Trigger 03 continue`.

**Nothing else is needed.** No other column, no new table, no type change, and no change to
`client:`/`server:` on any table. If the editor shows you anything beyond that single column,
**stop and tell me** rather than clicking through it.

---

## Already done — the half of the park Bruce completed before the round started

Spec §3.8 asked for two `ZZ` rows on `accounts` as well as the column. **Both rows were already
in the live table when this round opened**, exactly as §3.8 specified, so the park asks only for
the column.

| `acc_id` | `acc_name` | `archived` | state |
|---|---|---|---|
| `ZZ-TEST-ACTIVE` | `ZZ Test Active` | `false` | present, verified on the live bootstrap |
| `ZZ-TEST-ARCHIVED` | `ZZ Test Archived` | **`true`** | present, verified on the live bootstrap |

Both were compared field-for-field against the §3.8 table and match on every field. `accounts` is
therefore at **9** rows, not the 7 the spec's §3.8.4 check anticipated — **that check is written
against a pre-seeding reading and is corrected in Addendum 1 below.**

**This already closes S02's open gap, ahead of AC-3.5:** `serialise_account` has now emitted
`"archived": true` on a **live** response for the first time in the project's history — previously
provable only with a route mock, because `accounts` held 7 rows and 0 archived. Verified on the
live `GET /_/api/app/bootstrap` at 2026-08-20T14:22Z. The remaining half of AC-3.5 — that all five
clients render `ZZ Test Active` and render `ZZ Test Archived` nowhere — is a client criterion and
is judged after the clients are built.

---

## What is done so far

**Environment and gates (AC-10.3, first half).** Verified **before** the round's first commit,
2026-08-20T14:26:07Z: `git config core.hooksPath` = `tools/githooks`; both hooks present and
executable (`-rwxr-xr-x`); `python3 tools/repo_guard.py` exit **0**. Re-checked after the schema
click, per the standing rule that a platform write can silently strip the executable bit.

**Toolchain.** There is still no `node` on this Mac. As in S02, `node --check` and the golden-test
runner use the real node that Playwright ships —
`…/playwright/driver/node`, **v24.15.0** — confirmed to accept `--check`, to exit 0 on a valid
file and **non-zero on a deliberately broken one**, so the checker is live rather than assumed.

**Round-start snapshots, UTC-stamped, taken before anything changed** (the AC-4.4 / AC-11.2 /
AC-11.3 baselines): `/build/counts` at 2026-08-20T14:21:37Z —
`accounts 9 · budgets 58 · categories 14 · files 8 · settings 1 · sub_categories 57 ·
test_csv 5 · transactions 1300 · users 3` — and a full `GET /app/bootstrap` body.
**A round-start `?include=transactions` snapshot cannot exist yet**, because the parameter is what
this round builds; it is taken the moment ServerAppData v2 deploys and **before any write**, which
is what AC-4.4 and AC-11.2 actually require.

**Forms-app baseline (AC-9.1), captured before the round's first push** and locked. TEST2, at
1280×800 and 390×844, across Dashboard, Transactions, Budget, Reports and Settings, each screen
navigated and scrolled, console captured. It reproduces every pre-existing defect the spec
documents:

| | desktop 1280×800 | mobile 390×844 |
|---|---|---|
| Dashboard | renders, scrolls (837/779) | renders, scrolls (1278/661) |
| Transactions | renders, scrolls (1017/779) | renders, **cannot scroll** — `scrollHeight == clientHeight`, no scroller at all |
| Budget | renders, scrolls (1112/779) | renders, scrolls (1919/201) |
| Reports | renders, scrolls (832/779) | **Anvil error dialog**, textLen 87 |
| Settings | renders, scrolls (413/299) | **Anvil error dialog**, textLen 87 |
| console errors | 0 | 1 — a 404 on a resource |

Mobile Reports and mobile Settings are the **pre-existing S01-documented defects**; mobile
Transactions' missing scroller is the S02 finding that `m-trans` exists to fix. All three are
recorded as **baseline, not as regressions of this round**, and the round is judged no-worse
against this file.

**Two commits pushed to both remotes** (`f2018d0`):
1. `458d8c2` — the §3.7 housekeeping commit: `docs/cowork_project_instructions.md` committed
   **exactly as Bruce left it** on 2026-08-19, unchanged by this session, on its own.
2. `f2018d0` — `docs/specs/spec_03.md` committed as approved and locked.

**Round-03 fixtures built (§5)** and self-checked against every stated requirement: 443
transactions over **14** months, 24.8% uncategorised, 6 transfer-sentinel rows, a 28-day February
(01→28) and 31-day boundaries, two same-date same-account opposite-sign rows, an empty
description, a 380-character description, one `active:false` row, amounts spanning ±1 to
±9,999,999 cents, all integers, and an `accounts` array carrying **both** an `archived:false` and
an `archived:true` row. All values are `ZZ`-synthetic; **no real Budget X data is in the
fixtures.**

**Builders dispatched** (all four running in parallel, per §3.0):

| Builder | Model | Owns |
|---|---|---|
| **S** — server | **Opus** | `ServerTxn.py` (new) · `ServerAppData.py` v2 · `tools/api.py` |
| **C** — calc | **Opus** | `client_src/bx_calc.js` · `tools/calc_golden.mjs` · `tools/calc_cases.json` |
| **D** — desktop | **Sonnet** | `bx_core.css`/`bx_core.js` v2 (the canon) · `d-trans` · re-cut `x`, `d-dash` |
| **M** — mobile | **Sonnet** | `m-trans` · re-cut `m-dash` |
| Orchestrator | **Opus** | integration, deploy, ledger, reviewers, this debrief |

Model assignment follows the migration-phase exception: Opus orchestrator, Opus on the write
path and the money core, Sonnet on the localised client work. Final per-role record goes in the
closing debrief.

---

## Written-rows ledger (AC-11.1)

**Empty. Nothing has been written to any table.** Every live call so far has been a read
(`/auth/login`, `/me`, `/build/version`, `/build/counts`, `/app/bootstrap`) plus the Forms-app
baseline drive, which navigates and scrolls only. The Anvil Users service's own `last_login`
bookkeeping on TEST2 is the platform writing and is the standing S01 exemption.

Builders are working **entirely against a local fixture server** on `127.0.0.1:8703`. No builder
has credentials for a write endpoint, because no write endpoint is deployed.

---

## Open at the park

- **`transactions.active` does not exist yet** — the click above. Until it lands, `ServerTxn.py`
  and `ServerAppData` v2 are written but **cannot be deployed or tested**, and every
  `active`-dependent criterion (AC-1.2, AC-2, AC-3, AC-4) is unjudged.
- **The `hash` float/int question is the round's key open empirical unknown.** §4.4's formula is
  `str(day)+str(month)+str(year)+str(amount)+account`. The importer wrote a Python `int`
  (`csv_handler.py:157–160`), producing e.g. `"12345"` — but Anvil number columns are float-typed,
  and if the value reads back as `12345.0` then `str()` yields `"12345.0"` and a recomputation
  will not match the stored hash. **This cannot be settled by reading the code; it needs a live
  read of real rows**, which needs ServerAppData v2 deployed. AC-4.3 is exactly this test, on ten
  untouched rows, and it is deliberately run **before** any write relies on the formula.
- **AC-13.8 has a scheduling constraint worth naming now:** it requires **five** cold-start
  readings, each after a **≥10-minute idle**, spread across **at least two hours**. The app cannot
  be idle while it is being tested, so these readings have to be taken in genuine quiet windows
  after the final deploy. That alone sets a floor of roughly two hours on the round's wall-clock
  length, independent of how fast the build goes.

---

## §12 addenda raised so far

**Addendum 1 — 2026-08-20 — §3.8.4's `accounts` count check is written against a stale reading.**
§3.8.4 says the orchestrator verifies "`GET /build/counts` shows `accounts` at **9**, up by exactly
two". Both `ZZ` rows were already present at round start, so the round-start reading is **already
9** and the delta across this round is **0, not +2**. The substance of AC-11.3 is unaffected and
is judged as written — `accounts` must be **9 at round start and 9 at round end**, with the two
`ZZ` rows matching §3.8's field values exactly and **every pre-existing account row unchanged on
every field the payload exposes**. What changes is only the arithmetic of the check, not what it
proves. The `ZZ` rows were created by Bruce, outside this round, before it opened.
