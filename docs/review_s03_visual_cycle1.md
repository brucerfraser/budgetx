# Round 03 — visual review, cycle 1

**Reviewer:** `visual-reviewer`, model **Fable** (claude-fable-5), fresh read-only context.
**Commit reviewed:** `02b36ea`, five slugs live at 1.2.0.
**Scope:** AC-6, AC-7.3–7.8, AC-8, AC-9, AC-13.1–13.4, AC-14.
**Verdict: 26 PASS / 2 FAIL of 28 judged sub-criteria.**

Driven headless as TEST2 against the published URL, both widths, on the populated month
**2025-12 (273 rows)** — the reviewer was warned the server's current month is empty and that
judging it would make every criterion pass vacuously.

## FAIL — AC-8.5

**`m-trans`'s edit sheet silently destroys the transfer categorisation of any transfer row.**

The m-trans category `<select>` carries **58** options and **does not contain the transfer
sentinel** `ec8e0085-…` at all; `d-trans`'s rail select carries **59** and shows "Transfer"
selected correctly. So on a transfer row the sheet renders the select as empty, and **Save writes
`category: null`**, destroying a real row's transfer flag. Proven on
`0403433b-ee8c-4fd4-bda1-2bdc89a06fd1` ("MY WIFE", −R10,000) by an independent fetch diffed
against the round-start snapshot; the row was restored by the reviewer.

Same root cause, visible symptom: the m-trans category pill on a transfer row renders the **raw
UUID** as its label.

**Orchestrator's own confirmation of the root cause:** the sentinel is **not** a member of
`sub_categories` (57 rows, sentinel absent), it is published separately as the payload's
`transfer_category_id` key, and **12 live transactions carry it**. Neither client hardcodes the
value; `d-trans` resolves it from that payload key and `m-trans` does not.

The amount-edit mechanics AC-8.5 also asks about all worked: card `data-cents` and the running
total updated at ~150 ms, exactly one `/txn/update`, zero refetches, value confirmed server-side.

## FAIL — AC-14.4

**`d-trans`'s detail rail computes `border-radius: 0px`.** The criterion names "cards, the detail
rail and the sheet" at ≥12 px with a non-`none` shadow. The shadow is present
(`rgba(0,0,0,0.35) 0 2px 12px`) and every other surface passes — m-trans card 18 px, edit sheet
`18px 18px 0 0`, desktop confirm modal 18 px, triage rail card 18 px — but the rail itself, and
none of its children, carries a radius. A full-height flush panel may be a deliberate design
call; the reviewer correctly declined to waive a criterion on that basis.

## PASS — the other 26

AC-6.1–6.8 · AC-7.3–7.8 · AC-8.1–8.4, 8.6, 8.7 · AC-9.1–9.6 · AC-13.1–13.4 · AC-14.1–14.3,
14.5–14.7.

Highlights worth keeping:

- **AC-6.1** 273 rendered `data-txn-row` ids exactly equal the independent payload id set, diff 0.
- **AC-6.5** all five sort heads verified against independent Python sorts of the same data.
- **AC-7.7** 288 interactive controls enumerated across five pages × two widths, including with
  the rail and the edit sheet open; smallest anywhere **44 px**.
- **AC-7.5** `--error` measured at **6.018:1** on `--surface-1` (the old value computes 3.558).
- **AC-8.2** the scroller the screen exists to fix: scrollTop moved on all 10 driven steps to
  30679 (`scrollHeight 31351 > clientHeight 672`), last card bottom 736 clearing the bottom bar
  at 772 — and at 390×600 and 390×500 too.
- **AC-9.5** the Forms app renders this round's write as `R123.45` with its Aug-2026 Inflow
  agreeing, changed by exactly this round's row and nothing else.
- **AC-9.6** with `active=False` written via the API, the Forms app **still** displayed the row —
  proving it is genuinely unaffected by the new column.
- **AC-13.3** `responseEnd` → first painted row: **40 ms** (d-trans) / **31 ms** (m-trans).
- **AC-13.2** three driven swipe-accepts produced **exactly one** `/txn/categorise` with three
  items, fired only on deck close.
- **AC-14.7** with the write route held 2 s then failed, the UI updated at ~307 ms and then
  **rolled back**, with a toast naming what did not save.

## Reviewer honesty worth recording

Three apparent failures were correctly identified as the reviewer's own instrument rather than
defects, and re-run: clicks missing the `[data-sort]` target, a `time.sleep` blocking the
Playwright dispatcher, and an Undo whose 10-second window expired behind a slow fetch.

## Rows the reviewer wrote

Four transactions, every one restored and verified. Final reconciliation by the reviewer: fresh
`?include=transactions` vs its own round-start snapshot — 1301/1301 ids, **zero rows differing on
any field**, `sum(amount_cents)` identical. No structural row touched, no hard delete.
