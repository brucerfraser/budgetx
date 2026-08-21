# Budget X — Spec 04: Budget — the money engine, the structural write path, and two screens that have to be right

**Status:** **APPROVED AND LOCKED — Bruce, 2026-08-21.** Build against this text as written.
**Do not edit the approved text in place**; corrections go in §12 as dated addenda.
Trigger: `Read Claude.md, Trigger 04`.

**Round:** 04 · **Written:** 2026-08-21 (rulings 5 and 6 taken the same day, before locking) · **Source:** Migration Blueprint Part 3 ·
`DEBRIEF_S03.md` (FINAL 13/14) and its eight addenda · `CLAUDE.md` at `HEAD` ·
Bruce's rulings of 2026-08-21 (§0) · the legacy budget code, read for this spec and cited
inline by `file:line` throughout (§0.5)

**Build models:** Opus orchestrator. **Builder S (server)** on **Opus** — it opens the write path
to the app's *structural* tables and owns a schema migration. **Builder C (calc)** on **Opus** —
rollover, variance and the progress meter are the arithmetic the whole app is judged on.
**Builders D and M (HTML clients)** on **Sonnet** — localised client work. Record who actually
ran each role in the debrief.

---

## 0. BRUCE'S RULINGS FOR THIS ROUND — 2026-08-21

Recorded first because twelve sections below depend on them. **They are cited elsewhere as
"§0 ruling 1" … "§0 ruling 7".**

**Ruling 1 — every month-selector screen opens on the most recent month that holds data**, not
the server's current month. "This month" still returns to the server's current month exactly as
spec_03 AC-6.2 says. Round 03 shipped an app that opened on 2026-08 — a month holding **zero**
rows — with 1,300 transactions sitting six months behind it. One definition, in the canon, used by
every screen (§3.3, AC-6.1).

**Ruling 2 — the one-call bootstrap payload stays, and its page-open cost is a named exception to
the 1-second rule.** Round 03 measured it: 404 KB, p50 ~1.5 s reused / ~2.5 s fresh, of which the
transactions leg is only ~130 ms and the rest is Anvil's ~400–700 ms dispatch floor. Windowing
cannot get below the platform. **This round adds `budgets` to the same call** and measures what
that costs (AC-13.6). No windowing.

**Ruling 3 — best practice beats legacy compatibility on archival.** Bruce, asked whether to keep
the legacy `order = −1` archive sentinel: *"what is best practise for future? We must focus on
this, even if it means app doesn't work in some areas."*
**So: `categories` and `sub_categories` get real `active` bool columns** and `active` becomes the
authority. The legacy `order = −1` is **mirrored** on every archive and restore for as long as the
Forms app is still serving the root, so nothing silently breaks before round 08 retires it — that
mirror is a declared, temporary compatibility shim (§3.8), not a design. **This is a schema
change, so this round parks once for Bruce's approve-click and does NOT close unattended.**

**Ruling 4 — round 04 carries the full blueprint scope** — the money engine, the budget write path
and category/sub-category CRUD in one round, with both clients. **Re-affirmed 2026-08-21 after the
scope was put back to Bruce: run it whole.** §9 still carries a pre-declared `04a`/`04b` seam so
that if the gate forces a split at cycle 2 it costs one decision rather than a re-plan.

**Ruling 5 — the overspend model: the app always looks forwards.** Bruce, 2026-08-21, asked
whether an overspend should carry forward as a debt:

> *"Track budget cats/sub-cats as an accountant, corporate governance financial management: yes,
> carry debt across months/periods to track a YTD variance. BUT! We are aiming at individuals
> here. So the default setting is: we always look forwards. Overspending on one month MUST be
> accounted for of course — but it gets taken off next month's available to budget starting
> amount, and each budget cat is built from zero again. There may be more ways to show/do this in
> a way that helps users understand their overspend while not feeling bogged down by it in the
> next period. Suggestions welcome."*

Three consequences, and they change §4.5, §4.6's context, both screens and `/budget/summary`:

1. **No category ever carries a debt.** A sub-category's rollover pot clamps at zero on overspend,
   exactly as the legacy did — but where the legacy then *discarded* the overspend and returned a
   figure that read "exactly on budget" (fact 12), this round **captures it**.
2. **The overspend is accounted for one level up.** It is deducted from the **next month's
   available-to-budget starting amount** — a month-level pool this app does not have today and
   which §4.5A defines. Every category still starts the new month from its own budget.
3. **The accountant's lens is not the default, and it is not lost.** Cumulative YTD variance is a
   *Reports* question, not a Budget-screen one; round 05 owns it as an opt-in view (§10).

**This is the round's largest design change since the spec was first drafted**, and §4.5A and
§11.3 are where it is pinned down.

**Ruling 6 — income that does not arrive is treated exactly like an overspend, one month later.**
Bruce, 2026-08-21, asked whether a shortfall against planned income should reduce the pool:

> *"No — budgeted income stays and pool stays — cash flow might be a bit late, or not arriving at
> all. If it does not arrive, shortfall highlighted against INCOME, and subtracted against next
> month's in the same way as an overspent cat."*

Three consequences, and the first is the one a builder is most likely to "improve" away:

1. **The current month's pool is built on PLANNED income, in full, whatever has actually
   arrived.** Money that is late is not money that is lost, and a plan that collapses the moment
   an invoice slips is not a plan. **Never build `income_planned` from actual receipts.**
2. **A shortfall is shown against INCOME, in the month it happened**, with the same visual weight
   as an overspent expense category — because it has the same consequence.
3. **One month later it is deducted from the pool, exactly as an overspend is** — same mechanism,
   same one-month look-back, same non-chaining, and named separately in the chip so the two causes
   are never confused. §4.5A carries `carried_overspend` and `carried_shortfall` as sibling
   fields for exactly that reason.

**Ruling 7 — "Cover it" is designed now and built in round 07.** The one-tap action that reduces
this month's budgets by the carried amount is **specified in §4.5A** so round 07 inherits the
design, and is **not built in this round**. Round 04 is already the largest of the migration, and
the chip is honest and useful without it.

### 0.1 What this spec inherits from S03 without re-deciding

- **Money is integer cents everywhere.** `budgets.budget_amount` already holds cents, by the same
  evidence that settled `transactions.amount` (spec_03 §0.1, and `Sub_category:96`
  `self.b = self.budget_edit.text * 100` on save, `/100` on every display site).
  **Never multiply by 100 at a boundary.** The wire conversion is `int(round(value))`.
- **The four write rules** (server owns identity and derived fields · whitelist inputs · every
  write returns an independent read-back · no hard deletes).
- **AC-11.2 is corrected to *subset*** (spec_03 Addendum 8) — see §8 AC-11.2.
- **The migration hazard** (spec_03 Addendum 6): a migrated bool column arrives **`False` on every
  existing row**, and the bad window opens at the schema **push**, before approval. §3.7 is
  written entirely around that fact.
- **A "diff touches only" list must name every artefact the round's own method obliges it to
  commit** (spec_03 Addendum 7's generalisation) — debrief, reviewer verdicts, ledger. AC-10.4 is
  written correctly the first time.
- **An agent reporting that it did nothing is not evidence that it wrote nothing.** Round 03 lost
  a live unledgered row (`9189647a…`) to a dispatch that reported an API failure and had in fact
  written. AC-11.8 exists because of it.
- **`q.fetch_only()` errors app-wide on this app** — Accelerated Tables is not enabled, so every
  `fetch_only` query returns `TableError` (`ServerAppData.py:84-88`). Builder S is writing a module
  full of queries; this saves the same dead end round 03 spent an hour in.

### 0.5 Legacy facts established while writing this spec — read from the code, not assumed

Every claim below is cited so a builder or a reviewer can re-derive it. **These are the reasons
several rules in §3 exist**, and they are referred to elsewhere as "fact *n*".

| # | Fact | Evidence |
|---|---|---|
| 1 | **A read writes the database.** `load_budget_data` copies **last month's budget rows into the current month** before it returns anything, keyed on `date.today()`, and the copy block runs **even when `only_t=True`**. It fires at client module import — opening the Forms app writes rows. | `budget_work.py:98-112`; called at `BUDGET.py:20` (module level) and `Global.py:33` |
| 2 | The copy takes `period`, `budget_amount`, `belongs_to` only. **`notes` are not copied**, and rows are copied for **archived** sub-categories too. | `budget_work.py:110-112` |
| 3 | The copy is not concurrency-safe, and **the legacy actively breeds duplicates**: `update_budget` catches the multi-row `get()` exception and calls `add_row`, so a duplicate `(belongs_to, period)` pair creates more duplicates on every later edit. | `budget_work.py:102`; `BUDGET.py:160-165` |
| 4 | **Archive = `order = −1`**, plus a compaction of every sibling above it. Nothing is deleted; budgets and transactions keep pointing at the archived id. | `budget_work.py:84-96` |
| 5 | **Archived sub-categories still count toward every total.** `update_numbers` selects by parent only, with no `order >= 0` filter, unlike every display list. | `Budget/__init__.py:251, 266` vs `Category_holder:30, 49, 66` |
| 6 | **Income is identified by the literal name string `"Income"`, case-sensitively**, in ~14 places, and `is_income` raises `IndexError` if no such category exists. | `BUDGET.py:35-37, 121`; `Budget/__init__.py:31, 38, 44, 85, 142, 206` |
| 7 | **`neg_pos` is the sign rule:** income budgets forced **positive**, everything else forced **negative**, falsy → `0`. | `BUDGET.py:119-128` |
| 8 | **The cache write uses the wrong key.** `update_budget('amount')` writes `['amount']` where the column is `budget_amount`, so the **second and later** edits of the same cell update the table and leave every rollup reading the old figure until reload. | `BUDGET.py:154` |
| 9 | **Notes are effectively write-only on desktop** — written against the sub-category id, read against the parent category id, so the read never matches. | write `Budget/__init__.py:111`; read `edit_budget:36-37` |
| 10 | **A note can never be cleared** — the write is skipped on empty string. | `Budget/__init__.py:109` |
| 11 | **Money is stored as unrounded float cents.** `self.b = self.budget_edit.text * 100`, no `round`, no `int` — `12.34 * 100` stores `1233.9999999999998`. | `Sub_category:96` |
| 12 | **Roll-over is broken in a specific, findable way.** The loop deducts the current month's actual and the return statement adds it straight back; when the current month tips the pot into overspend the loop first sets `b = 0`, so the returned "budget" **equals this month's actual** — variance 0, empty pill, "exactly on budget" at the precise moment the cumulative pot was blown. | `BUDGET.py:57-98`, esp. `:86-87` and `:92` |
| 13 | **Income roll-over is unimplemented** — the positive branch is `pass  # what do we actually do here???`, and the header total deliberately routes around it. | `BUDGET.py:88-89`; `Budget/__init__.py:254-255` |
| 14 | **`roll_over = True` with `roll_over_date = None` crashes** (`while cd <= ld` against `None`), and the toggle deliberately creates exactly that state. | `roll_date_list` `BUDGET.py:104`; toggle `Budget/__init__.py:229` |
| 15 | **Client-side reorder has three real defects** — a `NameError` on "first category, up", an undefined `cat_id` on "last category, down", and a non-deterministic swap in the middle case that reverts the item it just moved about half the time. A **correct** server-side implementation exists and is never called. | `Global.py:143, 148, 160-164`; unused `budget_work.py:11-72` |
| 16 | **The progress pill's zero point jumps 20% → 50% → 80%** across three branches, and **the number printed on the pill changes meaning** between them: remaining → overspend → total spend. The code comments state 25% and 75%; the real figures are 20% and 80%. Branch 3 is saturated — a 3× and a 30× overspend render identically. | `Budget/__init__.py:326-352`; renderer `ProgressBar:139-151` |
| 17 | Two money formats on one screen: header `R{:,.2f}` (grouped, no space), rows `R {:.2f}` (spaced, ungrouped); and the sub-category budget label carries **no `R` at all**, rendering a negative as `(123.45)`. | `Budget/__init__.py:298-305` vs `:318-319`; `Sub_category:43, 46` |
| 18 | On mobile, **the tap-to-edit budget path never persists anything** — no server call, no table write; the value survives until the row re-renders, and the only close is Enter, on a keyboard that may not have one. | `Sub_category_mobile:141-179`, esp. `:150` and `:175-179` |
| 19 | The mobile focus-mode sub-category list **shows archived rows and does not sort them**, unlike the normal expand path. | `budget_category:15, 20` |
| 20 | The notes/roll-over edit panel always operates on **today's** month, never the selected month. | `Category_holder:89-90`, `Sub_category:121-122` |
| 21 | `sub_categories.budget` is a `link_multiple` column that **no code reads**. | `anvil.yaml` `sub_categories` |
| 22 | **Nothing recomputes when a drill-down modal closes** — categorising inside the FIX-IT modal leaves the banner, every actual and every pill stale until something else forces a reload. | `Budget/__init__.py:381-384`; `Sub_category:147-150` |
| 23 | **The mobile header's collapsed state is not remembered.** `update_numbers` defaults to `expand=True`, so any other caller silently re-expands the grid to four rows while the CSS variable stays at the collapsed height, clipping the header. | `Budget_Mobile:384` vs `:539` |
| 24 | **Leaving mobile focus mode rebuilds the entire screen.** The only exit re-triggers the app's own nav handler, so scroll position, header state and every expansion are lost. | `Category_holder_mobile:160` → `budget_page_link_click()` |
| 25 | **A focused Income category is totalled by the expense code path**, which uses `roll_over_calc` where the unfocused path reads the raw budget — so the same category shows different numbers depending on how you are looking at it. | `Budget_Mobile:419-437` vs `:404-409` |

**Read fact 1 twice.** It means the round's own AC-9 drive of the Forms app can create budget
rows. §7 trap 12 and AC-9.7 are written to expect that and enumerate it rather than be surprised.

---

## 1. WHY

Round 03 gave the app a write path and a money core. This round is the one where the money core
does the thing the app exists for: **tell Bruce what he has left.**

Three thresholds cross here.

- **The first write to the app's *structure*.** Round 03 wrote `transactions` — a table that a CSV
  re-import regenerates. This round writes `categories` and `sub_categories`, which it does not.
  A destroyed transaction is re-importable; a destroyed category taxonomy is not. That is why
  every structural write in §3.2 is soft, reversible and proven by an independent read-back, why
  this round adds real `active` columns instead of inheriting a magic `order` value, and why every
  destructive proof in §8 runs on `ZZ` rows this round creates (§3.13).
- **Arithmetic that cannot be checked by looking at it.** A rollup is obvious when wrong. A
  **twelve-month rollover carry** is not — the legacy one has been quietly returning "exactly on
  budget" at the moment a pot is blown (fact 12) and nobody noticed, because the number looked
  plausible. So this round ships a **server-side recomputation instrument**,
  `GET /budget/summary`, whose only job is to disagree with the client when the client is wrong.
  Every money AC in §8 is a three-way agreement: client-rendered `data-cents` = `/budget/summary`
  = an independent recomputation in Python.
- **A read stops writing the database.** Fact 1 is the oldest defect in the app and the most
  surprising. `POST /budget/open-month` replaces it with an explicit, idempotent, ledgered call.

And it is the round where the beauty mandate has to carry real information. The legacy progress
pill (fact 16) is a three-state indicator wearing a gauge's clothes. Replacing it is not
decoration — it is the difference between a bar that tells Bruce how his month is going and one
that tells him three different things without saying which.

**This round is still invisible at the app root.** The Forms app keeps serving
`https://budget-x.anvil.app` untouched.

---

## 2. WHAT MUST NOT CHANGE

1. **The app root.** Keeps serving the Forms app. No endpoint at `/`, startup form stays `Frame`.
2. **`client_code/` — not one byte.** Both Forms UI trees stay untouched, and the tree hash is
   compared at both ends of the round (AC-10.4). This is load-bearing in a new way again: the
   Forms app reads `categories.order` and `sub_categories.order` as its archive signal and knows
   nothing about `active`, so §3.8's mirror is what keeps it coherent.
3. **The five original server modules** — `ServerModule1`, `account_work`, `budget_work`,
   `csv_handler`, `transaction_work`. **No edits.** In particular `budget_work.load_budget_data`
   keeps its month-copy behaviour (fact 1); this round replaces it *for the new clients* and
   retires it at round 08, it does not repair it in place. The S01 platform-authored exemption
   stands and `ls -l tools/githooks/` is re-checked immediately after any service change.
4. **`ServerApi.py` is frozen.** If a builder believes it needs changing, STOP and park.
5. **Table access settings.** `categories`, `sub_categories`, `budgets`, `settings` and
   `transactions` stay `client: full` / `server: full`. **They are flipped to `client: none` at
   round 08 and not before** — the Forms app writes them directly from the browser and would
   break the moment they flip.
6. **Schema — exactly TWO changes, both Code's edit and Bruce's approve-click** (§3.7):
   **`categories.active`, type `bool`** and **`sub_categories.active`, type `bool`**.
   Nothing else: no third column, no new table, no type change, no `client:`/`server:` change.
   **`budgets` gets no `active` column** — a budget row is created, amended and superseded, never
   archived, and CLAUDE.md forbids retrofitting standard columns speculatively.
7. **Business data.**
   - **`transactions`: writable, real rows included** — Bruce's round-03 ruling stands. This round
     barely needs it: only the `ZZ` rows of §3.13.
   - **`categories` and `sub_categories`: writable, but ONLY through this round's own endpoints,
     and every write is reversible and ledgered.** No existing row may be renamed, recoloured or
     re-parented. **Every archive, restore and CRUD proof runs on the `ZZ` rows of §3.13**, never
     on a real category.
     **The one exception is `order`**, which `/cat/reorder` and the archive compaction rewrite
     across the whole set by design (§3.2). §3.1 measurement 10 records the exact round-start
     sequences, every reorder is ledgered as one entry, and **the stored sequences are restored
     verbatim before the round closes** — AC-11.3 judges it that way.
   - **`budgets`: writable.** Amounts and notes may be set freely on **`ZZ` sub-categories**. On a
     **real** sub-category, nothing is written at all — the round has no need to, and Bruce's
     planning figures are not test data.
   - **`settings`, `accounts`, `users`: untouched.** No row created, edited or archived. The two
     `ZZ` accounts from round 03 stay as they are; round 06 owns `accounts`.
   - **Hard deletes are forbidden anywhere, on any table, including rows this round created** —
     proven by AST walk of every module the round touches. **No criterion in §8 may require a
     row to be removed**, and none does.
8. **`GET /app/bootstrap`'s existing response is frozen.** This round may only **ADD**: new
   `include` tokens, one new top-level key per recognised token, and new fields on existing
   objects. A call with **no query string** must still return a body whose key-set **exactly
   equals** spec_02 §4 (AC-1.1).
9. **The five round-03 slugs keep working.** `x`, `d-dash`, `m-dash`, `d-trans`, `m-trans` are
   all re-cut this round (the canon and `bx_calc.js` change underneath them) with **no behaviour
   change except the §3.11 carry-fixes and §0 ruling 1's default month**, and spec_03's AC-6,
   AC-8 and AC-14 are re-proven against the new builds (AC-10.7).
10. **The GitHub↔Anvil sync stays UNLINKED.** Deploy = `git push anvil master`, mirrored to
    `origin`. Never force-push. `git fetch anvil && git merge --ff-only anvil/master` first.

---

## 3. SCOPE

One new server module, two bumped, one touched for a single fix, one canon file at v2, two at v3,
two new HTML clients, five re-cut HTML clients, one schema change with an initialisation step, one
measurement pass. Nothing else.

### 3.0 Builder ownership — the parallel plan

| Builder | Model | Owns (nobody else may touch) |
|---|---|---|
| **S** — server | Opus | `server_code/ServerBudget.py` (new) · `server_code/ServerAppData.py` (v3) · `server_code/ServerBuildTools.py` (v4 — module registration **and** the two build-secret tools of §3.7 and §3.1) · `server_code/ServerTxn.py` (v2, §3.11 fix 1 only) · `tools/api.py` |
| **C** — calc | Opus | `client_src/bx_calc.js` (v2) · `tools/calc_golden.mjs` · `tools/calc_cases.json` |
| **D** — desktop | Sonnet | `client_src/bx_core.css` (v3) · `client_src/bx_core.js` (v3) — **the canon** · slug `d-budget` · re-cut of `x`, `d-dash`, `d-trans` |
| **M** — mobile | Sonnet | slug `m-budget` · re-cut of `m-dash`, `m-trans` |
| **Orchestrator** | Opus | `anvil.yaml` (the §3.7 schema edit, textual) · `CLAUDE.md` · `docs/specs/spec_04.md` addenda · the §3.1 measurements · the initialisation run and its reconciliation · integration, deploy, ledger, promotes, debrief |

**`server_code/ServerBuildTools.py` is named in Builder S's list deliberately, and it holds this
round's two migration tools deliberately.** `_module_versions()` enumerates modules explicitly, so
`ServerBudget` is invisible to `/build/version` until a branch is added for it (spec_03 Addendum 2
learned this the expensive way). And putting `POST /build/init-active` and
`GET /build/budget-audit` here rather than in `ServerBudget` is what makes §3.7 step 2's "commit 1
contains no code that reads the new columns" **true** rather than aspirational — shipping
`ServerBudget` early would ship `/cat/archive` and `/budget/summary` alongside it.

**Order of work.** All four builders start together.

- **C is on the critical path.** `bx_calc.js` v2 is a pure function library over the §4 shapes and
  depends on nothing else in the round; both client builders embed it and both compute every money
  figure from it. C must hand back a green golden run **before** D or M begin arithmetic-dependent
  work; until then D and M build layout, interaction and the §5 fixtures.
- **D authors the canon; M consumes it.** M builds against the §5 fixtures and the pinned token
  block until `bx_core.*` v3 exists, then embeds it verbatim and hash-checks.
- **S builds to the §4 contract**, which is fixed before anyone starts, and to the §3.7 sequence.

Upload/promote discipline during the build: builders may round-trip drafts on `zz-b04-d`,
`zz-b04-m` freely. **The seven real slugs are promoted by the orchestrator only**, each with its
ledger line written into the debrief **as part of the promote step** — never afterwards.

### 3.1 Round-start measurements — taken before anything is written (Orchestrator)

Ten facts this spec could not settle from code, each of which changes a decision. All are
UTC-stamped, written to `scratch/s04/measurements.json`, and reproduced in the debrief. **Any
surprise here is reported before the round proceeds, not absorbed.**

Measurements 5, 6, 7, 9 and 10 read the `budgets`, `categories` and `sub_categories` tables in
detail, which no live endpoint exposes. They are taken through
**`GET /build/budget-audit`** — build-secret-gated, strictly read-only, added to
`ServerBuildTools` in commit 1 and retired at round 08 with the rest of the migration scaffolding.

1. `GET /build/counts` for every table.
2. **Does a category named exactly `Income` exist?** Its `category_id`, and whether any other
   category's name differs from `Income` only by case or whitespace. (The legacy test is
   case-sensitive, fact 6; `bxIncomeCategoryId` is case-insensitive — this measurement is what
   proves the widening is safe.)
