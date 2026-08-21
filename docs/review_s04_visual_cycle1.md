# Round 04 — visual review, cycle 1

**Reviewer:** independent visual reviewer (fresh context, read-only).
**Commit under review:** `884942a` on `master`. **Build confirmed live before judging:** all seven
slugs at **1.3.0**, `current=True` in `/build/list`, and the served bytes of all seven are
**sha256-identical** to `scratch/s04/clients/*.html` at that commit. Nothing stale was reviewed.

**Verdict: 50 PASS / 7 FAIL over 57 sub-conditions.**

**Driven as TEST2** (`bruce.fraserb+bxtest2@gmail.com`), through the real login page at
`?slug=x`, headless Chromium, at **1280×800** and **390×844**. Bruce's own login was never used
and `claude-in-chrome` was never used. Every screenshot is outside the repo, under
`/private/tmp/claude-501/-Users-brucefraser-BudgetX/21163a37-069e-4130-90e4-7812007f3083/scratchpad/vr/shots/`
(78 files). Working scripts are alongside them in `.../scratchpad/vr/`.

**Months driven:** AC-5.4 on **2025-11, 2025-12 and 2026-01**; AC-6, AC-8, AC-13, AC-14 on
**2025-12**; AC-6.12 / AC-8.10 on **2026-01** (predecessor 2025-12); the absent-chip case on
**2027-07**; AC-6.9's open-month case on **2026-03**; AC-5.8 / AC-6.1 on the app's own opening
month, **2026-02**.

---

## The three findings that matter most

### 1. SEVERE — `m-budget` at 390 px shows no category names, and clips every meter

At **360, 390 and 430 px**, every category card's `.bx-cat-card__name` computes to **width 0**
(`flex: 1 1 0%`, `min-width: 0`, `overflow: hidden`, `white-space: nowrap`), while the figures
block is `flex: 0 0 auto`. The card header's `scrollWidth` is **417 px** inside a **358 px**
`clientWidth`. Consequence, measured and photographed:

- Seven visible cards are identified **only by a one-letter swatch** — `I`, `L`, `S`, `S`, `S`,
  `G`, `H`. Sport, School and Saving are all "S". A user cannot tell which category any row is.
- The `[data-meter]` element's right edge is at **412–438 px** against a card right edge of
  **344–414 px**; `body { overflow-x: hidden }` then cuts it off, so part of every progress meter
  is unreachable at any phone width.

`.../shots/m-budget_2025-12_top.png` · `.../shots/m-budget_2025-12_390_dark.png`

390 px is this app's primary viewport and this is its main screen. No single sub-condition in my
mandate names "the category name is legible", so it is carried below as evidence under AC-7.5,
but it is reported first because it is the worst thing on the screen.

### 2. `d-budget`'s roll-over toggle is 22.4 px tall — the 44 px floor is explicitly overridden

`#railSubRollover`'s wrapping `<label class="bx-toggle" style="min-height:auto;">` measures
**85.5 × 22.4 px** at 1280, and the `<input type="checkbox">` inside it is **13 × 13 px**. The
inline `style="min-height:auto;"` is an explicit override of the canon's 44 px floor. On
`m-budget` the equivalent label is 82 × **44** px (so the effective target is fine there), but its
checkbox is also 13 × 13. AC-7.7 FAIL. `.../shots/d-budget_rail_2025-12.png`

### 3. An income shortfall is shown as ordinary progress, not as a consequence (§0 ruling 6)

In **2025-12**, `ZZ S04 Income Sub` earned R600 against a R1,000 budget. On both clients the row
renders: meter `data-state="under"`, `data-fraction="0.6000"`, **fill colour `rgb(30,185,128)`
(`--primary`, green)**, and its three figures all in `rgb(225,227,223)` (`--on-surface`). Nothing
is in `--negative` `rgb(184,124,76)`; no shortfall amount is named as a shortfall. Compare the
overspent expense row `ZZ S04 Sub A` in the same month: meter fill `rgb(184,124,76)`.
`Salary Esther 🎻`, R25,000 short, renders as a green bar at 0 %.

§0 ruling 6 requires the shortfall to "read as consequential rather than merely incomplete", and
AC-6.12 requires it "in `--negative` with the amount named, at the same visual weight as an
overspent expense category". It does not. AC-6.12 FAIL.
`.../shots/d-budget_2025-12_income_shortfall.png` · `.../shots/m-budget_2025-12_income_shortfall.png`

---

## Verdicts — one line per sub-condition (FAILs first)

### FAIL

- **AC-6.12: FAIL** — month driven **2026-01**. Eight of its nine bullets hold (below); the
  income-shortfall bullet does not. An income sub-category that fell short in **2025-12** renders
  its meter in `--primary` `rgb(30,185,128)` with `data-state="under"` and its figures in
  `--on-surface` `rgb(225,227,223)`; no element on the row computes to `--negative`
  `rgb(184,124,76)` and no shortfall amount is labelled as one — against an overspent expense row
  in the same month whose meter fill is `rgb(184,124,76)`. Computed colours asserted, not
  inspected. `.../shots/d-budget_2025-12_income_shortfall.png`
- **AC-7.5: FAIL** — `[data-cat-row]`'s own computed `background-color` is
  **`rgba(0, 0, 0, 0)`** on both clients, not the row's `colour_back`; the data colours live on a
  child `.bx-cat-card__swatch`. On `m-budget` the row's name colour is `rgb(225,227,223)`
  (`--on-surface`), not `colour_text`, and the name element is **0 px wide** (finding 1), so no
  `colour_text` is visible at all at 390 px. What *is* right: for all 15 categories on both
  clients the swatch's computed background equals `colour_back` and its colour equals
  `colour_text` **exactly, zero mismatches**. Contrast measured on all 15 pairs by the WCAG
  relative-luminance formula: one pair is below 4.5:1 — **`Holidays ✈️`, `#4e7a27` on `#333333`,
  2.49:1** — recorded as a **data** finding for Bruce, not a build failure, as the criterion
  directs. `.../shots/d-budget_1280x800_dark.png` · `.../shots/m-budget_2025-12_top.png`
