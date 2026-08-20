# Budget X — Session 03 debrief

**STATUS:** INTERIM

**Round:** 03 · **Spec:** `docs/specs/spec_03.md` (approved and locked, 2026-08-20)
**Round started (UTC):** 2026-08-20T14:21:37Z · **Updated (UTC):** 2026-08-20T19:20Z

> **The park is over — Bruce approved the migration and the round is running again.** The
> migration then did something the spec ruled out, hid all 1,300 transactions, and was found,
> diagnosed and fully reconciled; that incident is the most important thing in this debrief.
> **No acceptance criterion is FINAL** — the visual reviewer is running, the spec reviewer
> follows it.

---

## ⚠ THE INCIDENT — the migration wrote `False` into all 1,300 rows and hid every transaction

**This is the round's most important finding, and it is a platform fact the spec had explicitly
ruled out.**

Spec §3.8.3 and §4.3 state that adding the column "without touching the 1,300 existing rows"
leaves them reading `None`, and that *"this is deliberate and the serialiser depends on it"*.
**That is not what Anvil does.** After the migration was approved, every one of the 1,300
pre-existing rows carried a real **`False`**.

The failure was total and silent:

- `GET /app/bootstrap?include=transactions` returned **`200` with an empty array**.
- `/build/counts` still reported `transactions 1300` — nothing was deleted.
- Nothing raised, nothing logged, no error reached any client.
- Both new screens rendered **zero transactions**. The Forms app was unaffected throughout, because
  it knows nothing about `active`.

**The `is not False` test did not save us, and could not have.** §4.3 correctly insists on
`is not False` over `is True`, and the code implements it in exactly one function. But the stored
values genuinely *were* `False` — and no test can separate "archived" from "never initialised"
once the platform has written a real boolean. The defence the spec designed was aimed at the right
hazard and was defeated by a different mechanism.

**How it was found and handled:**

1. Caught by the orchestrator's own post-push health check, not by a reviewer and not by Bruce.
2. **Diagnosed with one minimal, reversible write** — a single `/txn/restore` on one id — which
   made exactly that row reappear in an independent fetch. Mechanism confirmed on one row before
   anything was done to 1,300.
3. All 1,300 rows restored to `active: true` in **seven batches of ≤200** through `/txn/restore`,
   every row written to the ledger as it happened.
4. **Reconciled against the snapshot taken before any write:**

| check | result |
|---|---|
| rows returned | **1300** (round-start 1300) |
| every `active` a real boolean | yes — distinct value set `[True]` |
| ids missing vs round-start | **0** |
| ids new vs round-start | **0** |
| rows differing on **any** field except `active` | **0** |
| `sum(amount_cents)` | **identical** — `-13,576,179` |
| row order contract | intact |
| all table counts | unchanged |

**The standing rule this produced**, now in CLAUDE.md, the Master Note and spec Addendum 6:

> **After adding a bool column, explicitly initialise every existing row in the same round, before
> anything reads it. Treat a migration as leaving the column *wrong*, not empty.** The bad window
> opens at the schema **push**, before approval — the intermediate state already returns `False`.
> Prove the recovery by field-by-field reconciliation against a pre-migration snapshot, never by a
> row count.

**Consequence for AC-3.1:** its wording — "every legacy `None`-valued row is present" — can no
longer be proven, because after remediation no row is `None`; all 1,300 carry an explicit `True`.
The substance (all 1,300 present, none lost, none altered) is proven, and more strongly than the
criterion asked. Recorded rather than quietly re-interpreted.

---

## Bruce's correction, applied in four places

Bruce, mid-round: *"I never add columns or tables. You do. Then I approve the schema."* Spec §3.8
had this backwards and asked him to create the column by hand. Corrected in **Addendum 5**, and the
rule now lives in **CLAUDE.md** (§"Schema changes need Bruce's click"), the vault's **Master
Note** standing decisions, and this session's memory. Code edited `db_schema` in `anvil.yaml`
**textually**, pushed it, and Bruce approved the migration — the sequence every later round follows.

