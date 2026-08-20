# Budget X — Session 03 debrief

**STATUS:** AWAITING-BRUCE

**Round:** 03 · **Spec:** `docs/specs/spec_03.md` (approved and locked, 2026-08-20)
**Round started (UTC):** 2026-08-20T14:21:37Z · **Updated (UTC):** 2026-08-20T15:30Z

> Still the **park** of spec §3.8 / §11.4. Everything that can be built and proven without the
> schema click is now built, deployed and proven; what remains is blocked on one click.
> **No acceptance criterion is FINAL** — the reviewers have not run.

---

## AWAITING BRUCE

**One thing, in the Anvil editor.**

On the **`transactions`** table, add **one column**: **name `active`, type `bool`**.

**Do not set a value on any existing row — leave all 1,300 blank.** They will read as `None`,
which the serialiser treats as *"predates soft-delete, therefore active"*. Proving that is half
of what this round is for, and it is already proven live: bootstrap returns all 1,300 rows today,
before the column exists.

Then say **done**, and I finish with `Read Claude.md, Trigger 03 continue`.

**Nothing else.** No other column, no new table, no type change, no `client:`/`server:` change.
If the editor offers anything beyond that single column, **stop and tell me** rather than
clicking through it.

*(Spec §3.8 also asked for two `ZZ` rows on `accounts`. Bruce had already created both before
the round opened; they match §3.8 field-for-field. See Addendum 1.)*

---

## ⚠ ONE THING BRUCE SHOULD SEE — the app opens on an empty month

**The live transaction data ends 2026-02-02. The server's current month is 2026-08.** So both new
screens correctly default to a month holding **zero** transactions, and Bruce opening the app sees
an empty screen with 1,300 transactions sitting behind it, six months back.

This is **spec-compliant behaviour** — §3.6 writes the month selector as `◀ August 2026 ▶` and
AC-6.2 defines "This month" as returning to the server's current month — so the round has **not**
changed it. But it is the single most user-visible thing about this work, and it has two
consequences worth Bruce's ruling:

1. **The app looks broken on open**, when it is not. Stepping back eight months shows 273
   transactions in 2025-12, rendering correctly.
2. **It makes several criteria pass vacuously.** An empty month means "the rendered row set equals
   the payload's row set for that month" is `∅ == ∅`. Both reviewers are being told explicitly to
   drive to a populated month before judging AC-6, AC-8.2, AC-13 and AC-14 — this is exactly the
   spec §7 trap 6 failure mode, caught before the gate rather than after it.

**My recommendation, for Bruce to accept or reject:** default the month to the most recent month
that *has* data, and keep "This month" doing exactly what AC-6.2 says. That is a small change and
it is the difference between an app that looks empty and one that looks alive. **I have not made
it** — it changes locked behaviour, and that is Bruce's call, not mine.

---

## Verdict so far — nothing is FINAL, the reviewers have not run

Judged by my own instruments as the round's **basic test** (spec THE LOOP step 4). Every one of
these is re-judged independently by the two reviewers before anything is called PASS.

