/* bx_calc.js v2 — Budget X money core (Round 03 Builder C; Round 04 Builder C)
   history:
   v1 — initial: bxSum/bxInflow/bxOutflow/bxNet, bxByMonth, bxGroupBySub/bxGroupByCat,
        bxExcludeTransfers, bxFmtCents, bxSmartIndex/bxSuggest. Integer cents throughout.
   v2 — spec_04 §3.3: sixteen additive exports — bxDefaultMonth, bxIncomeCategoryId, bxSignFor,
        bxActual, bxBudget, bxRollover, bxSubTotals, bxOverspend, bxIncomeShortfall,
        bxAvailableToBudget, bxCatTotals, bxHeaderTotals, bxVariance, bxProgress,
        bxOpenMonthPlan, bxCompare. Every v1 export unchanged in name, signature and behaviour.

   ── THE ONE RULE ──────────────────────────────────────────────────────────────
   Money is INTEGER CENTS in and INTEGER CENTS out. There is no floating-point
   arithmetic on money anywhere in this file, and NOTHING here ever multiplies by
   100 — the stored column already holds cents (spec_03 §0.1), so a ×100 would
   inflate every figure in the app 100×.

   The only division in the file is inside bxFmtCents, and it divides a value that
   has already had its remainder subtracted, i.e. an exact multiple of 100. Dividing
   an exact multiple of 100 (within Number.MAX_SAFE_INTEGER) by 100 is exact in
   IEEE-754, so no drift is introduced. Every other operation is integer + and -.

   ── SCOPE ─────────────────────────────────────────────────────────────────────
   Pure functions only. It touches no browser API of any kind — no DOM node, no
   network call, no global object, no timer — and holds no module-level mutable
   state. Same input → same output, every time. That is what makes the golden
   suite (tools/calc_golden.mjs) meaningful.

   ── DUAL LOADING ──────────────────────────────────────────────────────────────
   The file is written as a classic script: plain top-level `function` declarations,
   so pasting it verbatim inside a <script> tag makes bxSum(...) etc. callable as
   globals. The CommonJS tail at the very bottom is guarded on `typeof module`, which
   a browser never defines, so it is inert there; under node the file loads as
   CommonJS (no package.json in this repo → .js is CJS) and the golden runner pulls
   it in with createRequire.

   ── RECORDED DECISIONS (each one is pinned by a golden case) ───────────────────

   1. THE UNCATEGORISED KEY. bxGroupBySub / bxGroupByCat return a plain object, and
      a JS object key is always a string, so the uncategorised bucket is written as
      out[null] and reads back as out["null"]. out[null] and out["null"] are the SAME
      property — callers may use either. The consequence, stated plainly: a real
      sub_category_id of the literal text "null" would collide with the bucket. Real
      ids are UUIDs, so this cannot happen in practice, and a plain JSON-comparable
      object is worth far more to the golden suite than a Map with a true null key.

   2. WHAT COUNTS AS UNCATEGORISED. `category` values null, undefined and "" are all
      treated as uncategorised. spec_03 §4.2 keeps `category` nullable, but the same
      §4.2 rule turns null string fields into "", so both shapes reach the client.

   3. UNKNOWN SUB-CATEGORIES. In bxGroupByCat, a sub_category_id that is absent from
      the supplied sub_categories array (or whose `belongs_to` is empty) cannot be
      rolled up, so it lands in the same uncategorised `null` bucket. It is never
      silently dropped — the money always survives the rollup.

   4. MATCHING IS CASE-INSENSITIVE. bxSmartIndex indexes lowercased words and
      bxSuggest lowercases the description before lookup. The legacy is_it_smart is
      case-sensitive, which makes it miss "WOOLWORTHS" against an index built from
      "Woolworths" — and bank descriptions arrive in inconsistent case. The >= 3
      character length test is applied to the word as it appears, before lowercasing;
      lowercasing never changes a length.

   5. SCORE COUNTS DISTINCT WORDS. "PICK N PAY PICK N PAY" scores "pay" once, not
      twice, so a repeated word cannot inflate a suggestion.

   ── THE bxSmartIndex SHAPE, AND WHY ───────────────────────────────────────────

     {
       version: 1,
       categories: {
         "<sub_category_id>": {
           words:     { "<lowercased word>": true, ... },   // membership set
           last_date: "YYYY-MM-DD",                          // max date seen, "" if none
           txn_count: <int>                                  // rows that fed this entry
         },
         ...
       }
     }

   Three shape decisions:

   * `words` is an object-as-set rather than a Set so the whole index is plain JSON —
     it can be written into a golden case, diffed, logged, or shipped in a payload.
     It is built with Object.create(null) so a description word of "__proto__" or
     "constructor" is stored as an ordinary key instead of hitting an inherited
     setter, and every read goes through hasOwnProperty.
   * `last_date` exists because spec_03 §3.3 requires the tie to break on "the
     category appearing on the most recent transaction". That fact is not recoverable
     from a bare word set, so the index has to carry it. It is the maximum `date`
     over ALL rows bearing the category, not only the rows that supplied a matching
     word — the tiebreak asks which category is most recently in use. ISO
     YYYY-MM-DD strings sort correctly under plain string comparison, so no Date
     object and no timezone ever enters the calculation.
   * `txn_count` is not used by bxSuggest. It is carried because it is free at build
     time and it is what a later round will want in order to explain a suggestion to
     the user ("seen on 14 transactions").

   ── HOW bxSuggest DIFFERS FROM THE LEGACY is_it_smart ─────────────────────────
   (client_code/F_Global_Logic/Global.py:95 — read before writing this)

   The legacy loop does, for each category with at least one matching word,
   `leader[k] = 0; leader[k] += 1`, then `max(leader, key=leader.get)`. Every
   matching category therefore scores exactly 1, and Python's max returns the FIRST
   key at that value in dict insertion order — which is table-scan order. So the
   moment two categories match, the suggestion is decided by which transaction the
   importer happened to see first. Here:

   1. score is the NUMBER of distinct matching words, so more evidence wins;
   2. ties break deterministically — score desc, then last_date desc, then
      sub_category_id ascending — so the answer never depends on input order;
   3. the score is RETURNED, so a client can lead with score >= 2 and merely offer
      a weaker one.
*/

/* ---------- internal helpers ---------- */

/* True only for a safe, exact integer. Money that is not an integer is a defect
   upstream, and this file refuses to average it away. */
function bxIsInt(n) {
  return typeof n === 'number' && isFinite(n) && Math.floor(n) === n;
}

function bxOwns(obj, key) {
  return obj !== null && obj !== undefined && Object.prototype.hasOwnProperty.call(obj, key);
}

/* null / undefined / "" all mean "uncategorised" (decision 2). */
function bxCatKey(value) {
  if (value === null || value === undefined || value === '') { return null; }
  return String(value);
}

/* Year and 1-based month of a row's `date`. Accepts the wire format
   "YYYY-MM-DD" (spec_03 §4.2) and, defensively, a Date instance — read through
   its LOCAL components, which is how a Date built as new Date(2024, 1, 29) reads
   back. Anything else yields null and the row simply does not match a month. */
