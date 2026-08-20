# Budget X — Spec 03: Transactions — the first write path, the money core, and the triage inbox

**Status:** **APPROVED AND LOCKED — Bruce, 2026-08-20.** Build against this text as written.
**Do not edit the approved text in place**; corrections go in §12 as dated addenda.

**Round:** 03 · **Written:** 2026-08-20 · **Source:** Migration Blueprint + `DEBRIEF_S02.md`
(FINAL 14/14) + Bruce's rulings of 2026-08-20 (§0)

**Build models:** Opus orchestrator. **Builder S (server)** on **Opus** — it opens the first write
path to a business table. **Builder C (calc)** on **Opus** — `bx_calc.js` is the money core and
every later round's arithmetic rests on it. **Builders D and M (HTML clients)** on **Sonnet** —
localised client work. Record who actually ran each role in the debrief.

---

## 0. BRUCE'S RULINGS FOR THIS ROUND — 2026-08-20

Recorded first because six sections below depend on them.

1. **`--error` is amended to a WCAG-AA-passing red.** The §3.4 token block of spec_02 was locked
   verbatim; this spec amends it (§3.6) and re-locks the amended block. `#D64D47` (~3.6:1 on
   `--surface-1`) becomes **`#F2867C`**, and AC-7 requires the contrast to be **measured**, not
   assumed.
2. **44 px is a design-language rule on both form factors**, not a mobile-only one. Every
   interactive control in every client, desktop included, is ≥44 px in its smaller dimension.
   The desktop sidebar SIGN OUT (currently 228×41) is corrected in the canon.
3. **The desktop grid is a full-width table plus a right-hand detail rail.** `d-trans` fills the
   content area; selecting a row opens a persistent detail/edit rail; the triage inbox lives in
   that rail. The ~520 px-in-1020 px column `d-dash` inherited is retired.
4. **The write path this round is categorise + edit + soft-delete.** This requires the `active`
   column on `transactions` (§2.5) — a schema click, so **this round does NOT close unattended**.
5. **Money crosses the wire as integer cents.** The client never sees a float. See the correction
   in §0.1 — the boundary is simpler than it looked.
6. **The Forms app's auto-categoriser is ported into the client canon** and leads every triage
   card. Its ranking bug is fixed and the fix is golden-tested (§3.3).
7. **Real transaction data may be written freely.** Bruce's words: *"I'm ok if you test on my real
   data, at the end we'll be testing uploads so we can do a manual hard-delete of all rows and then
   send some variations of bank files. So go wild on my own data."* The standing "never test
   against Bruce's real budget data" rule is **suspended for the `transactions` table only**.
8. **On the structural tables, create `ZZ`-prefixed test rows rather than touching real ones**
   (Bruce, 2026-08-20, confirming §2.6: *"yes — for the rest add your own ZZ-… test rows"*). This
   is what finally closes S02's open gap: **`archived: true` has never travelled the live server
   path**, because `accounts` holds 7 rows and 0 archived, and S02 could only prove the filter with
   a route mock. Bruce seeds two real `ZZ` accounts at the §3.8 park — one active, one archived —
   and round 03 proves the whole path end to end on real rows, across all five clients
   (§2.6, AC-3.5).
9. **`docs/cowork_project_instructions.md` is committed as-is** before the round's first working
   commit (§3.7).
10. **Bruce will make the schema click** (§3.8): *"happy to click schema if needs be"*. The round
    parks at that point and resumes on his confirmation.

### 0.1 A correction to ruling 5, found while writing this spec

The ruling was written on the assumption that `transactions.amount` holds rands as a float and
would need `round(amount * 100)`. **It does not.** The column already holds **integer cents**,
stored in Anvil's float-typed number column:

- `server_code/csv_handler.py:157–160` — `d['amount'] = int(math.trunc(d['amount']*100))` on
  every imported row.
- `client_code/F_Components_Mobile/Transactions_Mobile/__init__.py:195` — the running totals
  render as `"Inflow: R{a:.2f}".format(a=i / 100)`.
- The same `/100` on display and `*100` on save appears in `add_transaction`,
  `edit_transaction`, `Budget_Mobile`, `Sub_category_mobile` and `Settings`.

**`budgets.budget_amount` and `accounts.recon_amount` are in cents too**, by the same evidence.

So the boundary is a *type* conversion, not a *scale* conversion: `int(round(amount))`, with an
assertion that the value was already integral. **A multiply by 100 anywhere in this round would
silently inflate every figure in the app by 100×**, and AC-2.5 exists specifically to catch it.

---

## 1. WHY

Round 02 built a shell with nothing in it. This round puts the app's largest and most-used
screen inside that shell, and in doing so it crosses three thresholds at once:

- **The first write to a business table.** Everything before this was read-only. From here the app
  can change Bruce's data, so the read-back rule stops being theory: with no audit log, *a write is
  proven by fetching the record back independently, never by the endpoint's own `ok:true`.*
- **The money core.** `client_src/bx_calc.js` is created here — integer-cents-only, node
  golden-tested, embedded byte-identically in every client from now on. Rounds 04, 05 and 07 are
  all arithmetic rounds and all of them rest on this file. **It is the single most important
  artefact of the migration and it is built once, correctly, in the quietest round that can hold
  it.**
- **The interaction bar.** A swipeable triage inbox that empties a month of uncategorised
  transactions in seconds is the first thing in this app that should feel *good* rather than
  merely correct. The beauty mandate has been decorative so far; here it does work.

The round also settles the desktop grid, makes the `data-*` hook set uniform, and replaces the
one Forms screen with a known structural defect — mobile Transactions cannot scroll at all
(`scrollHeight == clientHeight` at every width), which will clip rather than scroll the moment it
holds more rows.

**This round is still invisible at the app root.** The Forms app keeps serving at
`https://budget-x.anvil.app` untouched.

---

## 2. WHAT MUST NOT CHANGE

1. **The app root.** Keeps serving the Forms app. No endpoint at `/`, startup form stays `Frame`.
2. **`client_code/`** — not one byte. Both Forms UI trees stay untouched. **This is now load-bearing
   in a new way:** the Forms app reads `transactions.amount` as cents and knows nothing about
   `active`, so anything this round writes must leave the Forms app working. AC-9 proves it.
3. **The five original server modules** — `ServerModule1`, `account_work`, `budget_work`,
   `csv_handler`, `transaction_work`. No edits. The S01 platform-authored exemption stands
   (Anvil's injected imports, `runtime_options` rewrites, permission-bit changes are logged, not
   counted) and `ls -l tools/githooks/` is re-checked immediately after any service change.
4. **`ServerApi.py` is frozen.** The token spine passed review in S01 and S02. If a builder
   believes it needs changing, STOP and park.
5. **Schema — exactly ONE change, and Bruce makes it.** A single new column:
   **`transactions.active`, type `bool`**. Nothing else: no new table, no other column, no type
   change, no `client:`/`server:` change on any existing table. **This round therefore does not
   close unattended** — it parks at the schema click (§3.8) and resumes after Bruce confirms.
6. **Business data — `transactions` is open; the structural tables take `ZZ` rows only.** Per §0
   rulings 7 and 8:
   - **`transactions`: writable, real rows included.** Create, edit, categorise and archive
     freely. Every row touched is recorded (§8 AC-11) so the round's effect on the table is fully
     enumerated, but no permission is needed to touch one.
   - **`accounts`, `categories`, `sub_categories`, `budgets`, `settings`: no existing row may be
     created over, edited or archived.** These are the app's *structure*, not its data — a CSV
     re-import regenerates transactions but regenerates none of them. **New `ZZ`-prefixed rows may
     be added** where a test needs one, and only where a test needs one.
   - **The `ZZ` rows are enumerated in advance and Bruce creates them**, at the same park as the
     schema click (§3.8) — because this round opens a write path to `transactions` and to nothing
     else, and inventing an `accounts` write endpoint just to seed test data would be a worse
     trade than one extra line in a click Bruce is already making. **Exactly two `accounts`
     rows:** `ZZ-TEST-ACTIVE` / `ZZ Test Active` with `archived` **unticked**, and
     `ZZ-TEST-ARCHIVED` / `ZZ Test Archived` with `archived` **ticked**. Nothing else — no `ZZ`
     row in `categories`, `sub_categories`, `budgets` or `settings`, because the existing 14
     categories and 57 sub-categories are enough to categorise a transaction and set it back, and
     transactions are expendable.
   - **The two `ZZ` accounts are left in place at round close**, listed in the debrief. There is
     no hard-delete path and inventing one for cleanup would be worse than the clutter; the
     archived one is invisible to every client already, and Bruce can archive the active one from
     the Forms app's Settings screen whenever he likes. Round 06 owns `accounts` writes and may
     retire them properly.
   - `users`: the Anvil Users service's own bookkeeping on test accounts (`last_login`,
     `n_password_failures`) is the platform writing and is permitted; the S01 exemption for
     deliberate logged test-account provisioning stands, and none is expected.
   - **Hard deletes are forbidden anywhere, on any table, including on rows this round created.**
     Soft-delete by preference is the standing rule and this round is the one that gives
     `transactions` the column to honour it.
7. **The GitHub↔Anvil sync stays UNLINKED.** Deploy = `git push anvil master`, mirrored to
   `origin`. Never force-push. `git fetch anvil && git merge --ff-only anvil/master` first.
8. **`GET /app/bootstrap`'s existing response is frozen.** This round may only **ADD** — a new
   optional query parameter and a new top-level key that appears only when it is passed. A call
   with no query string must return a body whose key-set still **exactly equals** spec_02 §4.