3. **Is the transfer sentinel `ec8e0085-8408-43a2-953f-ebba24549d96` a real row** in
   `sub_categories`, in `categories`, or neither? Every list and total in §3.9 excludes it; the
   reorder validation in §3.2 must know whether it is in the set.
4. **The id sets, per table, of `categories` and `sub_categories` rows carrying `order == -1`** —
   the sets the §3.7 initialisation must reproduce exactly as `active == False`. **Id sets, not
   counts** — AC-4.4 compares sets.
5. **Duplicate `(belongs_to, period)` pairs in `budgets`** (fact 3). Count and list them. **Do not
   repair them** — a data repair is Bruce's decision, and the round reports it under §10.
6. **Budget rows and transactions per month**, so the reviewers can be handed a month that is not
   vacuous (§7 trap 11, §9).
7. **Any `budgets.budget_amount` that is not an integer** (fact 11) — listed by
   `(belongs_to, period)` with its stored value, in full.
8. **Any `sub_categories` row with `roll_over == True` and `roll_over_date` null or absent**
   (fact 14) — the state the legacy toggle creates and the new code must define.
9. **Any `budgets` row whose `belongs_to` matches no `sub_categories` row**, and any
   `sub_categories` row whose `belongs_to` matches no `categories` row — orphans that would make
   a rollup silently drop money.
10. **The exact round-start order sequences, verbatim:** the ordered list of
    `(category_id, order)` and, per parent, of `(sub_category_id, order)`. **This is the artefact
    AC-11.3 restores against**, and without it the round cannot prove it put Bruce's ordering back.
11. **Any `budgets` row against an income sub-category whose `amount_cents` is negative**, and any
    against an expense sub-category whose `amount_cents` is positive — rows where the legacy
    `neg_pos` sign rule (fact 7) never ran, listed in full. §4.5A's `max(0, …)` on `income_planned`
    exists because one such row would silently make the whole pool wrong.
12. **Per month, the total `overspend` under §4.5A's definition**, so the dispatch can name a month
    that **does** carry an overspend into the next (AC-6.12) and one that **does not** (the
    absent-chip case), instead of hoping one exists.

### 3.2 `server_code/ServerBudget.py` — new module (Builder S)

Self-contained per the standing pattern: declares its own `ApiError` / `api_http` /
`require_auth` (copy the shapes from `ServerApi` and `ServerTxn`, do not import across modules),
`v1` header stamp + history line, all `app_tables` access inside function bodies, JSON explicit,
non-200s **returned** never raised, headers read **case-insensitively**, `Content-Type` set with
`headers.__setitem__`.

**Every method is `POST` except `GET /budget/summary`.** The app's existing endpoints are all
`GET` or `POST`; no `PUT` is introduced, so `tools/api.py` and Anvil's `http_endpoint` handling
need no change.

**Every row write uses `row.update(**fields)`. The module contains ZERO subscript assignments of
any kind** — that is what makes AC-3.10's AST walk decidable, since a walk cannot otherwise tell a
table-row subscript from a header subscript. It is the same discipline `ServerAppData` already
imposes on itself (`ServerAppData.py:20-28`).

**Do not reach for `q.fetch_only()`** — it returns `TableError` on this app (§0.1).

**The four write rules of spec_03 §3.1 bind every endpoint here**, and two more, because this
module writes the app's structure:

- **Order is written, never nudged.** No endpoint shifts a sibling's `order` by ±1. A reorder
  submits the **complete desired sequence** and the server rewrites the whole set. This deletes
  the entire class of defect in fact 15 rather than porting it.
- **Archive and restore are symmetric and both are proven.** Every archive endpoint has a restore
  endpoint, and no acceptance criterion may use an archive that cannot be undone.

**The income category is identified server-side by one function, `_income_category_id()`** — the
category whose trimmed name equals `Income` case-insensitively, else `None` — mirroring
`bxIncomeCategoryId` exactly. It is the only place the magic name appears server-side, and round
08 replaces its body with a flag lookup.

All endpoints are Bearer-gated through `require_auth()` and return the uniform
`401 {"ok": false, "error": "unauthorized"}` with **no data keys** on any auth failure.

#### Reads

**`GET /budget/summary?month=YYYY-MM`** — **the verification instrument, and nothing else.**
A server-side recomputation, in integer cents, of every figure the clients compute locally, from
raw rows. Response shape in §4.4.

- It is **not** on any interactive path. **No client may call it** — AC-13.1 asserts the budget
  screens make exactly one data request per page open and this is not it.
- It **must not** be implemented by porting `bx_calc.js` to Python. It is written independently,
  from the §4.5 and §4.6 definitions, precisely so that agreement between it and the client is
  evidence. A shared implementation would agree with itself while both were wrong.
- **Read-only, and provably so:** a **function-scoped** AST walk of `api_budget_summary` and every
  function it calls finds no `add_row`, `update` or `delete` call (AC-3.11). A module-wide walk
  would be meaningless here, because the module must write.
- Unknown or malformed `month` → `400`. A month with no data → `200` with zero-filled totals and
  empty arrays, never a 404 — **and `available` is still a full thirteen-field object**, with
  `prev_month_has_data` saying why its figures are zero.

#### Budget writes

**`POST /budget/amount`** — body `{"sub_category_id": "str", "month": "YYYY-MM", "amount_cents": int}`.
- `amount_cents` must be an **integer**; a float, string or null → `400`. (Fact 11 is how float
  cents got into the table; this is the tripwire.)
- **The server applies the sign rule**, it is not trusted from the client: if the sub-category
  belongs to the income category the stored value is `abs(amount_cents)`, otherwise
  `-abs(amount_cents)`; `0` is stored as `0`. This is `neg_pos` (fact 7) moved to where authority
  lives.
- Creates the `(belongs_to, period)` row if absent, updates it if present. If **more than one**
  row matches (fact 3), the endpoint writes **nothing** and returns
  `400 {"error": "bad_request", "detail": "duplicate budget rows for that sub-category and month"}`.
  It never picks one, and it never adds a third — which is exactly what the legacy does
  (`BUDGET.py:160-165`).
- Response: `{"ok": true, "budget": <§4.3 object>}`, **read back from the table**.

**`POST /budget/notes`** — body `{"sub_category_id": "str", "month": "YYYY-MM", "notes": "str"}`.
- **An empty string clears the note.** Fact 10 is a defect, not a convention.
- Creates the row with `budget_amount = 0` if absent — the legacy behaviour, retained
  deliberately so a note can exist before a budget does.
- Response: `{"ok": true, "budget": <§4.3 object>}`, read back.

**`POST /budget/open-month`** — the explicit replacement for fact 1.
- Body `{"month": "YYYY-MM", "copy_from": "YYYY-MM"}`. **Both are required and neither defaults**
  — a read never writes, and neither does an under-specified write.
- Creates a budget row in `month` for **every sub-category that has a row in `copy_from` and none
  in `month`**, copying `budget_amount` only. **`notes` are not copied** (fact 2, retained: a note
  is commentary about a month). **Rows are not created for archived sub-categories** (fact 2's
  other half, corrected).
- **Idempotent.** A second identical call creates nothing and returns `"created": []`.
- Response: `{"ok": true, "created": [<§4.3 object>, …], "skipped": <int>, "direction": "forward|backfill"}`
  — `created` read back from the table, `skipped` counting sub-categories that already had a row.
  `month <= copy_from` is permitted (back-filling a past month is legitimate) and is flagged
  `backfill` so the client can confirm before it happens.

#### Category and sub-category writes

**`POST /cat/create`** — body `{"name": "str", "colour_back": "str", "colour_text": "str"}`.
- `name`: **trimmed**, 3–40 characters after trimming, and **must not** case-insensitively equal
  an existing non-archived category's name, or `Income`.
- Colours: `#RRGGBB`, validated by pattern; anything else → 400.
- Server mints `category_id` (`uuid4`), sets `active = True`, sets `order` to
  `max(order among non-archived) + 1`. A caller-supplied `category_id` or `order` is **ignored**.
- Response `{"ok": true, "category": <§4.2 object>}`, read back.

**`POST /cat/update`** — body `{"category_id": "str", "fields": {…}}`, accepted fields
`name`, `colour_back`, `colour_text` and **nothing else**. Same validation as create. The income
category may be recoloured but **not renamed** (fact 6 makes its name load-bearing until round 08;
renaming it would detach every income rule in the Forms app). Read-back response.

**`POST /cat/reorder`** — body `{"order": ["category_id", …]}`.
- The submitted list must be **exactly the set of non-archived categories** — no additions, no
  omissions, no duplicates. Anything else → `400` and **nothing written**.
- **The income category is pinned to `order` 0** regardless of where it appears in the list, and
  the remainder are written `1 … n` in the order given. This preserves the invariant the Forms
  app's own reorder depends on (`Global.py:126-128`'s `count = -1` seed).
- **If there is no income category** (§3.1 measurement 2), the submitted sequence is written
  `0 … n−1` and the archive compaction below is identical.
- Response `{"ok": true, "categories": [<§4.2 object>, …]}` — the **whole** non-archived set,
  read back, in stored order.

**`POST /cat/archive`** / **`POST /cat/restore`** — body `{"category_id": "str"}`.
- Archive: sets `active = False` **and** mirrors `order = -1` (§3.8), then rewrites the remaining
  non-archived categories contiguous, income still at 0 (or from 0 if there is none). **It does
  not touch the category's sub-categories** — they remain `active` and simply become unreachable
  in the UI, which is reversible; cascading would not be.
- Restore: sets `active = True` and appends the category at
  `max(order among non-archived) + 1`. **The original position is not recovered** — the legacy
  archive destroyed it and this round does not invent one. Say so in the UI copy.
- The **income category cannot be archived** → `400`.
- Response `{"ok": true, "categories": [<§4.2 object>, …]}`, the whole non-archived set, read back.

**`POST /subcat/create`** — body
`{"name": "str", "belongs_to": "category_id", "icon": "str|null", "roll_over": bool, "roll_over_date": "YYYY-MM|null"}`.
- `name`: **the same rule as `/cat/create`** — trimmed, 3–40 characters, and not a
  case-insensitive duplicate of a non-archived **sibling**'s name.
- `belongs_to` must be an existing **non-archived** category.
- **`roll_over: true` with a null `roll_over_date` is rejected `400`.** Fact 14 is a crash the
  legacy toggle creates deliberately; this endpoint makes the state unrepresentable.
- Server mints `sub_category_id` (`uuid4`), sets `active = True`, `order` to
  `max(order among non-archived siblings) + 1`, or `0` if none.
- Read-back response.

**`POST /subcat/update`** — body `{"sub_category_id": "str", "fields": {…}}`, accepted fields
`name`, `icon`, `roll_over`, `roll_over_date`, `belongs_to` and nothing else. The
roll_over/roll_over_date pair is validated **as a pair, after the merge**: the resulting row may
never have `roll_over == true` with a null date. A new `belongs_to` must be an existing
**non-archived** category, and re-parenting places the row at the end of the new parent's order.
Read-back response.

**`POST /subcat/reorder`** — body `{"belongs_to": "category_id", "order": ["sub_category_id", …]}`.
Same complete-set rule as `/cat/reorder`, scoped to one parent, written `0 … n−1`.

**`POST /subcat/archive`** / **`POST /subcat/restore`** — as the category pair, scoped to one
parent, with the `order = -1` mirror and the contiguous rewrite of remaining siblings.
**Budget rows and transactions pointing at an archived sub-category are left exactly as they
are** — that is what makes the archive reversible.

#### Error shapes

| Case | Status | Body |
|---|---|---|
| any auth failure | 401 | `{"ok": false, "error": "unauthorized"}` — no data keys |
| unknown id | 404 | `{"ok": false, "error": "not_found"}` |
| validation failure | 400 | `{"ok": false, "error": "bad_request", "detail": "<field and reason, never a value>"}` |

### 3.3 `client_src/bx_calc.js` — v2 (Builder C)

**Additive only. Every v1 export keeps its name, signature and behaviour**, and every v1 golden
case stays green — the round-03 clients embed this file and are re-cut against it (AC-7.2).
**Sixteen new exports**, of which `bxOverspend`, `bxIncomeShortfall` and `bxAvailableToBudget`
exist only because of §0 ruling 5.

**Transfer exclusion is an argument, not an assumption.** `bxRollover`, `bxSubTotals`,
`bxOverspend`, `bxIncomeShortfall` and `bxAvailableToBudget` each take **`transferCategoryId`** as
their last positional argument before any options object, and each excludes matching rows itself.
`bxActual` keeps its v1 contract — transfers are excluded *before* it is called — and the five new
functions are what do the excluding. This matters because §3.1 measurement 3 allows the sentinel to
be **neither** a `categories` nor a `sub_categories` row, in which case filtering "non-transfer
sub-categories" is a no-op and the exclusion has to happen on the transaction side.
Integer cents in, integer cents out, no floating-point arithmetic on money, no DOM, no `fetch`,
no globals beyond its own namespace.

New exports — **names are part of the contract; rounds 05 and 07 call them:**

| Function | Contract |
|---|---|
| `bxDefaultMonth(txns, serverDate)` | `{y, m}` — the most recent calendar month **at or before** `serverDate` holding at least one transaction; if none, the `serverDate` month. **Computed from transactions only**, never from budget rows, so every screen opens on the same month and a Forms-app-seeded empty month (fact 1) cannot drag the app onto a month with no money in it. This is §0 ruling 1 and it lives here so it has exactly one definition. |
| `bxIncomeCategoryId(categories)` | The `category_id` of the category whose trimmed name equals `Income` case-insensitively, else `null`. **The only place the magic name appears client-side.** Round 08 replaces its body with a flag lookup and nothing else changes. |
| `bxSignFor(categories, categoryId, cents)` | The `neg_pos` rule (fact 7): `abs` for the income category, `-abs` otherwise, `0` for `0`. Display-side mirror of the server's authority. |
| `bxActual(txns, subCategoryId, y, m)` | Integer cents: sum of `amount_cents` over rows in that calendar month whose `category` equals `subCategoryId`. **Transfers are excluded before this is called**, never inside it. |
| `bxBudget(budgets, subCategoryId, y, m)` | Integer cents, **or `null` when no row exists**. `null` and `0` are different facts and the UI shows them differently. |
| `bxRollover(budgets, txns, subCat, categories, y, m, transferCategoryId)` | The rollover accumulator. Returns the §4.5 object, **all nine fields**, on every branch. **`overspent` is captured, never discarded** (§0 ruling 5). |
| `bxSubTotals(txns, budgets, subCats, categories, y, m, transferCategoryId)` | `{sub_category_id: {budget, budget_present, actual, rollover}}` for every **active** sub-category. |
| `bxOverspend(budgets, txns, subCats, categories, y, m, transferCategoryId)` | `{total, by_sub: {sub_category_id: cents}}` — the sum of `bxRollover(...).overspent` over every **active, non-transfer expense** sub-category **that has a budget row for that month**. A positive integer (or 0), because it is a magnitude. **This is what §0 ruling 5 says must be accounted for**, and it is the only place it is computed. |
| `bxIncomeShortfall(budgets, txns, subCats, categories, y, m, transferCategoryId)` | `{total, by_sub}` — **per active income sub-category that has a budget row for that month**, `max(0, budget − actual)`, summed. Positive integers. The per-sub-category `max(0, …)` is what stops an income line that over-earns offsetting one that falls short (§4.5A rule 11). The exact structural twin of `bxOverspend`, because §0 ruling 6 makes them the same mechanism. |
| `bxAvailableToBudget(budgets, txns, subCats, categories, y, m, transferCategoryId)` | The §4.5A object: the month-level pool, its two carried-in deductions, what has been assigned and what is left. **The only function that looks at the previous month *for the pool*** — `bxRollover` reads the whole roll-over window, which can be a year or more. |
| `bxCatTotals(subTotals, subCats, categories)` | Rolls sub-category totals to `category_id`: `{budget, actual, variance}`, all integer cents, **summing each sub-category's MONTH budget, never its rollover `available`** (§4.5), and **excluding archived sub-categories** (fact 5 is a defect, not a convention). |
| `bxHeaderTotals(catTotals, categories)` | `{income: {budget, actual, variance}, expense: {…}}`, on the same month-budget basis. |
| `bxVariance(actualCents, budgetCents)` | `actual − budget`. The legacy convention (`Budget/__init__.py:296`) — positive is good on both sides of the grid. Kept, because changing it would silently invert every colour Bruce is used to. |
| `bxProgress(budgetCents, actualCents, isIncome)` | The §4.6 progress object. Replaces the three-branch pill (fact 16). |
| `bxOpenMonthPlan(budgets, subCats, fromY, fromM, toY, toM)` | The **pure** planner: the list of `sub_category_id`s a month-open would create rows for. The client shows it before confirming; **AC-2.5 asserts the server's `created` set equals this plan exactly.** |
| `bxCompare(a, b)` | The canonical string comparator: case-insensitive, then **code-point** as a tie-break, so it is a total order **and matches `ServerAppData`'s existing sort tie-break** (`ServerAppData.py:519-528`). Fixes §3.11 carry-fix 3 and is used by every sort in every client. |

**Golden tests — `tools/calc_golden.mjs` + `tools/calc_cases.json`, run under node, committed.**
The v1 suite (85 cases) stays green and the round adds **at least 75 new cases**, which must
include, at minimum:

- `bxDefaultMonth`: no transactions at all; all transactions in the future relative to
  `serverDate`; a month with exactly one transaction; two candidate months where the later is
  empty of transactions but full of budget rows (**the case §0 ruling 1 exists for**).
- `bxRollover`, one case per branch and per boundary: roll-over off; roll-over on with a null
  start date (`start_missing`); a start date **equal to** the target month (`months == 0`); a
  start date **after** the target month (`months == 0`, `carried_in == 0`, no crash); a 1-month
  window; a 13-month window crossing a year boundary; a month with no budget row inside the
  window; **the month that tips the pot into overspend**, with the legacy algorithm's answer and
  the new answer both computed and shown to differ (fact 12); the month **after** an overspend,
  proving the deficit does not carry; an income sub-category, proving `supported: false` and that
  no number is invented (fact 13). Every case asserts **all nine** §4.5 fields.
- `bxProgress`, one case per row of both §4.6 tables, plus: budget `null`; budget `0` with spend;
  budget `0` with no spend; **income target `0` with earnings** (the division-by-zero case); spend
  `0`; spend exactly equal to budget; **1.5× over, 3× over and 30× over, asserting `over_ratio`
  differs on all three** (fact 16); a **positive actual on an expense category** (a refund) with
  and without a budget.
- **`bxOverspend` and `bxAvailableToBudget`** (§0 ruling 5), at least twelve cases: a month with
  no overspend anywhere (`total == 0`); a month where one sub-category overspends and another
  underspends, proving **underspend does not net off overspend** (§4.5A); a month where a
  **roll-over** sub-category overspends its cumulative pot, proving its `overspent` reaches the
  pool; an **archived** sub-category that overspent, proving it is excluded; a **transfer**
  sentinel row, proving it is excluded; an **income** sub-category, proving it never contributes
  overspend; the month **after** an overspend, proving the pool is reduced by exactly that amount
  and **every category's own budget is untouched**; the month **two after**, proving the deduction
  **does not chain or compound**; a month whose predecessor has no data at all; a month where the
  deduction drives `unassigned` negative; an income shortfall present and non-zero with the pool
  and carried into the next month **exactly as an overspend is** (§0 ruling 6), with
  `carried_overspend` and `carried_shortfall` reported separately and `carried_total` their sum;
  a month where an income sub-category **over**-earns and another falls short, proving they do not
  net off; a month where income arrives **late but in full the following month**, proving the
  shortfall hits the pool once and does not chain; a month whose predecessor holds
  **transactions but no budget rows**, proving `bxOverspend` skips sub-categories with no budget
  row rather than treating a whole unbudgeted month's spend as overspent; and a month with **no
  income category at all**, proving the §4.5A rule 8 fallback.
  **These twelve are the golden half of AC-5.10 and AC-5.11**; §5's overspend triplet is the
  fixture half, and the two are not the same artefact.
- `bxCatTotals`: an archived sub-category with budget and spend, proving it is excluded (fact 5);
  a category containing a rollover sub-category with non-zero `carried_in`, proving the rollup
  uses the **month** budget; an orphan sub-category whose parent does not exist; a category with
  no sub-categories.
- `bxOpenMonthPlan`: target month already fully populated; source month empty; an archived
  sub-category with a source row, proving it is skipped.