function bxYearMonth(value) {
  if (value instanceof Date) {
    if (isNaN(value.getTime())) { return null; }
    return { y: value.getFullYear(), m: value.getMonth() + 1 };
  }
  if (typeof value !== 'string' || value.length < 7) { return null; }
  var y = parseInt(value.slice(0, 4), 10);
  var m = parseInt(value.slice(5, 7), 10);
  if (!isFinite(y) || !isFinite(m) || m < 1 || m > 12) { return null; }
  return { y: y, m: m };
}

/* Words of a description that are eligible for the suggestion index: whitespace
   separated, length >= 3 measured on the word as written, then lowercased. */
function bxWords(description) {
  if (typeof description !== 'string') { return []; }
  var raw = description.split(/\s+/);
  var out = [];
  for (var i = 0; i < raw.length; i++) {
    if (raw[i].length >= 3) { out.push(raw[i].toLowerCase()); }
  }
  return out;
}

/* ---------- days in a month — used by bxByMonth's boundary reasoning ----------
   Exported beyond the §3.3 contract because the month boundary is the thing that
   has to be right, and a directly testable day count is how that gets proven.
   Gregorian rule in full: divisible by 4, except centuries, except multiples of 400. */
function bxDaysInMonth(y, m) {
  if (m === 2) {
    var leap = (y % 4 === 0 && y % 100 !== 0) || (y % 400 === 0);
    return leap ? 29 : 28;
  }
  if (m === 4 || m === 6 || m === 9 || m === 11) { return 30; }
  return 31;
}

/* ---------- bxSum ---------- */
/* Integer sum of an array of integer cents. 0 for an empty array.
   Throws on a non-integer entry rather than quietly returning a wrong total —
   a silently wrong money figure is the worst outcome available here. */
function bxSum(cents) {
  if (!cents || !cents.length) { return 0; }
  var total = 0;
  for (var i = 0; i < cents.length; i++) {
    if (!bxIsInt(cents[i])) {
      throw new TypeError('bxSum: non-integer cents at index ' + i);
    }
    total += cents[i];
  }
  return total;
}

/* ---------- flows ---------- */
function bxAmounts(txns, predicate) {
  var out = [];
  if (!txns || !txns.length) { return out; }
  for (var i = 0; i < txns.length; i++) {
    var row = txns[i];
    if (!row) { continue; }
    var c = row.amount_cents;
    if (!bxIsInt(c)) {
      throw new TypeError('bxCalc: non-integer amount_cents on row ' + i);
    }
    if (predicate(c)) { out.push(c); }
  }
  return out;
}

/* Sum of positive amount_cents. Zero-amount rows are neither inflow nor outflow. */
function bxInflow(txns) {
  return bxSum(bxAmounts(txns, function (c) { return c > 0; }));
}

/* Sum of negative amount_cents — returns a NEGATIVE integer, matching the Forms app. */
function bxOutflow(txns) {
  return bxSum(bxAmounts(txns, function (c) { return c < 0; }));
}

/* Net = inflow + outflow (outflow already carries its sign). */
function bxNet(txns) {
  return bxInflow(txns) + bxOutflow(txns);
}

/* ---------- bxByMonth ---------- */
/* Rows whose `date` falls in calendar month (y, m), first day to last day
   inclusive — Transaction.date_me()'s semantics. `m` is 1-based. Because the
   span is exactly one calendar month, "between day 1 and day daysInMonth" is
   the same test as "same year and same month", and the latter needs no date
   arithmetic at all, so no timezone can move a row across a boundary. */
function bxByMonth(txns, y, m) {
  var out = [];
  if (!txns || !txns.length) { return out; }
  for (var i = 0; i < txns.length; i++) {
    var row = txns[i];
    if (!row) { continue; }
    var ym = bxYearMonth(row.date);
    if (ym && ym.y === y && ym.m === m) { out.push(row); }
  }
  return out;
}

/* ---------- groupings ---------- */
/* { sub_category_id: cents }, uncategorised under the key null — which JS stores
   and returns as the string "null" (decision 1). */
function bxGroupBySub(txns) {
  var out = {};
  if (!txns || !txns.length) { return out; }
  for (var i = 0; i < txns.length; i++) {
    var row = txns[i];
    if (!row) { continue; }
    var c = row.amount_cents;
    if (!bxIsInt(c)) {
      throw new TypeError('bxGroupBySub: non-integer amount_cents on row ' + i);
    }
    var key = bxCatKey(row.category);
    if (!bxOwns(out, key)) { out[key] = 0; }
    out[key] += c;
  }
  return out;
}

/* Rolls sub-category totals up to category_id using the bootstrap
   `sub_categories` array ({ sub_category_id, belongs_to, ... }). Uncategorised
   rows, and rows on a sub-category this array does not describe, land in the
   null bucket (decision 3) — the money is never dropped. */
function bxGroupByCat(txns, subCats) {
  var belongs = Object.create(null);
  if (subCats && subCats.length) {
    for (var s = 0; s < subCats.length; s++) {
      var sc = subCats[s];
      if (!sc) { continue; }
      var sid = bxCatKey(sc.sub_category_id);
      if (sid === null) { continue; }
      belongs[sid] = bxCatKey(sc.belongs_to);
    }
  }
  var bySub = bxGroupBySub(txns);
  var out = {};
  var keys = Object.keys(bySub);
  for (var k = 0; k < keys.length; k++) {
    var subKey = keys[k];
    var catKey = null;
    /* String(null) === "null" is exactly the key bxGroupBySub wrote for
       uncategorised, so that bucket falls through to null here as well. */
    if (subKey !== 'null' && bxOwns(belongs, subKey)) { catKey = belongs[subKey]; }
    if (!bxOwns(out, catKey)) { out[catKey] = 0; }
    out[catKey] += bySub[subKey];
  }
  return out;
}

/* ---------- transfers ---------- */
/* Drops rows whose `category` is the transfer sentinel. A transfer is neither
   income nor expenditure, so every total that is about spending calls this first.
   A null/empty sentinel means "nothing to exclude" and returns a copy. */
function bxExcludeTransfers(txns, transferCategoryId) {
  var out = [];
  if (!txns || !txns.length) { return out; }
  var sentinel = bxCatKey(transferCategoryId);
  for (var i = 0; i < txns.length; i++) {
    var row = txns[i];
    if (!row) { continue; }
    if (sentinel !== null && bxCatKey(row.category) === sentinel) { continue; }
    out.push(row);
  }
  return out;
}

/* ---------- formatting ---------- */
/* Integer cents → "R1,234.56"; negatives in parentheses → "(R1,234.56)".
   Formatting only: it never rounds, because there is nothing left to round.
   Non-integer input is a programming error and says so. */
function bxFmtCents(cents) {
  if (!bxIsInt(cents)) {
    throw new TypeError('bxFmtCents: expects integer cents, got ' + String(cents));
  }
  var negative = cents < 0;
  var abs = negative ? -cents : cents;
  var remainder = abs % 100;              /* exact: % on integers */
  var whole = (abs - remainder) / 100;    /* exact: an exact multiple of 100 / 100 */
  var minor = remainder < 10 ? '0' + remainder : String(remainder);
  var major = String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  var body = 'R' + major + '.' + minor;
  return negative ? '(' + body + ')' : body;
}

/* ---------- the suggestion index ---------- */
/* For every row with a non-null `category`: every whitespace-separated word of
   `description` of length >= 3, lowercased, into that category's word set; plus
   the latest date the category was seen on, for the tiebreak. Pure — the same
   transactions always build the same index. */