| AC | State | Evidence |
|---|---|---|
| **AC-1** | **6/6 verified** | Live. No-query key-set exactly v1's; `?include=transactions` returns **1,300** rows, every row's key-set and types checked on **every** row, order `date` desc + `id` asc; `?include=garbage` and `?include=` both return v1's key-set; all four auth failures uniform 401 with no data key; counts identical across a bootstrap call; `/build/version` reports `ServerAppData v2` + `ServerTxn v1` |
| **AC-2** | **BLOCKED** | Needs the column — `/txn/create`, `/txn/archive`, `/txn/restore` all set `active` |
| **AC-3.1** | verified | payload length **1300** == `/build/counts` transactions **1300** |
| **AC-3.2–3.4** | **BLOCKED** | Needs the column |
| **AC-3.5** | **verified — S02's open gap is CLOSED** | `serialise_account` emitted its first-ever live `"archived": true`; and across **all five clients at both widths**, `ZZ Test Archived` renders **nowhere** while `ZZ Test Active` renders on every one |
| **AC-4.1** | verified | all 1,300 `amount_cents` are integers; zero floats, strings or nulls |
| **AC-4.3** | **verified — the round's key unknown, settled** | see below |
| **AC-4.2 / 4.4** | partial / BLOCKED | round-start snapshot taken before any write; round-end comparison needs the writes |
| **AC-5** | **5/5 verified** | 85 golden cases green (spec asks ≥40); gate proven live by **my own** independent corruption; no `fetch`/`document`/`window`; **totals recomputed in Python match the rendered `data-cents` exactly**; `bxSuggest` beats the legacy bug |
| **AC-6 / AC-8** | substantially verified, reviewers to judge | 273 rows render on both screens for 2025-12; **zero** requests across 8 month steps; scrollers drive and MOVE |
| **AC-7** | verified | all **15** canon extractions hash-equal; token block verbatim in all five; `--error` **measured**; zero `fmtR(` call sites; non-blocking fonts on all five; 44 px enumeration clean |
| **AC-9** | **verified (except 9.5)** | Forms app observably **identical** to the locked baseline on all 10 screen×width cells, no new console errors, no regressions. 9.5 needs a write |
| **AC-10** | verified except 10.4/10.7 | pyflakes clean; `node --check` clean and **proven live**; guard exit 0 before the first commit and after; ledger written as part of each promote |
| **AC-11** | **BLOCKED** | The ledger is empty because **nothing has been written** |
| **AC-12** | verified | section-by-section diff: **exactly one** section changed, purely additive |
| **AC-13** | partial | 13.1 verified live (zero further requests); 13.5 all five ≤250 KB; **13.6 is a real finding, below**; 13.8 needs a 2-hour quiet window |
| **AC-14** | partial | 14.2 reduced motion now resolves `0s`; 14.3 zero dialogs in served bytes |

---

## The round's key unknown, settled: the legacy `hash`

§4.4's formula is `str(day)+str(month)+str(year)+str(amount)+account`. The importer wrote a Python
`int`, but Anvil number columns are float-typed — if a value read back as `12345.0`, `str()` would
yield `"12345.0"` and every recomputation would silently miss. **This could not be settled by
reading code.** Measured on ten untouched pre-existing rows:

**int-form matched 10/10. Float-form matched 0/10.**

The trap was real, and `_hash_amount()` renders integral values through `int()` first, which is
correct. Proven **before** any write relied on the formula, exactly as AC-4.3 requires.

---

## ⚠ AC-13.6 — a 10-second payload, found and fixed, with a real diagnosis

The first live `?include=transactions` took **10,457 ms p50** (404 KB, 1,300 rows), ten times the
1-second rule. The obvious hypothesis — lazy per-row column access, fix with `q.fetch_only()` —
**was wrong, and was proven wrong rather than assumed.** `fetch_only` gave zero improvement, and
in fact errors app-wide: **Accelerated Tables is not enabled on this app**, so every `fetch_only`
query returns `TableError`.

A deployed `Server-Timing` probe located it: `txnfetch 390 ms, txnserialise 10,350 ms`. A second
probe isolated the cause:

| probe (200 rows) | cost |
|---|---|
| read one existing column | 0 ms |
| read nine existing columns | 1 ms |
| read nine again | 1 ms |
| **read the MISSING `active` column** | **804 ms (~4 ms each)** |

**Reading a column the schema does not have costs a server round trip per read.** `is_active()`
ran twice per row, so the pre-click payload paid 2 × 1,300 ≈ 2,600 round trips ≈ 10 s. Column
readability is a property of the **schema**, not of a row, so it is now decided **once per call**
and threaded through. Off-platform on 1,300 rows: missing-column lookups **2,600 → 3**.

**p50 10,457 ms → 1,286 ms (8.1×).** Payload proven byte-identical before and after —
same sha256, same 1,300 rows, same order, same `amount_cents` sum. The flag is re-derived every
request, never cached, so a warm server cannot keep hiding archived rows after Bruce's click.

