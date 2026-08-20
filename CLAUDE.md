# Budget X — Anvil app

**This file is authoritative for any Claude Code session working in this repo.**

Budget X is a personal/household budgeting app on Anvil: accounts, budgets, categories,
transactions, CSV import, reporting. It is **not** IAMS. It shares IAMS's *working method*
— the trigger, the loop, the reviewer gate, the deploy path — and almost none of its
domain rules. Where a rule below is inherited from IAMS rather than learned here, it says
so; treat those as proven elsewhere and not yet re-tested on this app.

**There is no regulatory regime on this app.** No SACAA rules, no mandatory audit log, no
signature locks, no four-layer RBAC. Do not import them from IAMS "to be safe" — they are
real cost and they buy nothing here.

---

## THE TRIGGER — how every round starts

**Bruce's entire prompt will be: `Read Claude.md, Trigger <NN>`.** Nothing else. There is no
further brief and nothing will be added if you ask — **everything you need is this file plus
the spec.**

1. `git fetch anvil && git merge --ff-only anvil/master` (see the deploy section — Bruce's own
   editor edits reach this repo only through the `anvil` remote).
2. Read **`docs/specs/spec_<NN>.md`** — the approved, locked brief. It carries the WHY, what to
   change, and numbered acceptance criteria **AC-1 … AC-n**.
3. **If that file does not exist, or an outcome is not stated as a checkable condition, STOP and
   say so.** Do not infer the round's intent from chat context.
4. Run the round to completion — implement, gate, review, fix, re-test, promote — without coming
   back for permission. Bruce approved the spec; that was the gate.
5. Write **`DEBRIEF_S<NN>.md` at the repo root** and push it.

**One number joins everything:** `spec_<NN>` → `DEBRIEF_S<NN>` → Cowork's `Session <NN>` note.
Never renumber. **Budget X numbers from 01 and has its own sequence — it is unrelated to IAMS
session numbers.**

**Round numbers may carry a letter** (`03a`, `03b`) — the whole thing is `<NN>`, letter included,
in the trigger, the spec filename and the debrief. A lettered round is a full round in its own
right. `Read Claude.md, Trigger <NN> continue` resumes the *same* round after a human checkpoint;
fold the continuation into the same debrief.

**Cowork does not write application code.** Design stops at the spec — you implement all of it.

---

## Repo facts (measured 2026-08-19, at clone)

- **App name `Budget X`, Anvil app id `7CPSHQA3GUEYMLO5`.**
- **5 server modules** in `server_code/` — `ServerModule1`, `account_work`, `budget_work`,
  `csv_handler`, `transaction_work`. ~520 lines, **22 `@anvil.server.callable`, zero HTTP
  endpoints** at clone time.
- **9 tables** in `anvil.yaml` `db_schema`: accounts, budgets, categories, files, settings,
  sub_categories, test_csv, transactions, users.
