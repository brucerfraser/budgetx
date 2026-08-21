# Budget X — Session 04 debrief

**STATUS:** AWAITING-BRUCE

**Round:** 04 · **Spec:** `docs/specs/spec_04.md` (approved and locked 2026-08-21) ·
**Started:** 2026-08-21 · **This entry written:** 2026-08-21 UTC

---

## AWAITING BRUCE

**One click in the Anvil editor, please.**

The DATA tab is showing a ⚠ beside `Default Database`. Open it and click **RED / LEFT — *the
source code is correct*** — which migrates the database to match what I pushed: two new `bool`
columns, **`active` on `categories`** and **`active` on `sub_categories`**.

**Please do not set a value on any row** — I set them all myself in the next step, which is the
whole lesson of round 03. Then say done.

Nothing else is needed from you this round. Everything after the click runs unattended.

---

## Where the round is

Commits 1a and 1b are pushed and live. Building continues while the click is outstanding —
nothing that reads the new columns will be pushed or promoted until the initialisation and its
reconciliation are on record (§3.7 steps 4–6).

| Step | State |
|---|---|
| AC-9.1 Forms baseline, before the first push | **done** — 1280×800 and 390×844, all five screens, `/build/counts` identical either side |
| §3.1 round-start measurements | **done** — all twelve, `scratch/s04/measurements.json` |
| §3.7 step 1 pre-schema snapshot | **done** — `scratch/s04/snapshot_pre_schema.json` |
| Commit 1a — `ServerBuildTools` v4 (the two migration tools) | **pushed, live, `/build/version` reports v4** |
| Commit 1b — the two-column `anvil.yaml` edit | **pushed** |
| **Bruce's approve-click** | **← waiting here** |
| `POST /build/init-active` + reconciliation | blocked on the click |
| `ServerAppData` v3, `ServerBudget`, seven clients | blocked on the reconciliation |

---

## The round-start measurement that changed a decision

**No live month holds 20 budget rows.** §7 trap 11 and AC-5.4 asked the reviewers to drive three
months of ≥20 budget rows and ≥40 transactions. `budgets` holds **58 rows in total**, across 57
sub-categories and nine months — the table is sparse, not fully budgeted as the spec assumed.

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

Recorded as **spec Addendum 3**. The threshold existed to stop a vacuous month passing a money
criterion, and that intent is served by density rather than by the number 20, so it is restated as
**≥10 budget rows and ≥40 non-transfer transactions**. The three drive months are **2025-11,
2025-12 and 2026-01**, with **2025-12 primary** — measurement 12 shows it is the **only** live
month carrying an overspend (1,101,913 cents over two sub-categories), which makes 2026-01 a month
with a genuinely non-zero `carried_overspend` and puts AC-6.12's chip on Bruce's own data.

**The other nine measurements came back clean**, and several retire a hazard the spec had budgeted
for (**Addendum 4**): zero duplicate `(belongs_to, period)` pairs, zero non-integral
`budget_amount` values, zero `roll_over`-without-date rows, zero orphans, zero sign anomalies, and
exactly one category named `Income` with no near-misses — which is what proves the widening from
the legacy case-sensitive test to a case-insensitive one is safe.

**The transfer sentinel `ec8e0085-…` is a `categories` row**, named `Transfer`, carrying
`order == -1`, with **no** `sub_categories` row and 12 transactions pointing at it. So it is
already excluded from `/cat/reorder`'s non-archived set, and the exclusion has to happen on the
transaction side — exactly the case §3.3 made `transferCategoryId` an argument for.

---

## Corrections to the spec so far — four addenda, all in `docs/specs/spec_04.md` §12

1. **§3.7's commit 1 is split into 1a and 1b.** Step 1 requires the snapshot to be taken through
   `GET /build/budget-audit` "before any push", and step 2 only ships that endpoint in commit 1 —
   the sequence as written cannot be executed. Commit 1a carries the tools alone, the snapshot and
   measurements are taken, then commit 1b carries the `anvil.yaml` edit **with no Python at all**.
   Step 2's guarantee is made stricter, not weaker.
2. **AC-4.4 and AC-4.5 cannot both be judged against `set_false_ids`.** Bruce's click writes a real
   `False` into every existing row (spec_03 Addendum 6), so the archived rows already hold the
   correct value and come back **unchanged** on the first `init-active` call, leaving
   `set_false_ids` empty — the criterion would FAIL against a correct implementation.
   `POST /build/init-active` therefore returns two partitions: what it **wrote**
   (`set_*`/`unchanged_ids`) and what each row now **is** (`derived_*`). AC-4.4 is judged against
   `derived_false_ids`, AC-4.5's idempotence against `set_*`.
3. **The drive-month threshold and the three named months**, above.
4. **The nine clean measurements and what they settle**, above.

---

## Anvil editor actions

**None.** No action has been taken inside the Anvil editor this round. The migrate click is
Bruce's, deliberately.

---

## Data touched so far

**Nothing written.** `/build/counts` is identical to the round-start reading on every table:
`accounts 9 · budgets 58 · categories 14 · files 8 · settings 1 · sub_categories 57 ·
test_csv 5 · transactions 1305 · users 3`.

The AC-9.1 Forms-app baseline drive wrote **no** budget rows — `/build/counts` was taken
immediately before and after it and is byte-identical. Fact 1's month-copy did not fire, because
the server's current month (2026-08) has no predecessor month holding budget rows to copy from.
Recorded here because §7 trap 12 expects a delta and the absence of one is itself the evidence.

---

## Gates

- `git config core.hooksPath` = `tools/githooks` ✓, `python3 tools/repo_guard.py` exit **0** ✓ —
  both verified **before the round's first working commit** (`scratch/s04/gate/ac10_3_pre_first_commit.txt`).
  Both are re-checked **after** the schema click, per §3.7 step 7.
- `python3 -m pyflakes server_code/ServerBuildTools.py` — clean, empty output.
- Read-only AST walk of `api_build_budget_audit` and all 33 functions reachable from it (the
  `api_http` decorator chain included) — **0 violations**.
- `node` v26.7.0; the v1 `bx_calc.js` golden suite runs **85/85 green** at round start.

## Models

| Role | Model |
|---|---|
| Orchestrator | Opus |
| Builder S (server) | Opus |
| Builder C (calc) | Opus |
| Builders D and M (clients) | Sonnet — per the migration-phase exception |
| `fixer` | Opus |
| `spec-reviewer` | Opus |
| `visual-reviewer` | Fable |

*(Recorded against the migration-phase exception, CLAUDE.md. Final assignments confirmed in the
FINAL debrief.)*
