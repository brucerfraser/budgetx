/* bx_calc.js v1 — Budget X money core (Round 03, Builder C)
   history:
   v1 — initial: bxSum/bxInflow/bxOutflow/bxNet, bxByMonth, bxGroupBySub/bxGroupByCat,
        bxExcludeTransfers, bxFmtCents, bxSmartIndex/bxSuggest. Integer cents throughout.

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
    bxDaysInMonth: bxDaysInMonth
  };
}