- **AC-7.7: FAIL** — see finding 2. Full enumeration with skip accounting: 14 page/width
  combinations, `a[href],button,input,select,textarea,[role=button],[tabindex]` swept, then swept
  again with the rail, sheets, archived list, inline editors, focus mode and the chip sheet
  **opened** so nothing passed by not being found (51 distinct visible controls on `d-budget`, 46
  on `m-budget`, 32 on `d-trans`, 21 on `m-trans`). Skips: `d-trans@390` 39 and `d-budget@390` 65,
  every one of them the desktop tree suppressed behind the §3.11 fix-6 phone notice (correct
  behaviour, explicitly skipped, not measured-and-failed), leaving exactly one visible control
  each — the link to the `m-*` twin at 180.4 × 47 px. Every other measured control is ≥44 px in
  its smaller dimension (smallest passing: 44.0 px chevrons, 44.0 px sign-out, 56 × 48 bottom-bar
  targets). The **only** failures are the roll-over toggle label at **22.4 px** on `d-budget` and
  its 13 × 13 checkbox on both clients.
- **AC-7.9: FAIL** — the `x` client carries **three** `.bx-skeleton-row` placeholders (inside
  `#loadingState`) and **none of them has `data-skeleton`**, confirmed both in the served bytes
  and in the live DOM at 1280 and 390. The other six clients are clean: every `.bx-skeleton-row`
  carries the attribute (`d-dash` 4, `m-dash` 4, `d-trans` 6, `m-trans` 6, `d-budget` 6,
  `m-budget` 5), asserted **while the bootstrap route was throttled to 6 s** so the skeletons were
  actually on screen. The only other attribute-less elements are the outer wrappers
  (`bx-skeleton-wrap`, `bx-tr-skeleton`, `bx-bg-skeleton`), which are containers, not
  placeholders. `.../shots/x_skeleton.png` · `.../shots/d-budget_skeleton.png`
- **AC-14.1: FAIL** — month 2025-12, both widths. Category rows do **not** stagger in and meters
  do **not** animate from zero. At first paint every `[data-cat-row]` computes
  `animation: none`, `animation-duration: 0s`, `animation-delay: 0s`, and its class list is
  `bx-cat-card` (`m-budget`: `bx-cat-card bx-card--interactive`) — the canon's `.bx-enter` /
  `.bx-row-enter` classes exist in the embedded CSS of all seven clients but are **never applied
  by any client's JS** (searched the extracted inline JS; every occurrence is inside the CSS
  block). rAF sampling of the rendered values over **141 frames spanning 1.80 s from the moment
  the rows exist**, frame gaps 1.9–27 ms, yields **exactly one distinct value** for card opacity,
  card transform and meter fill width on both clients. The meter fill does declare
  `transition: width 0.2s cubic-bezier(...)`, but on load it is painted at its final width in one
  step. *(Motion is not absent from the app: `bx-fade-rise` plays on focus-mode entry,
  `bx-sheet-rise`/`bx-fade-in` on sheet open, `bx-shimmer` while loading — verified via
  `document.getAnimations()`. It is the two behaviours this criterion names that do not happen.)*
- **AC-14.4: FAIL** — computed styles: category card `border-radius 18px` + `box-shadow
  rgba(0,0,0,.35) 0 2px 12px` ✓; sheet `18px` / `18px 18px 0 0` + `rgba(0,0,0,.45) 0 8px 30px` ✓;
  **`d-budget`'s detail rail `#rail` `border-radius: 0px`** (shadow present); **`m-budget`'s
  focus-mode container `border-radius: 0px` and `box-shadow: none`**. Two of the four named
  surfaces miss the ≥12 px radius and one misses the shadow.
- **AC-5.7 (live half): FAIL** — `/budget/summary` is right: `ZZ S04 Income Sub` returns
  `supported: false`, `carried_in: 0` in 2025-12 and 2026-01. **The rendered rail never shows it.**
  With the income sub selected, `#railSubRolloverBreakdown` is `hidden` and its `[data-rollover]`
  element carries **none** of the nine `data-*` fields — only `class` and the bare
  `data-rollover`. I then drove the rail's own roll-over toggle on that sub-category (a `ZZ` row,
  restored afterwards) so `roll_over: true, roll_over_date: 2025-01-01`: the breakdown stayed
  hidden and still carried no attributes, while the row gained a `↻` badge and an
  "Avail R1,000.00" figure — i.e. the UI offers roll-over on income and then declines to say it is
  unsupported. The criterion's "and in the rendered rail" cannot be observed.
  `.../shots/d-budget_income_sub_rail.png` · `.../shots/d-budget_income_rollover_on.png`

### PASS

- **AC-5.4: PASS** — months **2025-11, 2025-12, 2026-01**, at both widths. Three legs, exact
  integer equality, no tolerance: rendered `data-cents` = `GET /budget/summary` = **my own**
  Python recomputation, written in this context from §4.4/§4.5/§4.5A/§4.6 alone
  (`.../vr_recompute.py`, ~230 lines; I did **not** lean on `scratch/s04/recompute.py`). Per
  month: the **6** header cells, **15** category rows (budget/actual/variance) and **60**
  sub-category rows (budget/actual) on `d-budget@1280` with every category expanded, and the same
  60 on `m-budget@390` collected by entering focus mode on all 15 categories. Rollover figures
  (`data-source="rollover"`) checked separately against `rollover.available`. **Zero mismatches
  on 1,206 compared values.** My Python independently agrees with `/budget/summary` field-for-field
  on every one of 62 sub-categories × (5 scalars + 9 rollover + 6 progress) and 15 categories for
  2025-11, 2025-12, 2026-01 **and** 2026-02. Sample figures read on 2025-12: income budget
  `R166,000.00` / actual `R280,659.13` / variance `R114,659.13`; expense budget `(R25,000.00)` /
  actual `(R148,855.35)` / variance `(R123,855.35)`. `.../shots/d-budget_2025-12_1280_dark.png`