9. **`x`, `d-dash` and `m-dash` keep working.** They are re-cut this round (the canon changes
   underneath them) but their behaviour is unchanged and spec_02's AC-4, AC-5, AC-6 and AC-8 are
   re-proven against the new builds (AC-10.7).

---

## 3. SCOPE

Two server modules (one new, one v2), one new canon file, two canon files at v2, two new HTML
clients, three re-cut HTML clients, one schema click, one housekeeping commit. Nothing else.

### 3.0 Builder ownership — the parallel plan

| Builder | Model | Owns (nobody else may touch) |
|---|---|---|
| **S** — server | Opus | `server_code/ServerTxn.py` (new) · `server_code/ServerAppData.py` (v2) · `tools/api.py` |
| **C** — calc | Opus | `client_src/bx_calc.js` (new) · `tools/calc_golden.mjs` + `tools/calc_cases.json` (new) |
| **D** — desktop | Sonnet | `client_src/bx_core.css` (v2) · `client_src/bx_core.js` (v2) — **the canon** · slug `d-trans` · re-cut of slugs `x` and `d-dash` |
| **M** — mobile | Sonnet | slug `m-trans` · re-cut of slug `m-dash` |
| **Orchestrator** | Opus | `CLAUDE.md` amendment · `docs/specs/spec_03.md` addenda · the housekeeping commit (§3.7) · integration, deploy, ledger, debrief |

**Order of work.** All four builders start together.

- **C is on the critical path and starts first among equals.** `bx_calc.js` has no dependency on
  anything else in the round — it is a pure function library over the §4 shapes — and both client
  builders embed it. C must hand back a green golden-test run **before** D or M begin their
  arithmetic-dependent work; until then D and M build layout and interaction against the §5
  fixtures.
- **D authors the canon; M consumes it.** Same as round 02: M builds against the §5 fixtures and
  the §3.6 token block until `bx_core.*` v2 exists, then embeds it verbatim and hash-checks.
- **S builds to the §4 contract**, which is fixed before anyone starts.

The orchestrator integrates only when each builder's own gate is clean (§3.9), then deploys,
basic-tests, and dispatches the review cycle **on the round as a whole**. The review gate never
fragments per builder.

Upload/promote discipline during the build: builders may round-trip drafts on `zz-b03-d`,
`zz-b03-m`, `zz-b03-x` freely. The real slugs are promoted by the orchestrator only, each with its
ledger line written into the debrief **as part of the promote step** (S01 Addendum 6 — never
afterwards).

### 3.1 `server_code/ServerTxn.py` — new module (Builder S)