**AC-11.5 — the `anvil.yaml` diff for the whole round is exactly one column:**
`transactions.active`, type `bool`. `client: full` / `server: full` unchanged on the table, no
other table touched, no top-level key altered, no `runtime_options` churn. Verified by a read-only
parse against a pre-edit copy, never `safe_load` → `dump`.

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
| **AC-2** | **8/8 verified** | Every write proven by an **independent** bootstrap re-fetch, never the endpoint's own `ok:true`. Single + 25-row batch categorise; bad category and a **mixed** batch both 400 with **no row changed** (atomic); `"transaction_id":"FORGED"` / `"hash":"FORGED"` ignored and a real uuid4 + computed hash stored, with neither forged value anywhere in the table; hash recomputed on date/amount/account change and matched by independent Python; archive removes the row from the payload while `/build/counts` is **unchanged**; archive→restore returns it; 404 with no data keys, 201-item batch 400 |
| **AC-3.1** | verified in substance, **wording overtaken** | payload length **1300** == `/build/counts` **1300**. Its "`None`-valued row" wording is no longer provable — see the incident and Addendum 6 |
| **AC-3.2–3.4** | **verified** | Archiving one row removed **exactly** that id (1301→1300) with every other row still present, compared by **id set**; restore returned the set to exactly its former membership (symmetric difference **0**); a row created this round carries `active: true` as a real bool and the serialiser emits no null for `active` on any of 1,301 rows |
| **AC-3.5** | **verified — S02's open gap is CLOSED** | `serialise_account` emitted its first-ever live `"archived": true`; and across **all five clients at both widths**, `ZZ Test Archived` renders **nowhere** while `ZZ Test Active` renders on every one |
| **AC-4.1** | verified | all 1,300 `amount_cents` are integers; zero floats, strings or nulls |
| **AC-4.3** | **verified — the round's key unknown, settled** | see below |
| **AC-4.4** | **verified** | Every `(transaction_id, amount_cents)` pair compared between the round-start snapshot and a post-remediation fetch: **zero** rows differ on any field except `active`, `sum(amount_cents)` identical at `-13,576,179` |
| **AC-5** | **5/5 verified** | 85 golden cases green (spec asks ≥40); gate proven live by **my own** independent corruption; no `fetch`/`document`/`window`; **totals recomputed in Python match the rendered `data-cents` exactly**; `bxSuggest` beats the legacy bug |
| **AC-6 / AC-8** | substantially verified, reviewers to judge | 273 rows render on both screens for 2025-12; **zero** requests across 8 month steps; scrollers drive and MOVE |
| **AC-7** | verified | all **15** canon extractions hash-equal; token block verbatim in all five; `--error` **measured**; zero `fmtR(` call sites; non-blocking fonts on all five; 44 px enumeration clean |
| **AC-9** | **verified, 9.5 included** | Forms app observably **identical** to the locked baseline on all 10 screen×width cells, no new console errors, no regressions. **9.5 is the strongest proof in the round:** the row this round wrote with `amount_cents: 12345` renders in the Forms app — which knows nothing about `amount_cents` and divides the raw column by 100 — as **R123.45**, with its own Inflow total agreeing. Not R1,234,500, not R1.23 |
| **AC-10** | verified except 10.4/10.7 | pyflakes clean; `node --check` clean and **proven live**; guard exit 0 before the first commit and after; ledger written as part of each promote |
| **AC-11** | **verified** | 1,357 ledger entries across 1,301 distinct ids, written **as the writes happened**; reconciled field-by-field; structural tables moved by **zero**; `anvil.yaml` diff is exactly the one column |
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

## Written-rows ledger (AC-11)

**1,357 entries across 1,301 distinct `transaction_id`s**, written to
`scratch/s03/ledger/written_rows.jsonl` **as each write happened**, never reconstructed. The
evidence file stays on disk — the repo carries code only.

| operation | entries | what |
|---|---|---|
| `restore` | **1,301** | the remediation: 1,300 rows Anvil's migration had wrongly set to `False`, plus the single diagnostic probe that confirmed the mechanism |
| `categorise` | 52 | AC-2.1's single row + a 25-row batch, **each reverted to its original category** (26 forward, 26 back) |
| `create` | 1 | the AC-2.3/2.5 probe row |
| `update` | 1 | AC-2.4's date/amount/account change, to force a hash recomputation |
| `archive` | 2 | AC-2.6/2.7 archive→restore, and one further archive during the cycle |

**AC-11.2 — the ledger reconciles against the data.** A post-remediation
`?include=transactions` compared field-by-field against the round-start snapshot yields **zero**
rows differing on any field except `active`, zero ids missing and zero ids new. Every categorise
was reverted and confirmed reverted by an independent fetch.

**AC-11.3 — the structural tables moved by exactly zero.** Round start (14:21:37Z) and now
(19:20Z), UTC-stamped:

| table | round start | now |
|---|---|---|
| `accounts` | 9 | **9** |
| `budgets` | 58 | **58** |
| `categories` | 14 | **14** |
| `sub_categories` | 57 | **57** |
| `settings` | 1 | **1** |
| `users` | 3 | **3** |
| `files` / `test_csv` | 8 / 5 | **8 / 5** |
| `transactions` | 1300 | **1301** (+1, the deliberate probe) |

Every pre-existing `accounts` row is unchanged on every field the payload exposes. The two `ZZ`
accounts pre-dated the round (Addendum 1), so the round's own structural delta is **zero** — not
the +2 §3.8.4 anticipated.

**AC-11.4 — nothing was hard-deleted.** `transactions` ended **≥** its start count (1300 → 1301),
and every round-start `transaction_id` is present in a round-end fetch. `ServerTxn.py` contains
**zero** `.delete(` calls, proven by AST walk.

**Live rows left behind, declared:**

- `74f7a3a5-c7f9-4671-98c7-bf6781453b03` — description **"ZZ S03 cents probe"**, `amount_cents`
  **12345**, dated 2026-08-20, account `619b96af-2` (Discovery), currently **active**. It is
  AC-2.5's and AC-9.5's evidence and is deliberately left in place for the reviewers to reproduce.
  It is visible in the Forms app's Transactions list as `R123.45`. **There is no hard-delete path
  by design**; Bruce can archive it from the new Transactions screen whenever he likes.
- The two `ZZ` accounts, `ZZ-TEST-ACTIVE` and `ZZ-TEST-ARCHIVED`, which pre-dated the round.

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