- **AC-5.8 (live half): PASS** — both budget screens open on **2026-02**, which is exactly what my
  independent computation of "most recent calendar month at or before `server_date` 2026-08-21
  holding ≥1 active non-transfer transaction" returns from the payload. Addendum 17's archive of
  the 2026-08 probe is live and effective: 2026-08 holds no active transaction.
- **AC-5.9: PASS** — `bootstrap_no_income.json` served through `page.route` to both clients.
  `bxIncomeCategoryId([...])` returns **`null`**; `bxSignFor` returns `-500, -500, -500, 0` for
  income-less input (every category an expense, `0 → 0`); both clients render with **zero console
  errors and zero page errors** and a non-empty category list of **6** rows (the archived
  `ZZ Fixture Archived Cat` correctly hidden). `.../shots/d-budget_no_income.png` ·
  `.../shots/m-budget_no_income.png`
- **AC-5.10 (live half): PASS** — month **2026-01**, predecessor 2025-12. `carried_overspend` =
  **1,491,913** in `/budget/summary` and in my independent Python, over four sub-categories
  (`ZZ S04 Sub A` 300,000 · `ZZ S04 Sub D` 90,000 · `Apps and Subs` 103,506 · `Groceries`
  998,407). `starting_available` 12,059,888 = `income_planned` 16,500,000 − `carried_total`
  4,440,112, so the overspend is deducted in full, once. *(Note: the criterion says "lower than
  `income_planned` by exactly that amount", meaning the overspend alone; the live month also
  carries a 2,948,199 shortfall, so the true deduction is `carried_total` — exactly §4.5A's
  definition. Recorded as spec wording that needs an addendum, not as a defect.)* The overspend
  reaches **no** per-category or per-sub-category figure: every `categories[].budget_cents` equals
  my Python sum of that month's own rows, and every `data-budget`, `data-actual`, `data-variance`
  and `data-meter` matched my recomputation from 2026-01's rows alone (zero mismatches, 15
  categories). `ZZ S04 Cat`, which overspent 4.1× in 2025-12, carries **no** `over` meter state in
  2026-01 — it starts clean.
- **AC-5.11 (no-income clause): PASS** — under `bootstrap_no_income.json`, **no `[data-available]`
  element exists** in either client and `#availableWrap` renders empty (0 bytes of inner HTML);
  no `[data-carried]` chip exists. The block is suppressed, not zeroed, on both clients. Header
  totals still render (`expense-budget -5,745,000`), which incidentally corroborates Addendum 6's
  archived-category exclusion.
- **AC-6.1: PASS** (2026-02) — `d-budget` and `m-budget` both open with
  `[data-month] data-value="2026-02"`, equal to my independent `bxDefaultMonth` from the payload.
- **AC-6.2: PASS** (driven 2026-01 → 2025-12; "This month" from 2026-02) — "This month" returns
  **2026-08**, the server's current month (`server_date` 2026-08-21). Stepping back one month
  changed `data-month` 2026-01 → 2025-12, changed all six header cells
  (`16500000,0,-16500000,-1690000,-6917232,-5227232` → `16600000,28065913,11465913,-2500000,-14885535,-12385535`)
  and changed every category row's figures, with the rendered id set unchanged; the new header
  equals `/budget/summary` for 2025-12. *(I re-ran this deliberately after a first attempt stepped
  2026-08 → 2026-07, where both months are empty and the check would have been vacuous.)*
- **AC-6.3: PASS** (2025-12) — the rendered `data-cat-row` set equals the active, non-transfer
  category set from an independent bootstrap fetch, compared programmatically (15 = 15). I
  archived `ZZ S04 Cat B` through the rail: one `POST /cat/archive`, the row leaves the list
  (`querySelector` → false), the toggle reads **"Archived (1)"**, and revealing it renders
  `<div class="bx-archived-cat-row" data-cat-row="3b481020…" data-active="false">` with a Restore
  button. Restoring from that affordance issued one `POST /cat/restore`, and an **independent**
  fetch confirms `active: true, order: 14` — its exact round-start state.
  `.../shots/d-budget_archived_revealed.png`
- **AC-6.4: PASS** (2025-12) — expanding `ZZ S04 Cat` renders exactly `ZZ S04 Sub A`,
  `ZZ S04 Sub B`, `ZZ S04 Sub D` in `order` 0,1,2, all `data-active="true"`; the archived
  `ZZ S04 Sub C` renders nowhere. Recomputed both ways: with Sub C the category would be
  budget −110,000 / actual −485,000; the rendered figures are **−90,000 / −460,000**, i.e. Sub C
  (budget −20,000, spend −25,000) contributes to no total. Fact 5 is not reproduced.
- **AC-6.5: PASS** (2025-12) — selecting `ZZ S04 Sub A` opened the rail with its values. Editing
  the budget to `123.45` and committing produced **exactly one** `POST /budget/amount` and no
  refetch; the row moved to `data-cents="-12345"` ("(R123.45)"), the category total −90,000 →
  −92,345, the header expense-budget −2,500,000 → −2,502,345 and the available block
  −2,400,000 → −2,402,345, all without a fetch. An **independent** bootstrap fetch returned
  `amount_cents: -12345`. Notes: `""` → `"ZZ vr note"` (one `POST /budget/notes`, independent
  fetch confirms), then **cleared** to `""` (one more request, independent fetch confirms `""` —
  fact 10 is not reproduced). Restored to −10,000.