- `bxSignFor` / `bxIncomeCategoryId`: **no category named Income at all** — every function must
  degrade to a defined answer rather than raising (fact 6).
- Float-drift cases: a rollover window whose float-arithmetic equivalent drifts, asserting the
  exact integer.

The runner exits non-zero on any mismatch, printing case name, expected and actual. **A green run
is Builder C's gate, one deliberately corrupted expectation is shown to make it exit non-zero, and
both outputs go in the debrief.**

### 3.4 `client_src/bx_core.css` and `bx_core.js` — v3 (Builder D)

Additive, plus four corrections. Everything existing keeps working unchanged.

**`bx_core.js` v3 adds:**

- `bxMonthNav(opts)` — the month selector as one component: `◀ Month YYYY ▶`, a "This month"
  reset, `data-month` with `data-value="YYYY-MM"`, and **initialisation from
  `bxDefaultMonth()`**. Every screen uses it; no screen implements its own (the round-03 screens
  are re-cut onto it).
- `bxMeter(opts)` — the progress meter element, rendered from a `bxProgress()` object. One
  implementation, used by category rows, sub-category rows and the rail.
- `bxInlineEdit(opts)` — the tap/click-to-edit money field. **A field whose value has been changed
  commits on EVERY dismissal path** — blur, Enter, backdrop tap, Escape, sheet dismissal and the
  device back gesture. An unchanged field closes without a write. **Escape does not discard a
  money edit**: fact 18 is a field that looked like it saved and did not, and a second way to lose
  a typed figure is not an improvement. Every commit routes through `bxWrite()`.
- `bxLayer(opts)` — the history contract, so that AC-8.5 and AC-8.8 are implementable: **entering
  mobile focus mode and opening a sheet each push exactly one history entry**, and `popstate`
  closes the topmost layer and commits any pending edit inside it. Nothing traps the back gesture.
- `bxError(msg)` — resolves its container **at call time**, never at load (§3.11 fix 5).
- `bxDesktopOnPhoneNotice()` — a `d-*` client loaded at ≤998 px renders a full-screen notice with
  a link to its `m-*` twin instead of an unusable overlay (§3.11 fix 6).

**Four corrections to v2:**

- **`.bx-sidebar-phone-link` moves into the canon** — it is currently duplicated verbatim in
  `d-dash` and `d-trans` and had to be fixed twice, which is exactly the two-clients drift the
  canon exists to prevent (S03 finding 7).
- **`fmtR()` is deleted.** It was deprecated-not-deleted in round 03 with a standing AC that no
  client calls it; round 03 proved zero call sites across all five clients. It takes rands in an
  app that moves cents, and leaving it callable through three more rounds is a 100× defect waiting
  for a tired builder. **This supersedes spec_03 AC-7.6, which required the definition to be
  present** — see AC-10.7.
- **Skeleton rows carry `data-skeleton`** on every client, `d-trans` included (S03 finding 5).
- **Error containers are resolved at render time**, via `bxError` (S03 finding 8).

**`bx_core.css` v3 adds** the styles for: the budget category card and its expanded sub-category
list, the meter, the desktop budget grid + detail rail, the mobile collapsible header, the mobile
**single-category focus mode** (§3.9), the colour-picker control, and the inline money editor.

**The token block is unchanged from spec_03 §3.6 and is re-locked verbatim.** Category colours
continue to come from the data (`colour_back` / `colour_text` per row) and are the only colours in
the app that are not tokens.

**Carried forward from S02/S03 as binding rules, not advice:** the non-blocking fonts pattern is
mandatory in every client (`media="print"` + `onload="this.media='all'"` + `<noscript>`); every
embedded canon block is compared by **hash**, never containment; no `<script src=`, no CDN, no
build step.

### 3.5 The `data-*` hook set — additions for this round

Spec_03 §3.5's set stands unchanged. This round adds:

| Hook | On | Carries |
|---|---|---|
| `data-cat-row="<category_id>"` | each rendered category row/card | `data-active="true\|false"` |
| `data-sub-row="<sub_category_id>"` | each rendered sub-category row | `data-active="true\|false"` |
| `data-budget` | the budget figure inside a row | `data-cents="<int>"`, `data-source="month\|rollover"`, `data-present="true\|false"` |
| `data-actual` | the actual figure inside a row | `data-cents="<int>"` |
| `data-variance` | each variance figure | `data-cents="<int>"` |
| `data-meter` | each progress meter | `data-fraction="<0..1, 4dp>"`, `data-state="none\|under\|at\|over"`, **`data-over="<uncapped ratio, 4dp, or empty when not over>"`** |
| `data-header-cell="<income\|expense>-<budget\|actual\|variance>"` | each of the six header grid figures | `data-cents="<int>"` |
| `data-available` | the available-to-budget block (§4.5A) | `data-cents` = **`unassigned`** (may be negative) · `data-starting` = **`starting_available`** · `data-assigned` = **`assigned`** · `data-income-planned` = **`income_planned`**. Named field-for-field so AC-6.12's equality has a defined subject |
| `data-carried` | the "last month" chip, **present only when `carried_total > 0`** | `data-cents` = **`carried_total`** · `data-overspend` = **`carried_overspend`** · `data-shortfall` = **`carried_shortfall`** · `data-state="outstanding\|covered"` |
| `data-overspend-sub="<sub_category_id>"` | each expense row of the chip's sheet | `data-cents="<int, positive>"` |
| `data-shortfall-sub="<sub_category_id>"` | each income row of the chip's sheet | `data-cents="<int, positive>"` |
| `data-focus="<category_id>"` | the mobile focus-mode container when open | — |
| `data-rollover` | the roll-over indicator on a sub-category row, and the rollover breakdown in the rail / sheet | **all nine §4.5 fields**: `data-supported`, `data-start-missing`, `data-months`, `data-carried-in` (`carried_in`), `data-month-budget`, `data-available`, `data-spent`, `data-remaining`, `data-overspent` — every cents value a raw signed integer. AC-6.6 compares field for field and cannot do that by parsing `R1,234.56` |
| `data-skeleton` | every skeleton placeholder, all seven clients | — |