function bxSmartIndex(txns) {
  var index = { version: 1, categories: {} };
  if (!txns || !txns.length) { return index; }
  for (var i = 0; i < txns.length; i++) {
    var row = txns[i];
    if (!row) { continue; }
    var key = bxCatKey(row.category);
    if (key === null) { continue; }
    if (!bxOwns(index.categories, key)) {
      index.categories[key] = { words: Object.create(null), last_date: '', txn_count: 0 };
    }
    var entry = index.categories[key];
    entry.txn_count += 1;
    var d = typeof row.date === 'string' ? row.date : '';
    if (d > entry.last_date) { entry.last_date = d; }
    var words = bxWords(row.description);
    for (var w = 0; w < words.length; w++) {
      entry.words[words[w]] = true;
    }
  }
  return index;
}

/* ---------- the suggestion ---------- */
/* { sub_category_id, score } or null. score = number of DISTINCT words of the
   description present in that category's set. Ties break: score desc, then
   last_date desc, then sub_category_id ascending. Deterministic by construction —
   nothing depends on the order the categories were inserted. */
function bxSuggest(index, description) {
  if (!index || !index.categories) { return null; }
  var words = bxWords(description);
  if (!words.length) { return null; }

  /* distinct words, order irrelevant to the score */
  var seen = Object.create(null);
  var distinct = [];
  for (var i = 0; i < words.length; i++) {
    if (!bxOwns(seen, words[i])) { seen[words[i]] = true; distinct.push(words[i]); }
  }

  var best = null;
  var keys = Object.keys(index.categories).sort();  /* stable, input-order independent */
  for (var k = 0; k < keys.length; k++) {
    var key = keys[k];
    var entry = index.categories[key];
    if (!entry || !entry.words) { continue; }
    var score = 0;
    for (var d = 0; d < distinct.length; d++) {
      if (bxOwns(entry.words, distinct[d])) { score += 1; }
    }
    if (score === 0) { continue; }
    var lastDate = typeof entry.last_date === 'string' ? entry.last_date : '';
    if (best === null) {
      best = { sub_category_id: key, score: score, last_date: lastDate };
      continue;
    }
    if (score > best.score) {
      best = { sub_category_id: key, score: score, last_date: lastDate };
    } else if (score === best.score && lastDate > best.last_date) {
      best = { sub_category_id: key, score: score, last_date: lastDate };
    }
    /* equal score AND equal last_date: `keys` is ascending and `best` was set
       first, so the lower sub_category_id already holds — nothing to do. */
  }

  if (best === null) { return null; }
  return { sub_category_id: best.sub_category_id, score: best.score };
}

/* ══════════════════════════════════════════════════════════════════════════════
   v2 — spec_04 §3.3, §4.5, §4.5A, §4.6.  ADDITIVE ONLY.

   Everything above is untouched. Everything below is new, and every figure it
   returns is an integer number of cents except the two ratios `fraction` and
   `over_ratio` in bxProgress, which are derived for layout and are never money.
   There is not one floating-point literal in this file.

   ── THE SHAPES IT READS ───────────────────────────────────────────────────────
   budget row  { sub_category_id, month: "YYYY-MM", amount_cents: int, notes }   §4.3
   txn row     { transaction_id, date: "YYYY-MM-DD", amount_cents: int, category }  spec_03 §4.2
   sub-cat     { sub_category_id, name, icon, belongs_to, order, roll_over,
                 roll_over_date: "YYYY-MM-DD"|null, active }                     §4.2
   category    { category_id, name, colour_back, colour_text, order, active }    §4.2

   The legacy column names `budget_amount`, `period` and `belongs_to`-on-a-budget
   never appear here: the wire field is `amount_cents` and the wire month is
   `month` (§4.5A).

   ── SIGN CONVENTION ───────────────────────────────────────────────────────────
   Expense budgets and expense actuals are stored NEGATIVE; income POSITIVE
   (fact 7, §4.5). The single exception is §4.5A's pool, which talks in positive
   magnitudes because it is the one figure a person reads as "money I still have
   to give out"; `unassigned` alone may be negative there.

   ── RECORDED v2 DECISIONS (each one is pinned by a golden case) ───────────────

   6. INCOME BEATS EVERY OTHER ROLLOVER BRANCH. §4.5 lists branch A (roll_over
      off), B (roll_over on, no start date) and C (income) as a case analysis
      without stating precedence. bxRollover tests C FIRST, so an income
      sub-category returns supported:false whatever its roll_over flag says.
      That is what AC-5.7 asks for unconditionally, and it is the only ordering
      that is safe: branch A's closing rule applied to income's positive figures
      turns an under-earning line into "overspent", which §4.5A rule 4 forbids
      and which bxIncomeShortfall already reports properly under its own name.

   7. A SUB-CATEGORY IS A TRANSFER IF EITHER ITS OWN id OR ITS PARENT id IS THE
      SENTINEL. §3.1 measurement 3 allows the sentinel to be a `sub_categories`
      row, a `categories` row, or neither. Testing both covers all three at no
      cost; when it is neither, the test is a no-op and the exclusion happens
      entirely on the transaction side via bxExcludeTransfers, exactly as §3.3
      says it must.

   8. bxSubTotals OMITS THE TRANSFER SENTINEL sub-category from its map. §3.3
      says "every active sub-category", but §4.4 requires the category rollup and
      the header totals to exclude transfer rows, and bxCatTotals takes no
      sentinel argument — so the exclusion has to be here or nowhere. It costs
      nothing when the sentinel is not a sub-category row (decision 7).

   9. ORPHANS ARE EXCLUDED FROM bxCatTotals AND NOWHERE ELSE. §4.4 excludes
      orphans from `categories[]` and `totals`, and a sub-category whose parent
      does not exist cannot be attributed to a category anyway. §4.5A's
      definitions of overspend, shortfall and `assigned` enumerate their own
      exclusions — active, non-transfer, expense-or-income, has-a-budget-row —
      and orphans are not among them, so an orphan's real overspend still
      reaches the pool. Money is never silently dropped from the pool.

  10. `budget` IN bxSubTotals IS AN INTEGER, NEVER null. bxBudget returns null
      for "no row" because §3.3 says null and 0 are different facts. bxSubTotals
      carries the same distinction in a companion boolean, `budget_present`, and
      reports `budget: 0` — which is what §4.4's `budget_cents: 0` +
      `budget_present: false` pair does on the wire, so the client and
      /budget/summary compare field for field.

  11. bxCatTotals EMITS AN ENTRY FOR EVERY CATEGORY — including one with no
      sub-categories (zeros) and including an ARCHIVED one — but
      bxHeaderTotals EXCLUDES ARCHIVED CATEGORIES FROM THE ROLL-UP.
      The two halves are deliberate and they are not in tension. §3.9 binds both
      clients: "archived categories and sub-categories are hidden by default and
      excluded from every total (fact 5)" — so an archived category's money must
      not reach the header. But the "Archived (n)" affordance still has to be
      able to SHOW that category's figures, and it gets them from bxCatTotals.
      So the entry exists; it simply is not summed.
      This matters the moment anyone archives a category: §3.2 says /cat/archive
      does NOT touch the category's sub-categories, so they stay active and keep
      producing sub-totals under a parent that is gone from the UI. Counting
      them would make the header disagree with the rows beneath it — which is
      exactly the legacy defect fact 5 records.
      (Corrected during round 04 integration: the first cut of this file summed
      archived categories into the header and disagreed with the server's
      recomputation by exactly one archived category's budget.)

  12. bxBudget TAKES THE SMALLEST CENTS VALUE when fact 3's duplicate
      (sub_category, month) pairs are present — SPEC_04 ADDENDUM 10. It does not
      take the first row and it does not sum them: summing would silently double
      a budget, which is the failure this app cannot afford, and "first" is only
      deterministic if every instrument iterates in the same order, which
      /budget/summary and GET /build/budget-audit do not.
      The minimum is arbitrary but it is order-independent, so all three
      instruments agree on two runs. Nothing here ever repairs a duplicate; the
      write path refuses to touch a duplicated pair at all (§3.2).
      (This file's first cut took the first matching row; corrected to the
      addendum during round 04 integration so the client and the server converge.)

  13. EVERYTHING DEGRADES, NOTHING RAISES, WHEN THERE IS NO INCOME CATEGORY
      (fact 6). bxIncomeCategoryId returns null; bxSignFor then treats every
      category as an expense; bxRollover never takes branch C; bxIncomeShortfall
      is empty; and bxAvailableToBudget returns income_category:false with
      income_planned 0, which is §4.5A rule 8's suppressed state.

  14. bxCompare's TIE-BREAK IS ON THE ORIGINAL STRINGS, BY CODE POINT. Primary
      key is the lower-cased string, so "Apple Watch" sorts beside "apple juice"
      and not before every lower-case description (§3.11 carry-fix 3). When two
      strings differ only in case the raw code points decide, which makes it a
      total order and matches ServerAppData's `(name.lower(), id)` sort key
      (ServerAppData.py:519-528) on its primary component. Comparison is by CODE
      POINT, not by UTF-16 code unit, so it agrees with Python's `<` on strings
      containing astral characters rather than sorting them before U+E000.
   ══════════════════════════════════════════════════════════════════════════════ */