- **AC-6.6: PASS** (2025-12) — turning roll-over on for `ZZ S04 Sub D` with no start month issued
  **zero** requests, an independent fetch shows the row untouched, and the UI said
  **"Pick a start month to turn on roll-over."** in `rgb(184,124,76)` (`--negative`). Selecting
  `November 2025` then issued **one** `POST /subcat/update` and an independent fetch returned
  `roll_over: true, roll_over_date: "2025-11-01"`. The rail's rollover breakdown for
  `ZZ S04 Sub B` matches `/budget/summary`'s `rollover` object **field for field, all nine**:
  `supported true · start_missing false · months 11 · carried_in -100000 · month_budget -50000 ·
  available -150000 · spent -30000 · remaining -120000 · overspent 0`. Sub D restored to
  `roll_over: false, roll_over_date: null`.
- **AC-6.7: PASS** (2025-12) — every category row's budget element carries
  `data-source="month"` (asserted over all 15). `ZZ S04 Cat`'s `data-budget data-cents="-90000"`
  = A(−10,000) + B(−50,000) + D(−30,000), the **month** budgets, while `ZZ S04 Sub B`'s
  `carried_in` is −100,000 and its rollover figure appears only on the sub-row as
  `data-source="rollover" data-cents="-150000"` and in no rollup.
- **AC-6.8: PASS** — moving `ZZ S04 Cat` up issued **exactly one** `POST /cat/reorder` (and no
  other request) whose body was the **whole non-archived set** of 14 ids in the desired sequence;
  after the read-back the rendered order equalled the stored order exactly. I then moved it back
  (one more call) and the stored sequence is **byte-identical to the round-start sequence**.
- **AC-6.9: PASS** (2026-03) — "Open this month" is offered only there, opens a
  `data-kind="confirm"` sheet reading *"Open 2026-03 — Copy 13 budget amount(s) from 2026-02 into
  2026-03? Notes are not copied."* and listing all 13 sub-categories. `/build/counts` `budgets`
  = **77 before, 77 while the confirmation was open, 77 after cancelling**, and zero
  `/budget/open-month` requests were issued. **My drive stopped at the confirmation and did not
  confirm.** `.../shots/d-budget_2026-03_openmonth_confirm.png`
- **AC-6.10: PASS** (2025-12) — `#scroller` (`[data-scroller]`) driven from `scrollTop 0`; it
  MOVED at every push and reached its maximum; the last category row went from `inview: false`
  (bottom 1110 px) to fully in view. The sidebar, `#headerGrid` and `#rail` bounding boxes are
  **identical objects before and after**. `.../shots/d-budget_2025-12_1280_scrolled.png`
- **AC-6.11: PASS** — BUDGET carries `bx-nav-item--current`; DASHBOARD (`?slug=d-dash`) and
  TRANSACTIONS (`?slug=d-trans`) are real anchors; REPORTS and SETTINGS are `<span>`s with
  `aria-disabled="true"` and force-clicking each via `element.click()` left `page.url` unchanged.
- **AC-7.3: PASS** — spec_03 §3.6's amended `:root` block is present **verbatim** (exact string
  match) in all seven served files, and all **19** custom properties were compared value-for-value
  with no duplicate or divergent declaration anywhere in any file.
- **AC-7.4: PASS** — `getComputedStyle(document.body).backgroundColor` is **`rgb(25, 28, 26)`** on
  all seven pages at both widths (14/14). `[data-primary]` **exists** on all seven (asserted
  before reading) and resolves to `background-color: rgb(30, 185, 128)` on all 14.
- **AC-7.6: PASS** — `fmtR` occurs **0** times in the served bytes of all seven pages, as a
  definition or a call site.
- **AC-7.8: PASS** — all seven carry exactly one Google-Fonts stylesheet link outside `<noscript>`,
  each with `media="print"` and `onload="this.media='all'"`, plus a `<noscript>` block containing
  the plain fallback link. Also on all seven: zero `<script src=`, zero `@import`, zero
  `url(http`, zero `<img src="http`.
- **AC-8.1: PASS** (2025-12) — at **390×844, 390×600 and 390×500** the `#topbar` and `#bottombar`
  bounding boxes are identical objects before and after a fully driven scroll.
- **AC-8.2: PASS** (2025-12) — `scrollHeight > clientHeight` asserted explicitly (1176 > 495 /
  251 / 151); `scrollTop` driven 0 → max in 150 px steps, MOVING at every step until saturation
  (681 / 925 / 1025); at the end the last card's bottom edge is **above** the bottom bar's top
  edge at all three heights (731.98 < 772, 487.98 < 528, 387.98 < 428). No tall-viewport capture
  was used as evidence.
- **AC-8.3: PASS** — bottom-bar targets measured: Archived 56×48, **Add 56×56 carrying
  `data-primary`**, Sort it 56×48, Menu 56×48. All ≥44×44.
- **AC-8.4: PASS** (2025-12) — expanded the grid, then collapsed it
  (`bx-header-collapsible--collapsed`, height 0, `aria-expanded="false"`, grid still 83.56 px
  tall), then forced a re-render by editing `ZZ S04 Sub A`'s budget through the sheet. The state
  after the re-render is **identical on all four measures**. Fact 23 is not reproduced.
  `.../shots/m-budget_header_collapsed_after_rerender.png`