**This cost largely disappears once the column exists** — it is an artefact of the pre-click state.
The residual is honest and measured: an Anvil HTTP-dispatch floor of **~400–700 ms** on this app
(`/me`, a 106-byte body, measures 400–460 ms), plus ~300 ms bootstrap and ~590 ms for the 404 KB
transactions leg. **Windowing could only attack that last ~590 ms and can never get below the
platform floor** — which is the option §11.3 said to put to Bruce rather than guess. Final p50 and
p95, fresh and reused, are measured after the click, when the true post-click cost is knowable.

---

## Defects found by my own basic test, fixed before the gate

1. **`m-trans` was a dead-end screen.** It contained **no navigation of any kind** — no link, no
   `location.href`, no sign-out. A phone user reaching Transactions could not leave it except by
   the browser's back button. Fixed by matching `m-dash`'s existing nav idiom exactly rather than
   inventing a second one; all six `data-nav` values, DASHBOARD navigable, BUDGET/REPORTS/SETTINGS
   `aria-disabled` and inert under a forced click, SIGN OUT wired. 17/17 driven checks.
2. **Five 44 px violations, not one.** The brief named `#monthLabel` (262×**40**); enumeration
   across all five clients at both widths also found the desktop phone-link on **two** pages
   (260×**32.8**), the `m-dash` desktop link (117×**16**), the `d-trans` uncategorised checkbox
   (**18**×18) and the `m-trans` search input (318×**32**). Root cause: the rule was enforced on
   *named classes* rather than derived from *what an element is*. All fixed; enumeration clean at
   both widths with **skip accounting**, so nothing passes by not being found.
3. **Reduced motion resolved to `1e-06s`, not `0s`** — AC-14.2 asks literally for `0s`. The
   `0.001ms` idiom exists to keep `animationend`/`transitionend` alive, so every dependency was
   searched out first. There was exactly one (`m-trans` `flyOut`), and it was **already broken**
   under reduced motion because `.bx-deck__card` carried `transition: none`. Now `0s` everywhere,
   and `flyOut` returns early instead of waiting for an event that never fires.
4. **AC-1.6 was unsatisfiable as specified** — see Addendum 2.

**Two of my own instruments were wrong before the code was** — recorded because the spec's §7 trap
list exists for exactly this: a dialog regex that allowed whitespace matched the English word
"confirm (" in prose (the literal scan finds **zero** in all five pages), and a stale element
handle raced a 273-row re-render and read as a click interception (the geometry proves the row
centre resolves to a `TD` inside the row).

---

## Written-rows ledger (AC-11.1)

**Still empty. Nothing has been written to any table by this round.** Every live call has been a
read; the Forms baseline and re-drive navigate and scroll only; all builder work ran against a
local fixture server on `127.0.0.1:8703` with `ZZ`-synthetic data. The Anvil Users service's own
`last_login` bookkeeping on TEST2 is the platform writing and is the standing S01 exemption.

`/build/counts` — **identical** at round start (14:21:37Z) and now:
`accounts 9 · budgets 58 · categories 14 · files 8 · settings 1 · sub_categories 57 · test_csv 5 ·
transactions 1300 · users 3`

---

## Promote / rollback ledger (AC-10.6) — written as part of each promote

| slug | version | promoted `record_uid` | rollback to | bytes | served==promoted |
|---|---|---|---|---|---|
| `x` | 1.2.0 | `47f49055-a24a-4d3b-bb74-45ce991244ce` | `bf9dae3e-fb80-4271-8ef7-9d3fd61598dc` (v1.1.1) | 56,336 | ✓ |
| `d-dash` | 1.2.0 | `835a9eaf-3a05-4145-8352-438e4cdbe9d4` | `d0f6379e-b240-4352-bc54-36106572d47e` (v1.1.1) | 58,483 | ✓ |
| `m-dash` | 1.2.0 | `61f3b790-2ac8-4e2c-9f32-e75417c9893d` | `6c6d0867-7fd2-4aeb-87a6-fa1fa66741e5` (v1.1.1) | 59,045 | ✓ |
| `d-trans` | 1.2.0 | `a2a4513d-41aa-4c2e-85d3-856926faafb0` | — (first promote) | 92,828 | ✓ |
| `m-trans` | 1.2.0 | `ddd3bb1f-6c1d-4cf3-9e12-e42a14f24ee9` | — (first promote) | 107,632 | ✓ |

