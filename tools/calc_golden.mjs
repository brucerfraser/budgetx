#!/usr/bin/env node
/* calc_golden.mjs v2 — the golden-test runner for client_src/bx_calc.js
   (Round 03 Builder C; Round 04 Builder C)
   history:
   v1 — initial: JSON-driven case runner, $ref/$index resolvers, deep equality,
        throw expectations, and the legacy is_it_smart comparison for AC-5.5.
   v2 — spec_04: $sort resolver, the ported legacy roll_over_calc and its
        `legacy_rollover` case option (fact 12, AC-5.5), suite-size floor raised
        to spec_04 §3.3's 160 (85 v1 cases + at least 75 new).

   Run from the repo root:   node tools/calc_golden.mjs
   Exits 0 when every case is green; exits non-zero on the first-and-every mismatch,
   printing case name, expected and actual.

   Loading: bx_calc.js is a classic script with a guarded CommonJS tail. This repo has
   no package.json, so node treats .js as CommonJS and createRequire loads it directly —
   the SAME bytes the browser client embeds, with nothing rewritten for the test.

   The cases live in tools/calc_cases.json and are the specification of the arithmetic.
   They are data, deliberately: an expectation nobody can read is an expectation nobody
   can challenge. */

import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, '..');
const calcPath = join(repoRoot, 'client_src', 'bx_calc.js');
const casesPath = join(here, 'calc_cases.json');

const require = createRequire(import.meta.url);
const bx = require(calcPath);
const suite = JSON.parse(readFileSync(casesPath, 'utf8'));

/* ---------- the legacy algorithm, ported faithfully from
   client_code/F_Global_Logic/Global.py:70 (smarter) and :95 (is_it_smart).

   Kept here rather than in bx_calc.js because it is a museum piece: it exists only
   so a golden case can show, on the same input, that bxSuggest and the legacy
   disagree and that bxSuggest is the one that is right (spec_03 AC-5.5).

   Fidelity notes:
   * SMART is built by scanning transactions in order, so category insertion order is
     first-seen order — reproduced with a Map.
   * matching is case-SENSITIVE, as the Python is.
   * leader[k] is set to 0 then incremented once per matching CATEGORY, never per
     matching word — that is the bug.
   * Python's max(leader, key=leader.get) returns the first key holding the maximum
     in dict insertion order; since every value is 1, it returns the first inserted. */
function legacySmart(txns) {
  const smart = new Map();
  for (const row of txns) {
    if (row.category === null || row.category === undefined || row.category === '') continue;
    const words = String(row.description || '').split(/\s+/).filter((w) => w.length >= 3);
    if (!smart.has(row.category)) smart.set(row.category, []);
    const list = smart.get(row.category);
    for (const w of words) if (!list.includes(w)) list.push(w);
  }
  return smart;
}

function legacyIsItSmart(smart, description) {
  const words = String(description || '').split(/\s+/).filter((w) => w.length >= 3);
  const leader = new Map();
  for (const [k, v] of smart) {
    let m = 0;
    for (const w of words) if (v.includes(w)) m += 1;
    if (m > 0) {
      if (!leader.has(k)) leader.set(k, 0);
      leader.set(k, leader.get(k) + 1);   /* the bug: +1 per category, not per word */
    }
  }
  if (leader.size === 0) return null;
  let bestKey = null;
  let bestVal = -Infinity;
  for (const [k, v] of leader) {          /* first key at the max wins, as Python's max does */
    if (v > bestVal) { bestVal = v; bestKey = k; }
  }
  return bestKey;
}

/* ---------- the legacy roll_over_calc, ported faithfully from
   client_code/F_Global_Logic/BUDGET.py:57-98 (roll_over_calc), :20-33 (get_actual)
   and :104 (roll_date_list).

   Kept here, like legacyIsItSmart above, because it is a museum piece: it exists
   only so a golden case can show, on the same input, that bxRollover and the
   legacy disagree — and that the legacy is the one that is wrong (spec_04 AC-5.5,
   fact 12). It is NOT a reimplementation of anything this app ships.

   Fidelity notes, each one a real property of the Python:
   * roll_date_list runs from the roll-over start date to the FIRST OF THE
     SELECTED PERIOD inclusive — so the current month M is inside the loop, and
     then its actual is added a SECOND time by the return statement.
   * get_actual returns sum(amount)/100 as a float in rands, and line 86 then
     multiplies it back by 100. The round trip is reproduced exactly, drift and
     all, because smoothing it would be a different algorithm.
   * `if b < 0: if b < a: b = b - a  else: b = 0` — the clamp. When the current
     month tips the pot, the loop's last iteration sets b = 0 and the return
     statement hands back 0 + actual(M): a "budget" equal to the month's own
     actual, i.e. variance 0 and an empty pill at the precise moment the pot was
     blown.
   * the b > 0 (income) branch is `pass` — fact 13 — so income accumulates budget
     for ever and is never reduced by anything. Reproduced as a no-op. */