- **AC-8.5: PASS** (2025-12) — tapping a card sets `data-focus="47c09e56-…"` and renders exactly
  `ZZ S04 Sub A`, `ZZ S04 Sub B`, `ZZ S04 Sub D` in `order`; the archived `ZZ S04 Sub C` renders
  nowhere (fact 19 not reproduced). All three exits leave it: the back affordance, a second tap on
  the card (its focus-mode title), and `page.go_back()`. Verified for all 15 categories across
  three months during the AC-5.4 sweep — 45 enter/exit cycles, zero failures.
  `.../shots/m-budget_focus_ZZ.png`
- **AC-8.6: PASS** (2025-12) — with the header expanded and `scrollTop` set to 300, 420 and 0 in
  turn, entering focus mode and leaving it by the back affordance, the device back gesture and a
  second tap **each restored `scrollTop` and `aria-expanded` exactly**. *(A first run reported a
  failure; that was my instrument — Playwright's `click()` scrolls the target into view first.
  Re-driven with `element.click()` dispatched in-page, it passes.)*
- **AC-8.7: PASS** (2025-12) — `ZZ S04 Cat` inside focus mode: budget −90,000, actual −460,000,
  variance −370,000, meter `over/1.0000/4.1111` — **identical** to outside. The **income**
  category likewise: 16,600,000 / 28,065,913 / 11,465,913, meter `over/1.0000/0.6907`, identical
  inside and out. Fact 25 is not reproduced. `.../shots/m-budget_focus_income.png`
- **AC-8.8: PASS** (2025-12, `ZZ S04 Sub A`) — typing then dismissing **commits on every path**,
  each confirmed by an independent bootstrap fetch: backdrop tap (real click at 195,166 on
  `.bx-sheet-backdrop`) → `-10100`; **Escape** → `-10200`; **device back** → `-10300`. With
  `**/budget/amount` failed 500, the value rolls back visibly to the pre-edit figure and a toast
  reads **"Budget amount did not save"**; the server value is unchanged. Fact 18 is not
  reproduced. `.../shots/m-budget_write_failure_toast.png`
- **AC-8.9: PASS** — archiving `ZZ S04 Sub D` went through a `data-kind="confirm"` sheet
  (*"Archive ZZ S04 Sub D? Its budget rows and transactions are left exactly as they are…"*), **no
  native dialog**; an independent fetch then shows `active: false, order: -1`; the toast reads
  **"Archived. Undo"**; tapping UNDO and re-fetching shows `active: true, order: 2` — its exact
  prior state. `.../shots/m-budget_archived_undo_toast.png`
- **AC-8.10: PASS** (2026-01) — the available block's box is the **identical object** before and
  after collapsing the six-figure grid and after a driven scroll to the bottom
  (`x16 y70 w358 h138.98`), and is never occluded (its top 70 > `#topbar` bottom 56). Its four
  attributes equal `/budget/summary` **and** my Python: `data-cents` −? → `unassigned 10,369,888`,
  `data-starting` `12,059,888`, `data-assigned` `1,690,000`, `data-income-planned` `16,500,000`.
  The chip renders as a `<button>` of **221.2 × 44 px**, opens a `data-kind="overspend"` sheet,
  and flips `outstanding` → `covered` under the `page.route`-mutated body (below).
  `.../shots/m-budget_2026-01_chipsheet.png`
- **AC-9.1: PASS** — `scratch/s04/baseline.json` (mtime 2026-08-21 08:53) plus 12 PNGs covering
  Dashboard, Transactions, Budget, Reports and Settings at 1280×800 and 390×844 with console
  output, captured **before** the round's first push (first round-04 commit `d222e72` at 08:54).
  The debrief records `/build/counts` taken immediately either side of that drive and identical.
- **AC-9.2: PASS** — I re-ran the identical instrument after the final deploy. The root still
  serves the Forms app; login succeeded at both widths; all five screens navigated and showed
  their observables at 1280 and at 390 **except** mobile Reports and mobile Settings, which show
  *"This app has experienced an error"* — **byte-identical to the baseline banner**, textLen
  87 → 87, i.e. no worse and not counted against this round. The only content deltas anywhere are
  the Budget screens' textLen (809 → 850 desktop, 796 → 839 mobile), which is the round's own
  `ZZ S04 Cat` / `ZZ S04 Cat B` rows appearing.
- **AC-9.3: PASS** — every judged Forms view with a scroller was actually scrolled and `scrollTop`
  MOVED, before and after: Dashboard 837/779, Transactions 1017/779, Budget 1112→1197/779,
  Reports 832/779, Settings 413/299 (desktop); Dashboard 1278/661, Budget 1939→2087/201 (mobile),
  with below-fold markers reached where present. **Mobile Transactions reports `scrollable: false`
  (`scrollHeight == clientHeight`) in both baseline and after — recorded as unchanged.**
- **AC-9.4: PASS** — console errors: desktop 0 → 0; mobile 1 → 1, and the one is the same
  pre-existing `Failed to load resource: 404` present in the baseline. No new error.
- **AC-9.5: PASS** — `POST /budget/amount` with `amount_cents: 12345` on `ZZ S04 Sub A` stored
  **−12,345** (server flipped the sign). The Forms Budget screen on December 2025 then rendered
  that row as **`(123.45)`** — not 1,234,500, not 1.23 — and `ZZ S04 Cat`'s header budget moved
  **`(2100.00)` → `(2123.45)`**, exactly the 23.45 delta, with the Expenses total moving
  `(R35,194.00)` → `(R35,217.45)`. Restored to −10,000 afterwards.
  `.../shots/forms_zz_before.png` · `.../shots/forms_zz_after_write.png`