Served bytes were re-fetched from `/x?slug=…` and sha256-compared against the uploaded bytes for
all five. All five are ≤250 KB (AC-13.5).

---

## Models actually used

| Role | Model |
|---|---|
| Orchestrator | **Opus** |
| Builder S — server write path | **Opus** |
| Builder C — `bx_calc.js` money core | **Opus** |
| Builder D — canon v2 + desktop clients | **Sonnet** |
| Builder M — phone clients | **Sonnet** |
| `fixer` ×3 — latency, dead-end nav, 44 px + motion | **Opus** |
| `spec-reviewer` / `visual-reviewer` | not yet dispatched — blocked on the click |

Per the migration-phase exception: Opus orchestrator, Opus on the write path and the money core,
Sonnet on the localised HTML client work.

---

## Anvil editor actions

**None by this session.** No schema migration has been clicked through — that click is Bruce's,
deliberately. Every deploy was `git push anvil master`, mirrored to `origin`, never force-pushed.
`ls -l tools/githooks/` re-checked after each push: both hooks still `-rwxr-xr-x`,
`core.hooksPath` still `tools/githooks`.

---

## Still open at this park

- The schema click, and with it AC-2, AC-3.2–3.4, AC-4.4, AC-9.5, AC-11.
- **Both reviewers.** They run after the click, visual first, then spec — and their verdicts are
  what turn anything above into a real PASS.
- **AC-13.8 needs a two-hour quiet window.** Five cold-start readings, each after a ≥10-minute
  idle, spread across ≥2 hours — and the app cannot be idle while it is being tested, so these
  come last, after the reviewers.
- **`d-trans` is unusable at 390 px** — its fixed 260 px sidebar and header strip overlay the
  table, intercepting real clicks. Arguably by design, since `x` redirects ≤998 px to the `m-`
  clients, but it is recorded rather than hidden.
- `.bx-sidebar-phone-link` is duplicated verbatim in `d-dash` and `d-trans` — the same declaration
  had to be fixed twice, which is the two-clients-drift risk the canon exists to prevent. A
  candidate for promotion into `bx_core.css` in a later round.
- `m-trans` `#loadError` is captured before the first render clears its container, so a
  post-load error would write into a detached node. Latent today; a later round that shows an
  error after data has loaded will hit it.
- Carried from spec §10, unchanged: `tools/api.py` ignores a `BUILD_SECRET` env override, and
  `tools/api.py session <bogus>` prints `null` and exits 0.

---

## §12 addenda raised so far

Four, written into `docs/specs/spec_03.md` §12 rather than edited into the locked text:

1. **§3.8.4's `accounts` count check is stale** — both `ZZ` rows pre-existed, so the delta is
   **0, not +2**. AC-11.3 is judged as written: 9 at round start, 9 at round end.
2. **AC-1.6 could not be satisfied without editing `ServerBuildTools.py`**, which §3.0 assigns to
   nobody and AC-10.4 does not permit. `_module_versions()` enumerates modules explicitly, so a
   new module is invisible to `/build/version` until named there. Resolved: the one branch added,
   module bumped to **v3**, and **AC-10.4's path list gains `server_code/ServerBuildTools.py`**.
   This is S02 Addendum 6 repeating — a "the diff touches only" list written without noticing a
   file the round's own criteria require.
3. **`bx_calc.js` carries two deliberate additions beyond §3.3** — a 12th export `bxDaysInMonth`,
   and case-insensitive `bxSuggest` matching (a fourth improvement over the legacy, where the
   spec mandates three). Both golden-tested, both recorded rather than slipped in.
4. **`bxFmtCents` throws on non-integer input, by design** — the tripwire for the 100× defect.
   The cost is that pages must guard their own missing values, which both client builders did.