function legacyMonthKey(y, m) {
  return `${y}-${m < 10 ? `0${m}` : m}`;
}

function legacyRollDateList(startY, startM, endY, endM) {
  const out = [];
  let y = startY;
  let m = startM;
  while (y * 12 + (m - 1) <= endY * 12 + (endM - 1)) {
    out.push({ y, m });
    m += 1;
    if (m > 12) { m = 1; y += 1; }
  }
  return out;
}

/* get_actual(...)*100 — the float round trip, verbatim. */
function legacyActualCents(txns, subId, y, m) {
  let sum = 0;
  for (const t of txns || []) {
    if (!t) continue;
    if (String(t.category) !== String(subId)) continue;
    const d = String(t.date || '');
    if (parseInt(d.slice(0, 4), 10) !== y) continue;
    if (parseInt(d.slice(5, 7), 10) !== m) continue;
    sum += t.amount_cents;
  }
  return (sum / 100) * 100;
}

function legacyRollOverCalc(budgets, txns, subId, startY, startM, y, m) {
  const list = legacyRollDateList(startY, startM, y, m);
  if (!list.length) return 0;
  let b = 0;
  for (const p of list) {
    const key = legacyMonthKey(p.y, p.m);
    const row = (budgets || []).find(
      (r) => r && String(r.sub_category_id) === String(subId) && r.month === key,
    );
    b += row ? row.amount_cents : 0;
    const a = legacyActualCents(txns, subId, p.y, p.m);
    if (b < 0) {
      if (b < a) { b = b - a; } else { b = 0; }
    }
    /* b > 0 → `pass  # what do we actually do here???` (fact 13) */
  }
  const last = list[list.length - 1];
  return b + legacyActualCents(txns, subId, last.y, last.m);
}

/* ---------- argument resolution ----------
   {"$ref": "name"}                     → suite.fixtures[name]
   {"$index": "name"}                   → bx.bxSmartIndex(suite.fixtures[name])
   {"$call": {"fn": "...", "args":[…]}} → bx[fn](…resolved args…), recursively
   Anything else passes through untouched. $call is what lets a case assert a
   COMPOSED result — "inflow of the transfer-excluded set" — which is how the
   functions are actually used, rather than only in isolation. */
function resolve(arg) {
  if (Array.isArray(arg)) return arg.map(resolve);
  if (arg && typeof arg === 'object') {
    if (typeof arg.$ref === 'string') {
      if (!(arg.$ref in suite.fixtures)) throw new Error(`unknown fixture: ${arg.$ref}`);
      return suite.fixtures[arg.$ref];
    }
    if (typeof arg.$index === 'string') {
      if (!(arg.$index in suite.fixtures)) throw new Error(`unknown fixture: ${arg.$index}`);
      return bx.bxSmartIndex(suite.fixtures[arg.$index]);
    }
    if (arg.$call && typeof arg.$call.fn === 'string') {
      const f = bx[arg.$call.fn];
      if (typeof f !== 'function') throw new Error(`unknown export: ${arg.$call.fn}`);
      return f.apply(null, (arg.$call.args || []).map(resolve));
    }
    /* {"$sort": {"fn": "bxCompare", "of": [...]}} → the array sorted THROUGH the
       exported comparator. A comparator can only be shown to be a total order by
       sorting something with it, so this is what AC-12.2's case asserts. */
    if (arg.$sort && typeof arg.$sort.fn === 'string') {
      const cmp = bx[arg.$sort.fn];
      if (typeof cmp !== 'function') throw new Error(`unknown export: ${arg.$sort.fn}`);
      return resolve(arg.$sort.of).slice().sort(cmp);
    }
    const out = {};
    for (const k of Object.keys(arg)) out[k] = resolve(arg[k]);
    return out;
  }
  return arg;
}