- **Services in use: Anvil Users, Anvil Files, Tables.** Users is the credential store and
  stays that way (Bruce's ruling, 2026-08-19) — the API spine issues session tokens *on top of*
  it rather than replacing it.
- **Client-side business logic: ~1,612 lines** in `client_code/F_Global_Logic/` —
  `Reporting.py` (1,046), `Global.py` (208), `BUDGET.py` (176), `Transaction.py` (94),
  `Responsive.py` (88). **In the target architecture this belongs server-side.**
- **Two complete parallel UI trees** — `client_code/F_Components` (desktop) and
  `client_code/F_Components_Mobile`. Every screen is currently built twice.
- Startup form is `Frame`. No scheduled tasks.

If you need a count, a module name or a schema fact — **read it from the repo.** Do not repeat a
number from this file without checking it; this section is a snapshot, and the migration below
is deliberately changing most of it.

---

## WHERE THIS APP IS GOING — the migration

Budget X was built as a classic Anvil app (Forms + `@anvil.server.callable`). Bruce's decision,
2026-08-19: **reshape it like IAMS** — server modules exposing HTTP endpoints and business logic
server-side, with the UI written as HTML by Code, served from the database and versioned through a
build/promote pipeline. That puts the logic where authority belongs.

**Bruce's ruling, 2026-08-20 — every screen ships as TWO clients.** The earlier "single responsive
client" target is withdrawn. Each screen is a **desktop client** (`d-<screen>`) and a **phone-first
client** (`m-<screen>`) designed for thumbs rather than a squeezed desktop, plus the one shared
**`x` entry/login client** that serves both form factors and redirects on
`matchMedia("(max-width: 998px)")` — the breakpoint the Forms app's `Responsive.py` already uses.
Two designed clients replace the two hand-maintained Form trees; what collapses is `client_code/`,
not the design.

### The slug scheme

| Slug | What it is | Round |
|---|---|---|
| `x` | Entry + login. One page, both form factors. The only login surface. | 01 placeholder · 02 real |
| `d-dash` / `m-dash` | Dashboard shell — nav, auth, one bootstrap fetch | 02 |
| `d-trans` / `m-trans` | Transactions | 03 |
| `d-budget` / `m-budget` | Budget | 04–07 |
| `d-reports` / `m-reports` | Reports (`Reporting.py`, 1,046 lines — its own round) | 04–07 |
| `d-settings` / `m-settings` | Settings | 04–07 |
| `zz-*` | Throwaway build/review slugs. Never promoted to a real name. | any |

Slugs are served from `/_/api/x?slug=<slug>`. **The app root is never one of them** — it keeps
serving the Forms app until every screen has landed.

**This is several rounds, and it is staged so the app never stops working:**

- **Session 01 — the spine, invisible to users.** `api_http`/`ApiError` helpers, session tokens
  over Anvil Users, `/me`, `/build/upload|promote|list|version`, an `app_versions` table, a
  landing route. Existing Forms keep running untouched.
- **Session 02 — the shell.** A login page plus a desktop and a phone shell that authenticate and
  fetch real data through `GET /app/bootstrap`. The pattern every later screen copies, and the
  round that sets the design language and the speed bar.
- **Session 03+ — screen by screen**, retiring each desktop/mobile Form pair as its replacement
  lands. `Reporting.py` is its own round; 1,046 lines is not a side-quest.

**Until the spine exists there are no version pings, no `tools/api.py`, and no API-level
acceptance evidence.** Round 01's own criteria have to be proven some other way, and the debrief
must say which.

### Standing rules of the migration

*(from Session 01 — each one cost a review cycle to learn)*

- **Platform-authored changes are exempt from no-edit criteria, but they are logged.** What Anvil
  itself writes when a service is enabled or its git round-trips — injected imports,
  `runtime_options` rewrites, permission-bit changes — is not an edit by the round; every such
  change is listed in the debrief.
- **Re-check `ls -l tools/githooks/` immediately after any service change.** Anvil silently strips
  the executable bit, disabling the repo guard without saying so.
- **Deliberate, logged test-account provisioning requested of Bruce is exempt** from `users`-count
  criteria. It is setup, not a business-data write.
- **The rollback-ledger line is written into the debrief as part of the promote step** — slug,
  version, `record_uid`, and the row that was current before — never reconstructed afterwards.

*(Bruce, 2026-08-20 — the 1-second rule)*

- **No interaction a user feels may wait on the network.** Any load over one second is named in the
  debrief with its cause and its justification; page behaviour is the round's to fix, platform
  latency is reported to Bruce with options rather than silently accepted.
- **Display maths runs client-side** — it holds no secrets. **Authority and verification stay
  server-side**, and every money figure must remain reproducible by independent recomputation from
  the raw rows.

*(Bruce, 2026-08-20 — the beauty mandate)*

- **The clients must be beautiful, not merely correct.** This app talks to a person about their
  money. The `bx_core` design language — layered dark surfaces, 16–20 px radii, soft shadows,
  150–250 ms motion, skeleton states while data is in flight — and **no browser `alert()`,
  `confirm()` or `prompt()` anywhere, ever**. The current Forms app is a floor, not a ceiling.
- **Feel criteria are first-class acceptance criteria**, driven by the visual reviewer — motion
  that actually plays, reduced motion honoured, surfaces that compute to the design language.

*(shared code)*

- **The canonical `client_src/` files are embedded verbatim in every client.** Each embedded copy
  must be byte-identical to the canon in the same commit, compared by hash — that is what stops
  two clients per screen drifting into two design languages.

*(Session 03 — money, writes, and the client contract)*

- **Money is integer cents everywhere.** The tables already store cents (`csv_handler.py` writes
  `int(math.trunc(amount*100))` on import; every Forms screen divides by 100 to display), the wire
  carries `amount_cents`, and `bx_calc.js` computes in cents. **Never multiply by 100 at a
  boundary — the value is already scaled**; the conversion is a type cast, `int(round(amount))`.
  A stray `*100` inflates every figure in the app 100×. **Never do float arithmetic on money.**
- **`client_src/bx_calc.js` is the money core.** Every money figure in every client comes from it.
  It is golden-tested under node and embedded byte-identically in every client. A round that needs
  new arithmetic **adds a function and a golden case** — it does not compute money in a page.
- **The four write rules**, binding on every endpoint that writes:
  1. **The server owns identity and derived fields.** A caller-supplied id or hash is ignored,
     never stored.
  2. **Whitelist inputs, never blacklist.** Each endpoint accepts an exact key set; unknown keys
     are ignored silently. There is no "update whatever you send".
  3. **Every write returns the row it wrote, re-read from the table** — not the payload it was
     given, and not the handle it wrote through. Anvil Row handles cache per handle.
  4. **No hard deletes.** Soft-delete by preference; prove it by AST walk, not by grep.
- **44 px minimum on every interactive control, on BOTH form factors** (Bruce, 2026-08-20). It is
  a design-language rule, not a mobile-only one — desktop buttons and nav items included.
- **The non-blocking fonts pattern is mandatory in every client** — `media="print"` +
  `onload="this.media='all'"` + a `<noscript>` fallback. A render-blocking `<link rel="stylesheet">`
  defers execution of every later `<script>`, including one at the end of `<body>`. **Measured on
  this app in S02: 970 ms → 44 ms.**
- **Embed checks compare by HASH, never containment.** S02 shipped `canon + "\n"` past a
  containment check. Extract the block between exact delimiters and compare sha256.
- **Any "the diff touches only these paths" criterion must name that round's `DEBRIEF_S<NN>.md`**
  in its own path list. The debrief is written and committed as part of the round, so a list that
  omits it fails against a tree that is correct (S02 Addendum 6).

---

## THE LOOP — how a build round runs

**Code → Push → Deploy → Basic test → Fix → { spec review / visual review → Fix } ×3 → Complete.**

Note what it fixes: **basic testing comes BEFORE the review cycle**, and **the ×3 limit applies
to the review cycle**, not the whole round. Bruce briefs and approves; everything after runs
unattended. He expects to brief at night and wake to a working app.

1. **Code** — implement against the spec, bump the module `vN` header stamp and add a one-line
   history entry, run **pyflakes** on every touched `.py` and `node --check` on every touched JS.
2. **Push** — commit, `git push anvil master`, then mirror the same commit to `origin`.
3. **Deploy** — confirm the deployed version (see the deploy section).
4. **Basic test** — drive the live app as the **dedicated test account, never Bruce's own login**,
   and confirm the change is present and nothing obvious is broken. Your own check, before anyone
   reviews you.
5. **Fix** — root-cause anything the basic test found. Never patch over.
6. **{ spec review / visual review → Fix } ×3** — the gate, and not yours to mark.
7. **Complete** — only when every AC is PASS, stated as a count ("9/9 PASS").

**Never report success on an unverified criterion. An honest partial is worth more than a
confident overstatement.**

### THE REVIEWERS ARE NOT OPTIONAL AND ARE NOT CONDITIONAL

**Dispatch the independent `spec-reviewer` on EVERY round, by default, without being asked.** The
trigger line is only ever `Read Claude.md, Trigger <NN>` — **it will never carry a dispatch
instruction, so do not wait for one.** Where the round changes anything a human looks at,
dispatch the **visual reviewer** too, on the same terms.

A round self-assessed by the session that wrote the code is not reviewed; it is marked by its own
author. Agent definitions live in `.claude/agents/`.

**If your harness refuses to dispatch a subagent:** say so explicitly and prominently in the
debrief, mark the review outcome **FAIL** (never PASS, never silently self-assess), and state the
exact refusal you hit. **A refusal is not permission to skip the gate.**

### Reviewer rules

- `spec-reviewer` runs in a **fresh context** and is **read-only**. It never edits, commits or
  repairs anything it finds.
- It returns **one line per outcome**: `AC-n: PASS | FAIL — evidence`.
- **Evidence means observed behaviour, not the presence of code that looks like it should work.**
  An outcome that cannot be verified is a **FAIL**.
- **Partial credit does not exist.** No "mostly", no "acceptable", no "passes apart from".
- On any FAIL: fix, then **re-run the FULL review from AC-1** — never only the failures, because
  repairs regress neighbours. **Three full cycles maximum**, then stop and report the outstanding
  FAILs with the reviewer's evidence.
- Repairs are made by a **fixer** role in its own context — not by the orchestrator (which then
  marks its own homework) and not by the reviewer (which stops being independent the moment it
  edits).

### A reviewer is never weaker than what it reviews, and never the same context

A round built on Opus is not reviewed by Sonnet; a round is never reviewed by the session that
wrote it. If either is about to happen, stop and report it — a review that cannot fail is worse
than none, because it manufactures confidence.

**If a model is out of credit, fall back to Opus and carry on.** No round stalls and no gate is
skipped for want of credits. Record in the debrief which model actually ran each role.

### FREEZE PROMOTES WHILE A REVIEWER IS RUNNING

**A reviewer cannot certify a build that changes underneath it.** Build and stage as much as you
like while a cycle runs; **promote nothing until it hands back.** If a fix has to go live before
the gate can judge it, promote it *before* you dispatch, not during. *(Inherited from IAMS, where
a verdict was twice rendered against a build that no longer existed.)*

---

## Verification rules inherited from IAMS — they were expensive to learn

These came from real defects that survived multiple review cycles on the other app. They are
method, not domain, so they apply here unchanged.

### Use the page like a human — present is not reachable

IAMS shipped a dashboard that **could not scroll vertically** and it survived one self-check plus
three independent review cycles, because every capture enlarged the viewport and nobody ever
asserted vertical reachability. A first real user found it in minutes.

- **An interaction a user cannot avoid must be driven, not photographed.** Every judged view is
  actually scrolled (scrollTop must MOVE; content below the fold must be REACHED), at desktop and
  390 px, both themes. **Tall-viewport captures are disallowed as sole evidence** — a 1280×3000
  shot happily renders what a 1280×800 user can never see.
- **Verification effort is spent in user order:** can you reach it → does it work → is it right →
  is it polished. Field-perfect evidence on an unreachable panel is worthless.
- **Reviewer independence is not method diversity.** Three fresh contexts sharing one
  verification style pass the same blind spot three times. Where two reviewers run, give them
  different mandates — one drives interactions, one audits evidence — and dispatch **visual →
  commit its verdict → then spec**, so the spec reviewer never judges visual ACs whose evidence
  does not yet exist.

### Verify the artefact, not your model of it

**A gate that measures what you designed will pass anything.** When a criterion is about what
something *is* — what a file contains, what a page looks like, what the user receives — the
evidence has to be **the thing itself, read back after it was produced**. Geometry you compute
from your own model is a description of your intent, not of the output. IAMS made this mistake
four times in two rounds, each time with the instrument agreeing with the code and disagreeing
with the artefact.

And when a round changes a rendered artefact, **ask what has already been shelved or cached** — a
fix can be deployed and invisible because stored bytes predate it.

### An endpoint returning `ok:true` is not evidence of a write

The single most dangerous bug shape this project family has produced, twice, on the other app:
a success return from a path that wrote nothing. **Read the record back from an independent
fetch** — not from the handle you just wrote through. *(Anvil Row handles cache per handle:
`get()` and `search()` return different cached views of one record.)*

There is no mandatory audit log on Budget X, so read-back **is** the only proof of a write.

### A default is not a default if something stored shadows it

Registry and settings lookups that merge a stored override must **fill keys the stored entry
lacks**, and never overwrite one it has. Otherwise a newly added default never reaches an
environment that was seeded before it existed — silently, and for ever. Budget X has a `settings`
table; check this on every settings-backed default you add.

---

## Deployment mechanics

**The GitHub↔Anvil sync is UNLINKED** (Bruce, 2026-08-19). Anvil auto-pulling divergent history
is the failure class that broke the IAMS IDE; never relink without an explicit ruling.

- **Deploy = `git push anvil master`.** The `anvil` remote is the app's own git
  (`ssh://…@anvil.works:2222/7CPSHQA3GUEYMLO5.git`, key on Bruce's account). Measured on IAMS:
  ≤16 s push-to-live. No editor, no browser automation, no waiting.
- **Mirror every push to `origin`** (`github.com/brucerfraser/budgetx`) — same commit, plain push.
  GitHub is the offsite backup and Cowork's reading window; it feeds Anvil nothing.
- **Start of every round: `git fetch anvil` and merge before working** — Bruce's editor edits
  reach GitHub only through this Mac.
- **Never force-push, to either remote.**

### Schema changes need Bruce's click — this is a platform property

**A pushed schema NEVER applies on its own, in either direction. It always waits for a human
click in the Anvil editor.** Adding a table shows the schema-mismatch panel and needs Bruce's
migrate click *plus* a confirmation dialog; removing one needs the same. Nothing happens until he
clicks.

- **Therefore a round that touches schema CANNOT close unattended.** Say so in the debrief, hand
  Bruce the click, and mark any criterion that depends on the new schema as **BLOCKED** — never
  as passed.
- **The mismatch indicator is a ⚠ in the DATA tab**, beside `Default Database`; green ✓ when
  clear. It is **not** in Version History.
- **RED / LEFT = the source code is correct** → migrate the database to match git.
  **BLUE / RIGHT = the database is correct** → rewrite the source to match it. **Never take the
  blue side unattended** — it silently reverts the schema change the round intended.
- **A schema push forces reconciliation of the WHOLE schema, not just your change.** Before any
  schema push, diff the LIVE schema against `anvil.yaml` and declare every drifted column first.
  Reading the file is not reading the schema.
- **`anvil.yaml` must be parsed, not grepped** — `db_schema` does not run to `services:`, and a
  misplaced block fails silently with the panel still green.
- Otherwise **do not hand-edit `anvil.yaml`** — it is generated by Anvil's tooling.

Verbatim panel wording for every dialog: **`docs/anvil_schema_panel.md`** (carried over from IAMS;
re-capture it here the first time Budget X shows the panel, and correct the file if it differs).

### Anvil editor actions are logged in the debrief

Anvil access is on **Bruce's own account**, so the separation a second account would give is
replaced by an evidence trail. **Every action taken inside the Anvil editor is logged in the
debrief** — UTC timestamp, what was clicked, why, outcome — including exploratory runs and runs
that did nothing. **Never click through a schema migration**; that click is Bruce's, deliberately.

---

## THE REPO CARRIES CODE ONLY — machine-enforced

**Every byte committed here lands inside Anvil.** On 2026-08-19 the IAMS app stopped opening in
the Anvil IDE — all browsers, that app only, a full day of development access lost — because
rounds of committed build/review evidence had grown the synced tree to ~894 MB / 7,566 files,
~7× past the ~95 MB where Anvil's own forum documents repos breaking.

- **Evidence never enters the repo.** `scratch/` and `docs/evidence/` are gitignored; verdicts are
  recorded as small committed `.md` files, the artefacts behind them stay on disk.
- **`tools/githooks/` pre-commit and pre-push refuse** forbidden paths, media file types, blobs
  over 2 MB, trees over 25 MB or 500 files (`tools/repo_guard.py` holds the budgets and the
  allowlist). One-time per clone: `git config core.hooksPath tools/githooks` — **verify it is set
  before the first commit of any session** (`git config core.hooksPath`).
- **Never `git add -A`, never `git add scratch/`, never `-f` past the ignore.** A brief that says
  "commit evidence" is wrong; it says "write the verdict file, leave the evidence on disk".

Verified on this repo 2026-08-19: the guard passes the app tree at clone (exit 0) and refuses a
3 MB blob, a `scratch/` path and a `.png` under `docs/` — all three tested, all three refused.

---

## The spec, and the debrief

**The spec** is `docs/specs/spec_<NN>.md` — approved by Bruce and **locked**. If reality diverges
during the build — a stated fact turns out wrong, a criterion turns out unprovable — **add a dated
addendum at the bottom of the same spec file** and carry the correction into the debrief. **Never
silently deviate, and never edit the approved text in place.**

**The debrief** is `DEBRIEF_S<NN>.md` at the repo root, written at the end of every round and
pushed. It is the only channel back to Cowork, which transcribes it into Bruce's vault. **You do
not write the vault yourself, and you generally cannot reach it — never state a fact about the
vault you did not read.**

Carry: the verdict, one line per outcome, plus the count · corrections to the spec (expected
output, not failure) · new facts worth holding (deploy behaviour, platform findings, schema
truths) · findings you did not fix, with file and line · what you could not reach or verify, and
why · promotions made with their rollback rows · an honest record of anything you got wrong and
corrected, and any live data you touched.

### The STATUS line — it decides whether Bruce gets woken

**The second line of `DEBRIEF_S<NN>.md` must be exactly one of:**

```
**STATUS:** INTERIM
**STATUS:** AWAITING-BRUCE
**STATUS:** FINAL — n/n PASS
```

- **INTERIM** — work in progress, pushed for safety. **Bruce is NOT pinged.** Push these as often
  as you like; they cost him nothing.
- **AWAITING-BRUCE** — you are parked and cannot proceed without him. **He IS pinged.** Pair it
  with an `## AWAITING BRUCE` section naming **exactly** what he must do, where, and what happens
  next. One instruction, no ambiguity — he may be reading it on a phone between meetings.
- **FINAL** — every AC judged and the count stated. **He IS pinged.**

**Never write FINAL while any criterion is unjudged, any placeholder is unfilled, or a re-review
has not been reported.** A debrief that claims a re-review it does not contain is worse than an
INTERIM one, because it stops the watch.

---

## Secrets and live testing

`.secrets/budgetx.env` at the repo root — **gitignored, never committed, never echoed into chat
or a commit message.** `APP_BASE` is **https://budget-x.anvil.app**. The vault remains the source of truth; this file is a local convenience.
If it is missing, ask — **do not** put a secret anywhere else and do not proceed with a hardcoded
value.

**Test with the dedicated test account, never Bruce's own login.** Budget X has no role
distinction yet, so there is **one** test account rather than IAMS's permitted/forbidden pair; add
a second the round a permission boundary first exists. Test mail reaches Bruce's own inbox by
design (the account address is a `+` alias of it), which is fine — it must never be pointed
anywhere else., and never against his real budget
data. Budget X holds one person's finances: a test that writes to a live account, category or
transaction is corrupting real records, and there is no audit log here to reconstruct them from.
**Create `ZZ`-prefixed throwaway records of the same shape and drive those.** If a criterion
appears to need a live record, stop and report it as **BLOCKED**.

**Once the spine exists** (Session 01), most verification is HTTP: log in as a test account, get
a token, call the endpoint. That is faster, repeatable and better evidence than a screenshot.
`tools/api.py` will be ported at that point. **Until then, verification is Playwright against the
published app, plus reading records back through the Anvil app itself.**

### What needs a browser

Genuinely visual outcomes: does it render, does it lay out correctly at phone width, does the
interaction actually work. Playwright installed locally in the repo, driving the published URL
headless. **Do not use Bruce's own Chrome for the automated loop** — that is reserved for joint
live review with him watching.

---

## Model assignment

| Role | Model |
|---|---|
| **Orchestrator** — reads the spec, plans, dispatches, writes the debrief | Fable |
| **Builder** — implements the round | Sonnet or Opus, orchestrator's choice |
| **`fixer`** | Opus |
| **`spec-reviewer`** | Opus |
| **`visual-reviewer`** | Fable |

**Opus when the change touches:** a write path · the auth/token spine · schema or migrations ·
money arithmetic, budget rollups or reporting maths · anything where *"it returned `ok:true`"* is
not the same as *"it wrote"*.

**Sonnet is fine for:** localised client work, CSS and layout, copy, a bounded UI fix, tooling and
scripts, mechanical refactors with no behavioural intent.

**If unsure, use Opus.** The cost is asymmetric.

**If a model is out of credit, fall back to Opus and carry on.** No round stalls and no gate is
skipped for want of credits. Record in the debrief which model actually ran each role.

### MIGRATION-PHASE EXCEPTION (Bruce, 2026-08-19 — temporary, expires on completion)

**For the duration of the classic→HTML migration only**, the table above is relaxed: run an
**Opus orchestrator with Sonnet builders**, and grind the migration out over however many days it
takes. Bruce's reasoning: **nobody is using this app yet**, so the cost of a slow, cheap round is
low and the cost of a defect is bounded.

**On completion of the migration this reverts to the table above — Fable orchestrator, Opus
reviewers. Say so in the debrief of the round that ends the migration.**

Three things the exception does **not** relax, because they are what makes a cheap round safe:

1. **A reviewer is never weaker than what it reviews.** Sonnet-built work may be reviewed by
   Sonnet (equal) or Opus (stronger) — never the reverse, and **never by the session that wrote
   it**. The gate still runs, in a fresh read-only context, every round.
2. **The spine and the money still get Opus.** Session 01 (auth, tokens, build/promote) and any
   round touching budget rollups, variance or reporting arithmetic are built on Opus regardless
   of the exception. The exception exists for the **screen-by-screen HTML grind**, which is
   exactly the "localised client work" the table already assigns to Sonnet.
3. **Every AC is still proven by observed behaviour.** Cheap models do not get cheap evidence.

**Record in every debrief which model actually ran each role.** The record of who marked the work
has to stay true, and it matters more under the exception, not less.

## Architectural intent (target state)

**THE CLIENT KEEPS NO SECRETS. ALL AUTHORITY SERVER-SIDE.** Every protected endpoint re-validates
the session token and re-checks permission, whatever the client claims. Client-side permission
data is cosmetic — it controls what is shown, never what can be reached.

**Self-contained modules.** Modules copy the `ApiError / api_http / require_auth` helper shapes
rather than importing them across modules. Cross-imports are the exception and must be justified
in the module header.

**Each module header carries a version (`v9`, `v22`, …) and a changelog.** Read the full header
comment before editing — it documents decisions and gotchas accumulated over the build.

**Standard columns** on business tables, as the migration touches each one: `record_uid` (stable
UUID, safe to expose), `created_at`, `created_by`, `updated_at`, `updated_by`, `status`, `active`,
`source`. Existing Budget X tables predate this convention — **do not retrofit them speculatively;
add the columns as a round's spec calls for them.**

**Soft-delete by preference, not by regulation.** There is no legal no-delete rule here, but a
budgeting app that loses a year of transactions to a mis-click is a bad app. Prefer
`active = False` / `status = 'archived'` unless a spec says otherwise.