/* ---------- month helpers (internal) ----------
   A month is identified two ways in this app: as (y, m) with m 1-based, and as
   the wire string "YYYY-MM". These convert between them and give the ordinal
   §4.5 needs. All integer arithmetic; no Date object ever enters a calculation,
   so no timezone can move a month. */
function bxMonthIndex(y, m) {
  return (y * 12) + (m - 1);
}

function bxMonthKey(y, m) {
  var mm = m < 10 ? '0' + String(m) : String(m);
  return String(y) + '-' + mm;
}

function bxPrevMonth(y, m) {
  if (m === 1) { return { y: y - 1, m: 12 }; }
  return { y: y, m: m - 1 };
}

function bxAbs(n) {
  return n < 0 ? -n : n;
}

/* Clamp a layout ratio into [0, 1] (spec_04 Addendum 5). §4.6 says `fraction`
   and `over_fraction` are "capped at 1 for layout" — but min(ratio, 1) alone is
   not a cap, it is a ceiling: an anomalous negative income target makes row 7's
   (E - T) / T negative, and min(-1, 1) = -1 would drive a meter fill BACKWARDS.
   `over_ratio` is deliberately NOT clamped — it is the uncapped diagnostic value
   that data-over carries, and it stays free to go negative on an anomalous row. */
function bxClamp01(ratio) {
  if (!(ratio > 0)) { return 0; }
  return ratio < 1 ? ratio : 1;
}

/* True when the row is not archived. `active` absent or undefined means active —
   the same `is not False` test the server uses in one place (§4.2). */
function bxIsActive(row) {
  return !!row && row.active !== false;
}

/* Decision 7: the sentinel may be a sub-category id or a category id. */
function bxIsTransferSub(subCat, transferCategoryId) {
  var sentinel = bxCatKey(transferCategoryId);
  if (sentinel === null || !subCat) { return false; }
  return bxCatKey(subCat.sub_category_id) === sentinel
      || bxCatKey(subCat.belongs_to) === sentinel;
}

/* ---------- bxCompare ---------- */
/* Code-point comparison, not UTF-16 code-unit comparison (decision 14). */
function bxCodePointCompare(a, b) {
  var i = 0;
  var j = 0;
  while (i < a.length && j < b.length) {
    var ca = a.codePointAt(i);
    var cb = b.codePointAt(j);
    if (ca !== cb) { return ca < cb ? -1 : 1; }
    i += ca > 0xFFFF ? 2 : 1;
    j += cb > 0xFFFF ? 2 : 1;
  }
  if (i < a.length) { return 1; }
  if (j < b.length) { return -1; }
  return 0;
}

/* The canonical string comparator for every sort in every client: -1, 0 or 1.
   Case-insensitive first, then the raw code points, so it is a TOTAL order —
   two names differing only in case never compare equal, which is what stops a
   sort from being unstable across engines. null and undefined sort as "". */
function bxCompare(a, b) {
  var sa = (a === null || a === undefined) ? '' : String(a);
  var sb = (b === null || b === undefined) ? '' : String(b);
  var primary = bxCodePointCompare(sa.toLowerCase(), sb.toLowerCase());
  if (primary !== 0) { return primary; }
  return bxCodePointCompare(sa, sb);
}

/* ---------- bxDefaultMonth ---------- */
/* §0 ruling 1, and it lives here so the whole app has exactly one definition.
   The most recent calendar month at or before `serverDate` that holds at least
   one transaction; the `serverDate` month when there is none.

   COMPUTED FROM TRANSACTIONS ONLY. It does not take `budgets` and it never will:
   the Forms app writes next month's budget rows simply because somebody opened
   it (fact 1), so a budget row is not evidence that a month holds money. Round 03
   shipped an app that opened on a month with zero rows for exactly that reason.

   Returns { y, m }, or null in the one corner where there is nothing to answer
   from at all — no parseable transaction date AND no parseable serverDate. A
   caller that gets null has no data of any kind and has nothing to render. */
function bxDefaultMonth(txns, serverDate) {
  var bound = bxYearMonth(serverDate);
  var boundIdx = bound === null ? null : bxMonthIndex(bound.y, bound.m);
  var bestIdx = null;
  var best = null;
  if (txns && txns.length) {
    for (var i = 0; i < txns.length; i++) {
      var row = txns[i];
      if (!row) { continue; }
      var ym = bxYearMonth(row.date);
      if (ym === null) { continue; }
      var idx = bxMonthIndex(ym.y, ym.m);
      if (boundIdx !== null && idx > boundIdx) { continue; }
      if (bestIdx === null || idx > bestIdx) { bestIdx = idx; best = ym; }
    }
  }
  if (best !== null) { return { y: best.y, m: best.m }; }
  if (bound !== null) { return { y: bound.y, m: bound.m }; }
  return null;
}

/* ---------- bxIncomeCategoryId ---------- */
/* THE ONLY PLACE THE MAGIC NAME APPEARS CLIENT-SIDE. The category whose trimmed
   name equals "Income" case-insensitively, else null. Round 08 replaces the body
   with a flag lookup and nothing else in the app changes.

   The legacy test is case-sensitive and raises IndexError when no such category
   exists (fact 6). This one widens the match and returns null instead — every
   caller below is written to cope with null.

   Archived categories are NOT skipped: the legacy `is_income` scans every
   category, and an archived Income category still governs the sign of its
   sub-categories' budgets. First match in the supplied array order wins, and the
   array arrives in a total order from the server (§4.2), so it is deterministic. */