/* ---------- deep equality ----------
   Own enumerable keys only, so a null-prototype object (bx_calc's word sets)
   compares equal to the plain object a JSON expectation produces. */
function deepEqual(a, b) {
  if (a === b) return true;
  if (typeof a === 'number' && typeof b === 'number') return a === b;
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const ka = Object.keys(a);
  const kb = Object.keys(b);
  if (ka.length !== kb.length) return false;
  for (const k of ka) {
    if (!Object.prototype.hasOwnProperty.call(b, k)) return false;
    if (!deepEqual(a[k], b[k])) return false;
  }
  return true;
}

const show = (v) => (v === undefined ? 'undefined' : JSON.stringify(v));

/* ---------- run ---------- */
const failures = [];
let passed = 0;

console.log(`bx_calc golden suite — ${suite.cases.length} cases`);
console.log(`  calc:  ${calcPath}`);
console.log(`  cases: ${casesPath}`);
console.log('');

for (const c of suite.cases) {
  const fn = bx[c.fn];
  let ok = false;
  let actual;
  let detail = '';

  /* A case may assert a RESOLVED EXPRESSION instead of a direct call — used for
     $sort, where what is being asserted is the order a comparator produces
     rather than any single return value. */
  if (!c.fn && c.value !== undefined) {
    try {
      actual = resolve(c.value);
      ok = deepEqual(actual, c.expect);
    } catch (err) {
      actual = `${err.name}: ${err.message}`;
      ok = false;
      detail = 'threw unexpectedly';
    }
    if (ok) {
      passed += 1;
      console.log(`  ok  ${c.name}`);
    } else {
      failures.push({ name: c.name, expected: show(c.expect), actual: show(actual), detail });
      console.log(`FAIL  ${c.name}`);
      console.log(`        expected: ${show(c.expect)}`);
      console.log(`        actual:   ${show(actual)}`);
      if (detail) console.log(`        note:     ${detail}`);
    }
    continue;
  }

  if (typeof fn !== 'function') {
    failures.push({ name: c.name, expected: `export ${c.fn}`, actual: 'not exported' });
    console.log(`FAIL  ${c.name} — ${c.fn} is not exported by bx_calc.js`);
    continue;
  }

  try {
    const args = (c.args || []).map(resolve);
    actual = fn.apply(null, args);
    /* "pluck" keeps row-returning cases readable: assert the transaction_ids the
       function selected, not a screenful of re-quoted row objects. */
    if (c.pluck && Array.isArray(actual)) actual = actual.map((r) => r[c.pluck]);
    if (c.throws) {
      ok = false;
      detail = 'no error thrown';
    } else {
      ok = deepEqual(actual, c.expect);
    }
  } catch (err) {
    actual = `${err.name}: ${err.message}`;
    if (c.throws) {
      ok = String(err.message).includes(c.throws);
      if (!ok) detail = `error message did not contain "${c.throws}"`;
    } else {
      ok = false;
      detail = 'threw unexpectedly';
    }
  }

  /* AC-5.5: on the flagged case, compute the legacy answer too and require that it
     DIFFERS from bxSuggest's. If the legacy ever agreed, this case would no longer be
     demonstrating the fix and the suite says so. */
  let legacyLine = null;
  if (ok && c.legacy_compare) {
    const fixture = suite.fixtures[c.legacy_compare.fixture];
    const legacyAnswer = legacyIsItSmart(legacySmart(fixture), c.legacy_compare.description);
    const ours = actual && actual.sub_category_id !== undefined ? actual.sub_category_id : null;
    legacyLine = `        legacy is_it_smart → ${show(legacyAnswer)} | bxSuggest → ${show(ours)} (score ${actual ? actual.score : 'n/a'})`;
    if (legacyAnswer === ours) {
      ok = false;
      detail = 'legacy answer did NOT differ — this case no longer demonstrates the fix';
    } else if (c.legacy_compare.legacy_expect !== undefined
               && legacyAnswer !== c.legacy_compare.legacy_expect) {
      ok = false;
      detail = `legacy answer was ${show(legacyAnswer)}, case says it should be ${show(c.legacy_compare.legacy_expect)}`;
    }
  }

  /* AC-5.5 / fact 12: on the flagged rollover case, run the ported legacy
     roll_over_calc on the SAME fixtures and require that the two answers DIFFER
     in the specific way the spec names — the legacy handing back a "budget"
     equal to the month's own actual (variance 0, "exactly on budget"), while
     bxRollover reports overspent > 0 and remaining == 0. If the legacy ever
     agreed, this case would no longer be demonstrating the fix and the suite
     says so instead of quietly passing. */
  let rolloverLines = null;
  if (ok && c.legacy_rollover) {
    const lr = c.legacy_rollover;
    const budgets = suite.fixtures[lr.budgets];
    const txns = suite.fixtures[lr.txns];
    if (!budgets || !txns) {
      ok = false;
      detail = `legacy_rollover names an unknown fixture (${lr.budgets} / ${lr.txns})`;
    } else {
      const start = { y: parseInt(lr.roll_over_date.slice(0, 4), 10), m: parseInt(lr.roll_over_date.slice(5, 7), 10) };
      const legacyRaw = legacyRollOverCalc(budgets, txns, lr.sub_category_id, start.y, start.m, lr.y, lr.m);
      const legacyCents = Math.round(legacyRaw);
      const monthActual = Math.round(legacyActualCents(txns, lr.sub_category_id, lr.y, lr.m));
      rolloverLines = [
        `        legacy roll_over_calc → budget ${legacyCents} (raw ${legacyRaw}), month actual ${monthActual}`,
        `        legacy variance (actual - budget) → ${monthActual - legacyCents}`,
        `        bxRollover → available ${actual.available}, spent ${actual.spent}, overspent ${actual.overspent}, remaining ${actual.remaining}`,
      ];
      if (legacyCents !== lr.legacy_expect_cents) {
        ok = false;
        detail = `legacy roll_over_calc returned ${legacyCents}, case says it should be ${lr.legacy_expect_cents}`;
      } else if (legacyCents !== monthActual) {
        ok = false;
        detail = `legacy answer ${legacyCents} is not equal to the month's own actual ${monthActual} — this case no longer demonstrates fact 12`;
      } else if (legacyCents === actual.available) {
        ok = false;
        detail = 'legacy answer did NOT differ from bxRollover.available — this case no longer demonstrates the fix';
      } else if (!(actual.overspent > 0) || actual.remaining !== 0) {
        ok = false;
        detail = `bxRollover must report overspent > 0 and remaining == 0 here, got overspent ${actual.overspent} remaining ${actual.remaining}`;
      }
    }
  }

  if (ok) {
    passed += 1;
    console.log(`  ok  ${c.name}`);
    if (legacyLine) console.log(legacyLine);
    if (rolloverLines) for (const l of rolloverLines) console.log(l);
  } else {
    failures.push({ name: c.name, expected: c.throws ? `throws containing "${c.throws}"` : show(c.expect), actual: show(actual), detail });
    console.log(`FAIL  ${c.name}`);
    console.log(`        expected: ${c.throws ? `throws containing "${c.throws}"` : show(c.expect)}`);
    console.log(`        actual:   ${show(actual)}`);
    if (detail) console.log(`        note:     ${detail}`);
    if (legacyLine) console.log(legacyLine);
    if (rolloverLines) for (const l of rolloverLines) console.log(l);
  }
}

console.log('');
/* spec_03 §3.3 set the floor at 40; spec_04 §3.3 keeps all 85 v1 cases green and
   adds at least 75 more, so the floor is now 160. A suite that shrinks is a suite
   somebody deleted a case from. */
const MIN_CASES = 160;
if (suite.cases.length < MIN_CASES) {
  console.log(`FAIL  suite size — spec_04 §3.3 requires at least ${MIN_CASES} cases (85 v1 + >=75 new), found ${suite.cases.length}`);
  console.log(`${passed}/${suite.cases.length} cases green, but the suite is too small.`);
  process.exit(1);
}

if (failures.length) {
  console.log(`${passed}/${suite.cases.length} green — ${failures.length} FAILED:`);
  for (const f of failures) console.log(`  - ${f.name}: expected ${f.expected}, actual ${f.actual}`);
  process.exit(1);
}

console.log(`${passed}/${suite.cases.length} cases green. bx_calc.js golden suite PASS.`);
process.exit(0);
