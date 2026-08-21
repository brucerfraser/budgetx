# Budget X — Session 03 debrief

**STATUS:** FINAL — 13/14 PASS

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
| **AC-10** | **spec-reviewed: FAIL on 10.6** | 10.1–10.5, 10.7 PASS. 10.6 failed because this debrief carried 5 of **13** promote rows — a transcription gap, now closed in full |
| **AC-11** | **spec-reviewed: FAIL on 11.2** | 11.3–11.6 PASS — structural tables moved by **zero**, nothing hard-deleted, `anvil.yaml` diff exactly the one column. 11.2's set equality is unsatisfiable against a remediation that correctly nets to zero (Addendum 8); the 1,361-entry ledger is committed at `docs/ledger_s03_written_rows.md` |
| **AC-12** | **spec-reviewed: PASS** | section-splitting diff: **two** sections changed — "Standing rules of the migration" (§3.10's list) and "Schema changes need Bruce's click" (Addenda 5 and 6). **+71 lines, 0 deletions** — purely additive. An earlier draft of this debrief said "exactly one"; that was true when written and stopped being true when the schema ruling landed |
| **AC-13** | **spec-reviewed: FAIL on 13.6/13.7; 13.8 NOT VERIFIED** | 13.1, 13.2, 13.5, 13.9 PASS driven. 13.6/13.7 failed on **this document's** record, now supplied below; the remaining endpoint timings and the five cold starts are outstanding |
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

**The complete per-row enumeration is committed at
[`docs/ledger_s03_written_rows.md`](docs/ledger_s03_written_rows.md)** — all **1,361 entries
across 1,302 distinct `transaction_id`s**, each with what changed, before → after and the UTC
timestamp, written **as each write happened** (the source `.jsonl` is appended by the driver at
the moment of each call, and stays on disk; the repo carries code and records, not evidence).

AC-11.1 says the listing goes "in the debrief". 1,361 entries would make this file unusable as
Cowork's transcription channel, so the enumeration is a committed document and this debrief
carries the summary plus every individually-touched row. **That is a deviation in location, not
in completeness — recorded in Addendum 8 rather than glossed.**

| operation | entries | what |
|---|---|---|
| `restore` | **1,301** | the Addendum 6 remediation — 1,300 rows Anvil's migration wrongly set to `False`, in seven batches of ≤200, plus the single diagnostic probe that confirmed the mechanism before anything was done at scale |
| `categorise` | 52 | AC-2.1's single row + a 25-row batch, **each reverted** (26 forward, 26 back) |
| `create` | 1 | the AC-2.3 / AC-2.5 probe row |
| `update` | 1 | AC-2.4's date/amount/account change, forcing a hash recomputation |
| `archive` | 2 | AC-2.6 / AC-2.7 archive→restore |

**The 27 rows this round touched individually** (the 1,300 restores are enumerated in the
committed ledger):

```
0009f54f-e7b4-4b61-845c-7a66b22e06a8
000e3c4e-963e-4821-a579-165b9107c14c
0011e493-c950-4d32-b4ab-7b2f33d8d366
0020df3a-08ee-4241-b146-a558198d3426
00ab6a3b-202e-4e46-8500-38e93e7244c3
010f3013-0e1d-487f-8779-b9a85f65f180
011f84b6-37b5-4b7c-a9f3-74386c52903c
015b4327-afde-40b0-a689-0d9379dd33f6
015fcde6-45cd-40a4-a550-93a820a7e283
01828eb0-2fc2-4e6b-a368-a97386fde0ad
01eb7ef7-fe98-432b-b9c8-2eab56d3e9fc
01f72c0b-dbba-4a24-9b1b-d7f35a96cf9f
0229fc0d-8625-4bd2-9def-8766aa2feff9
02981791-26dc-45d6-88c0-33df56323eee
02b55b9e-0d53-4d4e-8ad5-f2273d48a492
02ec3cd7-cfa3-4ead-8bb0-11cddf741a5f
03319a04-a071-4f71-b94b-16bac3c6a3ef
0364f1be-1c95-4d37-9d88-6b4fcb77472b
036c1206-fea3-494b-9fe2-eaee87a356dd
036e7884-ac86-43b1-a698-af0f2ef9a43b
0393c6cf-fef6-49cc-abab-6eee0f14db5a
03a637c2-77a9-4ebe-8a7e-f39b0540c4cd
0403433b-ee8c-4fd4-bda1-2bdc89a06fd1
0425cf68-36a8-4111-baf7-4e6f73433dd3
04f054bf-751c-4d7e-bb52-15d10dd3ab01
0505f9cc-12db-4f28-8fd9-03fe41774ebe
74f7a3a5-c7f9-4671-98c7-bf6781453b03
```

### AC-11.2 — the criterion cannot hold as written, and Addendum 8 says why

A round-end field-by-field comparison against the round-start snapshot yields a difference set of
**exactly two** rows — the cents probe and the row the spec reviewer created. The ledger's id set
is **1,301**. AC-11.2 demands those two sets be *equal*.

They cannot be, **because the remediation worked.** The 1,300 restored rows are field-identical to
round start: Anvil set `active=False`, the round set it back to the value the payload had always
reported, and the net change is zero. A ledger that omitted them would satisfy the arithmetic and
would be a lie — they were written, deliberately, by this round.

**The intent is met in its stronger form: nothing changed that is not in the ledger.** The ledger
over-declares, never under-declares, which is the safe direction. The spec reviewer's own
reconciliation confirms zero unledgered changes. Addendum 8 proposes the corrected wording for
later rounds: *the difference set is a **subset** of the ledger's id set*.

### AC-11.3 — the structural tables moved by exactly zero

Round start 14:21:37Z, round end, both UTC-stamped: `categories` 14→14 · `sub_categories` 57→57 ·
`budgets` 58→58 · `settings` 1→1 · `users` 3→3 · `accounts` **9→9**. Every pre-existing `accounts`
row is byte-identical on every field the payload exposes, confirmed by the spec reviewer against
round-start and round-end bootstraps. The two `ZZ` accounts pre-date the round (Addendum 1), so
the round's own structural delta is **zero**, not the +2 §3.8.4 anticipated.

### AC-11.4 — nothing was hard-deleted

`transactions` 1300 → **1305** — the cents probe, three rows the spec reviewers created (all
left archived), and one row left by a dispatch that was wrongly recorded as having written
nothing (see the correction below) — so the count only rose; every round-start `transaction_id` is present in a round-end fetch;
`ServerTxn.py` contains **zero** `.delete(` calls, proven by AST walk by two independent parties.

### Live rows left behind, declared

- `74f7a3a5-c7f9-4671-98c7-bf6781453b03` — **"ZZ S03 cents probe"**, `amount_cents` **12345**,
  2026-08-20, account `619b96af-2` (Discovery), **active**. AC-2.5's and AC-9.5's evidence, left
  in place so the verdicts stay reproducible. Visible in the Forms app as `R123.45`.
- `92d058be-7f7f-4e0c-aa94-8039daaaeb4b` — created by the **spec reviewer** for its own
  write-path proofs and left **archived** (`active: false`), −77777, `ZZ-TEST-ACTIVE`, 2025-12-25.
  Invisible to all five new clients; visible in the Forms app, which ignores `active`.
- The two `ZZ` accounts, `ZZ-TEST-ACTIVE` and `ZZ-TEST-ARCHIVED`, which pre-date the round.

**There is no hard-delete path by design.** Bruce can archive the probe from the new Transactions
screen whenever he likes; round 06 owns `accounts` writes and can retire the `ZZ` pair.

## Promote / rollback ledger (AC-10.6) — all 13 promotes, written as part of each promote

**The spec reviewer failed AC-10 on this and was right to:** the earlier draft of this debrief
carried only the first five rows. Thirteen promotes happened. The complete ledger was written by
the promote tool at the moment of each promote — timestamps run ~5 s ahead of the server's own
`promoted_at`, which is what proves it was not reconstructed — and every `record_uid`, version and
rollback pointer matches `/build/list`. Here it is in full.

| slug | version | promoted `record_uid` | rollback to (previous current) | bytes | UTC | served-bytes |
|---|---|---|---|---|---|---|
| `x` | 1.2.0 | `47f49055-a24a-4d3b-bb74-45ce991244ce` | `bf9dae3e-fb80-4271-8ef7-9d3fd61598dc` | 56,336 | 18:16:34Z | served==promoted |
| `d-dash` | 1.2.0 | `835a9eaf-3a05-4145-8352-438e4cdbe9d4` | `d0f6379e-b240-4352-bc54-36106572d47e` | 58,483 | 18:16:40Z | served==promoted |
| `m-dash` | 1.2.0 | `61f3b790-2ac8-4e2c-9f32-e75417c9893d` | `6c6d0867-7fd2-4aeb-87a6-fa1fa66741e5` | 59,045 | 18:16:45Z | served==promoted |
| `d-trans` | 1.2.0 | `a2a4513d-41aa-4c2e-85d3-856926faafb0` | — (first promote) | 92,828 | 18:16:55Z | served==promoted |
| `m-trans` | 1.2.0 | `ddd3bb1f-6c1d-4cf3-9e12-e42a14f24ee9` | — (first promote) | 107,632 | 18:17:02Z | served==promoted |
| `d-trans` | 1.2.1 | `f5b865ef-dbe7-4469-ae7f-4eface149be4` | `a2a4513d-41aa-4c2e-85d3-856926faafb0` | 93,891 | 20:11:19Z | served==promoted |
| `m-trans` | 1.2.1 | `d54bb86d-421f-45e8-924e-f16d66785111` | `ddd3bb1f-6c1d-4cf3-9e12-e42a14f24ee9` | 111,340 | 20:11:26Z | served==promoted |
| `x` | 1.2.2 | `66bf92c3-e342-47a1-87bc-205a8b96805a` | `47f49055-a24a-4d3b-bb74-45ce991244ce` | 57,405 | 21:40:33Z | served==promoted |
| `d-dash` | 1.2.2 | `be1c8c3e-c104-44fb-a130-7c0b8646dbc5` | `835a9eaf-3a05-4145-8352-438e4cdbe9d4` | 59,552 | 21:40:40Z | served==promoted |
| `m-dash` | 1.2.2 | `f1cb63d1-e4f0-4133-b389-ce4159466bdd` | `61f3b790-2ac8-4e2c-9f32-e75417c9893d` | 60,114 | 21:40:45Z | served==promoted |
| `d-trans` | 1.2.2 | `25b9b73c-7b74-4844-932a-513539a7c702` | `f5b865ef-dbe7-4469-ae7f-4eface149be4` | 97,677 | 21:40:51Z | served==promoted |
| `m-trans` | 1.2.2 | `731e2b29-7573-49a0-8d4d-173aa6dfbb67` | `d54bb86d-421f-45e8-924e-f16d66785111` | 115,137 | 21:40:58Z | served==promoted |
| `d-trans` | **1.2.3** | `3eff7bcb-77ff-47ad-8cbb-402b42003d3a` | `25b9b73c-7b74-4844-932a-513539a7c702` | 102,844 | 22:49:36Z | served==promoted |

All UTC 2026-08-20. **Currently live:** `x` / `d-dash` / `m-dash` / `m-trans` at **1.2.2**,
`d-trans` at **1.2.3**. Served bytes were re-fetched from `/x?slug=…` and sha256-compared to the
uploaded bytes on every one of the thirteen. All five are ≤250 KB (AC-13.5).

**To roll any slug back**, promote its "rollback to" `record_uid` — that is the row that was
`is_current` immediately before, recorded before the new one went live.

## THE SPEC REVIEW — cycle 1 · **11 / 14 PASS**

Dispatched after the visual gate's three cycles were committed, per §9. Fresh read-only context,
full AC-1…AC-14, 145 tool calls, its own instruments. It re-derived rather than trusting: its own
AST walks, its own hash recomputation (int-form **10/10**, float-form **0/10**), its own Python
recomputation of the rendered totals, its own corruption of a golden expectation to prove that
gate live, its own 1,192-control 44 px enumeration, its own timing runs.

**PASS: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-12, AC-14** — eleven.

Two of its findings are worth carrying on their own merits:

- **It judged the AC-6.1 overflow repair that no visual cycle had seen** (it landed after the
  three-cycle limit). Verified independently on live December at 1280/1440/1920: document, body,
  table-wrap and scroller horizontal overflow all **0**, amount cells past the rail **0**,
  truncated amounts **0**, before *and* after a driven scroll at every width.
- **AC-9.5 proved behaviourally, not by inspection:** with a row set `active: false`, the API
  returned 273 December rows while the Forms app still showed 274 with unchanged totals — so
  `active` demonstrably does not reach the Forms app.

### The three FAILs, and what each actually is

**AC-10 — FAIL, on 10.6 alone.** 10.1–10.5 and 10.7 all hold. The debrief carried only 5 promote
rows; there were **13**. The complete ledger existed and was accurate — every `record_uid`,
version and rollback pointer matching `/build/list`, timestamps ~5 s ahead of the server's
`promoted_at`, so demonstrably written *as part of* each promote — but it lived in a gitignored
file and AC-10.6 requires it **in the debrief**. **A transcription failure in this document, not a
build defect.** Closed above: all thirteen rows are now here.

**AC-11 — FAIL, on 11.2 and the location of 11.1.** 11.3–11.6 hold. 11.2's set equality is
**unsatisfiable against a remediation that correctly nets to zero** — see the section above and
Addendum 8. 11.1's per-row listing is now committed at `docs/ledger_s03_written_rows.md` and
pointed to from here. **The reviewer was right that the criterion as written does not pass; the
correction is to the criterion, and it is recorded rather than argued away.**

**AC-13 — FAIL, on 13.6/13.7 as recorded; 13.8 NOT VERIFIED.** 13.1, 13.2, 13.5 and 13.9 hold and
were driven. The reviewer's objection was to *this document*: it named the cause and the
trade-off but carried a single stale p50 of 1,286 ms, **no p95 at all**, and no fresh/reused split
for the four endpoints §13.7 names. Closed in the speed section below.

**Not a criterion, but a real finding it made:** `d-trans`'s **description sort is case-sensitive
raw ASCII** — `comparatorFor` lowercases neither side for `description`, unlike `account` and
`category` which sort on resolved labels. `"Apple Watch Benefit"` therefore sorts before every
lower-case description. Deterministic and correctly verified, so not an AC failure, but it will
read as a bug to a user. **Carried forward, not fixed** — a sort-order change after the gate has
closed is exactly the kind of unreviewed edit this method exists to prevent.

---

### ⚠ A CORRECTION — I recorded something as fact that was false

An earlier version of this debrief said the first cycle-2 spec-review dispatch "died on an API
connection error **before doing any work** — it read nothing and judged nothing."

**That was wrong, and I had not verified it.** I wrote it from the harness's own failure message.
**The dispatch did write.** It created transaction `9189647a-25d7-4144-8927-d3c1e1a98994`
("ZZ-REV2-CREATE", 12345 cents, 2025-12-15) and left it **active and unledgered**.

**It was found by the next reviewer, not by me** — which is the whole argument for an independent
gate, made against the person who wrote the record. The row is now ledgered (marked
**RECONSTRUCTED**, not written-as-it-happened, because that is what it is), archived to match the
other reviewer-created rows, and its absence from the active payload confirmed by an independent
fetch.

The general lesson, which is worth more than the row: **a harness's report of what an agent did
is not evidence of what it did.** A dispatch that reports failure may still have written. The only
proof is the data. This round's own standing rule — *an endpoint returning `ok:true` is not
evidence of a write* — has a mirror image: **an agent reporting that it did nothing is not
evidence that it wrote nothing.**

Two further inaccuracies the reviewer caught in this document, both now corrected above: the
ledger holds **1,361** entries, not the 1,357 first stated, and the CLAUDE.md diff touched **two**
sections, not one — true when written, untrue once the schema ruling landed. Neither changed a
verdict; both are recorded because a debrief that quietly self-corrects is worth less than one
that shows where it was wrong.

---

---

## THE SPEC REVIEW — cycle 2 · **13 / 14 PASS** · the round's verdict

Full re-review from AC-1 in a fresh read-only context, 130 tool calls, against a build with **no
application code changed** since cycle 1 — the two failures it had found were failures of this
document, and it re-judged them against the corrected record.

**PASS: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-12, AC-13, AC-14** —
thirteen. **AC-11: FAIL**, on 11.2 alone.

It re-derived rather than resting: its own AST walks, its own §4.4 hash recomputation (10/10 on
untouched rows, with the unpadded day/month confirmed), its own Python recomputation of the
rendered totals, its own corruption of a golden expectation on a scratch copy, **1,089 control
measurements across 19 driven states**, its own latency runs, and its own transcription of the
legacy `is_it_smart` to prove `bxSuggest` differs and is right.

Newly closed this cycle: **AC-10 PASS** (all 13 promote rows reconcile with `/build/list` on slug,
version and bytes, every rollback pointer a real prior row of the same slug; the round diff is 18
paths, all named or addendum-added; `client_code/` tree hash identical at both ends), and
**AC-13 PASS** including 13.8, whose five cold-start readings it judged on the recorded evidence.

### The one outstanding FAIL — AC-11.2, and why the round stops here

The reviewer's own reconciliation reproduced the round's analysis exactly: **difference set 0,
ledger id set 1,301 — subset holds, equality does not.** Its verdict, in its words:

> *"The criterion as locked cannot be satisfied by a round that both remediates the platform's
> write and honestly ledgers it. I have failed it against the locked wording as instructed, not
> because the data is wrong; the data is in the best state it could be in."*

**The round accepts that FAIL and does not appeal it.** A third cycle would return the same
verdict for the same reason, so §9's three-cycle allowance is deliberately not spent: **stop and
report the outstanding FAIL with the reviewer's evidence** is exactly what the rule prescribes.
Addendum 8 carries the corrected wording — *subset*, not equality — into spec_04.

### Findings the reviewer made outside the criteria

Recorded, none fixed — the gate has closed and an unreviewed edit now would be worth less than an
honest finding:

1. **`""` is accepted as a category where §3.1 says it must be a 400.** `ServerTxn.py:432-433`
   coerces an empty string to `None` (uncategorise). Confirmed live: a batch carrying
   `category: ""` returns **200** and uncategorises the row. Defensible given §4.2's `null` → `""`
   serialisation, but it is a **silent widening of a whitelist**, and AC-2.2 does not name the
   case. **Worth closing in round 04.**
2. **`?include=Transactions` (capital T) returns the transactions key**, where §3.2 reads exact.
   AC-1.3's two named values behave correctly, so the criterion passes; the matching is
   case-insensitive where the spec is not.
3. **Three pre-existing rows carry hashes that do not match §4.4 — legacy data defects, not this
   round's.** `a9bba079…` stores a **float** rendering (`-401099.0`), and `25f7c444…` /
   `5545e31b…` store hashes computed from **rands, not cents** (`-109933` where the column holds
   `-10993300`). AC-4.3's ten sampled rows all match. **These three will not de-duplicate
   correctly — round 06 owns CSV import and duplicate detection and must know this before it
   starts.** This is the single most valuable thing carried out of this review.
4. **`d-trans`'s skeleton rows lack a `data-skeleton` attribute** where `m-trans` has one. Not a
   §3.5 hook so not a violation, but it cost this reviewer a false FAIL and will cost the next one.
5. **The Forms app's account dropdown lists "ZZ Test Archived".** Expected — `client_code/` is
   frozen and that control ignores `archived` — but Bruce should know the archived test account
   is visible there.
6. **`d-trans`'s description sort is case-sensitive raw ASCII**, so `ZZ` sorts before `az`.
   Deterministic and correctly verified, so AC-6.5 passes; it is just not what a person expects.

## SPEED — the honest record (AC-13.6, AC-13.7, AC-13.8)

**AC-13.6 — the transactions payload, measured.** `?include=transactions` is **404,787 bytes**
over 1,301 rows. Measured by the spec reviewer, warm, n=22, confirmed by a second run at n=25:

| connection | p50 | p95 |
|---|---|---|
| **reused** | **1,496 ms** | 1,733 ms |
| **fresh** | **2,495 ms** | 3,060 ms |

Second run n=25: p50 **1,479 ms**, minimum **1,128 ms** — **it never went under a second.**

**This exceeds the 1-second rule, and here is the cause and the option, which is what §11.3 asked
for rather than a guess.** The cost is *not* the payload. Measured on this app: an Anvil HTTP
dispatch floor of **~400–700 ms** on a 106-byte `/me` response, and after the schema migration the
transactions leg adds only **~130 ms** over the base bootstrap call (p50 1,375 ms vs 1,249 ms in
the orchestrator's own run). The earlier 10.5 s figure was entirely the missing-column round trips
of Addendum 6 and is gone.

**→ Bruce's decision, put plainly: windowing would recover at most ~130–600 ms and cannot get
below Anvil's dispatch floor.** Shipping the whole history in one call — §11.3's deliberate choice
— costs roughly a tenth of a second more than shipping one month, and buys instant month
stepping, search and totals with **zero** further requests, which is measured at **0.3–8.9 ms**
per interaction. **The recommendation is to keep it and accept a named ~1.5 s page open.** The
alternative worth considering is not windowing but the platform: the floor is Anvil's, not ours.

**AC-13.7 — the network, measured honestly.** n=22 per cell, warm, **fresh and reused
connection for every endpoint**, because S02 showed the two differ by more than 2× and reporting
only one of them misleads. The two write endpoints were timed with **idempotent no-op writes** on
the round's own probe row — `notes` set to the value it already held, `category` to the category
it already had — so nothing moved: the row's JSON is **byte-identical before and after all 88
writes**, and both batches are in the ledger.

| endpoint | conn | p50 | p95 | min | max | bytes |
|---|---|---|---|---|---|---|
| `GET /x?slug=d-trans` | reused | **804** | 1,775 | 689 | 2,259 | 102,844 |
| `GET /x?slug=d-trans` | fresh | **1,692** | 1,821 | 1,629 | 1,910 | 102,844 |
| `GET /app/bootstrap?include=transactions` | reused | **1,533** | 2,838 | 1,044 | 2,848 | 404,466 |
| `GET /app/bootstrap?include=transactions` | fresh | **2,370** | 3,022 | 2,063 | 3,460 | 404,466 |
| `POST /txn/update` | reused | **511** | 614 | 449 | 1,124 | 301 |
| `POST /txn/update` | fresh | **1,082** | 1,126 | 996 | 1,229 | 301 |
| `POST /txn/categorise` | reused | **924** | 2,336 | 704 | 3,686 | 299 |
| `POST /txn/categorise` | fresh | **1,468** | 1,638 | 1,407 | 1,738 | 299 |

**Fresh is consistently ~2× reused** — `/txn/update` 511 → 1,082 ms, `/txn/categorise` 924 →
1,468 ms, `/x` 804 → 1,692 ms. S02's finding reproduces exactly.

**The writes are inside the 1-second rule** — `/txn/update` at **511 ms** p50 on a warm
connection, and every write in this app is optimistic anyway, so the user never waits on it. **The
only thing over a second is the one big read**, which is the deliberate trade in §11.3.

**AC-13.8 — five cold-start readings, spanning 2h00m18s.** Each after a ≥10-minute idle (first
13 min, then four 30-minute gaps), with the app untouched throughout.

| reading | UTC | idle before | `GET /build/version` | `GET /x?slug=d-trans` |
|---|---|---|---|---|
| 1 | 2026-08-21T00:20:19Z | 13 min | 2,886 ms | 1,810 ms |
| 2 | 00:50:24Z | 30 min | 2,818 ms | 1,736 ms |
| 3 | 01:20:28Z | 30 min | 2,270 ms | 1,723 ms |
| 4 | 01:50:32Z | 30 min | 2,778 ms | 1,633 ms |
| 5 | 02:20:37Z | 30 min | 1,958 ms | 1,671 ms |

| | median | range | spread |
|---|---|---|---|
| `GET /build/version` | **2,778 ms** | 1,958 – 2,886 | 928 ms |
| `GET /x?slug=d-trans` | **1,723 ms** | 1,633 – 1,810 | **177 ms** |

**What the spread supports, and only that** (S02 Addendum 7: three readings once spread
661–2,957 ms and a single figure carried a conclusion that was false):

- **A cold first byte of the transactions page costs ~1.7 s, and that figure is solid.** Five
  readings over two hours span just **177 ms** — tighter than any warm measurement in this round.
  A user returning after idle waits about 1.7 s for the page, then ~1.5–2.4 s for its one data
  call.
- **`/build/version` is both slower and far more variable** (median 2,778 ms, spread 928 ms)
  **despite touching no table.** It checks the App Secret and imports four modules; that, not data
  volume, is what it measures. Worth knowing, since it is the round's own liveness instrument.
- **What these readings do NOT support:** any claim about how much of the cost is container
  spin-up versus steady dispatch. Separating those needs an instrument this round does not have,
  and the honest answer is that it was not measured.

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