Self-contained per the standing pattern: declares its own `ApiError` / `api_http` / `require_auth`
(copy the shapes from `ServerApi`, do not import across modules), `vN` header stamp + history line,
all `app_tables` access inside function bodies, JSON explicit, non-200s **returned** never raised,
headers read **case-insensitively** (S01's lowercase-header lesson).

**This is the first module in the app that writes. Four rules bind every endpoint in it:**

- **The server owns identity and derived fields.** `transaction_id` and `hash` are computed
  server-side on every path. A caller-supplied `transaction_id` on create, or a caller-supplied
  `hash` anywhere, is **ignored, never stored** — the S02 `uploaded_by` lesson, applied to a
  business table.
- **Whitelist, never blacklist.** Each endpoint accepts an exact set of keys; unknown keys are
  ignored silently. There is no "update whatever you send".
- **Every write returns the row it wrote, read back from the table** — not the payload it was
  given, and not an echo of its own in-memory dict. With no audit log this is the only proof.
- **No hard delete exists in this module.** There is no `.delete()` call anywhere in the file, and
  AC-2.6 proves it by AST walk of the pushed source.

Five endpoints, all Bearer-gated via `require_auth()`, all returning the uniform 401
`{"ok": false, "error": "unauthorized"}` with no data keys on any auth failure:

**`POST /txn/categorise`** — the inbox's endpoint, and the only batch one.
Body: `{"items": [{"transaction_id": "str", "category": "str|null"}, …]}`, 1–200 items.
`category` is a `sub_category_id` that must exist in `sub_categories`, **or** the transfer sentinel
`ec8e0085-8408-43a2-953f-ebba24549d96`, **or** `null` (uncategorise). Any other value → the whole
batch is rejected 400, nothing written. Response: `{"ok": true, "updated": [<row>, …]}` where each
row is a §4.2 transaction object **read back from the table after the write**.

**`POST /txn/update`** — single row. Body: `{"transaction_id": "str", "fields": {…}}`.
Accepted fields, and nothing else: `date` (ISO `YYYY-MM-DD`), `description` (str),
`amount_cents` (int), `notes` (str), `category` (as above), `account` (an `acc_id` that must
exist), `transfer_account` (an `acc_id` or null). If `date`, `amount_cents` or `account` changes,
the server **recomputes `hash`** by the legacy formula (§4.4) so the Forms app's duplicate
detection keeps working. Response: `{"ok": true, "transaction": <row>}`, read back.

**`POST /txn/create`** — single row. Body: the same accepted field set, with `date`,
`amount_cents` and `account` required. Server mints `transaction_id` (`uuid4`), computes `hash`,
sets `active = True`. Response: `{"ok": true, "transaction": <row>}`, read back.

**`POST /txn/archive`** — soft delete. Body: `{"transaction_ids": ["str", …]}`, 1–200 items.
Sets `active = False`. Response: `{"ok": true, "archived": ["str", …]}` — the ids confirmed
**by re-reading each row and checking `active is False`**, not the ids that were sent.

**`POST /txn/restore`** — the inverse; sets `active = True`. Same shape. **This endpoint exists so
that every write this round makes is reversible from the API**, which is what makes AC-11's
enumeration meaningful.

Not-found on any single-row endpoint → `404 {"ok": false, "error": "not_found"}`, no data keys.
Validation failure → `400 {"ok": false, "error": "bad_request", "detail": "<short reason>"}`;
`detail` names the field, never echoes a value.

### 3.2 `server_code/ServerAppData.py` — v2 (Builder S)

**One additive change.** `GET /app/bootstrap` gains an optional query parameter:

- `?include=transactions` → the response gains **one** new top-level key, `transactions`
  (§4.2). Any other `include` value is ignored.
- **With no query string the response is byte-shape-identical to v1** — same key-set, no
  `transactions` key at all. AC-1.1 proves it, and it is what keeps `d-dash`/`m-dash` honest.

The transaction set returned is **every row where `active` is not `False`** — see §4.3 on why the
test is `is not False` and not `is True` — sorted by `date` descending then `transaction_id`
ascending (a total order, so the payload is reproducible). No windowing this round: the whole
history goes in one call, because the client does all display maths locally and every later screen
needs the same set. **AC-13.6 measures what that costs and names it.**

Bump the header stamp to `v2` with a one-line history entry; `/build/version` must report it. The
module stays read-only: still no `add_row`, no `update`, no `delete`, proven by AST walk.

### 3.3 `client_src/bx_calc.js` — new canon file (Builder C)

**The money core. Integer cents in, integer cents out, no floating-point arithmetic on money
anywhere in the file.** No DOM access, no `fetch`, no globals beyond its own namespace — a pure
function library, so it can be `import`ed by the golden-test runner under node and embedded
verbatim in a browser client without change.

Required exports (names are part of the contract; later rounds call them):

| Function | Contract |
|---|---|
| `bxSum(cents[])` | Integer sum. Returns `0` for an empty array. |
| `bxInflow(txns)` / `bxOutflow(txns)` | Sum of `amount_cents > 0` / `< 0`. Outflow returns a **negative** integer, matching the Forms app. |
| `bxNet(txns)` | `bxInflow + bxOutflow`. |
| `bxByMonth(txns, y, m)` | Rows whose `date` falls in that calendar month, first day to last day inclusive — the `Transaction.date_me()` semantics. |
| `bxGroupBySub(txns)` | `{sub_category_id: cents}`, with uncategorised under the key `null`. |
| `bxGroupByCat(txns, subCats)` | Rolls sub-category totals up to `category_id`. |
| `bxExcludeTransfers(txns, transferCategoryId)` | Drops rows whose `category` is the sentinel. **Transfers are not income and not expenditure**; every total that is about spending uses this first. |
| `bxFmtCents(cents)` | `R1,234.56`, negatives in parentheses — `(R1,234.56)`. Delegates formatting only; no rounding. |
| `bxSmartIndex(txns)` | Builds the suggestion index: for every row with a non-null `category`, every whitespace-separated word of `description` with `length >= 3`, mapped category → word set. |
| `bxSuggest(index, description)` | Returns `{sub_category_id, score}` or `null`. |

**Three things `bxSuggest` must do that the Forms app's `is_it_smart` does not:**

1. **Score by match count, not by presence.** The legacy implementation increments `leader[k] += 1`
   for any category with at least one matching word, so **every matching category scores exactly 1**
   and `max()` returns whichever key was inserted first — the suggestion is effectively arbitrary
   whenever two categories match. `bxSuggest` scores by the **number of matching words**.
2. **Break ties deterministically** — highest score, then the category that appears on the most
   recent transaction, then `sub_category_id` ascending. A suggester that returns different answers
   on the same input cannot be golden-tested.
3. **Return the score**, so the client can lead with a strong suggestion and stay quiet on a weak
   one (`score < 2` renders as a suggestion the user must confirm rather than a swipe-right
   default).

**Golden tests — `tools/calc_golden.mjs` + `tools/calc_cases.json`, run under node, committed.**
At least **40** cases, and they must include: empty inputs; a single row; negative-only and
positive-only sets; **a set whose float-arithmetic equivalent would drift** (e.g. cents summing
across values that lose precision as rands — the test asserts the exact integer); month boundaries
on a 28-, 30- and 31-day month, and a leap February; transfers included and excluded; uncategorised
rows in every grouping function; a `bxSuggest` tie that the legacy implementation gets wrong, with
the correct answer as the expectation; and a `bxSuggest` case with no match at all.

The runner exits non-zero on any mismatch and prints case name, expected and actual. **A green run
is Builder C's gate and its output goes in the debrief.**

### 3.4 `client_src/bx_core.css` and `bx_core.js` — v2 (Builder D)

The canon gains what a write-capable screen needs. Both files keep their existing contents working
unchanged; this is addition plus the three corrections below.

**`bx_core.js` v2 adds:**

- `bxWrite(path, body, opts)` — the **optimistic write** helper. Applies the change to the local
  model and repaints immediately, fires the request in the background, and on failure **rolls the
  local model back and raises a toast naming what did not save**. It never blocks a repaint on the
  network, which is the 1-second rule applied to writes. It also **serialises writes to the same
  `transaction_id`**, so a fast double-tap cannot land two conflicting updates out of order.
- `bxSheet(opts)` — a bottom sheet on mobile, a centred modal on desktop, from one call. Focus is
  trapped, `Escape` and a backdrop tap close it, focus returns to the invoking element.
- `bxConfirm(opts)` — a styled two-button confirm returning a promise. **It exists so that nothing
  in this app ever needs `window.confirm`**, which the no-dialog rule forbids and AC-14.3 greps for.
- `bxFmtCents(n)` — a thin re-export of `bx_calc.js`'s formatter, so pages have one money
  formatter, not two.

**Three corrections to v1, each from an S02 finding:**

- **`fmtR()` is deprecated, not deleted.** It takes rands and this app now moves cents; leaving it
  callable is how a later round accidentally renders every figure 100× too small. It keeps working,
  gains a comment saying so, and **no client in this round may call it** — AC-7.6.
- **The desktop sidebar button honours the 44 px rule** (§0 ruling 2).
- **The `data-*` hook set is made uniform** (§3.5) — S02's `d-dash`-has-no-`data-primary`
  inconsistency is closed here.

**`bx_core.css` v2 adds** the styles for: the desktop table + detail rail grid (§3.6), the mobile
transaction row and the month header, the swipe deck (transform-based, GPU-composited), the bottom
sheet, the confirm, and the amount treatment — `--primary` for positive, `--on-surface` for
negative, **never red**; `--error` is for errors only, which is why its contrast matters.

**The amended token block** replaces spec_02 §3.4's, verbatim, in every client:

```css
:root {
  --surface-0: #191C1A;        /* page */
  --surface-1: #212925;        /* raised card */
  --surface-2: #2A332E;        /* higher card / sheet */
  --surface-variant: #404943;
  --on-surface: #E1E3DF;
  --on-surface-variant: #C0C9C1;
  --primary: #1EB980;          /* Rally green */
  --primary-container: #005235;
  --on-primary-container: #73FBBC;
  --outline: #8A938C;
  --negative: #B87C4C;         /* Amount Negative — amber, not red */
  --error: #F2867C;            /* amended R03: #D64D47 failed WCAG AA on --surface-1 */
  --radius: 18px;
  --radius-sm: 12px;
  --shadow-1: 0 2px 12px rgba(0,0,0,.35);
  --shadow-2: 0 8px 30px rgba(0,0,0,.45);
  --motion: 200ms cubic-bezier(.2,.7,.3,1);
  --font-head: 'Eczar', serif;
  --font-body: 'Roboto Condensed', sans-serif;
}
```

**Carried forward from S02 as binding rules, not advice:**

- **The non-blocking fonts pattern is mandatory in every client** — `media="print"` +
  `onload="this.media='all'"` + a `<noscript>` fallback. A render-blocking `<link rel="stylesheet">`
  defers execution of every later `<script>`, including one at the end of `<body>`; S02 measured
  970 ms → 44 ms. Any page in this round that loads the fonts the obvious way fails AC-13.3.
- **Every embedded canon block is compared by HASH, never containment.** S02's `m-dash` shipped
  `canon + "\n"` past a containment check.
- No `<script src=`, no CDN, no build step. The file is the artefact.

### 3.5 The `data-*` hook set — part of the deliverable

Specified here so it is uniform from the start across all five clients. Hooks are what make §7's
"reproducible by anyone, including the reviewers" true, and S02 lost a gate to an ad-hoc one.

| Hook | On | Carries |
|---|---|---|
| `data-primary` | the page's single primary action | — |
| `data-nav="<screen>"` | each sidebar / nav item | `dashboard`, `budget`, `transactions`, `reports`, `settings`, `signout` |
| `data-txn-row="<transaction_id>"` | each rendered transaction row/card | — |
| `data-txn-amount` | the amount element inside a row | `data-cents="<int>"` — **the raw integer**, so a reviewer can recompute a total from the DOM without parsing `R1,234.56` |
| `data-txn-category` | the category element inside a row | `data-sub="<sub_category_id\|>"` (empty = uncategorised) |
| `data-total="<inflow\|outflow\|net>"` | each running total | `data-cents="<int>"` |
| `data-scroller` | the single scrollable region of the page | — |
| `data-inbox` | the triage deck container | `data-remaining="<int>"` |
| `data-inbox-card` | the top card of the deck | `data-txn="<transaction_id>"` |
| `data-suggestion` | the suggestion chip on an inbox card | `data-sub="<sub_category_id>"`, `data-score="<int>"` |
| `data-month` | the month selector | `data-value="YYYY-MM"` |
| `data-sheet` | any open sheet/modal | `data-kind="edit\|confirm\|picker"` |

`d-dash`, `m-dash` and `x` are re-cut to carry the `data-nav` and `data-primary` hooks uniformly.

### 3.6 The two new clients

Both are **complete, self-contained HTML files**: inline CSS and JS, no external resource except
the Google Fonts stylesheet, loaded non-blocking. Both embed `bx_core.css`, `bx_core.js` and
`bx_calc.js` verbatim.

**Both make exactly ONE data request per page open:**
`GET /app/bootstrap?include=transactions`. Everything after that — month filtering, totals,
grouping, search, suggestions — is computed locally from that payload. Writes go out through
`bxWrite()` and never trigger a refetch; the local model is updated from the write's read-back
response.

#### Slug `d-trans` — desktop transactions (Builder D), 1280-first

Bruce's ruling 3: **full-width table plus a right-hand detail rail.**

- **Sidebar** as `d-dash`, with TRANSACTIONS now highlighted and linked; DASHBOARD keeps its link;
  BUDGET, REPORTS, SETTINGS remain visibly disabled with `aria-disabled="true"`.
- **Header strip:** the month selector (`◀ August 2026 ▶`, plus a "This month" reset), a search
  box, an "Uncategorised only" toggle, and the three running totals — Inflow, Outflow, Net —
  computed by `bx_calc.js` over the *currently filtered* set, each carrying `data-cents`.
- **The table** fills the remaining width: Date · Description · Account · Category · Amount.
  Sortable by clicking a column head (date descending is the default; the sort is client-side and
  stable). Amounts right-aligned in Eczar, positive in `--primary`, negative in `--on-surface`.
  Uncategorised rows carry a quiet dot, not an alarm.
- **The detail rail** (right, ~380 px, persistent): selecting a row opens it for editing — date,
  description, amount, account, category, notes — with Save, Archive and a Cancel. Save is
  optimistic. Archive asks via `bxConfirm()` and is reversible from a toast ("Archived. Undo") for
  10 seconds, which calls `/txn/restore`.
- **The triage inbox lives in the rail**, launched from a header button that shows the
  uncategorised count for the current month. Keyboard-driven on desktop: `→` accepts the
  suggestion, `←` opens the picker, `↓` skips, `Esc` closes. Every accept is one item on a batch
  that flushes to `/txn/categorise` when the deck empties or the rail closes — **not one request
  per card**.
- **Only the table region scrolls** (`data-scroller`); the sidebar, header strip and rail are fixed.

#### Slug `m-trans` — phone transactions (Builder M), 390-first

Designed for thumbs. **This screen replaces the one Forms screen that cannot scroll at all**, so
its scroller is not incidental — it is the point.

- **Fixed top bar (56 px):** the month selector, centred, with chevrons either side.
- **Fixed bottom bar (72 px):** Search · Uncategorised · **Add** (primary, centre) · Triage · with
  the uncategorised count as a badge on Triage. Every target ≥44 px.
- **Scrollable content between the bars** (`data-scroller`), grouped by day with a small sticky day
  header, one card per transaction: description and account on the left, amount right in Eczar,
  category as a coloured pill beneath. **Nothing is ever occluded by either bar** and the last card
  is reachable.
- **A running total strip** sits directly under the top bar and updates as the filter changes.
- **Tapping a card** opens the edit bottom sheet (`bxSheet`, `data-kind="edit"`). **Long-pressing**
  offers Archive via `bxConfirm()`, with the same 10-second Undo toast.
- **The triage inbox is a full-screen swipe deck.** One uncategorised transaction per card, largest
  amount first (the ones worth getting right). The card leads with `bxSuggest`'s answer when
  `score >= 2`: **swipe right accepts it**, **swipe left opens the sub-category picker**, **swipe
  down skips**. The deck shows `data-remaining`. Accepts accumulate and flush as one
  `/txn/categorise` batch when the deck empties or the user leaves. Swipes are transform-based and
  must not drop frames; the whole deck honours `prefers-reduced-motion` by falling back to buttons.
- **Only the content region scrolls.** The month's rows are rendered; other months are not in the
  DOM, which is what keeps the node count small with 1,300 rows in memory.

#### The three re-cut clients

`x`, `d-dash` and `m-dash` are rebuilt from the v2 canon **with no behaviour change**, so that
every embedded copy of `bx_core.*` hashes to the same canon (AC-7.2 spans all five clients). They
also gain the uniform `data-*` hooks and — for `d-dash` and `m-dash` — a working link to
TRANSACTIONS. Their promoted version goes to **1.2.0** alongside the new clients.

### 3.7 Housekeeping, before the round's first working commit (Orchestrator)

Per §0 ruling 9: **commit `docs/cowork_project_instructions.md` as-is, on its own**, message noting
it is Bruce's own edit of 2026-08-19 being committed unchanged. The round then starts from a tree
that matches both remotes. This commit is exempt from AC-10.4's path list and is named in the
debrief.

### 3.8 The park — one schema click and two test rows (Orchestrator)

Bruce has agreed to both (§0 rulings 8 and 10). The round runs as far as it can **without** them,
then parks **once**, asking for everything at the same time:

1. Builder S writes `ServerTxn.py` and `ServerAppData` v2 to their final shape, treating `active`
   as present. Builders C, D and M work entirely from fixtures and are unaffected.
2. When the code is ready, the orchestrator **parks AWAITING-BRUCE** with exactly this request:

   > **Two things in the Anvil editor, please.**
   >
   > **1 — Schema.** On the **`transactions`** table, add one column: **name `active`, type
   > `bool`**. Do not set a value on any existing row — leave them all blank.
   >
   > **2 — Two test rows** on the **`accounts`** table, so the archived path can be proven for the
   > first time:
   >
   > | `acc_id` | `acc_name` | `archived` |
   > |---|---|---|
   > | `ZZ-TEST-ACTIVE` | `ZZ Test Active` | leave unticked |
   > | `ZZ-TEST-ARCHIVED` | `ZZ Test Archived` | **tick it** |
   >
   > Leave every other column on both rows blank. Then say done.

3. Existing `transactions` rows will read as `None`, not `False`. **This is deliberate and the
   serialiser depends on it** — see §4.3.
4. On Bruce's confirmation the orchestrator verifies, before deploying: the `anvil.yaml` diff shows
   **exactly** that one column added, with `client: full` / `server: full` unchanged on the table
   and no other change anywhere in the file; and `GET /build/counts` shows `accounts` at **9**, up
   by exactly two.
5. **The `ZZ` account rows are the only new structural rows this round** (§2.6). If Bruce's rows
   differ from the table above in any field, the orchestrator says so and asks rather than adapting
   silently — AC-3.5 compares against these exact values.

`anvil.yaml` is edited by Bruce's click, never by hand. The S01 rule stands: never
`yaml.safe_load` → `yaml.dump` this file.

### 3.9 Gates per builder, before integration

- **Builder S:** pyflakes clean on both Python files and `tools/api.py`; a fixtures-conformance
  self-check of every response shape in §4; and a self-run AST walk of `ServerTxn.py` confirming
  **zero `.delete(` calls** and of `ServerAppData.py` confirming zero write calls.
- **Builder C:** `tools/calc_golden.mjs` exits 0 with all cases green, output recorded; `node
  --check` clean on `bx_calc.js`; **and one deliberately corrupted expectation is shown to make the
  runner exit non-zero**, proving the gate is live (S02's node-checker lesson).
- **Builders D and M:** each HTML file's inline JS extracted verbatim (HTML comments stripped
  first — S02's regex lesson) and passed through `node --check`, output recorded; the file opens
  locally against the §5 fixtures and renders; every embedded canon block **hashes equal** to
  `client_src/bx_core.css`, `bx_core.js` and `bx_calc.js` at the same commit.
- **Orchestrator:** `python3 tools/repo_guard.py` exit 0 and `git config core.hooksPath` =
  `tools/githooks`, verified **before the round's first commit**; re-checked after the schema click,
  since the click is a platform write.

The HTML files are **not committed** — they are uploaded to `app_versions`. Working copies live in
`scratch/s03/` (gitignored).

### 3.10 The CLAUDE.md amendment (Orchestrator)

Additive only, in the sections that already exist:

- **Money is integer cents everywhere** — in the tables (already true, evidence in §0.1), on the
  wire (`amount_cents`), and in `bx_calc.js`. Never multiply by 100 at a boundary; the value is
  already scaled. Never do float arithmetic on money.
- **`client_src/bx_calc.js` is the money core.** Every money figure in every client comes from it;
  it is golden-tested under node and embedded byte-identically. A round that needs new arithmetic
  adds a function and a golden case — it does not compute money in a page.
- **The write rules** (§3.1's four): server owns identity and derived fields; whitelist inputs;
  every write returns an independent read-back; no hard deletes.
- **44 px minimum on every interactive control, both form factors** (Bruce, 2026-08-20).
- **The non-blocking fonts pattern is mandatory**, with the 970 ms → 44 ms measurement as its
  reason.
- **Embed checks compare by hash, never containment.**
- **Any "the diff touches only" criterion must name that round's `DEBRIEF_S<NN>.md`** (S02
  Addendum 6).
- The slug table gains `d-trans` / `m-trans`.

Nothing else in CLAUDE.md changes.

---

## 4. THE CONTRACT

### 4.1 `GET /app/bootstrap` — unchanged, plus one optional parameter

With no query string: exactly spec_02 §4, unchanged. With `?include=transactions`: the same body
plus **one** additional top-level key:

```json
{
  "…all spec_02 §4 keys, unchanged…",
  "transactions": [ <transaction object>, … ]
}
```

### 4.2 The transaction object — used by bootstrap and by every write response

```json
{
  "transaction_id": "str",
  "date": "YYYY-MM-DD",
  "description": "str",
  "amount_cents": 0,
  "account": "str",
  "category": "str|null",
  "transfer_account": "str|null",
  "notes": "str",
  "hash": "str",
  "active": true
}
```

Rules:

- **`amount_cents` is an integer, always** — never a float, never a string, never null. It is
  `int(round(amount))` over the stored column, which already holds cents (§0.1). If a stored value
  is **not** integral, the serialiser rounds it, **and the row is listed in the debrief** — a
  non-integral cent value would be a pre-existing data defect worth knowing about.
- **`amount` (the legacy float name) does not appear.** One name for money on the wire.
- `date` is ISO `YYYY-MM-DD`; `str` fields serialise `null` → `""` (spec_02 Addendum 4's rule,
  applied here); `category` and `transfer_account` are the only nullable fields besides those
  spec_02 already names.
- `active` is always a real boolean in the payload — `null` in the table serialises as `true`
  (§4.3).
- `hash` is returned so a client can detect a duplicate without a round trip; it is **read-only to
  the client** and any supplied value is ignored.
- **Row order:** `date` descending, then `transaction_id` ascending. Unlike spec_02's payload, this
  order **is** part of the contract, because a stable order is what lets a reviewer diff two calls.
- Future rounds may only ADD keys, never rename or repurpose these.

### 4.3 `active`, and why the test is `is not False`

Bruce's click adds the column without touching the 1,300 existing rows, so they read `None`. A
`None` here means *"this row predates soft-delete"*, which is to say **active**.

- **Serialisation:** `active = (row['active'] is not False)` → `None` and `True` both become
  `true`.
- **Querying:** the active set is `q.not_(active=True)`'s complement expressed safely — fetch with
  `active=q.not_(False)` **or** fetch all and filter in Python on `is not False`. Whichever Builder
  S chooses, **AC-3.2 proves it by making a row `False` and watching it leave the payload while a
  `None` row stays in it.**
- **Writes always set a real boolean.** After this round, any row the app touches carries `True` or
  `False`; only untouched legacy rows stay `None`. The app never writes `None` to this column.

**A `is True` test would hide all 1,300 of Bruce's transactions.** It is the single most likely
serious defect in this round and it has its own criterion.

### 4.4 The legacy `hash` formula — reproduced exactly

The Forms app's CSV importer detects duplicates with it, so it must not drift:

```
hash = str(date.day) + str(date.month) + str(date.year) + str(amount) + account
```

where `amount` is the **cents integer as Python `str()` renders the stored value** and the day and
month are **not zero-padded**. Builder S reproduces this from
`server_code/transaction_work.py:25` and `server_code/csv_handler.py:161`, and **AC-4.3 proves the
reproduction by recomputing the hash of ten untouched existing rows and matching the stored
value** — before any write relies on it.

### 4.5 Error shapes

| Case | Status | Body |
|---|---|---|
| any auth failure | 401 | `{"ok": false, "error": "unauthorized"}` — no data keys |
| unknown `transaction_id` | 404 | `{"ok": false, "error": "not_found"}` |
| bad field / bad category / batch too large | 400 | `{"ok": false, "error": "bad_request", "detail": "<field name and reason, no values>"}` |

---

## 5. FIXTURES — what client builders build against

`scratch/s03/fixtures/` (gitignored), constructed by the orchestrator at round start from the
shapes above with **ZZ-synthetic values**:

- `bootstrap_full.json` — the spec_02 §4 keys, with the `accounts` array carrying **both an
  `archived: false` and an `archived: true` row** (mirroring §3.8's `ZZ` pair, so the clients are
  built against the archived case from the first minute rather than meeting it at review), plus
  **at least 400 transactions** spanning
  **14 months**, including: ~25% uncategorised; several transfer-sentinel rows; a 28-day February
  and a 31-day month; two rows on the same date and account with opposite signs; a row with an
  empty description; a row with a very long description; at least one `active: false` row; and
  amounts spanning `1` to `9_999_999` cents, positive and negative.
- `write_ok.json`, `write_404.json`, `write_400.json`, `unauthorized.json` — the §4.5 shapes.

**Builders D and M must render, filter, total, sort, search, triage and write correctly from these
fixtures alone**, with the write endpoints stubbed to return `write_ok.json`. Builder S's endpoints
must match the fixture **shapes** key-for-key against the real tables; the reviewer compares the
live response's key-set and types against §4, never against fixture values.

Builder C's golden cases are **not** the fixtures — they are `tools/calc_cases.json`, committed,
because they are the specification of the arithmetic rather than sample data.

---

## 6. SECRETS AND TEST ACCOUNTS

- `.secrets/budgetx.env` holds `APP_BASE`, `BUILD_SECRET`, `TEST1_*`, `TEST2_*`. If any needed
  value is empty, park AWAITING-BRUCE; never generate or hardcode.
- **Drive everything as TEST2** (`tools/api.py --account 2`, now the default — spec_02 Addendum 1).
  **After any deliberate failed-login test, immediately log in successfully with TEST2** so
  Anvil's `n_password_failures` resets. Unknown-address cases use a synthetic address not in
  `users`. At most one failed login may ever target TEST1, and none is expected.
- Never Bruce's own login. No secret, password or live token in any commit, debrief, log line or
  CLI output; hashes and tokens are masked to 6 chars + `…` (spec_02 Addendum 4 widened this to any
  run of 32+ lowercase hex).

---

## 7. INSTRUMENTS — what proves what

| What | Instrument |
|---|---|
| API shapes, auth failures, write read-backs | `curl` / `urllib` against `https://budget-x.anvil.app/_/api/…`, plus `tools/api.py` |
| **Every write proven** | a **second, independent** `GET /app/bootstrap?include=transactions`, fetched after the write, compared on the specific row — **never the write endpoint's own response** |
| Table row counts | `GET /build/counts` before/after, UTC-stamped |
| Served bytes = promoted bytes | sha256 of `GET /x?slug=…` vs `/build/list` |
| Canonical embeds | sha256 of each extracted block vs `client_src/*.js|css` at the reviewed commit — **hash, not containment** |
| Arithmetic | `node tools/calc_golden.mjs`, plus **independent recomputation in Python** from the raw payload (AC-5.4) — the reviewer must not check JS with the same JS |
| Rendering, scroll, swipe, sheets, tokens, timing | Playwright headless against the published URL at **1280×800 and 390×844**, driving the real pages — never Bruce's Chrome |
| Schema | `anvil.yaml` diff, read-only parse |
| Module stamps | `/build/version` |
| Speed | timed `curl` (≥20 requests per endpoint, p50/p95) and Playwright navigation timing at both widths |

**Instrument traps, handed to the reviewers up front** (S02 lost four false FAILs to instruments
rather than defects — this list is the fix, and it is part of the spec, not a courtesy):

1. **Time render from the navigation entry's `responseEnd`**, never from `page.goto()` — the latter
   includes the HTML download the criterion excludes.
2. **Read a 401 body with `page.route` + `route.fetch()`**, never Playwright's `response` event
   during a bounce; the page navigates away and the body becomes unresolvable, which reads as a
   FAIL of a passing page.
3. **The serving route `/x` is itself under `/_/api`**, so a page's own HTML passes any
   leaked-data-key filter, and it contains the words "email", "accounts" and now "transactions".
   Filter the serving route out first.
4. **Compare embedded canon blocks by hash.** Containment passed `canon + "\n"` in S02.
5. **Read headers case-insensitively.** Anvil returns lowercase header names over HTTP/2;
   `dict(r.headers)['Content-Type']` is empty and looks like a failure.
6. **Assert an element exists before reading its computed style**, or a "not found" passes
   vacuously — S02's AC-7.4 did exactly that.
7. **Screenshots are too slow to catch a 200 ms animation.** Use CDP screencast frames or rAF
   sampling for AC-14.
8. **Strip HTML comments before extracting inline JS.** These pages document their own pipeline in
   comments that contain the literal string `<script>`.
9. **A textual scan changes what the code may say.** AC-14.3 greps served bytes for `alert(`, so
   even a comment promising not to use it reads as a violation.

Everything below is reproducible by anyone holding `.secrets/budgetx.env`, including the reviewers,
with no reliance on the builder's transcript.

---

## 8. ACCEPTANCE CRITERIA

Each numbered sub-condition is a separate proof. Partial credit does not exist.

### AC-1 — the bootstrap contract is extended, not broken

1. `GET /_/api/app/bootstrap` with **no query string** and a valid TEST2 Bearer returns 200 and a
   key-set **exactly equal** to spec_02 §4 — **no `transactions` key** — verified programmatically.
2. `?include=transactions` returns 200 with exactly those keys **plus** `transactions`, and every
   object in it matches §4.2's key-set and types exactly — checked on **every** row, not a sample.
3. `?include=garbage` and `?include=` behave as (1): no extra key.
4. Auth failures (no header, malformed header, never-issued 64-hex token) return **401** with the
   uniform body and **no data key** — `transactions` included — in any of them.
5. `ServerAppData.py` in the pushed commit contains **no write call** — proven by an **AST walk**
   (not a regex) finding no `add_row`/`update`/`delete` call and no subscript assignment — and
   `/build/counts` is identical before and after a bootstrap call with `include=transactions`.
6. `/build/version` reports `ServerAppData` at **v2** and `ServerTxn` at **v1**, matching the
   pushed header stamps.

### AC-2 — the write endpoints obey their own rules

On real rows (permitted, §2.6); every row touched is recorded per AC-11.

1. **`/txn/categorise`** sets a category, and an **independent bootstrap fetch** shows the new
   `category` on that row. A batch of ≥20 items in one call updates all 20, confirmed the same way.
2. **Category validation:** a `sub_category_id` that does not exist, and a non-string, each return
   **400**, and an independent fetch shows **no row changed** — a rejected batch is atomic.
3. **`/txn/create`** with `"transaction_id": "FORGED"` and `"hash": "FORGED"` in the body returns
   200, and the read-back shows a **server-minted uuid4** `transaction_id` and a
   **server-computed** `hash` — neither is `"FORGED"`, and no row anywhere in `transactions`
   carries either value.
4. **`/txn/update`** changing `date`, `amount_cents` or `account` produces a **recomputed `hash`**
   matching §4.4's formula, verified by recomputing it independently in Python.
5. **The 100× guard.** A row is created with `amount_cents: 12345`; an independent bootstrap fetch
   returns `amount_cents: 12345`; and **`/build/counts` plus a direct read of the stored value show
   `12345`, not `1234500` and not `123.45`.** The same row read through the **Forms app** (AC-9)
   renders as **R123.45**.
6. **`ServerTxn.py` contains no `.delete(` call at all** — proven by an AST walk of the pushed
   source — and `/build/counts`'s `transactions` count is **unchanged** by an archive: archived
   rows are still rows.
7. **`/txn/archive` then `/txn/restore`** on the same id returns it to `active: true`, and an
   independent fetch shows it back in the payload — proving every write this round makes is
   reversible.
8. Unknown `transaction_id` → **404** with no data keys; a batch of 201 items → **400**.

### AC-3 — `active` is honoured, the 1,300 legacy rows survive, and `archived` finally travels

**The round's highest-risk criterion.**

1. Before any write: `?include=transactions` returns a `transactions` array whose length **equals
   the `transactions` count from `GET /build/counts`** (1,300 at the time of writing) — every
   legacy `None`-valued row is present.
2. A single row is archived. An independent fetch then shows: that row **absent**, the array
   length **exactly one shorter**, and **every other row still present** — compared by
   `transaction_id` set, not by count alone.
3. That row is restored; the set returns to exactly its former membership.
4. A row created this round carries `active: true` as a **real boolean** in the payload, and the
   serialiser never emits `null` for `active` on any row.

5. **The `archived` account path travels the live server for the first time** — S02's open gap,
   closed with real rows instead of a route mock. With the two `ZZ` accounts of §3.8 in place:
   - `GET /app/bootstrap` returns **9** accounts, including `ZZ-TEST-ACTIVE` with
     `"archived": false` and `ZZ-TEST-ARCHIVED` with **`"archived": true`** — the first `true` ever
     emitted by `serialise_account`, asserted on the live response, not a mock.
   - **All five clients render `ZZ Test Active` and render `ZZ Test Archived` nowhere** — asserted
     by searching the rendered DOM of `d-dash`, `m-dash`, `d-trans`, `m-trans` (and `x` after
     login) at both widths. The filter is proven against real data on every surface.
   - A transaction assigned to `ZZ-TEST-ACTIVE` appears in both transactions screens with that
     account name resolved from the payload, proving account resolution is not hardcoded.

### AC-4 — the money contract holds at the boundary

1. Every `amount_cents` in the payload is a Python/JS **integer** — no floats, no strings, no
   nulls — checked across all rows programmatically.
2. The sum of all `amount_cents` in the payload **equals** an independently computed sum of the
   `amount` column read through `/build/counts`-adjacent means or a direct scripted read, to the
   cent. *(If no such read is available to the reviewer, the equivalent proof is: the sum is a
   whole number of cents and matches the Forms app's own Inflow+Outflow for the same month, read
   from its rendered totals.)*
3. **The `hash` reproduction is proven before it is relied on:** for **ten** untouched pre-existing
   rows, §4.4's formula recomputed independently equals the stored `hash` exactly. Any mismatch
   is a FAIL of this criterion, not a rounding note.
4. **No row's `amount` value changed** for any row this round did not deliberately write —
   proven by comparing every `(transaction_id, amount_cents)` pair between a round-start payload
   snapshot and a round-end one, with the deliberate writes of AC-11 excluded by id.

### AC-5 — the money core is right, and proven by something other than itself

1. `node tools/calc_golden.mjs` exits **0** with **≥40** cases green; the full output is in the
   debrief.
2. **The gate is live:** one expectation is deliberately corrupted, the runner exits **non-zero**
   and names the case; the corruption is then reverted and the run is green again. Both outputs
   recorded.
3. `node --check` clean on `bx_calc.js`; the file contains **no** `fetch`, no `document`, no
   `window` reference, and no float literal used in money arithmetic.
4. **Independent recomputation, in a different language.** For the current month at both widths,
   the three rendered totals (`data-total` elements' `data-cents`) **equal** a **Python**
   recomputation from the raw bootstrap payload — inflow as the sum of positive `amount_cents`,
   outflow as the sum of negative, net as their sum, transfers excluded. Exact integer equality;
   no tolerance. **Checking JS with the same JS does not satisfy this.**
5. `bxSuggest` beats the legacy bug: on the tie case in `calc_cases.json`, the legacy
   `is_it_smart` algorithm's answer and `bxSuggest`'s answer are both computed and shown to
   **differ**, with `bxSuggest`'s the correct one.

### AC-6 — the desktop transactions screen is real

At 1280×800, logged in as TEST2 through the login page:

1. The table renders one row per transaction of the selected month, and the set of
   `data-txn-row` ids **equals** the set an independent bootstrap fetch yields for that month —
   compared programmatically.
2. The month selector moves: stepping back one month changes `data-month`'s `data-value`, changes
   the row set to that month's set, and the totals change accordingly. "This month" returns to the
   server's current month.
3. Search with a ≥3-character term filters to rows whose description or amount contains it, and
   the totals recompute over the filtered set. Clearing it restores the full month.
4. "Uncategorised only" filters to rows whose `data-txn-category` `data-sub` is empty, and the
   count matches an independent computation from the payload.
5. Sorting by each column head reorders the rows and the resulting order is verified against an
   independent sort of the same data.
6. Selecting a row opens the detail rail with that row's values; changing the description and
   saving updates the row **in the table without a refetch**, and an **independent bootstrap
   fetch** confirms the new value server-side.
7. **Scroll is driven, not photographed:** the `data-scroller` region's `scrollTop` is pushed and
   MOVES, the last row is reached, and the sidebar, header strip and rail bounding boxes are
   **identical before and after** — asserted from the DOM.
8. Sidebar: TRANSACTIONS highlighted and DASHBOARD navigable; BUDGET, REPORTS and SETTINGS
   `aria-disabled="true"` and force-clicking each leaves the URL unchanged.

### AC-7 — one look, self-contained files, and the amended palette

For **all five** served pages (`x`, `d-dash`, `m-dash`, `d-trans`, `m-trans`), on the **served
bytes**:

1. No `<script src=` at all; the only external `<link` targets are `fonts.googleapis.com` /
   `fonts.gstatic.com`; no `<img src=http`, no `@import`, no `url(http`.
2. The embedded `bx_core.css`, `bx_core.js` and `bx_calc.js` blocks are **byte-identical by
   sha256** to the `client_src/` files at the reviewed commit — **all fifteen extractions**.
3. The §3.6 amended token block is present **verbatim** in all five, every custom property compared
   value-for-value.
4. Playwright computed styles: `body` is `rgb(25, 28, 26)`, and each page's `[data-primary]`
   element **exists** (assert first) and resolves to `rgb(30, 185, 128)`.
5. **`--error` contrast is measured, not assumed:** the computed `--error` value against
   `--surface-1` is **≥4.5:1** by the WCAG relative-luminance formula, computed in the test and
   the ratio recorded.
6. **No client calls the deprecated `fmtR(`** — grep of all five served pages finds the definition
   in the canon block and **zero call sites** outside it.
7. **Every interactive control is ≥44 px in its smaller dimension**, at **both** widths, on all
   five pages — enumerated from the DOM (buttons, links with `data-nav`, sheet actions, month
   chevrons), each measured, the smallest reported.
8. **The fonts link is non-blocking** on all five: `media="print"` with an `onload` that sets
   `this.media='all'`, plus a `<noscript>` fallback.

### AC-8 — the phone transactions screen is designed for a phone

At 390×844, logged in as TEST2 through the login page:

1. Top and bottom bars are **fixed**: their bounding boxes are **byte-identical before and after a
   driven scroll**, asserted from the DOM at 390×844, 390×600 **and** 390×500.
2. **The scroller works** — the S02 finding this screen exists to fix. With a month holding ≥40
   transactions, `data-scroller`'s `scrollTop` is driven from 0 to its maximum, MOVES at every
   step, and the **last card's bottom edge is above the bottom bar's top edge** at the end.
   `scrollHeight > clientHeight` is asserted explicitly. **A tall-viewport capture is not
   evidence.**
3. Every bottom-bar target is ≥44×44 px and the Add button carries `data-primary`.
4. Tapping a card opens the edit sheet (`data-sheet` with `data-kind="edit"`); `Escape` and a
   backdrop tap both close it; focus returns to the card.
5. Editing an amount in the sheet and saving updates the card **and the running total** without a
   refetch, and an **independent bootstrap fetch** confirms the value server-side.
6. The month selector works as AC-6.2, and the running total strip recomputes.
7. Archive via long-press → `bxConfirm` → the Undo toast → tapping Undo restores the row, all
   confirmed by an independent fetch at each step.

### AC-9 — nothing user-facing moved, and the Forms app still reads the data

1. Baseline captured **before the round's first push**: the Forms app as TEST2 at 1280×800 and
   390×844 across Dashboard, Transactions, Budget, Reports, Settings, with console output, kept in
   `scratch/s03/` (never committed).
2. After the final deploy the root still serves the Forms app (startup `Frame`), and the five
   screens show their observables at both widths **except** mobile Reports and mobile Settings,
   the pre-existing S01-documented defects — listed, compared against baseline (must be no worse),
   not counted against this round.
3. Each judged Forms view is actually scrolled (`scrollTop` MOVES) where a scroller exists; the
   mobile Transactions screen's known `scrollHeight == clientHeight` is recorded as unchanged.
4. No new console error against the baseline.
5. **The Forms app reads this round's writes correctly.** The row created in AC-2.5 with
   `amount_cents: 12345` renders in the Forms app's own Transactions list as **R123.45**, and the
   Forms app's month Inflow/Outflow totals are **unchanged except by exactly the rows this round
   wrote**. This is what proves the cents contract did not corrupt the live app.
6. **The Forms app is unaffected by `active`.** It has no such column in its queries, so archived
   rows still appear there; this is expected, recorded, and not a defect until round 08.

### AC-10 — the gates are green

1. pyflakes clean on `ServerTxn.py`, `ServerAppData.py`, `tools/api.py` — commands and empty output
   recorded.
2. `node --check` clean on `bx_calc.js` and on the extracted inline JS of **all five** HTML
   clients (comments stripped first) — recorded, **and** a deliberately broken control file is
   shown to be rejected, proving the checker is live.
3. `python3 tools/repo_guard.py` exits 0 and `git config core.hooksPath` = `tools/githooks`,
   verified **before the round's first working commit** and **again after the schema click**.
4. The round's git diff touches only: `server_code/ServerTxn.py`, `server_code/ServerAppData.py`,
   `tools/api.py`, `client_src/bx_core.css`, `client_src/bx_core.js`, `client_src/bx_calc.js`,
   `tools/calc_golden.mjs`, `tools/calc_cases.json`, `CLAUDE.md`, `docs/specs/spec_03.md`
   (addenda only), **`DEBRIEF_S03.md`**, plus `anvil.yaml`'s single platform-authored column
   addition and the separate §3.7 housekeeping commit — and **nothing under `client_code/`**.
   File list shown. *(The debrief is named here deliberately: S02 Addendum 6.)*
5. `ServerTxn` carries `v1` + history line and `ServerAppData` `v2` + history line; both match
   `/build/version` (ties to AC-1.6).
6. **The rollback ledger is written as part of each promote** — for all five slugs: slug · version ·
   `record_uid` · the row that was current before — present in the debrief with the promote, never
   reconstructed after.
7. **The re-cut clients did not regress.** spec_02's AC-4 (login works and refuses), AC-5 (desktop
   shell), AC-6 (mobile shell) and AC-8 (dead token bounces) are **re-run in full against the
   1.2.0 builds** and all pass. The canon changed underneath these pages; this criterion is what
   stops that from being a silent regression.

### AC-11 — the round's effect on the data is fully enumerated

Real transactions may be written (§2.6). What replaces the old prohibition is a complete account.

1. **A written-rows ledger is in the debrief**, listing for **every** row this round created,
   updated, categorised, archived or restored: `transaction_id` · what changed · before → after ·
   UTC timestamp. Written as the writes happen, never reconstructed.
2. **The ledger reconciles against the data.** A round-end `?include=transactions` compared
   field-by-field against a round-start snapshot yields a difference set that is **exactly** the
   ledger's id set — no extra row changed, no ledger row unchanged.
3. **The structural tables moved by exactly the declared `ZZ` delta and no more.** At round start
   and round end, both readings UTC-stamped: `categories`, `sub_categories`, `budgets` and
   `settings` counts are **identical**; `users` is unchanged; `accounts` is **+2 and only +2**,
   and the two added rows are `ZZ-TEST-ACTIVE` and `ZZ-TEST-ARCHIVED` with the §3.8 field values.
   **Every pre-existing account row is byte-for-byte unchanged** on every field the payload
   exposes — compared between a round-start and a round-end `GET /app/bootstrap`.
4. **No row was hard-deleted.** `transactions`' count at round end is **≥** its count at round
   start, and every round-start `transaction_id` is still present in a round-end fetch that
   includes archived rows *(reviewer instrument: restore any row archived during testing, or read
   the count, which archiving does not reduce)*.
5. `anvil.yaml`'s diff for the whole round is **exactly** the one `active` column on
   `transactions` — no other column, no table, no `client:`/`server:` change, no
   `runtime_options` change beyond platform noise, which is listed if present. *(Adding rows to
   `accounts` is data, not schema, and must not appear in this diff at all.)*
6. **The `ZZ` rows are declared in the debrief** with their exact field values and their final
   state, so Bruce knows precisely what is in his `accounts` table that was not there before.

### AC-12 — CLAUDE.md tells the truth

1. The money rules of §3.10 are present: integer cents everywhere, never multiply by 100 at a
   boundary, no float arithmetic on money, `bx_calc.js` is the money core.
2. The four write rules, the 44 px rule, the non-blocking fonts pattern with its measurement, the
   hash-not-containment rule, and the debrief-in-diff-list rule are all present.
3. The slug table includes `d-trans` and `m-trans`.
4. No other section changed — diff shown, by the same section-splitting method S02 used.

### AC-13 — it is fast, and the truth about speed is on record

1. **Page discipline:** each of `d-trans` and `m-trans` makes **exactly one** data request per page
   open (`/app/bootstrap?include=transactions`), asserted from Playwright's network log. **Changing
   month, searching, filtering, sorting and opening the detail rail or a sheet make ZERO further
   requests.**
2. **Write discipline:** accepting **N** suggestions in the triage inbox produces **exactly one**
   `/txn/categorise` request, not N. Editing one row produces exactly one `/txn/update` and **no
   refetch**.
3. **Render speed:** with the bootstrap response mocked to resolve instantly, `responseEnd` →
   first painted transaction row is **< 400 ms** at both widths, with the ≥400-row fixture loaded.
   Timed from `responseEnd`, never from `page.goto()`.
4. **Interaction speed:** stepping the month, typing a search term, and toggling "uncategorised
   only" each repaint in **< 100 ms**, measured from the input event to the DOM mutation. These
   are pure client-side operations and there is no excuse for them being slower.
5. **Page weight:** each of the five served HTML files is **≤ 250 KB** (`bytes` from
   `/build/list`). *(Raised from spec_02's 200 KB because `bx_calc.js` is now embedded in all
   five; if any file exceeds it, that is a FAIL and a real finding, not a note.)*
6. **The transactions payload is measured and named.** Record the byte size and the p50/p95 over
   ≥20 timed requests of `?include=transactions` against the real 1,300 rows. **If the p50 exceeds
   1,000 ms, it is named with its cause and a windowing option is put to Bruce** — the 1-second
   rule allows a named, justified exception on a page open; it does not allow silence.
7. **The network, measured honestly:** p50 and p95 over ≥20 timed requests each, warm, for
   `GET /x?slug=d-trans`, `GET /app/bootstrap?include=transactions`, `POST /txn/categorise` and
   `POST /txn/update`, on both a fresh connection and a reused one — S02 showed those differ by
   more than 2×, and reporting only one of them misleads.
8. **Cold start: five readings, not one** (S02 Addendum 7 — three readings spread 661–2957 ms and
   one figure supported a conclusion that was false). Five separate ≥10-minute idles, spread across
   at least two hours; report all five, the median and the range, and **draw no conclusion the
   spread does not support**.
9. While the real bootstrap is in flight, both screens show the **skeleton state** (asserted by
   throttling the route), never a blank page or a browser spinner alone.

### AC-14 — it feels good (driven, not admired)

At both 1280×800 and 390×844:

1. **Motion exists and plays:** rows stagger in on load — computed `animation`/`transition` is
   non-`none` on the animated elements, and **CDP screencast frames ≤ 20 ms apart differ** in the
   animated region. Screenshots are too slow for this; use screencast or rAF sampling.
2. **Reduced motion is honoured:** with `prefers-reduced-motion: reduce` emulated, all content
   appears instantly, `animationDuration` resolves to `0s`, nothing is hidden or broken, **and the
   swipe deck falls back to visible buttons** that perform the same three actions.
3. **No native dialogs:** the served bytes of all five pages contain no `alert(`, `confirm(` or
   `prompt(` call, and **zero dialog events fire** across every drive in this round — including the
   archive path, which is exactly where a lazy implementation would reach for `window.confirm`.
4. **Surfaces are the design language:** cards, the detail rail and the sheet render with
   `border-radius` ≥12 px and a non-`none` `box-shadow`, read from computed styles.
5. **The swipe deck works by swiping**, not only by button: a driven pointer gesture (down, move,
   up) on `data-inbox-card` accepts the suggestion, the card leaves, `data-remaining` decrements,
   and the next card is on top. Left and down are driven too and do what §3.6 says.
6. **Nothing janks:** during a driven scroll of `m-trans` with animating content present, the top
   and bottom bars' bounding boxes yield **exactly one distinct box each** across ≥8 samples taken
   while `document.getAnimations()` is non-empty.
7. **The optimistic write feels instant:** with the write route held unanswered for 2 s, the UI
   **still updates immediately**; when the route is then failed, the change **rolls back** and a
   toast names what did not save. Both halves asserted.

---

## 9. THE REVIEW

- **Both reviewers run.** **visual-reviewer first** (AC-6, AC-7.3–7.8, AC-8, AC-9, AC-13.1–13.4,
  AC-14 — the driven-interaction and feel criteria), its verdict committed, **then spec-reviewer**
  on everything (fresh read-only context, full AC-1…AC-14).
- **Both reviewers are given §7's instrument-trap list up front.** S02 proved this is worth more
  than any other single line in the spec.
- **Freeze promotes on all five real slugs while any reviewer is running.** Reviewers may
  upload/promote freely on `zz-rev-s03*` slugs.
- Reviewer logins use TEST2 with §6's lockout hygiene.
- **Reviewers may write transactions** (§2.6) — every row they touch goes in the AC-11 ledger with
  the reviewer named, and each is restored or left in a stated condition.
- On any FAIL: `fixer` (Opus, own context) repairs, **full re-review from AC-1** — never only the
  failure, because repairs regress neighbours — three cycles maximum, then stop and report.
- If cycle 2 still fails structurally, split cleanly: `03a` = server + calc
  (AC-1/2/3/4/5/10/11/12) · `03b` = clients (AC-6/7/8/9/13/14). The seam is §4.
- Debrief `DEBRIEF_S03.md`, STATUS line rules unchanged. **Never FINAL with anything unjudged.**

---

## 10. ROUND CLOSE — what this round leaves behind

`bx_calc.js`, golden-tested and embedded everywhere: round 04 (Budget) computes variance from it,
round 05 (Reports) builds series from it, round 07 (Dashboard) leads with "left to spend" from it.
The write pattern in §3.1 is the template for every write path that follows. The desktop grid and
the sheet/confirm/toast vocabulary are set. And `transactions.active` gives round 06's CSV import
something to do with a duplicate other than destroy it.

**Closed by this round:** S02's open gap — `archived: true` had never travelled the live
`accounts` path, and could only be proven with a route mock. AC-3.5 proves it on real rows across
all five clients.

**Still open after this round**, carried forward deliberately:

- **The two `ZZ` accounts rows remain in `accounts`** (§2.6). Round 06 owns `accounts` writes and
  can retire them; until then the archived one is invisible and the active one is one tick away
  from being so.
- **`tools/api.py` ignores a `BUILD_SECRET` environment override**; it matters the first time
  there is a staging app.
- **`tools/api.py session <bogus>` prints `null` and exits 0** — a caller cannot distinguish "no
  such session" from a successful lookup.

---

## 11. WHAT BRUCE SETTLED BEFORE LOCKING — 2026-08-20

Recorded so the round does not relitigate them.

1. **§0.1 — the cents correction is accepted.** The original ruling said convert (`amount * 100`);
   the evidence in the legacy code says the column already holds cents and needs only an integer
   cast. **`int(round(amount))`, never a multiply.** A wrong answer here is a 100× error across the
   whole app, which is why AC-2.5 and AC-9.5 both exist.
2. **§2.6 — "go wild on my own data" applies to `transactions` and to nothing else.** Bruce:
   *"yes — for the rest add your own ZZ-… test rows."* The five structural tables keep every
   existing row untouched; the only new structural rows are the two `ZZ` accounts of §3.8.
3. **§3.2 — no windowing, deliberately.** The whole ~1,300-row history ships in one call.
   AC-13.6 measures the bytes and the p50 and **escalates to Bruce with options** if it crosses a
   second, rather than the spec guessing a window now.
4. **§3.8 — the round parks and does NOT close unattended.** Bruce: *"happy to click schema if
   needs be."* One park, asking for the column and the two `ZZ` account rows together.

---

## 12. ADDENDA

**Addendum 1 — 2026-08-20 — §3.8.4's `accounts` count check is written against a stale reading.**
§3.8.4 has the orchestrator verify that "`GET /build/counts` shows `accounts` at **9**, up by
exactly two" after Bruce's park. Both `ZZ` rows were **already present at round start** — Bruce
created them before the round opened — so the round-start reading is already **9** and this
round's delta is **0, not +2**. The substance of AC-11.3 is unchanged and is judged as written:
`accounts` must read **9 at round start and 9 at round end**, the two `ZZ` rows must match §3.8's
field values exactly, and every pre-existing account row must be unchanged on every field the
payload exposes. Only the arithmetic of the check changes, not what it proves.

**Addendum 2 — 2026-08-20 — AC-1.6 cannot be satisfied without editing `ServerBuildTools.py`,
which §3.0 assigns to nobody and AC-10.4 does not permit.**
AC-1.6 requires `/build/version` to report `ServerTxn` at `v1`. But
`ServerBuildTools._module_versions()` enumerates modules **explicitly**, one `try/import` branch
per module — a new module is invisible to the endpoint until it is named there. `ServerTxn` is a
new module, so with `ServerBuildTools` untouched the endpoint reports only `ServerBuildTools`,
`ServerApi` and `ServerAppData`, and **AC-1.6 fails no matter what Builder S writes**. The file is
not one of the five original server modules frozen by §2.3, and §2.4 freezes only `ServerApi`, so
editing it breaks no stated prohibition — but AC-10.4's path list omits it.

**Resolution:** the orchestrator adds the one `ServerTxn` branch (mirroring the existing
`ServerAppData` one exactly, imported inside the function, never at module level) and bumps the
module to **v3** with a history line. **AC-10.4's permitted path list gains
`server_code/ServerBuildTools.py`.** This is the S02 Addendum 6 pattern repeating: a
"the diff touches only" list written without noticing a file the round's own criteria require.

**Addendum 3 — 2026-08-20 — `bx_calc.js` carries two deliberate additions beyond §3.3.**
Recorded so neither looks like drift at review:
1. **A 12th export, `bxDaysInMonth(y, m)`.** §3.3's table names 11. The month boundary is the
   thing `bxByMonth` must get right, and a directly testable day count is how that is proven;
   it is additive and golden-tested.
2. **`bxSuggest` matching is case-insensitive.** §3.3 mandates three fixes to the legacy
   `is_it_smart`; this is a fourth. The legacy is case-**sensitive**, so it misses `WOOLWORTHS`
   against an index built from `Woolworths`, and bank descriptions arrive in inconsistent case.
   The `length >= 3` test is applied to the word as written, before lowercasing. Golden case
   `suggest_is_case_insensitive_where_the_legacy_finds_nothing` proves the improvement against
   the legacy algorithm's own answer.

**Addendum 4 — 2026-08-20 — `bxFmtCents` throws on non-integer input, by design.**
Not a spec change; a behavioural contract worth recording because it binds every later round.
`bxFmtCents(1234.56)`, `bxFmtCents(null)`, `bxFmtCents(undefined)` and `bxFmtCents("1234")` all
raise `TypeError` rather than rendering. It is the tripwire for the 100× defect §0.1 and §11.1
exist to prevent: a page that accidentally passes rands fails loudly instead of silently
rendering every figure 100× too small. **The cost is that a page must guard its own missing
values before formatting them**, which both client builders were told.

**Addendum 5 — 2026-08-20 — §3.8 asks Bruce for the wrong thing. Code adds the column; Bruce
approves the migration.**
§3.8 parks the round by asking Bruce to *"add one column"* on `transactions` in the Anvil editor.
That inverts how this project actually works. Bruce's ruling, given during the round:

> *"I never add columns or tables. You do. Then I approve the schema."*

**Corrected sequence, and the one now followed:** Code edits `db_schema` in `anvil.yaml`, pushes
it to `anvil`, the schema-mismatch panel appears in the DATA tab, and **Bruce clicks RED / LEFT —
*the source code is correct* — migrating the database to match git.** He never hand-creates the
object. The park still exists and the round still cannot close unattended; what changes is that
the request put to him is *approve this migration*, not *build this column*.

This is also the one sanctioned exception to CLAUDE.md's "do not hand-edit `anvil.yaml`": a
deliberate, spec'd schema change is edited into that file **textually**, never via
`yaml.safe_load` → `yaml.dump`. The diff was verified to be exactly the one column —
`transactions.active`, type `bool`, `client: full` / `server: full` unchanged, no other table and
no top-level key altered — which is what AC-11.5 requires.

The rule is now recorded in **CLAUDE.md** (§"Schema changes need Bruce's click") and in the
vault's **Budget X — Master Note** standing decisions, so no later round repeats the mistake.

**Addendum 6 — 2026-08-20 — §4.3 is WRONG about what the migration leaves behind. Anvil writes
`False`, not `None`, and it hid all 1,300 rows.**
§3.8.3 and §4.3 state that Bruce's click "adds the column without touching the 1,300 existing
rows, so they read `None`", and that *"this is deliberate and the serialiser depends on it"*.
**Measured on the live app: it is not what happens.** After the migration was approved, every one
of the 1,300 pre-existing rows carried a real **`False`**.

The effect was total and silent: `GET /app/bootstrap?include=transactions` returned **200 with an
empty array**, `/build/counts` still reported `transactions 1300`, and nothing raised. The
serialiser's `is not False` test — which §4.3 correctly insists on over `is True` — **does not
help**, because the stored values genuinely are `False`. No test can separate "archived" from
"never initialised" once the platform has written a real boolean.

**What actually happened, in order:** the column was pushed (14:5x) and the intermediate,
pre-approval state already returned `False` for unmigrated rows, hiding everything; the migration
was approved; the rows still read `False`. Diagnosed with one minimal, reversible `/txn/restore`
on a single id, which made exactly that row reappear in an independent fetch — confirming the
mechanism before anything was done at scale. All 1,300 rows were then restored to `active: true`
in seven batches of ≤200 through `/txn/restore`, every row ledgered as it happened.

**Reconciliation after remediation** (independent fetch vs the snapshot taken before any write):
1,300 rows returned, every `active` a real boolean with distinct value set `[True]`, **zero ids
missing, zero new, and zero rows differing on any field except `active`**, `sum(amount_cents)`
identical at `-13,576,179`, order contract intact, all table counts unchanged.

**The standing rule this produces** — now in CLAUDE.md: *after adding a bool column, explicitly
initialise every existing row in the same round, before anything reads it. Treat a migration as
leaving the column wrong, not empty, and prove the recovery by field-by-field reconciliation
against a pre-migration snapshot rather than by a row count.*

**Consequence for AC-3:** AC-3.1's "every legacy `None`-valued row is present" can no longer be
proven as written — after remediation no row is `None`; all 1,300 carry an explicit `True`. The
substance (all 1,300 rows present, none lost, none altered) **is** proven, and more strongly than
the criterion asked. AC-11's ledger now legitimately contains 1,300 restore entries plus the
single diagnostic restore, all of them this round's deliberate writes.

**Addendum 7 — 2026-08-20 — AC-10.4's path list omits the reviewer verdict files, which the
round's own method requires it to commit.**
AC-10.4 enumerates the paths the round's diff may touch. The round also commits
`docs/review_s03_visual_cycle1.md`, `…cycle2.md` (and a cycle-3 file if the gate runs a third
time), because **CLAUDE.md requires it**: *"verdicts are recorded as small committed `.md` files,
the artefacts behind them stay on disk"*, and spec §9 requires the visual reviewer's verdict to be
**committed before the spec reviewer runs** — precisely so a verdict cannot be tidied up after a
repair. A path list that forbids those files fails a tree that is correct.

**Resolution: AC-10.4's permitted path list gains `docs/review_s03_<NN>_*.md`** — the reviewer
verdict files for the round.

**This is the third occurrence of this exact pattern** — S02 Addendum 6 added `DEBRIEF_S<NN>.md`,
this round's Addendum 2 added `server_code/ServerBuildTools.py`, and now the verdict files. The
standing rule in CLAUDE.md already says a "the diff touches only" criterion must name that round's
debrief; **it should be read as naming every artefact the round's own method obliges it to
commit** — the debrief, the reviewer verdicts, and any file a criterion elsewhere in the same spec
forces the round to edit. Recorded so spec_04 writes the list correctly the first time.

**Verified for this round** (`7085660..HEAD`), 16 paths, every one either named in AC-10.4 or
added by an addendum: `CLAUDE.md` · `DEBRIEF_S03.md` · `anvil.yaml` · `client_src/bx_calc.js` ·
`client_src/bx_core.css` · `client_src/bx_core.js` · `docs/cowork_project_instructions.md` (the
§3.7 housekeeping commit, explicitly exempt) · `docs/review_s03_visual_cycle1.md` ·
`docs/review_s03_visual_cycle2.md` · `docs/specs/spec_03.md` · `server_code/ServerAppData.py` ·
`server_code/ServerBuildTools.py` (Addendum 2) · `server_code/ServerTxn.py` · `tools/api.py` ·
`tools/calc_cases.json` · `tools/calc_golden.mjs`.

**And nothing under `client_code/`:** the tree hash is `dbe106cf57e69d2e3ef9f0f1edbcd9bad3e8849d`
at round start and **identical** now — not one byte of either Forms UI tree changed. The five
original server modules (`ServerModule1`, `account_work`, `budget_work`, `csv_handler`,
`transaction_work`) are byte-identical by blob hash.
