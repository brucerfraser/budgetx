# Round 03 — visual review, cycle 2 (full re-review)

**Reviewer:** `visual-reviewer`, model **Fable**, fresh read-only context.
**Build reviewed:** `d-trans` / `m-trans` at **1.2.1**; `x` / `d-dash` / `m-dash` byte-identical at
1.2.0. Served bytes confirmed against `/build/list` for all five before judging.
**Scope re-run in full from the first criterion**, not just the cycle-1 failures.

**Verdict: 37 PASS / 1 FAIL of 38 judged sub-criteria.**

## Both cycle-1 FAILs re-proven fixed

- **AC-8.5 PASS.** On the live transfer row `0403433b`: the pill renders **"Transfer"**, the
  category select contains the sentinel **exactly once** and shows it **selected**; saving an
  unmodified transfer row sent **no write at all**, and an independent re-fetch showed the category
  still the sentinel; changing only the amount sent a body with **`category` absent entirely**, and
  the re-fetch showed the amount changed and the category intact. A normal row still saves its
  chosen category, and an explicit "Uncategorised" still writes `null`. The amount-edit half also
  holds — one `/txn/update`, zero refetch, running total moved by exactly one cent.
- **AC-14.4 PASS.** `#rail` computes `border-radius: 18px 0px 0px 18px` with a non-`none` shadow;
  cards 18 px, mobile sheet `18px 18px 0 0`, desktop confirm modal 18 px.

## FAIL — AC-7.7

**`.bx-sort-btn[data-sort="date"]` measures 40×44 px whenever another column is the active sort.**
The sort-arrow glyph leaves the button, and the rule has `min-height: 44px` but **no `min-width`**,
so the shortest label collapses below the 44 px floor. Default state measures 53×44, which is why
every earlier enumeration — including cycle 1's, which measured 288 controls — missed it: the
control only breaches the rule **after a state change**.

Reproduced in two independent reviewer sessions, and confirmed independently by the orchestrator:
DATE 53×44 → **40×44** after clicking the Amount head; every other control on all five pages at
both widths remains ≥44 px. `.bx-sort-btn` lives in the **canon** (`client_src/bx_core.css:514`).

## The other 37

AC-6.1–6.8 · AC-7.3–7.6, 7.8 · AC-8.1–8.7 · AC-9.1–9.6 · AC-13.1–13.4 · AC-14.1–14.7.

Worth keeping:

- **AC-13.1** exactly one bootstrap per page open; month stepping ×8, search, filter, all five
  sorts, scroll, rail and sheet — **zero** further requests.
- **AC-13.3** `responseEnd` → first painted row **53.7 ms** (1280) / **29.7 ms** (390).
- **AC-13.4** input → DOM mutation between **0.9 ms and 8.9 ms** across both clients.
- **AC-9.5** Forms August 2026 totals read Inflow R123.45 / Outflow R0.00 — exactly this round's
  one written row; December Forms totals equal the raw payload sums **to the cent**.
- **AC-9.6** an archived row still renders in the Forms app — proving it is genuinely unaffected
  by `active`.
- **AC-14.1** rAF sampling captured **18 distinct** animation states at 1280 and 17 at 390.
- **AC-14.7** the row updated at **0.33 s** with the write still held, then rolled back on failure
  with a toast naming it.
- **AC-8.7** long-press → `bxConfirm` → archive → independent fetch showed payload **1,300**;
  Undo → independent fetch showed **1,301**.

## Reviewer honesty

Five of its own instrument errors were caught and re-driven **before** any verdict was written: a
blocking sync route handler, a zero-hit search term that would have passed AC-6.3 vacuously,
trimmed/stale sort keys reading as "UNSORTED", measuring a confirm-sheet child instead of the
sheet, and a right-swipe on a card that had no suggestion. It also correctly declined to treat
"right-swipe does nothing without a suggestion" as a defect — that is §3.6's specified behaviour.

## Rows written

Seven transactions, each listed with before → after and **every one restored**. Round-end
reconciliation by the reviewer: 1,301 ids identical to its round-start snapshot, **zero rows
differing on any field**, `sum(amount_cents)` identical. No structural row touched, no hard
delete, nothing promoted.