- **AC-9.6: PASS** — with `ZZ S04 Cat B` archived by `/cat/archive` (`active: false`, `order: -1`),
  the Forms Budget category list does **not** contain it; after restoring it through the new
  client's Archived affordance, the Forms list shows it again. The §3.8 mirror works in the
  direction that matters. `.../shots/forms_budget_catB_archived_dec.png` ·
  `.../shots/forms_budget_catB_restored.png`
- **AC-9.7: PASS** — `/build/counts` `budgets` was **77 immediately before and 77 immediately
  after** every Forms-app drive I made (the full five-screen sweep at both widths, plus three
  targeted Budget drives). **The delta is zero and the enumeration is empty.** Cause, per fact 1:
  `load_budget_data` copies from the month before `date.today()`, and 2026-07 holds no budget
  rows, so the copy block creates nothing. Same finding as the round's own baseline note.
- **AC-12.2: PASS** — with six descriptions renamed through a `page.route`-mutated payload
  (`apple`, `Apple Watch`, `Banana`, `banana split`, `ZEBRA`, `zebra crossing`), `d-trans`'s
  description sort renders
  `apple, Apple Watch, Banana, banana split, ENGEN…, KODALY…, PARKSIDE…, REHOBOTHE…, ZEBRA, zebra crossing`
  — **exactly** an independent `bxCompare` sort (case-insensitive, code-point tie-break) of the
  same data, and the reverse of it on the second click. `"apple"` and `"Apple Watch"` are
  adjacent. Every sortable control checked: `description` ✓ and `account` ✓ equal `bxCompare`;
  `amount` sorts numerically ascending on `data-cents`; `date` sorts; `category` puts the eight
  uncategorised rows first and the two named ones in `bxCompare` order, consistent with sorting on
  `name || ""`. The other six clients expose **no** `[data-sort]` control, so there is no sortable
  column left unchecked. `.../shots/d-trans_sorted_description.png`
- **AC-12.3: PASS** — with the bootstrap route throttled to 6 s, `d-trans` renders **6**
  `[data-skeleton]` elements on screen; every `.bx-skeleton-row` in the file carries the
  attribute. `.../shots/d-trans_skeleton.png`
- **AC-12.4: PASS** — `m-trans` fully loaded and rendered (10 rows), then `**/txn/**` failed 500.
  A visible, **attached** banner appears — `#loadError`, class `bx-inline-error
  bx-error-banner--show`, text *"Could not update the transaction. Please try again."*, box
  `x14 y208 w362 h19.6`, `document.body.contains(el) === true` — plus a toast *"Update transaction
  did not save"*. Asserted on the rendered DOM, not on a detached node.
  `.../shots/m-trans_post_load_error.png`
- **AC-12.5: PASS** — at 390×844 both `d-trans` and `d-budget` render
  `[data-phone-notice]` (*"This screen needs more room… Use the phone version instead"*) with the
  desktop sidebar at `display: none` and only one interactive control reachable.
  `document.elementFromPoint(195, 422)` returns `P.bx-phone-notice__body`, inside the notice — no
  desktop element intercepts the centre click. Following the notice's link lands on
  `?slug=m-trans` / `?slug=m-budget`, and each twin renders (10 rows / 15 cards).
  `.../shots/d-budget_390_phone_notice.png`
- **AC-13.1: PASS** (2025-12 → 2026-01) — both clients make **exactly one** data request per page
  open: `GET /_/api/app/bootstrap?include=transactions,budgets`. After that, a month step back and
  forward, expanding a category, opening the rail, entering and leaving focus mode, opening the
  edit sheet, revealing archived rows and opening the `data-carried` sheet produced **zero**
  further requests on either client. **Neither client called `/budget/summary` at any point in any
  drive in this review.**
- **AC-13.2: PASS** — editing one budget amount produced exactly **one** `POST /budget/amount` and
  no refetch. Reordering produced exactly **one** `POST /cat/reorder`. Confirming "Open this
  month" produced exactly **one** `POST /budget/open-month` with body
  `{"month":"2026-03","copy_from":"2026-02"}` and no other request — driven with the route stubbed
  so no rows were written.
- **AC-13.3: PASS** — bootstrap mocked to resolve instantly with the §5 fixture
  (`bootstrap_full.json`), timed from the **navigation entry's `responseEnd`** (never
  `page.goto`): `d-budget` **67.9 / 84.2 / 95.5 ms**, `m-budget` **87.6 / 83.3 / 82.1 ms** to the
  first painted `[data-cat-row]`. Well inside 400 ms at both widths.
- **AC-13.4: PASS** — measured from the dispatched input event to the first DOM mutation:
  `d-budget` month step **23.0 / 35.6 ms**, expand **43.7 ms**; `m-budget` month step **43.4 ms**,
  focus enter **35.7 ms**, focus leave **0.7 ms**. All under 100 ms.
- **AC-14.2: PASS** (2025-12) — with `prefers-reduced-motion: reduce` emulated, every
  `animation-duration` and `transition-duration` on the rows and meters resolves to **`0s`** (not
  `1e-06s`), all 15 rows render at `opacity: 1`, and every meter's fill width divided by its track
  width equals its `data-fraction` to within 0.02 — meters at their final value. Focus mode still
  **opens** and **closes**. Nothing hidden, nothing broken.
  `.../shots/m-budget_reduced_2025-12.png`
- **AC-14.3: PASS** — the served bytes of all seven pages were parsed: HTML comments removed, then
  the inline JS extracted and stripped of `//`, `/* */` comments **and string literals**, then
  scanned for `(?<![\w$.])(alert|confirm|prompt)\s*\(`. **Zero hits in all seven** (and zero even
  before stripping, so trap 9 did not bite). `bxConfirm` is used instead (1–3 sites per client).
  **Zero `dialog` events fired** across every drive in this review, including both archive paths
  and the open-month confirmation — a dialog handler was attached to every page in every script.