function bxIncomeCategoryId(categories) {
  if (!categories || !categories.length) { return null; }
  for (var i = 0; i < categories.length; i++) {
    var c = categories[i];
    if (!c) { continue; }
    var name = typeof c.name === 'string' ? c.name.trim() : '';
    if (name.toLowerCase() === 'income') {
      var id = bxCatKey(c.category_id);
      if (id !== null) { return id; }
    }
  }
  return null;
}

/* ---------- bxSignFor ---------- */
/* `neg_pos` (fact 7) as a display-side mirror of the server's authority: income
   is forced positive, everything else negative, and anything falsy is 0. The
   server applies the same rule on /budget/amount and does not trust this one. */
function bxSignFor(categories, categoryId, cents) {
  if (cents === null || cents === undefined || cents === 0) { return 0; }
  if (!bxIsInt(cents)) {
    throw new TypeError('bxSignFor: expects integer cents, got ' + String(cents));
  }
  var incomeId = bxIncomeCategoryId(categories);
  var isIncome = incomeId !== null && bxCatKey(categoryId) === incomeId;
  var abs = bxAbs(cents);
  return isIncome ? abs : -abs;
}

/* ---------- bxActual ---------- */
/* Integer cents spent (or earned) on one sub-category in one calendar month.
   TRANSFERS ARE EXCLUDED BEFORE THIS IS CALLED, never inside it — that is the v1
   contract of this pairing and §3.3 keeps it. The five §4.5/§4.5A functions below
   all call bxExcludeTransfers themselves before they reach this. */
function bxActual(txns, subCategoryId, y, m) {
  var key = bxCatKey(subCategoryId);
  if (key === null) { return 0; }
  var rows = bxByMonth(txns, y, m);
  var total = 0;
  for (var i = 0; i < rows.length; i++) {
    if (bxCatKey(rows[i].category) !== key) { continue; }
    var c = rows[i].amount_cents;
    if (!bxIsInt(c)) {
      throw new TypeError('bxActual: non-integer amount_cents on row ' + i);
    }
    total += c;
  }
  return total;
}

/* ---------- bxBudget ---------- */
/* Integer cents, or NULL when no budget row exists for that (sub-category, month).
   null and 0 are different facts and the UI shows them differently: 0 is "I
   budgeted nothing here", null is "I have not budgeted this yet". Note that
   bxSubTotals reports the same state as `budget: 0` + `budget_present: false`
   (Addendum 9) — that is the wire shape; this null is the raw fact.

   On a fact-3 duplicate it returns the SMALLEST value, not the first (decision
   12 / Addendum 10). Scanning every match rather than returning early is the
   whole point: the answer must not depend on row order. */
function bxBudget(budgets, subCategoryId, y, m) {
  var key = bxCatKey(subCategoryId);
  if (key === null || !budgets || !budgets.length) { return null; }
  var want = bxMonthKey(y, m);
  var found = null;
  for (var i = 0; i < budgets.length; i++) {
    var row = budgets[i];
    if (!row) { continue; }
    if (row.month !== want) { continue; }
    if (bxCatKey(row.sub_category_id) !== key) { continue; }
    var c = row.amount_cents;
    if (!bxIsInt(c)) {
      throw new TypeError('bxBudget: non-integer amount_cents for ' + key + ' ' + want);
    }
    if (found === null || c < found) { found = c; }
  }
  return found;
}

/* ---------- bxRollover ---------- */
/* §4.5, stated once, in integer cents. ALL NINE FIELDS ON EVERY BRANCH.

   The closing rule, which every branch except income ends with:

       raw       = available - spent
       overspent = raw > 0 ? raw : 0        // a POSITIVE magnitude
       remaining = raw > 0 ? 0   : raw      // <= 0, an expense's leftover

   Expense figures are stored negative, so `available - spent` is positive exactly
   when the spend has exceeded the pot. THE OVERSPEND IS CAPTURED, NEVER DISCARDED.
   The legacy clamped the carry at zero and then threw the number away, returning
   a "budget" equal to the month's own actual — variance 0, empty pill, "exactly
   on budget" at the precise moment the pot was blown (fact 12). Here `available`
   and `spent` are separate fields and `overspent` has a name, so §4.5A can deduct
   it from next month's pool (§0 ruling 5) and the screen can say what happened.

   An overspend never carries INSIDE the category: `carried` clamps at 0 each
   month, so carried_in is always <= 0 for an expense and every category starts
   the new month from its own budget. */
function bxRollover(budgets, txns, subCat, categories, y, m, transferCategoryId) {
  var clean = bxExcludeTransfers(txns, transferCategoryId);
  var sid = subCat ? bxCatKey(subCat.sub_category_id) : null;

  var monthBudget = bxBudget(budgets, sid, y, m);
  if (monthBudget === null) { monthBudget = 0; }
  var spent = bxActual(clean, sid, y, m);

  /* Branch C — income. Tested FIRST (decision 6). Income does not carry, and
     this round says so rather than inventing a number the legacy left as
     `pass  # what do we actually do here???` (fact 13). NOT the closing rule:
     `remaining = available - spent` and `overspent` is 0, always. An income line
     that falls short is a SHORTFALL, reported by bxIncomeShortfall (§0 ruling 6),
     never an overspend (§4.5A rule 4). */
  var incomeId = bxIncomeCategoryId(categories);
  if (incomeId !== null && subCat && bxCatKey(subCat.belongs_to) === incomeId) {
    return {
      supported: false, start_missing: false, months: 0, carried_in: 0,
      month_budget: monthBudget, available: monthBudget, spent: spent,
      remaining: monthBudget - spent, overspent: 0
    };
  }

  var rollOver = !!subCat && subCat.roll_over === true;
  var start = rollOver ? bxYearMonth(subCat.roll_over_date) : null;

  /* Branch B — roll_over on with no usable start date. A DEFINED STATE, NOT A
     CRASH: the legacy toggle creates exactly this and `while cd <= ld` against
     None then raises (fact 14). The write path now makes the state
     unrepresentable; the read path still never assumes it cannot happen. */
  var startMissing = rollOver && start === null;

  /* Branch D — the accumulator, D … M-1. `months` is the count of COMPLETED
     months contributing to the carry, so a start equal to the target month gives
     0 and a start after it gives 0 (never a negative range, never a crash).
     Branch A (roll_over off) is this with zero iterations. */
  var months = 0;
  var carried = 0;
  if (rollOver && start !== null) {
    months = bxMonthIndex(y, m) - bxMonthIndex(start.y, start.m);
    if (months < 0) { months = 0; }
    var py = start.y;
    var pm = start.m;
    for (var k = 0; k < months; k++) {
      var budgetP = bxBudget(budgets, sid, py, pm);
      if (budgetP === null) { budgetP = 0; }
      var availableP = carried + budgetP;
      var spentP = bxActual(clean, sid, py, pm);
      var remainingP = availableP - spentP;
      carried = remainingP <= 0 ? remainingP : 0;
      pm += 1;
      if (pm > 12) { pm = 1; py += 1; }
    }
  }

  var available = carried + monthBudget;
  var raw = available - spent;
  return {
    supported: true,
    start_missing: startMissing,
    months: months,
    carried_in: carried,
    month_budget: monthBudget,
    available: available,
    spent: spent,
    remaining: raw > 0 ? 0 : raw,
    overspent: raw > 0 ? raw : 0
  };
}

