# Round 03 — visual review, cycle 3 (final visual cycle; the spec allows three)

**Reviewer:** `visual-reviewer`, model **Fable**, fresh read-only context.
**Build reviewed:** all five slugs at **v1.2.2**, served bytes confirmed against `/build/list`.
**Verdict: 37 PASS / 1 FAIL of 38.**

Both earlier repairs re-proven on this build: **AC-7.7 PASS** (DATE now 44×44 in all ten sort
states) and **AC-8.5 PASS** (sentinel present exactly once and selected; unmodified Save sends no
request at all; an amount-only change sends a body with `category` absent entirely and the
independent re-fetch shows the category intact). The `setMonth` triage repair was judged too:
3 accepts then a month change flushed **exactly one** `/txn/categorise` carrying exactly those 3
ids, a full payload diff showed no row outside the batch changed, and re-opening triage built a
queue holding only the new month with `data-remaining` equal to the header count.

## FAIL — AC-6.1 · the table overflowed its region and clipped every amount behind the rail

The id-set condition AC-6.1 literally states **passed** (273 DOM rows == the independent
bootstrap's December set). The reviewer failed it on the broader clause — the table did not render
December correctly — and was right to.

Measured at 1280×800 on live December (273 rows), and confirmed independently by the orchestrator:

| | before | after |
|---|---|---|
| scroller `clientWidth` / `scrollWidth` | 640 / **707** | 640 / **640** |
| horizontal overflow | **67 px** | **0** |
| amount cells past the rail's left edge | **all of them** (right edge 923 vs rail 900) | **0** (worst 856 vs rail 900) |
| amounts truncated | `(R10,000.00)` showing ~52 px of 75; `R92.66` as `R9…`; header as `AMOU` | **0** |
| dates wrapping to two lines | yes | no |

**Truncated money is wrong money on screen**, on the app's most-used screen at its primary desktop
width. Root cause: `.bx-table` had no `table-layout`, so `auto` sized columns to the widest
content and one long description pushed the table under the fixed 380 px rail. The declared
`.bx-col-*` widths were only suggestions under `auto`, which is why DATE wrapped despite a width.

**Not a regression.** The same clipping is visible in this round's own cycle-1 evidence
(`scratch/s03/evidence/live_d-trans_2025-12.png`). It survived two full review cycles because
every earlier check measured **vertical** scroll only; nobody compared `scrollWidth` to
`clientWidth`.

**Repaired** with `table-layout: fixed` plus measured column widths — the amount column at 128 px,
sized from the rendered width of `(R1,234,567.89)` (90.4 px in Eczar, 98.3 px for a ten-million
value), with description as the only flexible column, ellipsised and carrying the full text in
`title`. Table width is now independent of content and row count, which is the structural reason
a denser month cannot reproduce it. Stress-tested at 300 rows × 384-character descriptions:
`scrollWidth == clientWidth` at all three widths.

A second defect in the same cells was found and fixed while looking at the result: the category
pill was hard-clipping **mid-glyph through its own rounded cap**, because `.bx-pill` is
`display: inline-flex` and `text-overflow: ellipsis` does not apply to a flex container's
anonymous text item. Fixed inside this table's category cell only; the canon pill, the triage
chip and `m-trans` are untouched.

**Verified on live December after the repair**, at 1280×800, 1440×900 and 1920×1080: overflow
**0**, amounts past the rail **0**, amounts truncated **0** at every width.
`d-trans` promoted at **v1.2.3**.

## ⚠ The status of that repair

**The three-cycle visual limit is now exhausted**, and this fix landed *after* cycle 3. It is
therefore **not covered by the visual gate**. It was verified by the fixer and independently by
the orchestrator on live data at three widths, and it is put to the **spec reviewer**, which
judges AC-1…AC-14 in a fresh read-only context and covers AC-6. **It is not claimed as a
visual-gate PASS.**

## A question raised by the fixer, closed with existing evidence

The fixer reported that `m-trans` has "zero `<select>` elements" and that it could not open the
edit sheet. That is a **harness limitation, not a defect** — the sheet is built on demand, and
neither `row.click()` nor `locator.tap()` opens it, because the card binds `pointerdown` /
`pointerup`. A real pointer press/release does: the orchestrator's own drive returned
`{"sheet":"edit","selects":2,"n":19,"value":"ec8e0085…","label":"Transfer","sentinelOptions":1}`,
and cycle 3 passed AC-8.5 independently on a live transfer row. Two orchestrator scripts
(`verify_transfer_fix.py`, and the fixer's harness) carry the flawed interaction; the pages do not.

## The other 37

AC-6.2–6.8 · AC-7.3–7.8 · AC-8.1–8.7 · AC-9.1–9.6 · AC-13.1–13.4 · AC-14.1–14.7 — all PASS.
Notable: `responseEnd` → first painted row **12.7–20.3 ms** (d-trans) and **13.1–24.4 ms**
(m-trans); input → DOM mutation **0.3–3.5 ms**; zero native dialog events across every drive;
reduced motion resolving `0s` with the deck's fallback buttons driven and working.

## Rows written

Seven transactions, each listed with before → after and **every one restored**. Final
reconciliation at 22:22:01Z: 1,301 rows, id sets equal to round start, **zero rows differing on
any field**, `sum(amount_cents)` identical at −13,563,834.