- **AC-14.5: PASS** (2025-12) — `ZZ S04 Sub A` (budget −10,000, spend −310,000) renders
  `data-over="30.0000"`; `ZZ S04 Sub D` (budget −30,000, spend −120,000) renders
  `data-over="3.0000"`. **They differ**, both `data-state="over"`, both `data-fraction="1.0000"`,
  both fills computed `rgb(184,124,76)` (`--negative`, not `--error`). `label_cents` (300,000 and
  90,000) equals my independent recomputation and `/budget/summary`. Fact 16's saturation is gone.
  **Discrepancy to record:** the criterion predicts `29.0000` and `2.0000`. §4.6's `over_ratio` is
  `(S−B)/B`, and §3.13 row 10's live data makes the *overspend* 30× and 3× the budget rather than
  the *spend*, so the correct values are 30.0000 and 3.0000. The arithmetic is right; the spec's
  parenthetical describes a different fixture. Needs an addendum, not a code change.
- **AC-14.6: PASS** — `m-budget` at 390×844, entering focus mode so `bx-fade-rise` was running,
  then driving `[data-scroller].scrollTop` +45 px per frame across **12 rAF samples** (45 → 540,
  moving every frame, `scrollHeight 1176 > clientHeight 495`). `document.getAnimations()` was
  **non-empty at every sample** (1–2 running animations). `#topbar` and `#bottombar` each yielded
  **exactly one distinct bounding box** across all 12. Also confirmed during the skeleton shimmer
  (5 running animations, 10 samples, one distinct box each).
- **AC-14.7: PASS** (2025-12, both widths) — with `**/budget/amount` held unanswered for 2 s and a
  50 ms-resolution timeline: at **t = 111 ms** (desktop; 113 ms mobile) the sub-row moved
  −10,000 → **−77,700**, the `ZZ S04 Cat` total −90,000 → **−157,700** and the header
  expense-budget −2,500,000 → **−2,567,700** — all three, long before any response. When the route
  was then failed, at **t = 2,138 ms all three rolled back** to −10,000 / −90,000 / −2,500,000 and
  a toast read **"Budget amount did not save"**; an independent fetch confirms the server value
  never changed. The rollback is asserted on the **header**, not only the edited row. *(My first
  pass reported this as a failure; that was my instrument — `keyboard.press('Enter')` did not
  reach the input. Re-driven with a dispatched `keydown`, it passes.)*
  `.../shots/d-budget_optimistic_rollback.png`

### AC-6.12 — the eight bullets that hold, for the record