/* ---------- bxSubTotals ---------- */
/* { sub_category_id: { budget, budget_present, actual, rollover } } for every
   ACTIVE sub-category, the transfer sentinel excepted (decision 8). `budget` is
   an integer with `budget_present` carrying the null-versus-0 distinction
   (decision 10). Note the argument order: txns first, then budgets. */
function bxSubTotals(txns, budgets, subCats, categories, y, m, transferCategoryId) {
  var out = {};
  if (!subCats || !subCats.length) { return out; }
  var clean = bxExcludeTransfers(txns, transferCategoryId);
  for (var i = 0; i < subCats.length; i++) {
    var sc = subCats[i];
    if (!bxIsActive(sc)) { continue; }
    if (bxIsTransferSub(sc, transferCategoryId)) { continue; }
    var sid = bxCatKey(sc.sub_category_id);
    if (sid === null) { continue; }
    var b = bxBudget(budgets, sid, y, m);
    out[sid] = {
      budget: b === null ? 0 : b,
      budget_present: b !== null,
      actual: bxActual(clean, sid, y, m),
      rollover: bxRollover(budgets, clean, sc, categories, y, m, transferCategoryId)
    };
  }
  return out;
}

/* ---------- bxOverspend ---------- */
/* { total, by_sub } — the sum of bxRollover(...).overspent over every ACTIVE,
   NON-TRANSFER EXPENSE sub-category THAT HAS A BUDGET ROW for that month.
   Positive integers, because an overspend is a magnitude. This is the only place
   §0 ruling 5's "overspending MUST be accounted for" is computed.

   Four exclusions, each of which changes the answer (§4.5A rule 3):
     * archived  — the same exclusion as every other rollup;
     * transfers — a transfer is neither income nor expenditure;
     * income    — income never overspends (rule 4); it falls short instead;
     * NO BUDGET ROW — without this clause an unbudgeted month reports
       available 0 against real spending, makes every sub-category 100% over,
       and wipes out the following month's pool. §5 guarantees the round meets a
       month with no budget rows at all, so this is not a hypothetical.

   `by_sub` names ONLY the sub-categories that actually overspent. A zero is not
   an entry. */
function bxOverspend(budgets, txns, subCats, categories, y, m, transferCategoryId) {
  var bySub = {};
  var total = 0;
  if (!subCats || !subCats.length) { return { total: total, by_sub: bySub }; }
  var clean = bxExcludeTransfers(txns, transferCategoryId);
  var incomeId = bxIncomeCategoryId(categories);
  for (var i = 0; i < subCats.length; i++) {
    var sc = subCats[i];
    if (!bxIsActive(sc)) { continue; }
    if (bxIsTransferSub(sc, transferCategoryId)) { continue; }
    if (incomeId !== null && bxCatKey(sc.belongs_to) === incomeId) { continue; }
    var sid = bxCatKey(sc.sub_category_id);
    if (sid === null) { continue; }
    if (bxBudget(budgets, sid, y, m) === null) { continue; }
    var over = bxRollover(budgets, clean, sc, categories, y, m, transferCategoryId).overspent;
    if (over > 0) { bySub[sid] = over; total += over; }
  }
  return { total: total, by_sub: bySub };
}

/* ---------- bxIncomeShortfall ---------- */
/* The exact structural twin of bxOverspend, because §0 ruling 6 makes them the
   same mechanism: per ACTIVE INCOME sub-category THAT HAS A BUDGET ROW for that
   month, max(0, budget - actual), summed. Positive integers.

   The per-sub-category max(0, ...) is what stops an income line that over-earns
   from offsetting one that falls short (§4.5A rule 11) — netting them would hide
   both facts. A sub-category with no budget row contributes nothing: unplanned
   income is not a shortfall, it is income nobody forecast. */
function bxIncomeShortfall(budgets, txns, subCats, categories, y, m, transferCategoryId) {
  var bySub = {};
  var total = 0;
  if (!subCats || !subCats.length) { return { total: total, by_sub: bySub }; }
  var incomeId = bxIncomeCategoryId(categories);
  if (incomeId === null) { return { total: total, by_sub: bySub }; }
  var clean = bxExcludeTransfers(txns, transferCategoryId);
  for (var i = 0; i < subCats.length; i++) {
    var sc = subCats[i];
    if (!bxIsActive(sc)) { continue; }
    if (bxIsTransferSub(sc, transferCategoryId)) { continue; }
    if (bxCatKey(sc.belongs_to) !== incomeId) { continue; }
    var sid = bxCatKey(sc.sub_category_id);
    if (sid === null) { continue; }
    var budget = bxBudget(budgets, sid, y, m);
    if (budget === null) { continue; }
    var short = budget - bxActual(clean, sid, y, m);
    if (short > 0) { bySub[sid] = short; total += short; }
  }
  return { total: total, by_sub: bySub };
}

/* ---------- bxAvailableToBudget ---------- */
/* §4.5A — the month-level pool, the concept this app did not have, and the one
   place last month is allowed to appear. Thirteen fields.

   THE POOL IS BUILT ON PLANNED INCOME, IN FULL, WHATEVER HAS ACTUALLY ARRIVED
   (§0 ruling 6, rule 10). Money that is late is not money that is lost, and a
   plan that collapses the moment an invoice slips is not a plan. This function
   never reads an income ACTUAL for the current month — a shortfall changes
   nothing in the month it happens except that it is shown against Income, and it
   reaches the pool exactly one month later as carried_shortfall.

   It looks back EXACTLY ONE MONTH and the deduction does not chain: M is reduced
   by M-1's overspend and shortfall and by nothing older, so an overspend is paid
   for once and is then done. That is what "we always look forwards" means
   arithmetically.

   Underspend nets off nothing. The pool carries unspent money nowhere at all — a
   sub-category's own opt-in roll-over is the only mechanism in this app that
   carries anything forward.

   With no income category the object still returns all thirteen fields with
   income_category:false, and BOTH SCREENS HIDE THE BLOCK (rule 8) rather than
   render a pool that is permanently negative whatever the user does. */