`data-cents` is always **the raw signed integer**, so a reviewer can recompute any total from the
DOM without parsing `R1,234.56`. **`data-over` carries the uncapped ratio** (§4.6's `over_ratio`),
not the layout-capped `over_fraction`, which is why AC-14.5 can tell a 3× overspend from a 30× one.

**`data-sheet`'s `data-kind` gains one value.** spec_03 §3.5 pins it to `edit|confirm|picker`;
this round adds **`overspend`** for the §4.5A explanatory sheet. No other value is added.

### 3.6 `server_code/ServerAppData.py` — v3 (Builder S)

**Two additive changes and one pinned behaviour.**

1. **`include` becomes a comma-separated token list.** Tokens are split on `,`, each stripped of
   surrounding whitespace, and matched **exactly and case-sensitively** against the recognised
   set `{"transactions", "budgets"}`. Unrecognised tokens are ignored silently; no token is an
   error. **`?include=Transactions` (capital T) returns the v1 key-set with no `transactions`
   key** — round 03 shipped `.strip().lower()` (`ServerAppData.py:500-505`) against a spec that
   read exact, and this round pins the contract to what the spec says rather than to what the code
   did (S03 finding 3).
2. **`?include=budgets` adds one new top-level key, `budgets`** (§4.3): every row of the
   `budgets` table, serialised, sorted by `month` ascending then `sub_category_id` ascending — a
   total order, so two calls are diffable. **No windowing**, consistent with §0 ruling 2.
3. **`categories[]` and `sub_categories[]` each gain one field, `active`** (§4.2), a real boolean,
   `is not False` — the same one-place test the module already uses for transactions.
   **Archived rows are still returned** with their flag, exactly as archived accounts already are;
   the client does the filtering. This keeps a restore possible from the UI without a second
   endpoint to list what is hidden.
4. **With no query string the response is byte-shape-identical to v1** — same key-set, no
   `transactions` key, no `budgets` key. AC-1.1 proves it.

The `_active_readable` once-per-call probe (`ServerAppData.py:380-401`) is **generalised to the
two new columns** and re-derived on every request, never cached — a cached "missing" would survive
Bruce's click inside a warm process and go on hiding rows after the column existed. The module
stays read-only: still no `add_row`, no `update`, no `delete`, no subscript assignment, proven by
AST walk.

Bump the header stamp to `v3` with a one-line history entry; `/build/version` must report it.

### 3.7 The schema change, and the initialisation that must land with it (Orchestrator)

**Spec_03 Addendum 6 is the whole design of this section.** A migrated bool column arrives
`False` on every existing row, the bad window opens at the **push** rather than the approval, and
`is not False` cannot save you because the values genuinely are `False`. So this round never lets
anything read the new columns before they are correct.

**The sequence, in order, and it is not negotiable:**

1. **Snapshot first.** Before any push: a full, independent fetch of `categories` and
   `sub_categories` through `GET /app/bootstrap` (v2, still live), the §3.1 measurements through
   `GET /build/budget-audit`, and `GET /build/counts` — all UTC-stamped and written to
   **`scratch/s04/snapshot_pre_schema.json`** and **`scratch/s04/measurements.json`** (gitignored,
   never committed, but **named here and in §7 so both reviewers know where to look**).
2. **Commit 1 contains the schema edit and the two build-secret tools, and nothing that reads the
   new columns.** `db_schema` in `anvil.yaml` is edited **textually** — never `yaml.safe_load` →
   `yaml.dump` — adding exactly `categories.active` (bool) and `sub_categories.active` (bool). The
   diff is verified read-only before pushing: exactly those two columns, `client: full` /
   `server: full` unchanged on both tables, no other table, no top-level key, no `runtime_options`
   churn. `ServerAppData` at this commit is **still v2**, and `ServerBudget` **does not exist yet**
   — the tools live in `ServerBuildTools` (§3.0) precisely so that shipping them does not ship
   `/cat/archive` and `/budget/summary` against columns the database does not have.
   **No client is promoted between this push and step 5.**
3. **Park AWAITING-BRUCE, once, with exactly this request:**

   > **One click in the Anvil editor, please.**
   >
   > The DATA tab is showing a ⚠ beside `Default Database`. Open it and click **RED / LEFT —
   > *the source code is correct*** — which migrates the database to match what I pushed: two new
   > `bool` columns, `active` on `categories` and `active` on `sub_categories`.
   >
   > **Please do not set a value on any row** — I set them all myself in the next step, which is
   > the whole lesson of round 03. Then say done.

4. **Immediately on Bruce's confirmation, and before anything else runs**, the orchestrator calls
   **`POST /build/init-active`** (build-secret-gated, in `ServerBuildTools`) which, for
   `categories` and `sub_categories` only:
   - sets `active = False` on every row whose `order == -1`,
   - sets `active = True` on every other row,
   - **writes only where the current value differs**, so a re-run is a no-op,
   - returns **id lists, not just counts**:
     `{"ok": true, "tables": {"categories": {"set_true_ids": [...], "set_false_ids": [...], "unchanged_ids": [...]}, "sub_categories": {…}}}`.

   **`active` is derived from the legacy sentinel, not blanket-set to `True`.** Blanket-truthing
   would resurrect every archived category the moment the clients started filtering on `active` —
   the mirror image of round 03's failure, and just as silent.
   **The id lists are what make step 5 self-proving**, since `ServerAppData` is still v2 and cannot
   yet show `active` on these tables.
5. **Reconcile before reading**, and write the result to
   **`scratch/s04/reconcile_post_init.json`**:
   - the `set_false_ids` returned per table **equal** §3.1 measurement 4's `order == -1` id sets,
     exactly, as sets;
   - `set_true_ids ∪ set_false_ids ∪ unchanged_ids` equals the full id set of each table from the
     step-1 snapshot, with no id in two lists;
   - an independent `GET /app/bootstrap` (still v2) compared field-by-field against the step-1
     snapshot shows **zero rows missing, zero new, and zero rows differing on any field** — v2
     does not serialise `active`, so this proves nothing *else* moved;
   - `GET /build/counts` identical.
6. **Only then** does `ServerAppData` v3 (which serialises `active`), `ServerBudget`, and any
   client that filters on `active` get pushed and promoted. Everything before this point is dark
   to the new columns.
7. `python3 tools/repo_guard.py` and `git config core.hooksPath` are re-checked **after** the
   click, because the click is a platform write (S01's stripped-executable-bit lesson).

**`POST /build/init-active` is bounded on purpose.** It accepts no table name from the caller —
the two tables are literals in the source. It writes only the `active` column. It writes only the
value derived from `order`. It is idempotent. It, and `GET /build/budget-audit`, are retired at
round 08 with the rest of the migration scaffolding, and §10 says so.

### 3.8 The archive mirror — declared, temporary, and owned by round 08

§0 ruling 3 makes `active` the authority. The Forms app cannot see it and reads `order == -1`
(fact 4). So **every archive writes both**, and every restore clears both:

| Operation | `active` | `order` |
|---|---|---|
| archive | `False` | `-1`, and remaining siblings rewritten contiguous |
| restore | `True` | `max(order among non-archived) + 1` |

- **The new clients read `active` and never `order == -1`.** The mirror exists for the Forms app
  and for nothing else.
- **The mirror is written by the server, in the same call**, never by a client and never as a
  follow-up request — a half-applied archive is exactly the inconsistency this round is here to
  remove.
- **Round 08 deletes the mirror** when the Forms app stops serving. It is named in §10 and in the
  CLAUDE.md amendment so it cannot become permanent by forgetting.
- If a row is found with `active` and `order` disagreeing at any point in this round, the round
  **reports it and stops**, rather than picking a winner.

### 3.9 The two new clients

Both are **complete, self-contained HTML files**: inline CSS and JS, no external resource except
the Google Fonts stylesheet, loaded non-blocking. Both embed `bx_core.css`, `bx_core.js` and
`bx_calc.js` verbatim and hash-check every block.

**Both make exactly ONE data request per page open:**
`GET /app/bootstrap?include=transactions,budgets`. Everything after that — month navigation,
rollups, rollover, variance, meters, expand/collapse, focus mode, search — is computed locally
from that payload. Writes go through `bxWrite()`, are optimistic, and never trigger a refetch: the
local model is updated from the write's own read-back response.

**Rules that bind both clients:**

- **Transfers are excluded from every list and every total.** The transfer sentinel is neither
  income nor expenditure (§3.1 measurement 3 establishes whether it is a real row).
- **Archived categories and sub-categories are hidden by default and excluded from every total**
  (fact 5), with an "Archived (n)" affordance that reveals them and offers Restore. Nothing is
  hidden with no way back.
- **A category or header total sums MONTH budgets, never rollover `available`** (§4.5). The
  rollover figure appears on the sub-category row and in the rail, labelled, and nowhere else.
- **Available to budget (§4.5A) is shown on both screens** — unless there is no income category,
  in which case the whole block is hidden (§4.5A rule 8) — with the `data-carried` chip beneath
  it when `carried_total > 0`: one line, past tense, naming an overspend and money that did not
  arrive **separately**, **`--negative` while `outstanding` and `--on-surface-variant` once
  `covered`, never `--error` in either state**, flipping to `covered` when
  `assigned > 0 && unassigned >= 0`. **No category's meter or figure in month `M` is ever marked
  for something that happened in `M − 1`** (§0 ruling 5: every category starts from zero) —
  **but a shortfall against Income IS marked in the month it happened** (§0 ruling 6), because
  that is where it will be explained.
- **`null` budget and `0` budget render differently** — "no budget set" versus "R0.00" — and
  `data-present` carries which.
- **The income category is not editable in the ways fact 6 makes dangerous**: it cannot be
  renamed, archived or reordered, and the UI says why rather than disabling silently.
- **Every money figure is rendered through `bxFmtCents`**, which throws on non-integer input
  (spec_03 Addendum 4). Pages guard their own missing values before formatting.
- **One money format**, everywhere, on both clients: `R1,234.56`, negatives in parentheses. Fact
  17's three competing formats do not survive.
- **Any drill-down or modal that can change data recomputes the screen on close** (fact 22).

#### Slug `d-budget` — desktop budget (Builder D), 1280-first

- **Sidebar** as `d-dash`/`d-trans`, with BUDGET now highlighted and linked; DASHBOARD and
  TRANSACTIONS linked; REPORTS and SETTINGS `aria-disabled="true"` and inert under a forced click.
- **The available-to-budget block** sits at the top of the header strip, above the six-figure
  grid, because §0 ruling 5 makes it the number the month is planned against:
  **`Available to budget`** with `data-available` and its four `data-*` figures, and — only when
  `carried_total > 0` — the single chip beneath it (`data-carried`), whose copy names the two
  causes separately per §4.5A and which flips to "covered" when `assigned > 0 && unassigned >= 0`.
  Clicking it opens a `bxSheet` (`data-kind="overspend"`) listing last month's overspent expense
  sub-categories and short income sub-categories in two labelled groups, each linking to that
  month's transactions in `d-trans`. When `carried_total == 0` **the chip is not rendered at all**
  — a month with nothing to answer for says nothing.
- **Header strip:** `bxMonthNav`, and the **six-figure grid** — Income and Expense × Budget,
  Actual, Variance — each carrying `data-header-cell` and `data-cents`. Variance colouring follows
  `bxVariance`: positive `--primary`, negative `--negative`. **Both rows are coloured**; fact
  17's asymmetry (income budget and actual never coloured) is not reproduced.
- **The uncategorised banner**, counting the selected month's uncategorised transactions from the
  same payload, linking straight into `d-trans`'s triage inbox. It **recomputes when the month
  changes and when the drill-down closes** (fact 22).
- **The category list** fills the remaining width: one row per active, non-transfer category —
  name in its own `colour_text` on its `colour_back`, budget, actual, variance, and a `bxMeter`.
  Clicking a row expands its sub-categories inline, sorted by `order`, each with its own budget,
  actual, meter, and a roll-over indicator where roll-over is on.
- **The detail rail** (right, ~380 px, persistent): the selected category or sub-category. For a
  category — name, the two colours, Archive. For a sub-category — the month's budget amount
  (inline-editable), notes (clearable), the roll-over toggle **with its start month, which cannot
  be left unset**, the rollover breakdown (`carried in`, `this month`, `available`, `spent`,
  `remaining`, and `overspent` when non-zero), Archive, and a link to that sub-category's
  transactions for the month in `d-trans`.
- **Add category / add sub-category** through `bxSheet` modals, with the name and colour rules of
  §3.2 enforced client-side *and* server-side.
- **Reorder** by explicit up/down controls that build the full desired sequence and submit it in
  one `/cat/reorder` or `/subcat/reorder` call. No optimistic reorder is committed until the
  read-back returns the same sequence.
- **"Open this month"** — a header action, visible only when the selected month has **no** budget
  rows and an earlier month does. It shows `bxOpenMonthPlan`'s list, names the source month, and
  **requires confirmation** before calling `/budget/open-month`. **This is the replacement for a
  read that wrote** (fact 1) and it must look like a decision, because it is one.
- **Only the category list scrolls** (`data-scroller`); sidebar, header strip and rail are fixed.

#### Slug `m-budget` — phone budget (Builder M), 390-first

Designed for thumbs, and **the single-category focus mode is deliberately preserved** — it is the
one interaction in the legacy mobile app that is better than its desktop twin.

- **Fixed top bar (56 px):** `bxMonthNav`, centred, chevrons either side.
- **The available-to-budget block is the first thing under the top bar**, and — unlike the
  six-figure grid — **it does not collapse**. On a phone it is the one figure worth permanent
  space: `Available to budget` (`data-available`) with the `data-carried` chip beneath it when
  there is one, on the same copy and the same two states as `d-budget`, tapping through to the
  same explanatory sheet.
- **A collapsible header grid** directly beneath it: collapsed shows Income and Expense headline
  figures; expanded shows the full six. The collapse is a **designed transition on a class**, not
  three hardcoded pixel heights driven from script, and **its state survives a re-render** —
  fact 23 is a header that silently re-expands into a container that did not.
- **Fixed bottom bar (72 px):** Archived · Add (primary, centre) · Sort it (badge = uncategorised
  count, links to `m-trans`'s inbox) · nav. Every target ≥44 px.
- **Scrollable content between the bars** (`data-scroller`): one card per active category, in
  `order`, painted with its own colours, showing budget, actual, variance and a `bxMeter`.
  **Nothing is ever occluded by either bar and the last card is reachable.**
- **Focus mode.** Tapping a card enters it: the header collapses, the other cards leave, and the
  category fills the screen with its sub-categories — sorted by `order`, **excluding archived**
  (fact 19). The container carries `data-focus="<category_id>"` and **one history entry is pushed**
  (`bxLayer`).
  - **Leaving focus mode restores the previous scroll position and the previous header state**,
    and does **not** rebuild the screen (fact 24). A back affordance, a second tap on the card,
    and the device back gesture all leave it. It is never a trap.
  - **Totals inside focus mode are computed exactly as outside it** — fact 25 is the same category
    showing different numbers depending on how you were looking at it.
- **Tapping a sub-category** opens the edit bottom sheet (`bxSheet`, `data-kind="edit"`, one
  history entry): budget amount, notes, roll-over toggle + start month, the rollover breakdown,
  Archive, and a link to its transactions. **The amount field commits on every dismissal path**
  (`bxInlineEdit`, §3.4) — fact 18 is a field that quietly discarded what Bruce typed.
- **Add** opens the same sheet in create mode, for a category or a sub-category.
- **Archive** is offered through `bxConfirm()` with a 10-second "Archived. Undo" toast that calls
  the matching restore endpoint. No browser dialog anywhere.

#### The five re-cut clients

`x`, `d-dash`, `m-dash`, `d-trans`, `m-trans` are rebuilt from the v3 canon and `bx_calc.js` v2
so every embedded copy hashes to the same canon (AC-7.2 spans **all seven** clients). Behaviour is
unchanged **except** for §3.11's carry-fixes and §0 ruling 1's default month, and spec_03's AC-6,
AC-8 and AC-14 are re-proven against the new builds (AC-10.7). `d-dash` and `m-dash` gain a working
link to BUDGET. All seven promote to **1.3.0**.

### 3.10 Gates per builder, before integration

- **Builder S:** pyflakes clean on all five Python files; a fixtures-conformance self-check of
  every response shape in §4; a self-run **module-wide** AST walk of `ServerBudget.py` confirming
  **zero `.delete(` calls and zero subscript assignments of any kind**, a **function-scoped** walk
  of `api_budget_summary` and its callees confirming no write call, and a module-wide walk of
  `ServerAppData.py` confirming no write call; and a self-run of every §4.5 and §4.6 definition
  against `tools/calc_cases.json`, proving `/budget/summary` and `bx_calc.js` agree **before**
  either meets a reviewer.
- **Builder C:** `tools/calc_golden.mjs` exits 0 with all v1 **and** v2 cases green, output
  recorded; `node --check` clean; **one deliberately corrupted expectation shown to make the
  runner exit non-zero**, then reverted and re-run green. Both outputs recorded.
- **Builders D and M:** each HTML file's inline JS extracted verbatim (**HTML comments stripped
  first**) and passed through `node --check`, output recorded; the file opens locally against the
  §5 fixtures and renders; every embedded canon block **hashes equal** to `client_src/bx_core.css`,
  `bx_core.js` and `bx_calc.js` at the same commit.
- **Orchestrator:** `python3 tools/repo_guard.py` exit 0 and `git config core.hooksPath` =
  `tools/githooks`, verified **before the round's first commit** and **again after the schema
  click**.

The HTML files are **not committed** — they are uploaded to `app_versions`. Working copies live in
`scratch/s04/` (gitignored).

### 3.11 Carry-fixes from round 03 — small, named, and each with its own criterion

Round 03 closed FINAL with findings it deliberately did not fix after the gate, plus two
tooling defects carried from spec_03 §10. All eight land here, in the re-cut, where they can be
reviewed.

| # | Fix | Owner | Criterion |
|---|---|---|---|
| 1 | **`""` is accepted as a category where it must be a 400.** `ServerTxn.py:432-433` coerces an empty string to `None` (uncategorise). A silent widening of a whitelist. `null` stays the only way to uncategorise. | S | AC-12.1 |
| 2 | **`?include` matching is pinned** to exact, case-sensitive tokens (§3.6). | S | AC-1.3 |
| 3 | **`d-trans`'s description sort is case-sensitive raw ASCII**, so `"Apple Watch"` sorts before every lower-case description. All sorts in all clients move to `bxCompare`. | D | AC-12.2 |
| 4 | **`d-trans`'s skeleton rows carry `data-skeleton`**, as `m-trans`'s already do. | D | AC-12.3 |
| 5 | **`m-trans`'s `#loadError` handle is captured before the first render clears its container** — a post-load error writes into a detached node. Replaced by the canon's `bxError()`. | M | AC-12.4 |
| 6 | **A `d-*` client at ≤998 px shows a notice and a link to its `m-*` twin**, instead of `d-trans`'s fixed sidebar overlaying the table and intercepting real clicks. | D | AC-12.5 |
| 7 | **`.bx-sidebar-phone-link` moves into `bx_core.css`** and the duplicate declarations are removed from both desktop clients. | D | AC-7.2 |
| 8 | **`tools/api.py` honours a `BUILD_SECRET` environment override**, and **`tools/api.py session <bogus>` exits non-zero** instead of printing `null` and exiting 0. | S | AC-12.6 |

### 3.12 The CLAUDE.md amendment (Orchestrator) — eight additions, judged by AC-15

Additive only, in the sections that already exist:

1. **The two new write rules of §3.2** — order is written as a complete sequence, never nudged;
   every archive has a restore and no criterion may use an archive that cannot be undone.
2. **The schema sequence of §3.7 as the standing pattern for any future bool column**: snapshot →
   push schema and migration tools alone → Bruce's click → initialise **from the legacy signal,
   not blanket-true**, returning **id lists** → reconcile → only then read it.
3. **`GET /budget/summary` is the money verification instrument**, written independently of
   `bx_calc.js` in a different language, on no interactive path, and it is how every money round
   from here proves itself.
4. **The named exception to the 1-second rule**: one bootstrap fetch per page open, currently
   ~1.5 s at 404 KB, cause recorded as Anvil's ~400–700 ms dispatch floor (§0 ruling 2).
5. **`bxDefaultMonth` is the one definition of "the month a screen opens on"** (§0 ruling 1).
6. **The archive mirror is temporary and round 08 deletes it** (§3.8).
7. **An agent reporting that it did nothing is not evidence that it wrote nothing** — the mirror
   of the `ok:true` rule. Every dispatch that reports an error is reconciled against the data
   before the round closes.
8. **The overspend model (§0 ruling 5), stated as a product rule** because every later money round
   has to honour it: *Budget X is for an individual, not a set of corporate accounts. No budget
   category ever carries a debt — each month it starts from its own budget again. An overspend is
   never discarded either: it is deducted once from the following month's available-to-budget
   pool, it does not chain past that month, underspend never nets it off, and it is shown as one
   quiet past-tense line that stops being shown once the month is back in balance. Income that
   was budgeted and did not arrive is treated the same way, one month later, and named separately
   — the current month always plans against PLANNED income in full, because late money is not lost
   money. Cumulative variance is a Reports question, not a Budget-screen one.*

The slug table gains `d-budget` / `m-budget`. **Nothing else in CLAUDE.md changes.**

### 3.13 The `ZZ` rows this round creates — enumerated in advance

Spec_03 enumerated its `ZZ` rows before the round started and it was the right call. **Every
destructive or structural proof in §8 runs on these and only these.** All are created by this
round's own endpoints, all are declared in the debrief (AC-11.7), and all are left in the stated
final condition.

| # | Row | Values | Final state |
|---|---|---|---|
| 1 | `categories` | name `ZZ S04 Cat`, colours `#3A4A42` / `#E1E3DF` | **active**, at the end of the order |
| 2 | `categories` | name `ZZ S04 Cat B` | **archived** (the AC-3.6 / AC-9.6 proof), left archived |
| 3 | `sub_categories` under row 1 | `ZZ S04 Sub A`, no roll-over | active |
| 4 | `sub_categories` under row 1 | `ZZ S04 Sub B`, `roll_over: true`, start month = 13 months before the newest data | active |
| 5 | `sub_categories` under row 1 | `ZZ S04 Sub C`, no roll-over | **archived** (the AC-6.4 exclusion proof), left archived |
| 6 | `sub_categories` under row 1 | `ZZ S04 Sub D`, no roll-over | active — a fourth sibling so `/subcat/reorder` has a meaningful sequence |
| 7 | `sub_categories` under the **real Income category** | `ZZ S04 Income Sub` | **archived at round close**, so it does not sit visibly on Bruce's income list |
| 8 | `budgets` | rows for subs **A, B, C and D** in the reviewers' chosen month and the two preceding months, **plus a row for `ZZ S04 Income Sub`** in the chosen month | left in place |
| 9 | `budgets` | rows for subs A and D in a **far-future month `X`** where no real sub-category has a row (the AC-2.5 open-month source, and the AC-6.12 absent-chip month at `X+1`) | left in place |
| 10 | `transactions` | ≥ 9 rows in the chosen month against subs **A, B, C and D** and `ZZ S04 Income Sub`, including one making sub C's archived total non-zero, one taking sub **A 30× over** its budget, one taking sub **D 3× over**, and one crediting the income sub **less than its budget**, so the month carries a non-zero shortfall as well as a non-zero overspend | left in place |
| 11 | `budgets` | rows for subs A, B and D in the month **after** the chosen one, all comfortably within budget, with **no** transactions against them | left in place |

**Rows 8, 10 and 11 are what let AC-6.12 be driven on live data**: the chosen month both
overspends and falls short on income on the `ZZ` rows, so the month after it carries a non-zero
`carried_overspend` **and** a non-zero `carried_shortfall` whatever Bruce's real rows do.
**It does not make AC-5.10's non-chaining clause live-provable** — `bxOverspend` sums over every
active expense sub-category including all of Bruce's, so the round cannot assert that any real
month has zero overspend. That clause is golden-suite only, and AC-5.10 says so.

**Row 9's `X+1` is the absent-chip month.** Its predecessor `X` holds budget rows and **no**
transactions, so `carried_overspend` there is `0` by construction — the only month the round can
guarantee has no chip.

**Row 7 exists because AC-2.2 must prove the server flips the sign for income**, and that proof
cannot run on one of Bruce's real income sub-categories. It is archived at round close so the
Forms app's income list is left as it was found, and that is declared.

**Rows 1–2 will be visible in the Forms app's Budget screen during the round** — that is expected,
and it is what makes AC-9.6's archive-mirror proof possible. Round 06 or 08 retires them; there is
no hard-delete path and inventing one would be worse than the clutter.

---

## 4. THE CONTRACT

### 4.1 `GET /app/bootstrap` — unchanged, plus two tokens

With no query string: exactly spec_02 §4, unchanged, **with `active` added to each
`categories[]` and `sub_categories[]` object** (§4.2). With `?include=transactions,budgets` the
same body gains, in this order:

```json
{
  "…all spec_02 §4 keys, unchanged…",
  "transactions": [ <spec_03 §4.2 transaction object>, … ],
  "budgets": [ <§4.3 budget object>, … ]
}
```

Tokens are split on `,`, stripped, and matched **exactly and case-sensitively**. Unrecognised
tokens are ignored; a repeated token adds the key once. Key order is always `transactions` then
`budgets`, whatever order the tokens arrive in.

### 4.2 The category and sub-category objects — one field added to each

```json
{
  "category_id": "str",
  "name": "str",
  "colour_back": "str",
  "colour_text": "str",
  "order": 0,
  "active": true
}
```

```json
{
  "sub_category_id": "str",
  "name": "str",
  "icon": "str|null",
  "belongs_to": "str",
  "order": 0,
  "roll_over": true,
  "roll_over_date": "YYYY-MM-DD|null",
  "active": true
}
```

- `active` is **always a real boolean**, `is not False`, in one place in the source.
- Every other field, its type and its null rule is **unchanged from v2** — `_text` gives `""`,
  `icon` uses `_text_or_none`, `roll_over_date` serialises `null` as `null`.
- **Archived rows are returned**, flagged, as archived accounts already are.
- Sort order is unchanged: `order` (nulls last), then name case-insensitively, then id.

### 4.3 The budget object

```json
{
  "sub_category_id": "str",
  "month": "YYYY-MM",
  "amount_cents": 0,
  "notes": "str"
}
```

- **`amount_cents` is an integer, always** — never a float, never a string, never null. It is
  `int(round(stored))` over `budgets.budget_amount`, which already holds cents. If a stored value
  is **not integral** (fact 11), the serialiser rounds it **and the row is listed in the debrief**
  with its `(sub_category_id, month)` and its stored value.
- **`month` is `YYYY-MM`**, derived from the stored `period` date, which is always the first of a
  month. A stored `period` that is not the first of a month is an anomaly, is still serialised to
  its month, and is **listed in the debrief**.
- `notes` serialises `null` → `""`.
- The legacy column names `belongs_to`, `period` and `budget_amount` **do not appear on the wire**.
- **Row order:** `month` ascending, then `sub_category_id` ascending — a total order.
- Future rounds may only ADD keys.

### 4.4 `GET /budget/summary?month=YYYY-MM`

```json
{
  "ok": true,
  "month": "2026-01",
  "income_category_id": "str|null",
  "sub_categories": [
    {
      "sub_category_id": "str",
      "belongs_to": "str",
      "active": true,
      "budget_cents": 0,
      "budget_present": true,
      "actual_cents": 0,
      "variance_cents": 0,
      "rollover": { "…the full §4.5 object, all nine fields…" },
      "progress": { "…the full §4.6 object…" }
    }
  ],
  "categories": [
    { "category_id": "str", "active": true, "budget_cents": 0, "actual_cents": 0, "variance_cents": 0 }
  ],
  "totals": {
    "income":  { "budget_cents": 0, "actual_cents": 0, "variance_cents": 0 },
    "expense": { "budget_cents": 0, "actual_cents": 0, "variance_cents": 0 }
  },
  "available": { "…the full §4.5A object, all thirteen fields…" },
  "excluded": { "transfers": 0, "archived_sub_categories": 0, "orphans": 0 }
}
```

- Every `*_cents` is an integer. `variance_cents` is **`actual_cents − budget_cents`** everywhere
  it appears, matching `bxVariance`.
- `budget_present` distinguishes a budget of `0` from no budget row.
- `categories[].budget_cents` and `totals` sum each active sub-category's **`budget_cents`** —
  the month budget — **never its rollover `available`** (§4.5). The rollover figure is reported
  per sub-category and rolls up nowhere.
- `categories[]` and `totals` **exclude** archived sub-categories, transfer-sentinel rows, and
  orphans, and `excluded` counts each so a reviewer can see what was dropped rather than inferring
  it from a difference.
- **`available` is the §4.5A pool**, computed here too, from raw rows — which means the endpoint
  reads month `M − 1` as well as `M`. It is the only part of the summary that reads `M − 1` **for
  the pool**; `rollover` independently reads every month of a sub-category's roll-over window,
  which can be a year or more (§4.5 branch D). An implementation that scopes its query to two
  months will return `carried_in: 0` everywhere and pass nothing.
- Computed **from raw rows, independently of `bx_calc.js`**.

### 4.5 The rollover definition — the arithmetic, stated once

All figures are integer cents. Expense budgets and actuals are **negative**; income **positive**.
**Transfer-sentinel rows are excluded from every `spent` figure**, in both implementations.

The return object always carries **all nine fields**, on every branch:

```json
{
  "supported": true, "start_missing": false, "months": 7,
  "carried_in": -45000, "month_budget": -120000, "available": -165000,
  "spent": -98000, "remaining": -67000, "overspent": 0
}
```

`months` is defined as `max(0, month_index(M) − month_index(D))`, where
`month_index(y, m) = y * 12 + (m − 1)`. It is the number of **completed** months contributing to
the carry, so `D == M` gives `0` and `D > M` gives `0`.

**Branch A — `roll_over` is false.**
`supported: true`, `start_missing: false`, `months: 0`, `carried_in: 0`,
`month_budget` = the budget row for `(S, M)` or `0`, `available` = `month_budget`,
`spent` = the month's actual, then `remaining` and `overspent` by the closing rule below.

**Branch B — `roll_over` is true and `roll_over_date` is null.** Identical to branch A, except
`start_missing: true`. **A defined state, not a crash** (fact 14). The write path prevents it from
arising again; the read path never assumes it cannot.

**Branch C — `S` belongs to the income category.** `supported: false`, `start_missing: false`,
`months: 0`, `carried_in: 0`, `month_budget` = the budget row for `(S, M)` or `0`,
`available` = `month_budget`, `spent` = the month's actual, and then —
**not the closing rule** — `remaining = available − spent` **and `overspent = 0`, always.**
The closing rule's overspend/remaining split is defined for **negative-stored expense figures
only**; applied to income's positive figures it would report an under-earning income line as
"overspent", which §4.5A rule 4 forbids and which `bxIncomeShortfall` already reports properly
under its own name. §3.13 row 7 `ZZ S04 Income Sub` is exactly this case and AC-5.7 drives it.
The legacy left this branch as
`pass  # what do we actually do here???` (fact 13); this round states that income does not carry
and shows it, rather than producing a number nobody can defend.

**Branch D — otherwise.** Let `D` be the month of `roll_over_date`. For each month `P` from `D`
to `M − 1` in order (an empty range when `months == 0`):

```
carried = 0
for P in D … M-1:
    budget_P  = budget row amount for (S, P), or 0
    available = carried + budget_P
    spent_P   = sum of amount_cents for S in P, transfers excluded
    remaining = available - spent_P
    carried   = remaining if remaining <= 0 else 0
```

**The closing rule, applied on every branch:**

```
month_budget = budget row amount for (S, M), or 0
available    = carried_in + month_budget
spent        = sum of amount_cents for S in M, transfers excluded
raw          = available - spent
overspent    = raw if raw > 0 else 0
remaining    = 0  if raw > 0 else raw
```

**Two deliberate decisions, both recorded rather than inherited:**

1. **An overspend never carries forward inside the category — and it is never discarded either.**
   `carried` clamps at 0, so every category starts the new month from its own budget: §0 ruling 5's
   *"each budget cat is built from zero again"*. The clamped-off amount is returned as `overspent`
   and **is accounted for one level up**, in §4.5A's month pool. The legacy clamped identically
   and then threw the number away (fact 12), which is why nobody could see what an overspend had
   cost them. **A rollover pot's `carried_in` is therefore always ≤ 0 for an expense, never
   positive-as-debt**, and the golden suite asserts it on the month after an overspend.
2. **The current month's spend is not subtracted and added back.** The legacy did exactly that
   (`BUDGET.py:92`) and, when the current month tipped the pot into overspend, returned a "budget"
   equal to the month's own actual — variance 0, empty bar, *"exactly on budget"* at the moment
   the pot was blown (fact 12). Here `available` and `spent` are separate fields and `overspent`
   is named, so the screen can say what happened.

### 4.5A Available to budget — the month-level pool (§0 ruling 5)

**This is the concept the app does not have today**, and it is where an overspend goes. All
figures are integer cents. `income_planned`, `carried_overspend`, `carried_shortfall`,
`carried_total`, `starting_available` and `assigned` are **positive magnitudes**, and `unassigned` may be negative —
this is the one place in the app that talks in plain-English amounts rather than signed storage
values, because it is the one figure a person reads as "money I still have to give out". Every
other figure in the app keeps its sign convention.

`bxAvailableToBudget(budgets, txns, subCats, categories, y, m, transferCategoryId)` returns:

```json
{
  "month": "2026-02",
  "prev_month": "2026-01",
  "prev_month_has_data": true,
  "income_category": true,
  "income_planned": 5000000,
  "carried_overspend": 132400,
  "carried_shortfall": 500000,
  "carried_total": 632400,
  "starting_available": 4367600,
  "assigned": 4220000,
  "unassigned": 147600,
  "overspend_by_sub": { "sub-aaaa-1111": 88200, "sub-bbbb-2222": 44200 },
  "shortfall_by_sub": { "sub-cccc-3333": 500000 }
}
```

Definitions, in order of computation. **`amount_cents` is the §4.3 wire field** — the legacy column
name `budget_amount` never appears in `bx_calc.js`:

```
month               = "YYYY-MM" of (y, m)
prev_month          = "YYYY-MM" of the calendar month before (y, m)
prev_month_has_data = prev_month holds >=1 budget row OR >=1 non-transfer transaction
income_category     = bxIncomeCategoryId(categories) !== null            (rule 8 below)
income_planned      = Σ max(0, amount_cents) for (S, M) over ACTIVE INCOME sub-categories  (>= 0)
                      — M's PLANNED income, IN FULL, whatever has actually arrived (rule 10)
carried_overspend   = bxOverspend(…, M-1, transferCategoryId).total                        (>= 0)
overspend_by_sub    = bxOverspend(…, M-1, transferCategoryId).by_sub
                      — keys are M-1's expense sub-category ids, values positive magnitudes
carried_shortfall   = bxIncomeShortfall(…, M-1, transferCategoryId).total                  (>= 0)
shortfall_by_sub    = bxIncomeShortfall(…, M-1, transferCategoryId).by_sub
                      — keys are M-1's income sub-category ids, values positive magnitudes
carried_total       = carried_overspend + carried_shortfall                                (>= 0)
starting_available  = income_planned - carried_total
assigned            = Σ abs(amount_cents) for (S, M) over ACTIVE, NON-TRANSFER
                      EXPENSE sub-categories                                               (>= 0)
unassigned          = starting_available - assigned                         (may be NEGATIVE)
```

`max(0, …)` on `income_planned` is not defensive noise: `neg_pos` (fact 7) only runs on a legacy
*save*, so a pre-existing negative income budget row is unconstrained, and one would silently make
the pool wrong while every internal comparison stayed self-consistent. **§3.1 measurement 11 counts
them.**

**Nine rules that make it decidable:**

1. **It looks back exactly one month, and the deduction does not chain.** Month `M` is reduced by
   `M − 1`'s overspend and by nothing older. If `M` then overspends, `M + 1` is reduced by `M`'s
   overspend only. An overspend is paid for once, by having less to assign in the following month,
   and then it is done. This is what "we always look forwards" means arithmetically, and the
   golden suite proves it at `M + 2`.
2. **Underspend does not net off overspend.** `bxOverspend` sums only the positive `overspent`
   values. A category that came in R500 under does not silently pay for another that went R500
   over — that would hide both facts, and the whole point of the pool is that the overspend is
   *visible*. **The pool carries unspent money nowhere at all**: a sub-category's own opt-in
   roll-over is the only mechanism in this app that carries anything forward.
3. **Only active, non-transfer expense sub-categories that HAVE a budget row for that month
   contribute overspend.** Archived rows, transfers and income are excluded — the same exclusions
   as every other rollup (§4.4) — **and so is a sub-category with no budget row**. Without that
   last clause an unbudgeted month reports `available = 0` against real spending, makes every
   sub-category 100 % overspent, and wipes out the following month's pool. §5 mandates a month
   with no budget rows at all, so this is a state the round will meet.
4. **Income never overspends.** An income sub-category that earns less than planned produces
   `carried_shortfall` in the following month, not `overspent` in this one.
5. **`unassigned` may be negative, and that is a real state, not an error.** It means the month's
   budgets add up to more than is available — usually because last month's overspend has just been
   taken off the top. The UI names it; it does not block anything and it does not go red-as-error.
6. **`prev_month_has_data: false`** — when `M − 1` holds no budget rows and no transactions,
   `carried_overspend` and `carried_shortfall` are `0` and the flag says why. A month with no
   predecessor is not a month with a clean slate by accident.
7. **An income shortfall and an expense overspend are the same mechanism** (§0 ruling 6): both are
   measured on `M − 1`, both are positive magnitudes, both are deducted **once** from `M`'s pool,
   neither chains, and **both are named separately** in `carried_overspend` / `carried_shortfall`
   and in the chip. They are siblings, never merged into one number, because *"I spent too much"*
   and *"the money did not come in"* are different problems with different answers.
8. **With no income category, the block is suppressed, not zeroed.** If `bxIncomeCategoryId`
   returns `null` (fact 6, AC-5.9), `income_planned` is `0` by definition and
   `starting_available` would be `−carried_overspend`, leaving `unassigned` permanently negative
   and the chip permanently "outstanding" whatever the user does. That is a dead end, not a
   reading. So the object carries **`"income_category": false`** and **both screens hide the
   available-to-budget block entirely**, including the chip. Everything else on the screen still
   works. The pool is a statement about planned income; with no income category there is no
   statement to make.
9. **`assigned` counts budget rows, not categories.** A sub-category with no budget row for `M`
   contributes `0` to `assigned` — it is unbudgeted, not budgeted at zero — which is the same
   `null`-versus-`0` distinction §3.3 draws for `bxBudget` and §3.9 renders differently.
10. **`income_planned` is never built from actual receipts.** §0 ruling 6: *"budgeted income stays
    and pool stays — cash flow might be a bit late."* The current month plans against what was
    budgeted, in full. **A shortfall changes nothing in the month it happens** except that it is
    shown against Income; it reaches the pool exactly one month later, as `carried_shortfall`.
    This is the rule a builder is most likely to "improve" away by reaching for actual income, and
    AC-5.11 exists to catch that.
11. **`carried_shortfall` counts only income sub-categories that HAD a budget row** for `M − 1`,
    by the same reasoning as rule 3: unplanned income is not a shortfall, it is simply income
    nobody forecast. `max(0, …)` per sub-category, so an income line that over-earns does not
    offset one that under-earns — the same no-netting rule as the expense side.

**How it is shown — the part Bruce asked for suggestions on.** §0 ruling 5 ends *"there may be
more ways to show/do this in a way that helps users understand their overspend while not feeling
bogged down by it in the next period."* Six answers; the first five are **specified and built this
round**, the sixth is designed here and built in round 07 (§0 ruling 7):

- **One line, not a scoreboard.** The header shows `Available to budget` and, only when
  `carried_total > 0`, a single quiet chip beneath it in `--negative`, never `--error`. One
  sentence, past tense, naming an amount rather than a judgement — and **naming the two causes
  separately** (§0 ruling 6), because they are different problems:
  - overspend only → **"Last month cost you R1,324.00"**
  - shortfall only → **"R5,000.00 of last month's income didn't arrive"**
  - both → **"Last month: R1,324.00 overspent, R5,000.00 income short"**
- **A shortfall is shown against Income in the month it happens, too.** An income sub-category
  whose actual falls short of its budget renders that shortfall in `--negative` with the amount
  named — the same visual weight as an overspent expense category, because it has the same
  consequence next month. `bxProgress` already returns `state: "under"` with
  `label_kind: "short"` for exactly this; what §0 ruling 6 adds is that it must **read as
  consequential rather than merely incomplete.**
- **It is a task that can be finished.** Once the month is **both budgeted and in balance** —
  `assigned > 0` **and** `unassigned >= 0` — the chip changes to **"Last month's R1,324.00 is
  covered"** and drops to `--on-surface-variant`. The overspend stops being a mark against the
  user the moment they have actually dealt with it, which is the difference between an app that
  helps and an app that nags.
  **The `assigned > 0` half of that test is not pedantry.** Without it, a month the user has not
  budgeted yet has `assigned == 0`, so `unassigned` is large and positive and the chip would open
  reading "covered" before they had done anything — and they would then have to *increase* their
  budgets to make it say "outstanding". §5 and AC-6.9 both guarantee an unbudgeted month will be
  seen, so this is a state the round meets, not a hypothetical.
- **Tapping the chip explains, it does not accuse.** It opens a sheet (`data-sheet` with
  `data-kind="overspend"`) listing last month's causes in two labelled groups — the overspent
  expense sub-categories (`data-overspend-sub`) and the short income sub-categories
  (`data-shortfall-sub`), each carrying `data-cents` and linking to that month's transactions. The
  user sees *what* happened, on the month it happened.
- **Red lives in the past, never in the present.** Stepping back to `M − 1` shows the overspent
  meters in `--negative`. Month `M` shows every category's meter starting clean from its own
  budget. A category is never marked for something it did last month.
- **"Cover it" — designed here, built in round 07 (§0 ruling 7).** A single action in that sheet
  that reduces this month's budgets by the carried amount — either proportionally across the
  categories that caused it, or from one category the user picks — turning the chip to "covered"
  in one tap. It is the difference between telling someone they are R1,324 short and handing them
  the fix. **Round 04 does not build it**; it lands with the Dashboard's "left to spend" headline,
  where the same "here is the fix" idiom belongs. Recorded here so round 07 inherits the design
  rather than reinventing it.

### 4.6 The progress meter definition

`bxProgress(budgetCents, actualCents, isIncome)` returns:

```json
{ "state": "none|under|at|over", "fraction": 0.0, "over_fraction": 0.0, "over_ratio": null,
  "label_cents": 0, "label_kind": "remaining|over|earned|short" }
```

`fraction` and `over_fraction` are **capped at 1** for layout. **`over_ratio` is uncapped** (or
`null` when `state` is not `over`) and is what `data-over` carries — so a 3× and a 30× overspend
are distinguishable, which the legacy's saturated third branch was not (fact 16).

**Expense** (income `false`). Evaluate the guards **in this order**; the first match wins:

| # | Condition | `state` | `fraction` | `over_fraction` / `over_ratio` | `label_cents` / `label_kind` |
|---|---|---|---|---|---|
| 1 | `budget === null` | `none` | 0 | 0 / `null` | `abs(actual)` / `over` if `actual < 0` else `remaining` |
| 2 | `actual > 0` (a refund) | `under` | 0 | 0 / `null` | `abs(budget) + actual` / `remaining` |
| 3 | `budget === 0 && actual === 0` | `none` | 0 | 0 / `null` | 0 / `remaining` |
| 4 | `budget === 0 && actual < 0` | `over` | 1 | 1 / `null` *(no budget to divide by)* | `abs(actual)` / `over` |
| — | otherwise, with `B = abs(budget)`, `S = abs(actual)`: | | | | |
| 5 | `S < B` | `under` | `S / B` | 0 / `null` | `B − S` / `remaining` |
| 6 | `S === B` | `at` | 1 | 0 / `null` | 0 / `remaining` |
| 7 | `S > B` | `over` | 1 | `min((S − B) / B, 1)` / `(S − B) / B` | `S − B` / `over` |

**Income** (income `true`), guards in order, `T = budget`, `E = actual`:

| # | Condition | `state` | `fraction` | `over_fraction` / `over_ratio` | `label_cents` / `label_kind` |
|---|---|---|---|---|---|
| 1 | `budget === null` | `none` | 0 | 0 / `null` | `E` / `earned` |
| 2 | `T === 0 && E === 0` | `none` | 0 | 0 / `null` | 0 / `short` |
| 3 | `T === 0 && E > 0` | `over` | 1 | 1 / `null` *(no target to divide by)* | `E` / `earned` |
| 4 | `E < 0` (a reversal) | `under` | 0 | 0 / `null` | `T + abs(E)` / `short` |
| 5 | `E < T` | `under` | `E / T` | 0 / `null` | `T − E` / `short` |
| 6 | `E === T` | `at` | 1 | 0 / `null` | 0 / `short` |
| 7 | `E > T` | `over` | 1 | `min((E − T) / T, 1)` / `(E − T) / T` | `E − T` / `earned` |

**The reversal guard is evaluated before `E < T` deliberately.** Any negative `E` also satisfies
`E < T` for a non-negative target, so a later reversal row could never fire — and `E / T` would
then hand back a **negative** `fraction`, breaking both the "capped for layout" contract and
property 1 below. The same ordering discipline is why the expense table tests `actual > 0` at
row 2.

**Three properties the legacy pill did not have, and each has a golden case:**

1. **`fraction` is monotone in spend.** It never jumps because a branch changed.
2. **`label_kind` says what `label_cents` means.** The legacy printed remaining, then overspend,
   then total spend, from the same element, with no signal (fact 16).
3. **A 30× overspend does not render identically to a 3× one** — `over_ratio` is uncapped and
   reaches the DOM as `data-over` to four decimal places.

Colour is the design language's, not the meter's: `under` and `at` use `--primary`, `over` uses
`--negative` (amber — **never `--error`**, which is for errors), `none` renders the track alone.

### 4.7 Error shapes

Identical to spec_03 §4.5, with `detail` naming the field and the reason and **never echoing a
value**.

---

## 5. FIXTURES — what client builders build against

`scratch/s04/fixtures/` (gitignored), constructed by the orchestrator at round start from the
shapes above with **ZZ-synthetic values**. Builders D and M must render, navigate, total, expand,
focus, edit and write correctly from these alone, with every write route stubbed.

`bootstrap_full.json` — the §4.1 body with `transactions` and `budgets`, containing at minimum:

- **Categories:** an income category named exactly `Income`; at least six expense categories; **at
  least one archived** (`active: false`, `order: -1`); one whose name is a very long string; one
  whose `colour_back` is near-black and one near-white, so contrast is tested rather than assumed.
- **Sub-categories:** ≥ 30, spread unevenly across parents; **at least one archived**; at least
  one with `roll_over: true` and a start date **13 months** before the newest data; one with
  `roll_over: true` and `roll_over_date: null` (the §4.5 branch B state); one with a start date
  **after** the newest month; one with no budget row in any month; one **orphan** whose
  `belongs_to` matches no category.
- **Budgets:** ≥ 14 months, including **one month with no budget rows at all** (so the "Open this
  month" affordance has a state to be in), one sub-category whose budget is exactly `0`, and one
  whose amount is large enough to test grouping (`≥ 99_999_999` cents).
- **Transactions:** ≥ 400 across the same 14 months, including transfer-sentinel rows, ~25 %
  uncategorised, rows against the archived sub-category, a month where one sub-category is
  **3× over budget** and another is **30× over**, a month with a **positive** amount in an expense
  category (a refund), and a month with none of a category's sub-categories touched at all.
- **An overspend triplet (§4.5A):** three consecutive months `P`, `P+1`, `P+2`, all fully
  budgeted, where **`P` overspends on two sub-categories and underspends on a third**, and neither
  `P+1` nor `P+2` overspends at all. This is the fixture that proves the pool is reduced in `P+1`,
  that underspend did not net it off, that no category's own budget in `P+1` was touched, and that
  **`P+2` is not reduced again**. It must also contain one **archived** sub-category and one
  **transfer** row that overspend in `P`, so the exclusions are proven rather than assumed. The triplet must also carry an **income shortfall in `P`** — an income sub-category budgeted and
  credited less than its budget — and an income sub-category that **over**-earns in the same
  month, so §0 ruling 6's carry and its no-netting rule are both provable.

`bootstrap_no_income.json` — the same body with **no category named `Income`**, for AC-5.9.
`summary_<month>.json` — a `GET /budget/summary` sample for two of those months.
`write_ok.json`, `write_404.json`, `write_400.json`, `unauthorized.json` — the §4.7 shapes.

Builder S's endpoints must match the fixture **shapes** key-for-key against the real tables; the
reviewer compares the live response's key-set and types against §4, never against fixture values.
Builder C's golden cases are **not** the fixtures — they are `tools/calc_cases.json`, committed,
because they are the specification of the arithmetic rather than sample data.

---

## 6. SECRETS AND TEST ACCOUNTS

Unchanged from spec_03 §6. `.secrets/budgetx.env` holds `APP_BASE`, `BUILD_SECRET`, `TEST1_*`,
`TEST2_*`; if any needed value is empty, park AWAITING-BRUCE and never generate or hardcode.
**Drive everything as TEST2**; after any deliberate failed-login test, log in successfully with
TEST2 immediately so Anvil's `n_password_failures` resets; unknown-address cases use a synthetic
address not in `users`; at most one failed login may ever target TEST1. Never Bruce's own login.
No secret, password or live token in any commit, debrief, log line or CLI output; any run of 32+
lowercase hex is masked to 6 characters + `…`.

---

## 7. INSTRUMENTS — what proves what

| What | Instrument |
|---|---|
| API shapes, auth failures, write read-backs | `curl` / `urllib` against `https://budget-x.anvil.app/_/api/…`, plus `tools/api.py` |
| **Every write proven** | a **second, independent** `GET /app/bootstrap?include=transactions,budgets` after the write, compared on the specific row — **never the write endpoint's own response** |
| **Every money figure proven** | three-way: the DOM's `data-cents` · `GET /budget/summary` · an **independent recomputation in Python** from the raw payload. Two agreeing is not enough when one of them is the thing under test |
| Table row counts | `GET /build/counts` before/after, UTC-stamped |
| Detailed table facts no live endpoint exposes | **`GET /build/budget-audit`** (build-secret-gated, read-only, §3.1) |
| The schema change and its initialisation | `anvil.yaml` diff (read-only parse) · **`POST /build/init-active`'s returned id lists** · and these named files, which both reviewers are given in the dispatch: **`scratch/s04/snapshot_pre_schema.json`**, **`scratch/s04/measurements.json`**, **`scratch/s04/reconcile_post_init.json`** |
| Served bytes = promoted bytes | sha256 of `GET /x?slug=…` vs `/build/list` |
| Canonical embeds | sha256 of each extracted block vs `client_src/*` at the reviewed commit — **hash, not containment** |
| Arithmetic | `node tools/calc_golden.mjs` · independent Python recomputation · `/budget/summary` |
| Rendering, scroll, focus mode, sheets, tokens, timing | Playwright headless against the published URL at **1280×800 and 390×844**, driving the real pages — never Bruce's Chrome |
| Payload variants (e.g. no income category) | `page.route` fulfilling a modified bootstrap body — the instrument for AC-5.9 |
| Module stamps | `/build/version` |
| Speed | timed `curl` (≥20 requests per endpoint, p50/p95, fresh **and** reused) and Playwright navigation timing at both widths |

**Instrument traps, handed to both reviewers up front.** Spec_03's nine still apply verbatim and
are repeated in the dispatch. Five more come from round 03's own experience and from this round's
shape:

1. Time render from the navigation entry's `responseEnd`, never from `page.goto()`.
2. Read a 401 body with `page.route` + `route.fetch()`, never Playwright's `response` event during
   a bounce.
3. **The serving route `/x` is itself under `/_/api`**, and these pages contain the words "email",
   "accounts", "transactions" and now "budgets". Filter the serving route out of any leaked-key
   scan first.
4. Compare embedded canon blocks by **hash**. Containment passed `canon + "\n"` in S02.
5. Read headers **case-insensitively**; Anvil returns lowercase names over HTTP/2.
6. **Assert an element exists before reading its computed style**, or "not found" passes vacuously.
7. Screenshots are too slow to catch a 200 ms animation — use CDP screencast frames or rAF
   sampling.
8. **Strip HTML comments before extracting inline JS.**
9. **A textual scan changes what the code may say** — a comment promising not to call `alert(`
   reads as a violation to a grep.
10. **A migration leaves a bool column WRONG, not empty.** No criterion touching `active` on
    `categories` or `sub_categories` may be judged before §3.7 step 5's reconciliation is on
    record. Judging one earlier will produce a confident, wrong PASS or FAIL. **And AC-4.4 is
    judged against the `init-active` response and the round-start measurement, not against a
    round-end fetch** — by round end the `ZZ` archived rows of §3.13 are legitimately in the
    `active: false` set.
11. **An empty month makes a money criterion vacuous.** `∅ == ∅` passes everything. Every AC-5.4,
    AC-6, AC-8, AC-13 and AC-14 drive must be on a month named in the dispatch, chosen from §3.1
    measurement 6 with **≥ 20 budget rows and ≥ 40 transactions**, and that month is named in the
    verdict. This is spec_03 §7 trap 6 and it cost round 03 real time.
12. **Opening the Forms app writes budget rows** (fact 1). The AC-9 baseline drive and the AC-9
    comparison drive both call `load_budget_data`, which seeds the **server's current month** from
    the previous one if it is empty. Take `/build/counts` immediately before and after every
    Forms-app drive; any `budgets` delta is **legacy-app-authored**, is enumerated in the ledger as
    such, and is **not** a round-authored write. A round that does not expect this will read it as
    an unledgered change and fail AC-11 against a correct tree.
13. **`/budget/summary` must not be compared against a client that called it.** AC-13.1 forbids
    the clients calling it at all; if a comparison ever agrees perfectly on a figure the client
    could not have computed, suspect the instrument before believing the result.
14. **`bxFmtCents` throws on non-integer input by design** (spec_03 Addendum 4). A page that
    renders `null` for a missing budget must guard before formatting; a thrown `TypeError` in a
    render loop looks like a layout failure.

Everything below is reproducible by anyone holding `.secrets/budgetx.env`, including the
reviewers, with no reliance on any builder's transcript.

---

## 8. ACCEPTANCE CRITERIA

Each numbered sub-condition is a separate proof. Partial credit does not exist. **Fifteen
criteria** — the debrief's count is out of 15.

### AC-1 — the bootstrap contract is extended, not broken

1. `GET /_/api/app/bootstrap` with **no query string** and a valid TEST2 Bearer returns 200 and a
   key-set **exactly equal** to spec_02 §4 — **no `transactions` key, no `budgets` key** — and
   every `categories[]` and `sub_categories[]` object matches §4.2's key-set and types **exactly,
   on every row**, `active` a real boolean on every one.
2. `?include=transactions,budgets` returns 200 with exactly those keys **plus both**, in that
   order, and every object in `budgets` matches §4.3's key-set and types exactly — checked on
   **every** row. Row order is `month` ascending then `sub_category_id` ascending, verified
   against an independent sort.
3. **Token matching is exact and case-sensitive:** `?include=budgets` adds only `budgets`;
   `?include=transactions` adds only `transactions`; `?include= budgets , transactions ` adds
   both; and **`?include=Transactions`, `?include=BUDGETS`, `?include=garbage` and `?include=`
   each add no key at all**.
4. Auth failures (no header, malformed header, never-issued 64-hex token) return **401** with the
   uniform body and **no data key** — `budgets` included — in any of them.
5. `ServerAppData.py` in the pushed commit contains **no write call** — proven by an **AST walk**
   finding no `add_row`/`update`/`delete` call and no subscript assignment — and `/build/counts`
   is identical before and after a bootstrap call with both tokens.
6. `/build/version` reports `ServerAppData` at **v3**, `ServerTxn` at **v2**, `ServerBudget` at
   **v1** and `ServerBuildTools` at **v4**, matching the pushed header stamps.

### AC-2 — the budget write path obeys its own rules

Every proof is an **independent** bootstrap re-fetch, never the endpoint's own response. All
writes are on the `ZZ` rows of §3.13.

1. **`POST /budget/amount`** on `ZZ S04 Sub A` sets the amount; the re-fetch shows it. A **float**,
   a **string** and a **null** `amount_cents` each return **400** and the re-fetch shows **no
   change**.
2. **The sign rule is the server's.** Posting `amount_cents: 50000` to `ZZ S04 Sub A` (an expense
   sub-category) stores **−50000**; posting **−50000** to `ZZ S04 Income Sub` stores **+50000**;
   posting `0` stores `0`. All three confirmed by re-fetch. **The client's sign is never trusted.**
3. **`POST /budget/notes` with `""` clears the note** — the re-fetch shows `""`, and a subsequent
   non-empty write sets it again. (Fact 10.)
4. **A note can exist before a budget:** `/budget/notes` on a `ZZ` sub-category with no row for
   that month creates one with `amount_cents: 0` and the note, confirmed by re-fetch.
5. **`POST /budget/open-month`** is proven **in the far-future month pair of §3.13 row 9**, where
   no real sub-category has a row: opening `X+1` from `X` creates exactly the `ZZ` set
   `bxOpenMonthPlan` predicts — **compared as sets, id by id** — copying amounts, **not** notes,
   and **skipping the archived `ZZ S04 Sub C`**. Every created row is confirmed by re-fetch.
   **No real sub-category gains a budget row**, asserted by comparing the `budgets` id set for
   `X+1` before and after.
6. **It is idempotent:** an identical second call returns `"created": []`, creates nothing, and
   `/build/counts` for `budgets` is unchanged by it.
7. **A duplicate `(belongs_to, period)` pair is refused, not guessed.** If §3.1 measurement 5
   found one or more, `/budget/amount` against that pair is shown to return **400** with nothing
   written. **If measurement 5 found none, this sub-condition is judged N/A on the measurement as
   evidence**, and the guard is proven instead by an off-platform unit test of the handler's
   duplicate branch, recorded in the debrief. **No duplicate is created deliberately** — this
   round has no delete path and §2.7 forbids inventing one.
8. Unknown `sub_category_id` → **404** with no data keys. A malformed `month` → **400**.

### AC-3 — the structural write path is soft, symmetric and complete-sequence

On the `ZZ` rows of §3.13. `/subcat/*` proofs run under the `ZZ` parent so no real sibling moves.

1. **`POST /cat/create`** with `"category_id": "FORGED"` and `"order": 99` in the body returns
   200, and the re-fetch shows a **server-minted uuid4** id and a server-computed `order` —
   neither forged value appears anywhere in `categories`.
2. **Name validation, on both endpoints:** a 2-character name, a 41-character name, a name that
   case-insensitively duplicates an existing non-archived name (a category for `/cat/create`, a
   sibling for `/subcat/create`), and the name `Income` for `/cat/create` each return **400** with
   nothing written. A name with leading and trailing whitespace is **trimmed** before both the
   length and the duplicate tests.
3. **Colour validation:** a non-`#RRGGBB` `colour_back` returns **400** with nothing written.
4. **`POST /cat/reorder` writes the whole sequence.** Submitting the complete non-archived set in
   a shuffled order returns the whole set read back in the submitted order, with **income at
   `order` 0** wherever it was submitted, and the rest contiguous. An independent re-fetch agrees.
   **The round-start sequence is then re-submitted and restored verbatim** (AC-11.3).
5. **An incomplete or padded sequence is refused atomically:** omitting one id, adding an unknown
   id, and repeating an id each return **400**, and an independent re-fetch shows **every**
   category's `order` unchanged.
6. **Archive is soft, mirrored and reversible.** Archiving `ZZ S04 Cat B` sets `active: false`
   **and** `order: -1` in the re-fetch, rewrites the remaining non-archived set contiguous with
   income still at 0, and **leaves its sub-categories `active: true`**. Restoring returns
   `active: true` with an `order` at the end of the sequence. `/build/counts` for `categories` is
   **unchanged** by both.
7. **The income category cannot be archived or renamed** → **400** on each, nothing written.
8. **`POST /subcat/create` refuses `roll_over: true` with a null `roll_over_date`** → 400. So does
   `/subcat/update` when the **merged** result would be that state — proven by updating
   `ZZ S04 Sub B` (which has `roll_over: true`) to clear its date. (Fact 14.)
9. **`/subcat/reorder`** behaves as AC-3.4/3.5 within the `ZZ` parent, written `0 … n−1` across
   its four active siblings, and re-parenting a `ZZ` sub-category to another `ZZ` category through
   `/subcat/update` places it at the end of the new parent's order, confirmed by re-fetch. A
   `belongs_to` naming an **archived** category returns **400**.
10. **No hard delete exists.** `ServerBudget.py` contains **zero `.delete(` calls and zero
    subscript assignments of any kind**, proven by a module-wide AST walk of the pushed source,
    and every table count at round end is **≥** its count at round start.
11. **`/budget/summary` is read-only**, proven by a **function-scoped** AST walk of
    `api_budget_summary` and every function it calls, finding no `add_row`, `update` or `delete`
    call; and `/build/counts` is identical before and after twenty summary calls.

### AC-4 — the schema change and its initialisation are proven, in order

**The round's highest-risk criterion**, and the reason it does not close unattended. Judged
against the §7 named artefacts and the `init-active` response, **not** against a round-end fetch
(§7 trap 10).

1. The `anvil.yaml` diff for the whole round is **exactly two columns** — `categories.active` and
   `sub_categories.active`, both `bool` — with `client: full` / `server: full` unchanged on both
   tables, no other table, no top-level key, and no `runtime_options` change beyond platform noise
   (which is listed if present). Verified by a read-only parse against a pre-edit copy, **never**
   `safe_load` → `dump`.
2. **The commit carrying the schema edit reads no `active` on these tables and promotes no
   client** — proven by showing `ServerAppData` at that commit is still v2 with no reference to
   `active` outside the transactions path, that `ServerBudget.py` does not exist at that commit,
   and that the promote ledger contains no entry between the schema push and step 5.
3. **`POST /build/init-active` is authorised by the build secret and by nothing else:** a call
   with no secret, with a wrong secret, and with a valid **session Bearer** but no secret each
   return **401** with no data keys and write nothing.
4. **It derives from the legacy sentinel.** The response's `set_false_ids` **equals** §3.1
   measurement 4's `order == -1` id set, per table, **exactly, as sets**; and
   `set_true_ids ∪ set_false_ids ∪ unchanged_ids` equals the full id set of that table in the
   step-1 snapshot, with no id appearing twice. Both artefacts are in the debrief.
5. **It is idempotent:** a second call returns empty `set_true_ids` and `set_false_ids` and an
   independent re-fetch is byte-identical to the one before it.
6. **Field-by-field reconciliation against `scratch/s04/snapshot_pre_schema.json`:** zero rows
   missing, zero new, and **zero rows differing on any field**, for both tables, on the v2
   payload. `/build/counts` identical for both.
7. **No row anywhere has `active` and `order` disagreeing** at round end — every `active: false`
   row has `order == -1`, every `active: true` row has `order >= 0`. (This holds at round end
   including the §3.13 `ZZ` archived rows, which is why it is stated as an invariant rather than
   a count.)
8. The serialiser **never emits `null` for `active`** on any row of either table.

### AC-5 — the money core is right, and proven by something other than itself

*(AC-5.4, AC-5.7's live half, AC-5.8's live half, AC-5.9, AC-5.10's live half and AC-5.11's
no-income clause are judged by the **visual** reviewer; the rest by the spec reviewer. This list
and §9's mandate are the same list, deliberately.)*

1. `node tools/calc_golden.mjs` exits **0** with **every v1 case still green** and **≥ 75 new
   cases** green; the full output is in the debrief.
2. **The gate is live:** one expectation is deliberately corrupted, the runner exits **non-zero**
   and names the case; the corruption is reverted and the run is green again. Both outputs
   recorded.
3. `node --check` clean on `bx_calc.js`; the file contains **no** `fetch`, no `document`, no
   `window`, and no float literal used in money arithmetic.
4. **Three-way agreement on real data.** For **three** months named in the dispatch (each with
   ≥ 20 budget rows and ≥ 40 transactions), at both widths: every rendered `data-cents` — the six
   header cells, every category row's budget/actual/variance, and every expanded sub-category
   row's budget/actual — **equals** `GET /budget/summary` for that month **and equals an
   independent recomputation in Python** from the raw payload. Exact integer equality, no
   tolerance. **Two of the three agreeing is a FAIL, not a pass.**
5. **The rollover is right where the legacy was wrong.** On the golden case that tips a pot into
   overspend, the legacy `roll_over_calc` algorithm's answer and `bxRollover`'s are both computed
   and shown to **differ**, with the legacy returning a "budget" equal to the month's own actual
   and `bxRollover` reporting `overspent > 0` and `remaining == 0`. (Fact 12.)
6. **An overspend does not carry.** On the month **after** an overspend in the same golden
   fixture, `carried_in` is **0**, not negative.
7. **Income rollover is declared, not invented:** `supported` is `false` for an income
   sub-category and `carried_in` is `0` — in the golden suite, in `/budget/summary` for
   `ZZ S04 Income Sub`, and in the rendered rail.
8. **`bxDefaultMonth` is computed from transactions only** — on the golden case where the latest
   month has budget rows but no transactions, the returned month is the latest month **with
   transactions**; and on the live app, both budget screens open on the month an independent
   computation from the payload predicts. (§0 ruling 1.)
9. **The app degrades when there is no income category:** against `bootstrap_no_income.json`
   served through `page.route`, `bxIncomeCategoryId` returns `null`, `bxSignFor` treats every
   category as an expense, and **both clients render without throwing** — asserted on console
   errors and on a non-empty category list.
10. **The overspend is captured, deducted once, and does not chain** (§0 ruling 5, §4.5A).
    **Golden half** — on §3.3's twelve pool cases and §5's `P`, `P+1`, `P+2` triplet:
    - `bxOverspend(P).total` equals an independent Python sum of the per-sub-category `overspent`
      values, and `overspend_by_sub` names exactly the sub-categories that overspent;
    - `P`'s **underspending** sub-category contributes **nothing** — `total` is the sum of the
      positive overspends only, **not** the net;
    - the **archived** sub-category and the **transfer** row that overspend in `P` contribute
      **nothing**, and neither does a sub-category with **no budget row** for `P` (§4.5A rule 3);
    - `P+2`'s `carried_overspend` is **0**, because `P+1` did not overspend — the deduction does
      not chain or compound. *(Golden only: `bxOverspend` sums over every active expense
      sub-category, so no live month can be asserted to have zero overspend.)*
    **Live half**, on the `ZZ` rows of §3.13 (rows 8, 10, 11) and the month after the chosen one:
    - `carried_overspend` there **equals** an independent Python recomputation of the chosen
      month's total overspend, and `starting_available` is lower than `income_planned` by exactly
      that amount;
    - **the overspend appears in no per-category and no per-sub-category figure.** For every
      category in that month, `categories[].budget_cents` from `/budget/summary` equals an
      independent Python sum of its active sub-categories' budget rows **for that month alone**,
      and every `data-budget`, `data-actual`, `data-variance` and `data-meter` value is a function
      of that month's own rows only. *This is the criterion that proves "each budget cat is built
      from zero again": the pool is the only place last month appears.*
11. **The pool's own arithmetic holds, and its edges are defined.** For three months on live data,
    every figure proven the AC-5.4 way — **independent Python recomputation**, not the endpoint's
    own restatement of its own intermediates:
    - `income_planned` equals an independent sum of `max(0, amount_cents)` over active income
      sub-categories for that month;
    - `carried_overspend` and `carried_shortfall` each equal an independent recomputation over
      the previous month, and `carried_total` is their sum;
    - **`income_planned` is the month's PLANNED income in full** — proven by showing it is
      unchanged when that month's income *actuals* are altered in a `page.route`-mutated payload
      while its income *budgets* are not. §0 ruling 6: late money is not lost money, and this is
      the clause that catches an implementation which reached for actual receipts;
    - `assigned` equals an independent sum of the **absolute** month budgets of active,
      non-transfer expense sub-categories;
    - `starting_available` and `unassigned` follow from those by §4.5A's definitions;
    - `unassigned` is **allowed to be negative** and is rendered rather than clamped;
    - a month whose predecessor holds no budget rows and no transactions reports
      `prev_month_has_data: false` with `carried_overspend: 0` and `carried_shortfall: 0`;
    - and on `bootstrap_no_income.json`, `income_category` is **`false`** and the block is
      **suppressed on both clients** rather than rendering a permanently-negative pool
      (§4.5A rule 8).
12. **`GET /budget/summary` matches §4.4 exactly.** Its top-level key-set, the key-set of every
    object in `sub_categories[]` and `categories[]`, the `totals` block, the thirteen-field
    `available` block and the nine-field `rollover` object are compared key-for-key and
    type-for-type against §4.4 — on **every** row, for a populated month **and** for a month with
    no data at all, where `available` is still a full thirteen-field object and the arrays are
    empty. *(Builder S's own §3.10 self-check is not an instrument; this is.)*

### AC-6 — the desktop budget screen is real

At 1280×800, logged in as TEST2 through the login page, on the **month named in the dispatch**
(§7 trap 11), which is repeated in the verdict:

1. The screen opens on **`bxDefaultMonth`'s month** — asserted by computing it independently from
   the payload — and `data-month`'s `data-value` matches.
2. "This month" returns to the **server's current month** (spec_03 AC-6.2's definition, unchanged),
   and stepping back one month changes `data-month`, the rendered set and every total accordingly.
3. The set of rendered `data-cat-row` ids **equals** the set of active, non-transfer categories an
   independent bootstrap fetch yields — compared programmatically. **Archived categories render
   nowhere** until the "Archived" affordance is used, at which point `ZZ S04 Cat B` renders **and
   can be restored**, confirmed by re-fetch. *(It is re-archived afterwards, per §3.13.)*
4. Expanding `ZZ S04 Cat` renders exactly its **active** sub-categories, in `order`, and the
   archived `ZZ S04 Sub C` — which has a budget and spend in this month (§3.13 rows 8 and 10) —
   **contributes to no total**, proven by recomputing the category's totals with and without it.
   (Fact 5.)
5. Selecting a sub-category opens the rail with that row's values; editing the budget amount and
   committing updates the row, the category total and the header grid **without a refetch**, and
   an **independent bootstrap fetch** confirms the value server-side. Editing the notes and
   **clearing them** does the same.
6. **The roll-over toggle cannot create the crash state:** turning roll-over on with no start
   month selected does not issue a write, and the UI says what is missing. Selecting a start month
   then writes both, confirmed by re-fetch, and the rollover breakdown in the rail matches
   `/budget/summary`'s `rollover` object for that sub-category, **field for field, all nine**.
7. **A category total uses the month budget, not the rollover figure.** For `ZZ S04 Cat`, whose
   `ZZ S04 Sub B` has a non-zero `carried_in`, the category row's `data-budget` `data-cents`
   equals the sum of its active sub-categories' **month** budgets, and each such row carries
   `data-source="month"`. The sub-category row's rollover figure appears with
   `data-source="rollover"` and in no rollup.
8. **Reorder submits a complete sequence:** moving a category up issues exactly **one**
   `/cat/reorder` request whose body is the whole non-archived set, and the rendered order after
   the read-back equals the stored order.
9. **"Open this month" is a decision, not a side effect:** on a month with no budget rows it is
   offered, it names the source month, it lists what will be created, and **nothing is written
   until it is confirmed** — asserted by checking `/build/counts` for `budgets` is unchanged while
   the confirmation is open. **The visual reviewer's drive stops at the confirmation and does not
   confirm** — the live write is proven by AC-2.5 on the `ZZ` far-future pair.
10. **Scroll is driven, not photographed:** the `data-scroller` region's `scrollTop` is pushed and
    MOVES, the last category is reached, and the sidebar, header strip and rail bounding boxes are
    **identical before and after**.
11. Sidebar: BUDGET highlighted; DASHBOARD and TRANSACTIONS navigable; REPORTS and SETTINGS
    `aria-disabled="true"` and force-clicking each leaves the URL unchanged.
12. **The available-to-budget block behaves as §4.5A says, and the overspend reads as past tense.**
    On the §3.13 month **after** the overspending one, which rows 8, 10 and 11 guarantee carries
    a non-zero `carried_overspend` **and** a non-zero `carried_shortfall`:
    - `data-available`'s four attributes **equal** `GET /budget/summary`'s `available` block
      field-for-field per §3.5's mapping (`data-cents` = `unassigned`, `data-starting` =
      `starting_available`, `data-assigned` = `assigned`, `data-income-planned` =
      `income_planned`) **and** equal an independent Python recomputation — the AC-5.4 three-way
      rule;
    - the `data-carried` chip is **present**, its `data-cents`, `data-overspend` and
      `data-shortfall` match `/budget/summary`, and its rendered text names each non-zero cause
      **separately** and in past tense (§0 ruling 6 — an overspend and money that did not arrive
      are never merged into one number);
    - **the `outstanding` → `covered` transition is driven against a `page.route`-mutated
      bootstrap body** — the §7 instrument already used for AC-5.9 — in which the month's budgets
      are reduced until `assigned > 0 && unassigned >= 0`. `data-state` flips and **the computed
      colour changes with it**, from `--negative` to `--on-surface-variant`. *(It is driven this
      way and not by writing budgets, because `assigned` sums Bruce's real sub-categories and §9
      forbids a reviewer writing to them.)*
    - **no category row in that month carries any overspend marking** — every `data-meter`
      `data-state` is computed from that month's own budget and spend alone, and stepping **back**
      to the overspending month shows the `over` states there;
    - clicking the chip opens a `data-kind="overspend"` sheet whose `data-overspend-sub` elements
      are **exactly** the keys of `overspend_by_sub` and whose `data-shortfall-sub` elements are
      **exactly** the keys of `shortfall_by_sub`, each `data-cents` matching;
    - **an income sub-category that fell short in the overspending month renders its shortfall in
      `--negative` with the amount named**, at the same visual weight as an overspent expense
      category — computed colour asserted, not inspected (§0 ruling 6);
    - **on §3.13 row 9's month `X+1`, whose predecessor holds budget rows and no transactions, the
      chip element does not exist in the DOM** — asserted as absent, not as hidden.

### AC-7 — one look, self-contained files, seven clients

For **all seven** served pages (`x`, `d-dash`, `m-dash`, `d-trans`, `m-trans`, `d-budget`,
`m-budget`), on the **served bytes**:

1. No `<script src=` at all; the only external `<link` targets are `fonts.googleapis.com` /
   `fonts.gstatic.com`; no `<img src=http`, no `@import`, no `url(http`.
2. The embedded `bx_core.css`, `bx_core.js` and `bx_calc.js` blocks are **byte-identical by
   sha256** to the `client_src/` files at the reviewed commit — **all twenty-one extractions** —
   and `.bx-sidebar-phone-link` is declared **once**, in the canon, and appears in no client
   outside its canon block.
3. The spec_03 §3.6 token block is present **verbatim** in all seven, every custom property
   compared value-for-value.
4. Playwright computed styles: `body` is `rgb(25, 28, 26)`, and each page's `[data-primary]`
   element **exists** (assert first) and resolves to `rgb(30, 185, 128)`.
5. **Category colours come from the data:** each `data-cat-row`'s computed background equals its
   row's `colour_back` and its text colour equals `colour_text`, compared to the payload — and
   **every one of those pairs is measured for contrast**, with any pair below 4.5:1 listed in the
   debrief as a **data** finding for Bruce, not a build failure.
6. **`fmtR` appears nowhere in any served page** — not as a definition, not as a call site. It is
   deleted from the canon (§3.4).
7. **Every interactive control is ≥44 px in its smaller dimension**, at **both** widths, on all
   seven pages — enumerated from the DOM with **skip accounting**, each measured, the smallest
   reported. Nothing passes by not being found.
8. **The fonts link is non-blocking** on all seven: `media="print"` with an `onload` that sets
   `this.media='all'`, plus a `<noscript>` fallback.
9. **Every skeleton placeholder carries `data-skeleton`** on all seven.

### AC-8 — the phone budget screen is designed for a phone

At 390×844, logged in as TEST2, on the month named in the dispatch:

1. Top and bottom bars are **fixed**: bounding boxes **byte-identical before and after a driven
   scroll**, at 390×844, 390×600 **and** 390×500.
2. **The scroller works:** `data-scroller`'s `scrollTop` is driven from 0 to its maximum, MOVES at
   every step, `scrollHeight > clientHeight` is asserted explicitly, and the **last card's bottom
   edge is above the bottom bar's top edge** at the end. A tall-viewport capture is not evidence.
3. Every bottom-bar target is ≥44×44 px and Add carries `data-primary`.
4. **The header grid collapses and stays collapsed.** Collapsing it, then triggering a re-render
   by editing a budget, leaves it collapsed with its geometry intact — the legacy's collapsed
   state was silently re-expanded by any other caller (fact 23).
5. **Focus mode works and is not a trap.** Tapping a category card enters focus mode
   (`data-focus="<category_id>"` present), renders exactly that category's **active**
   sub-categories in `order` — the archived `ZZ S04 Sub C` renders nowhere, and the list is sorted
   (fact 19) — and the back affordance, a second tap, **and the device back gesture** each leave
   it.
6. **Leaving focus mode restores state:** the scroll position and the header collapsed/expanded
   state are identical to what they were before entering, asserted from the DOM. (Fact 24.)
7. **Focus mode does not change the arithmetic.** A category's budget, actual and variance
   `data-cents` are **identical** inside focus mode and outside it, for the **income** category as
   well as an expense one. (Fact 25.)
8. **The amount field cannot silently discard input** (fact 18): typing a value then dismissing
   the sheet by backdrop tap, by **Escape**, and by the device back gesture each **commit** the
   value, confirmed by an independent bootstrap fetch after each; and with the write route failed,
   the value **rolls back visibly** with a toast that names what did not save.
9. Archive via `bxConfirm` → the "Archived. Undo" toast → tapping Undo restores the row, each step
   confirmed by an independent fetch.
10. **The available-to-budget block is permanent and correct on a phone.** Its bounding box is
    **identical before and after collapsing the six-figure grid** and after a driven scroll — it
    does not collapse and it is never occluded by the top bar. **On the same month AC-6.12 names**
    (§3.13 row 11's), its four attributes match `/budget/summary` per §3.5's mapping, and the
    `data-carried` chip renders, names each non-zero cause separately in past tense, is tappable at ≥44 px, opens the
    `data-kind="overspend"` sheet, and flips `outstanding` → `covered` under the same
    `page.route`-mutated body AC-6.12 uses.

### AC-9 — nothing user-facing moved, and the Forms app still reads the data

1. Baseline captured **before the round's first push**: the Forms app as TEST2 at 1280×800 and
   390×844 across Dashboard, Transactions, Budget, Reports, Settings, with console output, kept in
   `scratch/s04/` (never committed). **`/build/counts` is read immediately before and immediately
   after this drive** (§7 trap 12).
2. After the final deploy the root still serves the Forms app (startup `Frame`), and the five
   screens show their observables at both widths **except** mobile Reports and mobile Settings,
   the pre-existing S01-documented defects — listed, compared against baseline (must be no worse),
   not counted against this round.
3. Each judged Forms view is actually scrolled (`scrollTop` MOVES) where a scroller exists; the
   mobile Transactions screen's known `scrollHeight == clientHeight` is recorded as unchanged.
4. No new console error against the baseline.
5. **The Forms Budget screen still reads the same data, in the same units.** `ZZ S04 Sub A` is
   given `amount_cents: 12345` through `/budget/amount`, which stores **−12345** (an expense, per
   AC-2.2). The Forms Budget screen renders that row's budget as the magnitude **123.45** in its
   negative form (`Sub_category:43` renders `"({b:.2f})".format(b=-self.b/100)`), and its
   `ZZ S04 Cat` header figures move by exactly that amount. **Not 1,234,500. Not 1.23.** This is
   what proves the cents contract did not corrupt the live app, and it is the budget-side twin of
   round 03's AC-9.5.
6. **The archive mirror works in the direction that matters.** `ZZ S04 Cat B`, archived by
   `/cat/archive` (which sets `active: false` **and** `order: -1`), **does not appear** in the
   Forms Budget screen's category list, and restoring it makes it appear again. This is the whole
   justification for §3.8 and it is proven, not assumed.
7. **Any `budgets` delta caused by the Forms app is enumerated** with its cause (fact 1), its
   month, and the rows created — declared as legacy-app-authored, not round-authored.

### AC-10 — the gates are green

1. pyflakes clean on `ServerBudget.py`, `ServerAppData.py`, `ServerTxn.py`, `ServerBuildTools.py`
   and `tools/api.py` — commands and empty output recorded.
2. `node --check` clean on `bx_calc.js` and on the extracted inline JS of **all seven** HTML
   clients (comments stripped first) — recorded, **and** a deliberately broken control file is
   shown to be rejected, proving the checker is live.
3. `python3 tools/repo_guard.py` exits 0 and `git config core.hooksPath` = `tools/githooks`,
   verified **before the round's first working commit** and **again after the schema click**.
4. **The round's git diff touches only:** `server_code/ServerBudget.py` ·
   `server_code/ServerAppData.py` · `server_code/ServerTxn.py` ·
   `server_code/ServerBuildTools.py` · `tools/api.py` · `client_src/bx_core.css` ·
   `client_src/bx_core.js` · `client_src/bx_calc.js` · `tools/calc_golden.mjs` ·
   `tools/calc_cases.json` · `CLAUDE.md` · `docs/specs/spec_04.md` (addenda only) ·
   **`DEBRIEF_S04.md`** · **`docs/review_s04_*.md`** (the reviewer verdict files) ·
   **`docs/ledger_s04_written_rows.md`** · and `anvil.yaml`'s two-column addition — and
   **nothing under `client_code/`**, whose tree hash is shown identical at both ends of the round.
   File list shown. *(Written per spec_03 Addendum 7's generalisation: the list names every
   artefact this round's own method obliges it to commit.)*
5. `ServerBudget` carries `v1` + history line, `ServerAppData` `v3`, `ServerTxn` `v2`,
   `ServerBuildTools` `v4`; all four match `/build/version` (ties to AC-1.6).
6. **The rollback ledger is written as part of each promote** — for all **seven** slugs: slug ·
   version · `record_uid` · the row that was current before · bytes · UTC — present in the debrief
   with the promote, never reconstructed after, and every row reconciled against `/build/list`.
7. **The re-cut clients did not regress.** **spec_03's AC-6, AC-8 and AC-14 are re-run in full**
   against the 1.3.0 builds and all pass. **spec_03's AC-7 is superseded by spec_04's AC-7**,
   which spans all seven clients, twenty-one extractions, and a canon from which `fmtR` has been
   deleted — spec_03 AC-7.6 required its definition to be present and is deliberately no longer
   satisfiable.

### AC-11 — the round's effect on the data is fully enumerated

1. **A written-rows ledger is committed** at `docs/ledger_s04_written_rows.md` and summarised in
   the debrief, listing for **every** row this round created, updated, archived or restored, in
   any table: table · id · what changed · before → after · UTC timestamp. **Written as the writes
   happen, never reconstructed.** Any entry that is reconstructed is marked **RECONSTRUCTED** and
   says why. Each `/cat/reorder` or `/subcat/reorder` call is **one entry carrying the whole
   before and after sequence**.
2. **The ledger reconciles against the data.** A round-end fetch compared field-by-field against
   the round-start snapshot yields a difference set that is a **SUBSET** of the ledger's id set —
   **no row changed that is not in the ledger** — and every ledger entry whose net effect is zero
   is listed and explained. *(Corrected wording, spec_03 Addendum 8: set equality is the wrong
   test whenever a round legitimately writes a value back to what it already was.)*
3. **Every real structural row is unchanged at round end.** Every `categories` and
   `sub_categories` row that existed at round start is byte-identical on every field the payload
   exposes **except `active`** (whose value is proven correct by AC-4.4) **and `order`** (which
   `/cat/reorder` and the archive compaction rewrite by design). **The stored order sequences at
   round end equal §3.1 measurement 10's round-start sequences verbatim**, per table and per
   parent — compared as ordered lists, not as sets.
4. **`settings`, `accounts` and `users` are untouched** — counts identical at both ends and every
   exposed field byte-identical.
5. **`budgets` moved only by declared writes.** Every `(sub_category_id, month)` pair that differs
   between the round-start and round-end fetches is either in the ledger as a round write, or in
   AC-9.7's enumeration as a Forms-app write, with **nothing in neither**.
6. **No row was hard-deleted, in any table.** Every table's count at round end is **≥** its count
   at round start, every round-start id is present in a round-end fetch, and `ServerBudget.py`
   contains **zero `.delete(` calls**, proven by AST walk by two independent parties.
7. **Every `ZZ` row this round created is declared** in the debrief with its exact field values
   and its final state, matched against §3.13's table, so Bruce knows precisely what is in his
   tables that was not there before and which round retires it.
8. **Every dispatch that reported an error is reconciled against the data before the round
   closes.** For each builder, fixer or reviewer dispatch that failed or reported doing nothing,
   `/build/counts` and a bootstrap diff are checked and the result recorded. *(Round 03 lost a
   live unledgered row to a dispatch that reported an API failure and had in fact written: an
   agent reporting that it did nothing is not evidence that it wrote nothing.)*

### AC-12 — the round-03 carry-fixes landed

1. **`POST /txn/categorise` with `category: ""` returns 400** with nothing written, confirmed by
   an independent fetch; `category: null` still uncategorises correctly.
2. **Sorting is case-insensitive everywhere.** In `d-trans`, sorting by description places
   `"apple"` and `"Apple Watch"` adjacently, and the rendered order equals an independent
   `bxCompare` sort of the same data. Every sortable column on every client is checked.
3. **`d-trans`'s skeleton rows carry `data-skeleton`**, asserted while the bootstrap route is
   throttled.
4. **`m-trans` reports a post-load error visibly:** with the page loaded and rendered, a failed
   write is shown to surface a visible message — asserted on the rendered DOM, not on a detached
   node.
5. **`d-*` clients at ≤998 px show the phone notice**, not an overlaid unusable table: at 390×844
   `d-trans` and `d-budget` each render a notice with a working link to their `m-*` twin, and no
   element of the desktop layout intercepts a click at the centre of the viewport.
6. **`tools/api.py` honours `BUILD_SECRET` from the environment**, demonstrated by running one
   command with an override and showing it used; and **`tools/api.py session <bogus>` exits
   non-zero** with a message distinguishable from a successful lookup.

### AC-13 — it is fast, and the truth about speed is on record

1. **Page discipline:** each of `d-budget` and `m-budget` makes **exactly one** data request per
   page open (`/app/bootstrap?include=transactions,budgets`), asserted from Playwright's network
   log. **Changing month, expanding a category, entering and leaving focus mode, opening the rail
   or a sheet, revealing archived rows, and opening the `data-carried` sheet make ZERO further
   requests. Neither client calls `/budget/summary` at any point.** The available-to-budget block
   reads the previous month from the payload already in memory (§4.5A), so a month step never
   fetches.
2. **Write discipline:** editing one budget amount produces exactly **one** `/budget/amount`
   request and **no refetch**. Reordering produces exactly **one** `/cat/reorder` or
   `/subcat/reorder`. Opening a month produces exactly **one** `/budget/open-month`.
3. **Render speed:** with the bootstrap response mocked to resolve instantly, `responseEnd` →
   first painted category row is **< 400 ms** at both widths with the §5 fixture loaded. Timed
   from `responseEnd`, never from `page.goto()`.
4. **Interaction speed:** stepping the month, expanding a category, and entering focus mode each
   repaint in **< 100 ms**, measured from the input event to the DOM mutation. These are pure
   client-side operations.
5. **Page weight:** each of the seven served HTML files is **≤ 250 KB** (`bytes` from
   `/build/list`). If any exceeds it, that is a FAIL and a real finding.
6. **The payload cost of `budgets` is measured and named.** Record the byte size and p50/p95 over
   ≥20 timed requests of `?include=transactions,budgets` **and** of `?include=transactions` alone,
   fresh and reused. The **difference** is the budgets leg. §0 ruling 2 permits the ~1.5 s page
   open as a named exception; **it does not permit the budgets leg being unmeasured**, and if that
   leg alone exceeds 300 ms it is named with its cause.
7. **The network, measured honestly:** p50 and p95 over ≥20 timed requests each, warm, on **both a
   fresh and a reused connection**, for `GET /x?slug=d-budget`,
   `GET /app/bootstrap?include=transactions,budgets`, `POST /budget/amount`,
   `POST /subcat/reorder` and `GET /budget/summary`. S02 and S03 both measured fresh at ~2×
   reused; reporting one of them misleads. **The write endpoints are timed with idempotent no-op
   writes on the `ZZ` rows of §3.13** — `/budget/amount` re-writing the value the row already
   holds, `/subcat/reorder` re-submitting the `ZZ` parent's stored sequence — with the affected
   rows' JSON **byte-identical before and after all timed runs**, and both batches in the ledger.
   *(`/cat/reorder` is deliberately not the timed endpoint: it cannot be scoped to `ZZ` rows.)*
8. **Cold start: five readings, not one.** Five separate ≥10-minute idles spread across at least
   two hours; report all five, the median and the range, and **draw no conclusion the spread does
   not support**. **Taken after the final review cycle** (§9).
9. While the real bootstrap is in flight, both screens show the **skeleton state** (asserted by
   throttling the route), never a blank page or a browser spinner alone.

### AC-14 — it feels good (driven, not admired)

At both 1280×800 and 390×844, on the month named in the dispatch:

1. **Motion exists and plays:** category rows stagger in on load and meters animate from zero —
   computed `animation`/`transition` is non-`none` on the animated elements, and **CDP screencast
   frames ≤ 20 ms apart differ** in the animated region.
2. **Reduced motion is honoured:** with `prefers-reduced-motion: reduce` emulated, all content
   appears instantly, `animationDuration` resolves to **`0s`** (not `1e-06s` — spec_03's finding),
   meters render at their final value, **focus mode still opens and closes**, and nothing is hidden
   or broken.
3. **No native dialogs:** the served bytes of all seven pages contain no `alert(`, `confirm(` or
   `prompt(` call, and **zero dialog events fire** across every drive in this round — including
   the archive path, which is exactly where a lazy implementation reaches for `window.confirm`.
4. **Surfaces are the design language:** cards, the detail rail, the sheet and the focus-mode
   container render with `border-radius` ≥12 px and a non-`none` `box-shadow`, read from computed
   styles.
5. **The meter is honest.** For the §3.13 sub-category at **30× over** budget and one at **3×
   over**, the rendered `data-over` values **differ** (`29.0000` and `2.0000` to four decimal
   places), both `data-state` values are `over`, both `data-fraction` values are `1`, and both
   `label_cents` equal an independent recomputation. (Fact 16 is the defect this criterion exists
   to prevent recurring.)
6. **Nothing janks:** during a driven scroll of `m-budget` with animating content present, the top
   and bottom bars' bounding boxes yield **exactly one distinct box each** across ≥8 samples taken
   while `document.getAnimations()` is non-empty.
7. **The optimistic write feels instant:** with the write route held unanswered for 2 s, the UI
   **still updates immediately** — the row, its category total and the header grid all move; when
   the route is then failed, **all three roll back** and a toast names what did not save. Both
   halves asserted, and the rollback is asserted on the **header**, not only on the edited row,
   because a partial rollback is the failure mode that matters.

### AC-15 — CLAUDE.md tells the truth

1. All **eight** additions of §3.12 are present, each in the section it belongs to — including
   **the overspend model stated as a product rule**, since every later money round has to honour
   it.
2. The slug table includes `d-budget` and `m-budget`.
3. The schema-sequence entry names **all five** steps — snapshot, push tools-only, click,
   initialise from the legacy signal returning id lists, reconcile — and says a bool column
   arrives **wrong, not empty**.
4. **No other section changed** — diff shown, by the same section-splitting method S02 and S03
   used: the file is split on its headings and every unchanged section is shown byte-identical.

---

## 9. THE REVIEW

- **Both reviewers run.** **visual-reviewer first**, its verdict **committed**, then
  **spec-reviewer** on everything (fresh read-only context, full AC-1…AC-15).
- **The visual reviewer's mandate is:** AC-5.4 · AC-5.7's live half · AC-5.8's live half ·
  **AC-5.9** (using `page.route` with `bootstrap_no_income.json`) · **AC-5.10's live half** ·
  **AC-5.11's no-income clause** · AC-6 · AC-7.3–7.9 · AC-8 · AC-9 · AC-12.2–12.5 ·
  AC-13.1–13.4 · AC-14. *(CLAUDE.md's rule: the spec reviewer must never judge a visual AC whose
  evidence does not yet exist.)*
- **Both reviewers are given §7's instrument-trap list up front**, all fourteen, **and the named
  `scratch/s04/` artefact paths**, and **the three months to drive** — chosen from §3.1 measurement 6
  with ≥20 budget rows and ≥40 transactions — with a note that a vacuous month makes AC-5.4, AC-6,
  AC-8 and AC-14 pass without meaning anything.
- **Freeze promotes on all seven real slugs while any reviewer is running.** Reviewers may
  upload/promote freely on `zz-rev-s04*` slugs.
- Reviewer logins use TEST2 with §6's lockout hygiene.
- **Reviewers may write to `transactions` and to the §3.13 `ZZ` rows** — every row they touch goes
  in the AC-11 ledger with the reviewer named, and each is restored or left in a stated condition.
  **Reviewers may not write to a real category, sub-category or budget row.** Two named
  exceptions, both idempotent, both ledgered, both proven byte-identical before and after:
  `POST /build/init-active` for AC-4.5, and a re-submission of the **stored** category sequence
  where AC-3.4's restoration must be verified.
- On any FAIL: `fixer` (Opus, own context) repairs, **full re-review from AC-1** — never only the
  failure, because repairs regress neighbours — **three cycles maximum**, then stop and report the
  outstanding FAILs with the reviewer's evidence.
- **AC-13.8's five cold-start readings are taken after the final review cycle**, because the app
  cannot be idle while it is being tested, and **any promote during the series restarts it**.
  Round 03 hit this; plan the two-hour window rather than discovering it.
- If cycle 2 still fails structurally, split cleanly at this seam:
  **`04a`** = AC-1 · AC-2 · AC-3 · AC-4 · AC-5.1–5.3, 5.5–5.7 · AC-5.8's golden half ·
  AC-5.10's golden half · AC-5.11 except its no-income clause · AC-5.12 · AC-10.1–10.6 · AC-11 ·
  AC-12.1 · AC-12.6 · AC-15 (server, schema and calc) ·
  **`04b`** = AC-5.4 · AC-5.8's live half · AC-5.9 · AC-5.10's live half · AC-5.11's no-income
  clause · AC-6 · AC-7 · AC-8 · AC-9 · AC-10.7 · AC-12.2–12.5 · AC-13 · AC-14 (clients).
  The seam is §4.
- Debrief `DEBRIEF_S04.md`, STATUS line rules unchanged. **Never FINAL with anything unjudged.**

---

## 10. ROUND CLOSE — what this round leaves behind

`bx_calc.js` v2 carries rollover, variance and the meter into round 05 (Reports builds its series
from the same functions) and round 07 (the Dashboard's "left to spend" headline is `bxRollover`
and `bxProgress` in a different costume). `GET /budget/summary` becomes the standing money
instrument every later round proves itself against. The structural write pattern of §3.2 —
complete-sequence ordering, symmetric archive/restore, server-owned identity — is the template for
round 06's accounts and settings writes. And `active` on `categories` and `sub_categories`
finishes the soft-delete story that `transactions.active` started.

**Round 05 inherits one product decision from §0 ruling 5.** Bruce's answer opened with the
accountant's lens — *"carry debt across months/periods to track a YTD variance"* — and then ruled
it out **as the default for an individual**. It is not ruled out as a *view*. **Round 05 (Reports)
owns cumulative variance**: a year-to-date budget-vs-actual per category, built from
`bxOverspend` and the same month figures, opt-in and never on the Budget screen. The Budget screen
looks forwards; Reports is where you look back. Spec_05 should say so in its own §1.

**Still open after this round**, carried forward deliberately:

- **The archive mirror (§3.8) is temporary and round 08 must delete it** along with the
  `order == -1` convention, when the Forms app stops serving the root.
- **`POST /build/init-active` and `GET /build/budget-audit` are migration scaffolding** and are
  retired at round 08.
- **Income is still identified by the literal name `"Income"`**, now isolated in
  `bxIncomeCategoryId` and `ServerBudget._income_category_id`. Round 08 replaces it with a flag on
  `categories` and both bodies change; nothing else does. Note the deliberate widening: the legacy
  test is case-**sensitive** (fact 6), the new one is not, and §3.1 measurement 2 is what proves
  no live row collides.
- **`sub_categories.budget` is a `link_multiple` column no code reads** (fact 21). Round 08
  removes it.
- **`budget_work.load_budget_data` still writes on read** (fact 1) for as long as the Forms app
  runs. Round 08 retires the module.
- **Any duplicate `(belongs_to, period)` budget rows found by §3.1 measurement 5 are reported,
  not repaired** — a data repair on Bruce's own planning figures is his decision, and this round
  hands him the list. Note the legacy actively breeds them (fact 3).
- **Any non-integral `budgets.budget_amount`** (fact 11) and any `period` that is not a month
  start are listed for the same reason.
- **`ZZ S04 Cat` and `ZZ S04 Cat B` remain in `categories`**, and their sub-categories in
  `sub_categories` — visible in the Forms app's Budget screen. There is no hard-delete path;
  round 06 or 08 retires them.
- **Three pre-existing transactions carry malformed hashes** and will not de-duplicate correctly.
  **Round 06 owns CSV import and must know this before it starts** — carried unchanged from S03.
- **The Forms app's account dropdown lists `ZZ Test Archived`** — expected, since `client_code/`
  is frozen and that control ignores `archived`. Carried unchanged from S03.
- `tools/api.py`'s two S03 defects are fixed here (§3.11 fix 8), closing that carry.

---

## 11. WHAT BRUCE SETTLED BEFORE LOCKING — 2026-08-21

**All eight are settled.** Nothing in this spec is awaiting a decision; it is locked and built as
written.

1. **§0 ruling 3 / §3.7 — a schema change, so the round parks and does not close unattended.** Two
   bool columns, Code's edit, Bruce's approve-click, then Code initialises every row **from the
   legacy `order == -1` sentinel** and reconciles before anything reads them.
2. **§3.8 — the archive mirror.** `active` is the authority; `order = −1` is written alongside it
   so the Forms app stays coherent until round 08 deletes the mirror. This is the "even if it
   means the app doesn't work in some areas" ruling **taking the smaller cost**: best practice in
   the new app, one extra field write to keep the old one honest, and a named owner for its
   removal.
3. **§0 ruling 5 / §4.5 / §4.5A — the forward-looking overspend model, RULED 2026-08-21.** No
   category carries a debt; each month it starts from its own budget again. The overspend is not
   discarded either — it is deducted **once** from the next month's available-to-budget pool, it
   does not chain, underspend does not net it off, and it is shown as one quiet past-tense line
   that stops being shown once the month is back in balance. The accountant's cumulative-variance
   lens is not lost, it moves to Reports in round 05 (§10).
4. **§4.6 — the progress pill is replaced, not ported.** The legacy's zero point jumps 20% → 50%
   → 80% and the number on it changes meaning between branches. The replacement is monotone and
   labelled.
5. **§2.7 and §3.13 — real structural rows are not experimented on.** Every archive, restore,
   reorder and CRUD proof runs on the eleven `ZZ` rows enumerated in §3.13. Two `ZZ` categories will
   be visible in the Forms app's Budget screen during and after the round.
6. **Scope: RUN IT WHOLE, ruled 2026-08-21.** The round carries **15 criteria and ~123
   sub-conditions** against round 03's 14 and ~90, over fourteen new endpoints plus two temporary
   build tools, sixteen new calc
   exports, two new clients **plus five re-cuts**, and a schema migration with a park. §9's
   pre-declared `04a`/`04b` seam stands as an escape hatch if the gate forces a split at cycle 2 —
   it is not a plan to split.
7. **§0 ruling 6 — income that does not arrive, RULED 2026-08-21.** Bruce: *"budgeted income stays
   and pool stays — cash flow might be a bit late, or not arriving at all. If it does not arrive,
   shortfall highlighted against INCOME, and subtracted against next month's in the same way as an
   overspent cat."* So the current month plans against **planned** income in full — a late invoice
   does not collapse the plan — the shortfall is **shown against Income in the month it happened**,
   and one month later it is deducted from the pool by the **same mechanism as an overspend**,
   named separately so the two causes are never confused.
8. **§0 ruling 7 — "Cover it" is designed now and built in round 07, RULED 2026-08-21.** The
   one-tap action that reduces this month's budgets by the carried amount is specified in §4.5A so
   round 07 inherits the design, and is **not built in this round**. Round 04 is already the
   largest of the migration and the chip is honest and useful without it.

---

## 12. ADDENDA

*(Corrections found during the build are added here, dated, rather than edited into the approved
text above.)*

### Addendum 1 — 2026-08-21 (Orchestrator) — §3.7's commit 1 is split into 1a and 1b

**The contradiction.** §3.7 step 1 requires the round-start snapshot and the §3.1 measurements to
be taken **"before any push"**, and specifies that measurements 5, 6, 7, 9, 10, 11 and 12 are taken
**through `GET /build/budget-audit`**. §3.7 step 2 then puts that endpoint in **commit 1, alongside
the schema edit**. The endpoint therefore does not exist at the moment step 1 says to use it. As
written the sequence cannot be executed.

**The resolution.** Commit 1 is split, and the split makes step 2's guarantee *stricter*, not
weaker:

- **Commit 1a** — `server_code/ServerBuildTools.py` v4 alone: `GET /build/budget-audit`,
  `POST /build/init-active`, and the guarded `ServerBudget` branch in `_module_versions()`.
  **No `anvil.yaml` edit.** Neither tool reads an `active` column on `categories` or
  `sub_categories`; the audit reads the legacy `order == -1` sentinel, and `init-active` is never
  called before step 4.
- **The §3.7 step 1 snapshot and the §3.1 measurements are taken here**, between 1a and 1b.
- **Commit 1b** — the `anvil.yaml` two-column edit **alone**, carrying no Python at all.

§3.7 step 2's binding requirement is *"the commit carrying the schema edit contains nothing that
reads the new columns"*. Commit 1b contains **no code whatsoever**, so the requirement holds by
construction. **AC-4.2 is judged against commit 1b**, and its "promotes no client" clause spans
the whole window from 1a to step 5.

### Addendum 2 — 2026-08-21 (Builder S, adopted by the Orchestrator) — AC-4.4 and AC-4.5 cannot both be judged against `set_false_ids`

**The contradiction.** §3.7 step 4 requires `POST /build/init-active` to write **only where the
current value differs**, and **AC-4.5** proves idempotence by requiring a second call to return
**empty `set_true_ids` and `set_false_ids`** — so `set_*` must mean *what this call wrote*. But
**AC-4.4** requires `set_false_ids` to **equal** §3.1 measurement 4's `order == -1` id set.

Those are contradictory **on the very first call**, and precisely because of the hazard §3.7 is
built around. Spec_03 Addendum 6 established that Bruce's migrate click writes a real **`False`**
into every existing row. The archived rows therefore already hold their correct value when
`init-active` first runs: they are **unchanged**, `set_false_ids` comes back **empty**, and
`unchanged_ids` holds exactly the set AC-4.4 is looking for. The criterion as written would FAIL
against a correct implementation.

**The resolution.** `POST /build/init-active` returns **two partitions**, and they are not the same
partition:

- `set_true_ids` / `set_false_ids` / `unchanged_ids` — **what this call wrote**. Every row appears
  in exactly one of the three.
- `derived_true_ids` / `derived_false_ids` — **what each row's `active` now IS**, written or not.
  Every row appears in exactly one of the two.
- `prior_counts` — `{true, false, null}` as found before the call, which is direct evidence of what
  the click actually left behind.

**AC-4.4 is judged against `derived_false_ids`** (which equals measurement 4's set under either
hazard state), and its union clause against `derived_true_ids ∪ derived_false_ids`.
**AC-4.5's idempotence is judged against `set_true_ids` / `set_false_ids`.** Both artefacts go in
the debrief, as AC-4.4 already requires.

### Addendum 3 — 2026-08-21 (Orchestrator) — no live month has 20 budget rows; the drive months are named and the threshold is restated

**The §3.1 measurement that changed a decision.** §7 trap 11 and AC-5.4 require the reviewers to
drive **three** months each holding **≥ 20 budget rows and ≥ 40 transactions**, chosen from §3.1
measurement 6. Measurement 6, taken 2026-08-21 against the live tables through
`GET /build/budget-audit`, says **no such month exists** — and none can be made to exist by this
round, because §2.7 forbids writing budget rows on real sub-categories and §3.13's `ZZ` rows add
only five per month.

| month | budget rows | transactions | non-transfer |
|---|---|---|---|
| 2025-07 | 1 | 98 | 98 |
| 2025-08 | 1 | 190 | 190 |
| 2025-09 | 2 | 163 | 163 |
| 2025-10 | 6 | 205 | 205 |
| 2025-11 | 10 | 219 | 219 |
| **2025-12** | **12** | **273** | **261** |
| **2026-01** | **12** | **142** | **142** |
| 2026-02 | 14 | 10 | 10 |
| 2026-08 | 0 | 1 | 1 |

`budgets` holds **58 rows in total** across 57 sub-categories and nine months. The spec was written
expecting a fully-budgeted table; the real one is sparse.

**The resolution.** The threshold existed to stop a **vacuous** month passing a money criterion —
`∅ == ∅` passes everything (§7 trap 11). That intent is served by density, not by the number 20. So:

- **The threshold is restated as ≥ 10 budget rows and ≥ 40 non-transfer transactions.**
- **The three months named in both reviewer dispatches are `2025-11`, `2025-12` and `2026-01`.**
  They are the three densest live months and each clears the restated bar comfortably.
- **The primary drive month for AC-6, AC-8, AC-13 and AC-14 is `2025-12`.** It is chosen on
  evidence, not convenience: measurement 12 reports it is the **only** live month carrying a
  non-zero overspend (**1,101,913 cents across two sub-categories**), which makes **2026-01** a
  live month with a genuinely non-zero `carried_overspend` — so AC-6.12's chip is provable on
  Bruce's own data as well as on the `ZZ` rows.
- After §3.13's `ZZ` budget rows land, 2025-12 carries **17** budget rows and 2025-11 **15**.
- **Every verdict must name the month it drove**, exactly as §7 trap 11 already requires.

### Addendum 4 — 2026-08-21 (Orchestrator) — the other nine measurements, and what they settle

Measurement 6 was the only surprise. The rest came back clean, and several of them **retire a
hazard the spec had budgeted for**:

- **M2 — income.** Exactly one category named `Income`, byte-exact, **zero near-misses**. The
  widening from the legacy case-sensitive test (fact 6) to `bxIncomeCategoryId`'s
  case-insensitive one is proven safe: no live row collides.
- **M3 — the transfer sentinel `ec8e0085-…` IS a `categories` row** (name `Transfer`,
  `order == -1`, so legacy-archived) and is **not** a `sub_categories` row. 12 transactions point
  at it. Consequences: it is **excluded from `/cat/reorder`'s "complete set of non-archived
  categories"** by virtue of being archived, and because it has no sub-category rows the exclusion
  must happen **on the transaction side** — exactly the case §3.3 wrote `transferCategoryId` as an
  argument for.
- **M4 — `order == -1`:** exactly one category (the transfer sentinel) and one sub-category
  (`8b7038de-…`, `Tester2`). These two ids are what AC-4.4 compares `derived_false_ids` against.
- **M5 — zero duplicate `(belongs_to, period)` pairs.** Fact 3's breeding ground is empty today.
  **AC-2.7 is therefore judged N/A on the measurement as evidence**, and the duplicate guard is
  proven instead by the off-platform unit test AC-2.7 itself prescribes.
- **M7 — zero non-integral `budget_amount` values.** Fact 11's float cents are not present in the
  live table. §4.3's rounding path is still implemented and still golden-tested; it simply has no
  live row to list.
- **M8 — zero `roll_over == True` rows with a null date.** Fact 14's crash state does not exist
  live. §4.5 branch B is still implemented and golden-tested.
- **M9 — zero orphans**, in either direction.
- **M10 — the order sequences are captured verbatim** in `scratch/s04/measurements.json` under
  `order_sequences`. This is the artefact AC-11.3 restores against.
- **M11 — zero sign anomalies.** No income budget row is negative and no expense budget row is
  positive, so §4.5A's `max(0, …)` on `income_planned` has no live row to defend against. It stays.
- **M12 — overspend by month:** every month is `0` except **2025-12 → 1,101,913 cents over two
  sub-categories**. This is what names the drive month in Addendum 3, and it means the
  absent-chip case must be proven on §3.13 row 9's far-future pair as the spec already designed
  (or on any month whose predecessor is one of the eight zero months).

### Addenda 5–10 — 2026-08-21 (Orchestrator, on findings from Builders C and S) — six ambiguities ruled, so two independent implementations converge

Builder C (`bx_calc.js`) and Builder S (`/budget/summary`) are deliberately written from the spec
text without reference to each other — that independence is what makes AC-5.4's agreement
evidence. It only works if the spec text is decidable. Six clauses were not. Each is ruled below
and both builders were given the ruling, so they converge on **the spec's** reading rather than
each picking a defensible side.

**Addendum 5 — `over_fraction` is clamped to `[0, 1]`; `over_ratio` stays uncapped.**
§4.6 states that `fraction` and `over_fraction` are "capped at 1 for layout" and that `over_ratio`
is the uncapped one. Read literally, the **income** table's row 7 with an anomalous **negative**
target yields `over_fraction = min((E − T) / T, 1) = −1` — not a cap, and a value that would drive
a meter fill backwards. So `over_fraction` is `max(0, min(ratio, 1))` on **both** tables.
`over_ratio` is unchanged: uncapped, and free to be negative on such an input, because it is the
diagnostic value and `data-over` carries it. §3.1 measurement 11 found **zero** sign anomalies
live, so nothing reachable hits this path today; it is fixed because `neg_pos` only ever ran on a
legacy *save*, so the state remains representable.

**Addendum 6 — archived CATEGORIES are excluded from `totals`, but still reported in
`categories[]`.** §4.4 names archived sub-categories, transfers and orphans, and is silent on
archived *categories*. §3.9 is not silent: *"Archived categories and sub-categories are hidden by
default and excluded from every total (fact 5)."* So an archived category's still-`active`
sub-categories contribute **nothing** to `totals.income` / `totals.expense`. This is a
live-reachable state and not a fixture artefact — `/cat/archive` deliberately leaves the
sub-categories `active: true` (§3.2), because cascading would not be reversible. The archived
category is **still emitted in `categories[]`** with its own figures and `active: false`, because
the "Archived (n)" affordance renders them.

*Found by cross-checking `bxHeaderTotals` against the orchestrator's independent Python on fixture
month 2025-10: −6,020,000 versus −5,745,000, a difference of exactly the archived category's
−275,000.*

**Addendum 7 — an ORPHAN reaches the pool, but not the category roll-ups.** §4.4 excludes orphans
from `categories[]` and `totals` and counts them under `excluded.orphans`. §4.5A rule 3 enumerates
its **own** exclusions — active, non-transfer, expense, and has-a-budget-row — and orphans are not
among them. So a sub-category whose `belongs_to` matches no category is not income, is therefore
an expense, and **does** contribute its `overspent` to `carried_overspend` and its absolute month
budget to `assigned`. Builder C and the orchestrator derived this independently and agree.
§3.1 measurement 9 found **zero** orphans live.

**Addendum 8 — `bxSubTotals` omits the transfer sentinel.** §3.3 describes `bxSubTotals` as
covering "every **active** sub-category", but §4.4 requires the category roll-up and the header
totals to exclude transfer rows, and `bxCatTotals` takes no `transferCategoryId` argument. The
exclusion is therefore in `bxSubTotals` or nowhere. It is in `bxSubTotals`.

**Addendum 9 — `budget_present` carries the null/zero distinction; `budget_cents` is always an
integer.** A sub-category with no budget row for the month serialises `budget_cents: 0` **and**
`budget_present: false`, never `null`, in both `/budget/summary` and `bxSubTotals`. §4.4 already
says so; it is restated because §3.3's `bxBudget` returns `null` for the same state and the two
must not be confused. `bxBudget`'s `null` is unchanged — it is what §3.9 renders as "no budget
set" rather than "R0.00".

### Addenda 18–19 — 2026-08-21 (Orchestrator, on findings from the visual reviewer, cycle 1) — two criteria describe a fixture that is not the live one

**Addendum 18 — AC-5.10's live half: the pool is reduced by `carried_total`, not by `carried_overspend` alone.**
AC-5.10 says *"`starting_available` is lower than `income_planned` by exactly that amount"*, where
"that amount" is the chosen month's total overspend. That wording assumes the live month carries an
**overspend and nothing else**. It does not: §3.13 row 10 deliberately makes the chosen month carry
a **shortfall as well**, because §0 ruling 6 needs one. Measured on 2026-01:
`income_planned 16,500,000 − carried_total 4,440,112 = starting_available 12,059,888`, where
`carried_total = carried_overspend 1,491,913 + carried_shortfall 2,948,199`.

**§4.5A is right and the code is right** — `starting_available = income_planned − carried_total` is
the definition. AC-5.10's phrasing is the thing that is wrong. **The criterion is judged as:
`starting_available == income_planned − carried_total`, with `carried_overspend` separately equal to
an independent recomputation of the previous month's overspend.** Both hold.

**Addendum 19 — AC-14.5's `29.0000`/`2.0000` describes a different fixture from §3.13's.**
AC-14.5 predicts `data-over` values of `29.0000` and `2.0000` for the sub-categories §3.13 row 10
calls "30× over" and "3× over". §4.6 defines `over_ratio = (S − B) / B`. §3.13 row 10 sets the
**overspend** to 30× and 3× the budget — `ZZ S04 Sub A`, budget R100, spend R3,100 → `(3100−100)/100
= 30.0000`; `ZZ S04 Sub D`, budget R300, spend R1,200 → `(1200−300)/300 = 3.0000`. To yield 29 and 2
the **spend** would have to be 30× and 3× the budget.

**The arithmetic is right; the parenthetical predicts values for data the round does not create.**
**The criterion is judged on what it exists to prove** (fact 16): the two `data-over` values must
**differ**, both `data-state` must be `over`, and both `data-fraction` must be `1`. Measured:
`30.0000` vs `3.0000`, both `over`, both `1.0000`, `label_cents` 300,000 and 90,000 matching an
independent recomputation. A saturated meter that could not tell a 3× from a 30× overspend is
exactly what this replaces.

*(Also corrected, from the same review: live 2026-01 is **`covered`**, not `outstanding` —
`assigned 1,690,000 > 0` and `unassigned 10,369,888 ≥ 0` — so the chip there renders §4.5A's merged
covered copy. The separate-cause past-tense copy is reached by driving the month into `outstanding`,
which the reviewer did via a `page.route`-mutated body. The orchestrator's cycle-1 dispatch stated
the opposite and was wrong.)*

### Addendum 17 — 2026-08-21 (Orchestrator) — one leftover round-03 test row defeats §0 ruling 1, and is archived

**The finding.** `bxDefaultMonth` on the **live** payload returns **2026-08** — a month holding
**one** transaction and **zero** budget rows. The one transaction is
`74f7a3a5-c7f9-4671-98c7-bf6781453b03`, **"ZZ S03 cents probe"**, `amount_cents` 12345, created by
round 03 as AC-2.5's and AC-9.5's evidence and deliberately left `active` (DEBRIEF_S03, "Live rows
left behind, declared": *"Bruce can archive the probe from the new Transactions screen whenever he
likes"*).

**The function is not wrong.** §0 ruling 1 defines the default month as the most recent month
holding at least one transaction, and 2026-08 holds one. `bxDefaultMonth` is behaving exactly as
specified, and AC-6.1 and AC-5.8 would pass against 2026-08.

**But the outcome is precisely the one ruling 1 was written to prevent.** Round 03 shipped an app
that opened on a month holding zero rows with 1,300 transactions six months behind it; that is
quoted verbatim in §0 ruling 1 as the reason the rule exists. Shipping round 04 opening on a month
holding a single stale test row is the same defect with a smaller number in it.

**The resolution — archive the probe, do not weaken the definition.** This is a **data** problem,
not a code problem, and the fix belongs in the data:

- `POST /txn/archive` on that one row — **soft, reversible** (`/txn/restore`), and squarely inside
  what §2.7 permits (*"`transactions`: writable, real rows included"*). It is a `ZZ`-prefixed test
  row from a previous round, not one of Bruce's records.
- It is **ledgered as a round-04 write** with its reason, and declared in the debrief, exactly as
  §3.13 row 7 is archived at round close for the same kind of tidiness reason.
- **It is done BEFORE the reviewers drive**, not after, so the verdicts describe the app as it
  actually ships. Changing data underneath a running gate is forbidden (CLAUDE.md: freeze promotes
  while a reviewer is running); changing it beforehand and declaring it is not.
- **`bxDefaultMonth`'s definition is untouched.** After the archive the live default month is
  **2026-02** — 10 transactions and 14 budget rows, a real month.

**Not weakened, and recorded as the alternative that was rejected:** the round could have left the
row and reported the behaviour as correct-by-definition. That would have been true and useless —
the first thing Bruce sees on opening the app is the thing the round is judged on.

### Addendum 16 — 2026-08-21 (Orchestrator, on a finding from Builder D) — the deep-link contract the spec assumes but never defines

**The gap.** §3.9 requires `d-budget` and `m-budget` to link **into that month's transactions** in
three places: the carried chip's sheet ("each linking to that month's transactions"), the detail
rail ("a link to that sub-category's transactions for the month in `d-trans`"), and the
uncategorised banner ("linking straight into `d-trans`'s triage inbox"). AC-6.12 judges the first.
**But `d-trans` and `m-trans` accept no parameters at all** — they open on `bxDefaultMonth` and
show everything — so a bare `?slug=d-trans` link cannot reach "that month", and §2.9 forbids
changing the re-cut clients' behaviour beyond the §3.11 carry-fixes.

Builder D was right not to invent a contract silently, and right to flag it rather than let the
link quietly mean something weaker than the spec says.

**The resolution.** §3.9's requirement is explicit and §2.9's freeze exists to prevent *regression*,
not to prevent a named, specified addition. So the contract is defined here, once, for both
transaction clients:

```
/_/api/x?slug=<d-trans|m-trans>[&month=YYYY-MM][&sub=<sub_category_id>][&filter=uncategorised]
```

- **Every parameter is optional, and an unrecognised or malformed one is ignored silently** — the
  page must never fail to render because of a query string.
- **`month`** — if it matches `^\d{4}-(0[1-9]|1[0-2])$`, the month selector initialises to it
  **instead of** `bxDefaultMonth()`. Otherwise `bxDefaultMonth()` stands. §0 ruling 1 is unchanged:
  it remains the default, and this is an explicit override, not a second definition.
- **`sub`** — if it names a sub-category present in the payload, the list is filtered to that
  sub-category and the active filter is **visible and clearable**. An unknown id is ignored.
- **`filter=uncategorised`** — opens the triage inbox / uncategorised filter.
- **No additional network request.** The page still makes exactly one bootstrap fetch; the
  parameters only choose the initial view of a payload it was going to fetch anyway, so AC-13.1
  is unaffected.

**This is a behaviour addition to `d-trans` and `m-trans` beyond §3.11's carry-fixes**, and it is
declared here for that reason. Spec_03's AC-6, AC-8 and AC-14 are re-run against the re-cut builds
per AC-10.7 and must still pass **with no parameters present**, which is the state they were
written against.

### Addenda 11–15 — 2026-08-21 (Orchestrator, on findings from Builder S) — five more ruled

**Addendum 11 — `roll_over_date` is accepted as `YYYY-MM` *or* `YYYY-MM-DD`, and always serialised
as `YYYY-MM-DD`.** §3.2's `/subcat/create` and `/subcat/update` contract the input as
`"YYYY-MM|null"`; §4.2 serialises the output as `"YYYY-MM-DD|null"`. As written, **a client that
reads a sub-category and writes it straight back would be rejected by its own payload** — a
round-trip the UI performs on every roll-over edit. Both forms are therefore accepted on input; a
bare `YYYY-MM` stores the **first of that month**, which is what the legacy column already holds
everywhere. Output is unchanged: always `YYYY-MM-DD`.

**Addendum 12 — `excluded.transfers` counts SUB-CATEGORY rows, and on this app it is structurally
always `0`.** §4.4 gives `excluded` three counters and states the unit for only one of them
(`archived_sub_categories`). `transfers` counts the same unit as its siblings — sub-category rows
dropped from the roll-ups. **The consequence must be stated rather than discovered:** §3.1
measurement 3 established that the sentinel is a `categories` row with **no** `sub_categories`
children, so no sub-category is ever excluded as a transfer and the counter reads `0` for ever —
while **12 live transactions really are being dropped** from every `spent` figure and are not
represented anywhere in `excluded`. §4.4's key-set is pinned by AC-5.12 and may not gain a key
this round, so this is recorded as a **known gap in the instrument, not a defect in the
arithmetic**. Round 05 should add a transaction-level counter when it is free to extend the shape.

**Addendum 13 — "a month with no data" means no budget row AND no active, non-transfer
transaction.** §3.2 and AC-5.12 require such a month to return `200` with zero-filled totals,
**empty arrays**, and a full thirteen-field `available`. The predicate was unstated. It is: the
month holds neither a `budgets` row nor an active transaction that survives transfer exclusion.
A month holding transactions but no budget rows is **not** empty and lists every row — which is
the §4.5A rule 3 state §5 deliberately includes. *(The orchestrator's independent Python had this
wrong and was corrected to the spec text, not to Builder S's code.)*

**Addendum 14 — `/budget/notes` refuses a duplicate `(belongs_to, period)` pair, exactly as
`/budget/amount` does.** §3.2 gives the duplicate guard only to `/budget/amount`. Writing to one
of two duplicate rows is the same hazard whichever column is being written, and picking one is
precisely what the legacy does (fact 3). Both endpoints return
`400 {"error": "bad_request", "detail": "duplicate budget rows for that sub-category and month"}`
and write nothing.

**Addendum 15 — the transfer sentinel cannot be archived or restored.** No criterion touches it
and §3.2 does not mention it, but `/cat/restore` on `ec8e0085-…` would hand the Forms app a live
spending category called `Transfer`, with a real `order`, on Bruce's own budget screen. Both
operations return `400`. Recorded because it is a guard the spec did not ask for.

**Also settled, without needing an addendum:** §4.5's branches are listed A, B, C, D, and an income
sub-category with `roll_over: false` satisfies both A and C. **C wins** — §4.5's own rationale says
the closing rule is defined for negative expense figures only, and AC-5.7 wants `supported: false`
unconditionally. Builder C, Builder S and the orchestrator's Python all read it that way
independently.

**Addendum 10 — on a duplicate `(belongs_to, period)` pair, every READ takes the smallest cents
value, deterministically.** `POST /budget/amount` refuses to write against a duplicate outright
(§3.2), but §4.5's arithmetic has no rule and `/budget/summary`, `GET /build/budget-audit` and
`bx_calc.js` must all still answer. All three take the **smallest** value — arbitrary, but
deterministic, so two runs and three instruments agree — and never repair. §3.1 measurement 5
found **zero** duplicates live, so this is a guard rather than a live path.