Month **2026-01**, both clients.
1. `data-available`'s four attributes equal `/budget/summary`'s `available` block field-for-field
   per §3.5's mapping **and** my independent Python: `unassigned 10,369,888` · `starting_available
   12,059,888` · `assigned 1,690,000` · `income_planned 16,500,000`. Three-way, exact.
2. The chip is **present** and its `data-cents 4,440,112` / `data-overspend 1,491,913` /
   `data-shortfall 2,948,199` match `/budget/summary` exactly.
3. Past-tense copy naming each cause **separately**: driven in the `outstanding` state via a
   `page.route`-mutated bootstrap — *"Last month: R14,919.13 overspent, R29,481.99 income short"*.
   On the **live** payload 2026-01 is already `covered` (`assigned 1,690,000 > 0` and
   `unassigned 10,369,888 ≥ 0`), so the live copy is §4.5A's covered form, *"Last month's
   R44,401.12 is covered"* — one merged number, exactly as §4.5A specifies for that state.
   **The dispatch's premise that "the both copy is live" on 2026-01 is not correct**; the
   separate-cause copy exists and is right, but you have to drive the month into `outstanding` to
   see it.
4. `outstanding` → `covered` **driven**, not photographed: with `ZZ S04 Sub A`'s 2026-01 budget
   inflated to −13,000,000 through `page.route`, `assigned` = 14,680,000, `unassigned` = −2,620,112,
   `data-state="outstanding"`, computed colour **`rgb(184, 124, 76)`** (`--negative`). Reducing the
   budget back to R100.00 through the rail / sheet (write route stubbed, nothing written) drops
   `assigned` to 1,690,000, `unassigned` to 10,369,888, and `data-state` flips to `covered` with
   computed colour **`rgb(192, 201, 193)`** (`--on-surface-variant`). Both clients.
   `.../shots/d-budget_chip_outstanding.png` · `.../shots/d-budget_chip_covered.png`
5. No category row in 2026-01 is marked for 2025-12: every `data-meter` matched my recomputation
   from 2026-01's own rows (15/15, zero mismatches), and `ZZ S04 Cat` — 4.1× over in 2025-12 —
   carries **no** `over` state in 2026-01. Stepping **back** to 2025-12 shows the `over` states
   there (12 categories, `data-over` 0.1300 … 4.1111).
6. Clicking the chip opens `data-kind="overspend"`. Its `data-overspend-sub` elements are
   **exactly** the four keys of `overspend_by_sub` and its `data-shortfall-sub` elements
   **exactly** the three keys of `shortfall_by_sub`, every `data-cents` matching
   (300,000 · 90,000 · 103,506 · 998,407 / 2,500,000 · 408,199 · 40,000). Each row links to
   `?slug=d-trans&month=2025-12&sub=<id>` — **M − 1**, per Addendum 16.
7. *(the income-shortfall bullet — this is the FAIL, see above)*
8. On **2027-07**, whose predecessor 2027-06 holds budget rows and no transactions,
   `document.querySelectorAll('[data-carried]').length === 0` on **both** clients — the element is
   **absent from the DOM**, not hidden. `.../shots/d-budget_2027-07_no_chip.png`

---

## Rows I wrote — every one restored, and reconciled

Every write below was made to `transactions`-adjacent `ZZ` rows or to `ZZ` structural rows, except
the two `/cat/reorder` calls, which by construction submit the whole category sequence.

| # | Table | Row | Change | Final |
|---|---|---|---|---|
| 1 | `budgets` | `ZZ S04 Sub A` / 2025-12 | `amount_cents` −10000 → −12345 (AC-6.5 rail edit) → −10000 | **−10000, as found** |
| 2 | `budgets` | `ZZ S04 Sub A` / 2025-12 | `notes` "" → "ZZ vr note" → "" (AC-6.5) | **"", as found** |
| 3 | `sub_categories` | `ZZ S04 Sub D` | `roll_over` false → true, `roll_over_date` null → 2025-11-01 (AC-6.6), then false, then date → null | **false / null, as found** |
| 4 | `budgets` | `ZZ S04 Sub A` / 2025-12 | `amount_cents` −10000 → −12345 (AC-9.5 via `/budget/amount`) → −10000 | **−10000, as found** |
| 5 | `categories` | `ZZ S04 Cat B` (`3b481020…`) | `active` true → false, `order` 14 → −1 (AC-6.3/9.6 archive), then restore | **active true, order 14, as found** |
| 6 | `categories` | whole sequence ×2 | `/cat/reorder` moved `ZZ S04 Cat` 13 → 12 (AirBnb 12 → 13), then moved it back | **sequence byte-identical to round-start** |
| 7 | `sub_categories` | `ZZ S04 Income Sub` | `roll_over` false → true, `roll_over_date` null → 2025-01-01 (AC-5.7 probe), then false, then date → null | **false / null, as found** |
| 8 | `budgets` | `ZZ S04 Sub A` / 2025-12 | −10000 → −11100 → −10000, twice (AC-8.4 re-render trigger) | **−10000, as found** |
| 9 | `budgets` | `ZZ S04 Sub A` / 2025-12 | −10000 → −10100 → −10200 → −10300 → −10000, and −10100 → −10000 (AC-8.8 dismissal paths) | **−10000, as found** |
| 10 | `sub_categories` | `ZZ S04 Sub D` | `active` true → false, `order` 2 → −1 (AC-8.9 archive), then Undo | **active true, order 2, as found** |

**Reconciliation at the end of the review:** an independent bootstrap fetch compared field-by-field
against the fetch I took at the start of the review yields **zero differences** across
`categories` (16), `sub_categories` (62), `budgets` (77) and `transactions` (1,309).
`/build/counts` is unchanged on every table: `accounts 9 · budgets 77 · categories 16 · files 8 ·
settings 1 · sub_categories 62 · test_csv 5 · transactions 1,314 · users 3`.

**No real category, sub-category or budget row's planning figure was written.** The two
`/cat/reorder` calls necessarily rewrote `categories.order` for the whole non-archived set (AC-6.8
cannot be judged otherwise, and AC-11.3 anticipates it); the second call restored the round-start
sequence verbatim and the reconciliation above confirms it. All writes done through
`page.route`-stubbed endpoints (AC-6.12's transition, AC-13.2's open-month) wrote **nothing**.

---

## Could not reach or verify

- **`x`'s skeleton state in normal use.** The three `#loadingState` skeleton rows are only shown
  while a cached token is being validated, and the page then redirects. I judged AC-7.9 on the
  served bytes plus the live DOM at both widths (present, zero-sized, no `data-skeleton`).
- **AC-9.1's "before the first push" claim** is verified circumstantially — `baseline.json`'s
  mtime (08:53) precedes the first round-04 commit `d222e72` (08:54) — not by watching it happen.
- **`/budget/open-month`'s live write** was not driven: AC-6.9 forbids confirming, and confirming
  on the `ZZ` far-future pair would have populated 2027-07 and taken AC-2.5's evidence away from
  the spec reviewer. AC-13.2's open-month clause was measured with the route stubbed.
- **Light theme.** The app has **no** light theme: `prefers-color-scheme` appears zero times in
  `bx_core.css` or in any served client. Captured all seven pages with `color_scheme: 'light'`
  emulated anyway — `body` computes `rgb(25,28,26)` / `rgb(225,227,223)` identically to dark on
  all seven, so nothing breaks. Recorded as a design fact, not a defect.

---

## Observations outside my mandate (not verdicts)

1. **`m-budget`'s card layout is the root cause of finding 1**, and it is a one-rule fix: the
   mobile card reuses the desktop `.bx-cat-card__header` flex row (name · figures · meter) which
   needs ~417 px inside a 358 px card.
2. **The chip sheet's title reads `"2025-12 — what happened"`** — a raw month key, where every
   other surface in the app renders "December 2025".
3. **`d-budget`'s month label sits flush against both chevrons** (label 336→435.1, next chevron
   starts at 435.1 — a 0 px gutter), where `d-trans` leaves 8 px each side. No overlap, but it
   reads as a collision. `.../shots/d-budget_monthnav.png`
4. **The roll-over toggle is offered on income sub-categories** and, once switched on, adds a `↻`
   badge and an "Avail" figure to the row, while `/budget/summary` reports
   `supported: false` for the same row. §3.9 says the income category "cannot be renamed, archived
   or reordered, and the UI says why rather than disabling silently" — roll-over is not on that
   list, but this is the same class of problem.
5. **Data finding for Bruce (not a build failure, as AC-7.5 directs):** category `Holidays ✈️`
   uses `colour_text #333333` on `colour_back #4e7a27` — **2.49:1**, below WCAG AA 4.5:1. The
   other 14 pairs pass.
6. `budgets` did not move at all during any Forms-app drive, which means §7 trap 12's hazard is
   currently dormant on this data — it will wake the moment a month with budget rows becomes the
   predecessor of the server's current month.