function bxAvailableToBudget(budgets, txns, subCats, categories, y, m, transferCategoryId) {
  var clean = bxExcludeTransfers(txns, transferCategoryId);
  var prev = bxPrevMonth(y, m);
  var prevKey = bxMonthKey(prev.y, prev.m);
  var incomeId = bxIncomeCategoryId(categories);
  var i;

  /* rule 6 — "no predecessor" is a fact the block reports, not a clean slate it
     assumes. Any budget row at all, or any non-transfer transaction at all. */
  var prevHasData = false;
  if (budgets && budgets.length) {
    for (i = 0; i < budgets.length; i++) {
      if (budgets[i] && budgets[i].month === prevKey) { prevHasData = true; break; }
    }
  }
  if (!prevHasData) {
    prevHasData = bxByMonth(clean, prev.y, prev.m).length > 0;
  }

  /* income_planned — PLANNED, never actual (rule 10). max(0, ...) per row
     because `neg_pos` only ever ran on a legacy save, so a pre-existing negative
     income budget row is unconstrained and one would silently make the whole
     pool wrong while every internal comparison stayed self-consistent.
     assigned — rule 9: a sub-category with no budget row contributes 0. It is
     unbudgeted, not budgeted at zero. */
  var incomePlanned = 0;
  var assigned = 0;
  if (subCats && subCats.length) {
    for (i = 0; i < subCats.length; i++) {
      var sc = subCats[i];
      if (!bxIsActive(sc)) { continue; }
      if (bxIsTransferSub(sc, transferCategoryId)) { continue; }
      var sid = bxCatKey(sc.sub_category_id);
      if (sid === null) { continue; }
      var amount = bxBudget(budgets, sid, y, m);
      if (amount === null) { continue; }
      if (incomeId !== null && bxCatKey(sc.belongs_to) === incomeId) {
        if (amount > 0) { incomePlanned += amount; }
      } else {
        assigned += bxAbs(amount);
      }
    }
  }

  var over = bxOverspend(budgets, clean, subCats, categories, prev.y, prev.m, transferCategoryId);
  var shortfall = bxIncomeShortfall(budgets, clean, subCats, categories, prev.y, prev.m, transferCategoryId);
  var carriedTotal = over.total + shortfall.total;
  var starting = incomePlanned - carriedTotal;

  return {
    month: bxMonthKey(y, m),
    prev_month: prevKey,
    prev_month_has_data: prevHasData,
    income_category: incomeId !== null,
    income_planned: incomePlanned,
    carried_overspend: over.total,
    carried_shortfall: shortfall.total,
    carried_total: carriedTotal,
    starting_available: starting,
    assigned: assigned,
    unassigned: starting - assigned,
    overspend_by_sub: over.by_sub,
    shortfall_by_sub: shortfall.by_sub
  };
}

/* ---------- bxCatTotals ---------- */
/* Rolls bxSubTotals up to category_id: { budget, actual, variance }.

   IT SUMS EACH SUB-CATEGORY'S MONTH BUDGET, NEVER ITS ROLLOVER `available`
   (§4.5). A rollover pot is a fact about one sub-category over a long span; the
   moment it is added into a category total it double-counts months that have
   already been reported. The rollover figure rolls up nowhere.

   Archived sub-categories are excluded — fact 5 (`update_numbers` selecting by
   parent with no order filter, unlike every display list) is a defect, not a
   convention, and it is why the legacy header disagreed with the rows beneath it.
   Orphans are excluded too (decision 9): there is no category to attribute them
   to. Every category in `categories` gets an entry, zeros included (decision 11). */
function bxCatTotals(subTotals, subCats, categories) {
  var out = {};
  var known = Object.create(null);
  var belongs = Object.create(null);
  var i;
  var cid;
  if (categories && categories.length) {
    for (i = 0; i < categories.length; i++) {
      if (!categories[i]) { continue; }
      cid = bxCatKey(categories[i].category_id);
      if (cid === null) { continue; }
      known[cid] = true;
      if (!bxOwns(out, cid)) { out[cid] = { budget: 0, actual: 0, variance: 0 }; }
    }
  }
  if (subCats && subCats.length) {
    for (i = 0; i < subCats.length; i++) {
      var sc = subCats[i];
      if (!bxIsActive(sc)) { continue; }
      var sid = bxCatKey(sc.sub_category_id);
      if (sid === null) { continue; }
      belongs[sid] = bxCatKey(sc.belongs_to);
    }
  }
  var keys = Object.keys(subTotals || {});
  for (i = 0; i < keys.length; i++) {
    var key = keys[i];
    if (!bxOwns(belongs, key)) { continue; }
    cid = belongs[key];
    if (cid === null || !bxOwns(known, cid)) { continue; }
    var entry = subTotals[key];
    if (!entry) { continue; }
    out[cid].budget += entry.budget;
    out[cid].actual += entry.actual;
  }
  var outKeys = Object.keys(out);
  for (i = 0; i < outKeys.length; i++) {
    var t = out[outKeys[i]];
    t.variance = t.actual - t.budget;
  }
  return out;
}

/* ---------- bxHeaderTotals ---------- */
/* { income: { budget, actual, variance }, expense: { … } }, on the same
   month-budget basis as bxCatTotals. Every category that is not the income
   category is an expense, including one this payload cannot name — which is the
   same rule the sign convention already uses. With no income category the income
   block is a defined zero rather than absent.

   ARCHIVED CATEGORIES ARE EXCLUDED (decision 11). §3.9: "archived categories and
   sub-categories are hidden by default and excluded from every total (fact 5)".
   /cat/archive leaves the category's sub-categories active (§3.2), so without
   this filter their money keeps arriving in the header from a parent the UI no
   longer shows, and the header stops adding up to the rows beneath it — the
   legacy defect fact 5 records. A category id that appears in catTotals but not
   in `categories` at all is NOT archived and still counts; only an explicit
   `active === false` is excluded. */
function bxHeaderTotals(catTotals, categories) {
  var incomeId = bxIncomeCategoryId(categories);
  var income = { budget: 0, actual: 0, variance: 0 };
  var expense = { budget: 0, actual: 0, variance: 0 };
  var archived = Object.create(null);
  var c;
  if (categories && categories.length) {
    for (c = 0; c < categories.length; c++) {
      if (!categories[c] || categories[c].active !== false) { continue; }
      var acid = bxCatKey(categories[c].category_id);
      if (acid !== null) { archived[acid] = true; }
    }
  }
  var keys = Object.keys(catTotals || {});
  for (var i = 0; i < keys.length; i++) {
    var entry = catTotals[keys[i]];
    if (!entry) { continue; }
    if (bxOwns(archived, keys[i])) { continue; }
    var target = (incomeId !== null && keys[i] === incomeId) ? income : expense;
    target.budget += entry.budget;
    target.actual += entry.actual;
  }
  income.variance = income.actual - income.budget;
  expense.variance = expense.actual - expense.budget;
  return { income: income, expense: expense };
}

/* ---------- bxVariance ---------- */
/* actual - budget. The legacy convention (Budget/__init__.py:296), kept
   deliberately: with expenses stored negative, POSITIVE IS GOOD ON BOTH SIDES of
   the grid — an expense that under-spends and an income that over-earns both
   produce a positive variance. Changing it would silently invert every colour
   Bruce is used to reading. */
function bxVariance(actualCents, budgetCents) {
  if (!bxIsInt(actualCents)) {
    throw new TypeError('bxVariance: expects integer cents, got ' + String(actualCents));
  }
  if (!bxIsInt(budgetCents)) {
    throw new TypeError('bxVariance: expects integer cents, got ' + String(budgetCents));
  }
  return actualCents - budgetCents;
}

/* ---------- bxProgress ---------- */
/* §4.6 — the progress meter, replacing a three-state indicator wearing a gauge's
   clothes (fact 16: a zero point that jumped 20% → 50% → 80% across three
   branches, a printed number that silently changed meaning between remaining,
   overspend and total spend, and a saturated third branch in which a 3× and a
   30× overspend rendered identically).

   Three properties it has and the pill did not:
     1. `fraction` is monotone in spend — it never jumps because a branch changed;
     2. `label_kind` says what `label_cents` means;
     3. `over_ratio` is UNCAPPED, so 3× and 30× are distinguishable. `fraction`
        and `over_fraction` are capped at 1 for layout; `over_ratio` is null
        whenever `state` is not "over".

   `over_fraction` is clamped to [0, 1], not merely min(ratio, 1) — SPEC_04
   ADDENDUM 5, not this file's invention. §4.6's row 7 formula goes negative on an
   anomalous negative income target (reachable because `neg_pos` only ever ran on
   a legacy save), and a negative layout fraction fills a meter backwards. The
   anomaly stays fully visible in `over_ratio`, which is not clamped.

   THE GUARDS ARE EVALUATED IN ORDER AND THE FIRST MATCH WINS. Two of the
   orderings are load-bearing rather than incidental:
     * income row 4, the reversal guard, precedes `E < T`. Any negative E also
       satisfies E < T for a non-negative target, so a later reversal guard could
       never fire — and E / T would then hand back a NEGATIVE fraction, breaking
       both the capped-for-layout contract and property 1.
     * expense row 2, `actual > 0` (a refund), precedes everything that divides,
       for the same reason.

   Colour is the design language's, not the meter's: under and at use --primary,
   over uses --negative, none renders the track alone. */
function bxProgressResult(state, fraction, overFraction, overRatio, labelCents, labelKind) {
  return {
    state: state,
    fraction: fraction,
    over_fraction: overFraction,
    over_ratio: overRatio,
    label_cents: labelCents,
    label_kind: labelKind
  };
}

function bxProgress(budgetCents, actualCents, isIncome) {
  var budget = (budgetCents === null || budgetCents === undefined) ? null : budgetCents;
  if (budget !== null && !bxIsInt(budget)) {
    throw new TypeError('bxProgress: expects integer cents or null for budget, got ' + String(budgetCents));
  }
  if (!bxIsInt(actualCents)) {
    throw new TypeError('bxProgress: expects integer cents for actual, got ' + String(actualCents));
  }
  var actual = actualCents;
  var ratio;

  if (!isIncome) {
    /* 1 */ if (budget === null) {
      return bxProgressResult('none', 0, 0, null, bxAbs(actual), actual < 0 ? 'over' : 'remaining');
    }
    /* 2 */ if (actual > 0) {
      return bxProgressResult('under', 0, 0, null, bxAbs(budget) + actual, 'remaining');
    }
    /* 3 */ if (budget === 0 && actual === 0) {
      return bxProgressResult('none', 0, 0, null, 0, 'remaining');
    }
    /* 4 */ if (budget === 0 && actual < 0) {
      return bxProgressResult('over', 1, 1, null, bxAbs(actual), 'over');
    }
    var B = bxAbs(budget);
    var S = bxAbs(actual);
    /* 5 */ if (S < B) { return bxProgressResult('under', S / B, 0, null, B - S, 'remaining'); }
    /* 6 */ if (S === B) { return bxProgressResult('at', 1, 0, null, 0, 'remaining'); }
    /* 7 */ ratio = (S - B) / B;
    return bxProgressResult('over', 1, bxClamp01(ratio), ratio, S - B, 'over');
  }

  var T = budget;
  var E = actual;
  /* 1 */ if (T === null) { return bxProgressResult('none', 0, 0, null, E, 'earned'); }
  /* 2 */ if (T === 0 && E === 0) { return bxProgressResult('none', 0, 0, null, 0, 'short'); }
  /* 3 */ if (T === 0 && E > 0) { return bxProgressResult('over', 1, 1, null, E, 'earned'); }
  /* 4 */ if (E < 0) { return bxProgressResult('under', 0, 0, null, T + bxAbs(E), 'short'); }
  /* 5 */ if (E < T) { return bxProgressResult('under', E / T, 0, null, T - E, 'short'); }
  /* 6 */ if (E === T) { return bxProgressResult('at', 1, 0, null, 0, 'short'); }
  /* 7 */ ratio = (E - T) / T;
  return bxProgressResult('over', 1, bxClamp01(ratio), ratio, E - T, 'earned');
}

/* ---------- bxOpenMonthPlan ---------- */
/* The PURE planner behind POST /budget/open-month: the sub_category_ids a
   month-open would create rows for — every ACTIVE sub-category that has a budget
   row in the source month and none in the target month. The client shows this
   list before confirming, and AC-2.5 asserts the server's `created` set equals it
   exactly.

   Archived sub-categories are skipped: the legacy copied rows for them too
   (fact 2's other half), which is how a retired category quietly reappears with a
   budget every month for ever. Returned sorted, so two calls are diffable. */
function bxOpenMonthPlan(budgets, subCats, fromY, fromM, toY, toM) {
  var out = [];
  if (!subCats || !subCats.length) { return out; }
  var fromKey = bxMonthKey(fromY, fromM);
  var toKey = bxMonthKey(toY, toM);
  var hasFrom = Object.create(null);
  var hasTo = Object.create(null);
  var i;
  if (budgets && budgets.length) {
    for (i = 0; i < budgets.length; i++) {
      var row = budgets[i];
      if (!row) { continue; }
      var rid = bxCatKey(row.sub_category_id);
      if (rid === null) { continue; }
      if (row.month === fromKey) { hasFrom[rid] = true; }
      if (row.month === toKey) { hasTo[rid] = true; }
    }
  }
  for (i = 0; i < subCats.length; i++) {
    var sc = subCats[i];
    if (!bxIsActive(sc)) { continue; }
    var sid = bxCatKey(sc.sub_category_id);
    if (sid === null) { continue; }
    if (bxOwns(hasFrom, sid) && !bxOwns(hasTo, sid)) { out.push(sid); }
  }
  out.sort(bxCompare);
  return out;
}

/* Node-only export tail. A browser never defines `module`, so this is inert there
   and the functions above stay plain globals inside a <script> tag. */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    bxSum: bxSum,
    bxInflow: bxInflow,
    bxOutflow: bxOutflow,
    bxNet: bxNet,
    bxByMonth: bxByMonth,
    bxGroupBySub: bxGroupBySub,
    bxGroupByCat: bxGroupByCat,
    bxExcludeTransfers: bxExcludeTransfers,
    bxFmtCents: bxFmtCents,
    bxSmartIndex: bxSmartIndex,
    bxSuggest: bxSuggest,
    bxDaysInMonth: bxDaysInMonth,
    /* v2 — spec_04 §3.3 */
    bxDefaultMonth: bxDefaultMonth,
    bxIncomeCategoryId: bxIncomeCategoryId,
    bxSignFor: bxSignFor,
    bxActual: bxActual,
    bxBudget: bxBudget,
    bxRollover: bxRollover,
    bxSubTotals: bxSubTotals,
    bxOverspend: bxOverspend,
    bxIncomeShortfall: bxIncomeShortfall,
    bxAvailableToBudget: bxAvailableToBudget,
    bxCatTotals: bxCatTotals,
    bxHeaderTotals: bxHeaderTotals,
    bxVariance: bxVariance,
    bxProgress: bxProgress,
    bxOpenMonthPlan: bxOpenMonthPlan,
    bxCompare: bxCompare
  };
}
