# Budget X — Claude project instructions

---

## OPERATING RULE — read first, every session

Two documents govern this project and they do not overlap:

- **`CLAUDE.md` at the root of the `BudgetX` repo** is authoritative for **how a round is built,
  tested and deployed**. Code reads and obeys it; Code frequently cannot reach the vault. It is
  the longer of the two and it wins on any mechanics question.
- **`Projects/Budget X — Master Note.md`** in the Obsidian vault is authoritative for **the
  project's design history, decisions and roadmap** — the things Code does not need and cannot
  see. Read it before doing any design work.

**If the two conflict on build mechanics, the repo wins** — and fix the Master Note in the same
session rather than leaving two answers standing. **If they conflict on why a decision was made,
the Master Note wins.** Older chat memory loses to both.

Session-by-session history lives in **`Projects/Budget X Sessions/`** (same vault) — one file per
round. **Budget X numbers its rounds from 01 and has its own sequence, unrelated to IAMS session
numbers. Never renumber, and never let the two sequences touch.** The Master Note holds only a
short newest-first index of links to that folder plus a "Now current" version line; it should
rarely need editing.

**At the end of every session:** create ONE NEW file in `Projects/Budget X Sessions/` (naming:
`Session {NN} — {date} — {title}.md`, with frontmatter for `session` / `date` / `title` /
`parent` — match the existing files' format), add one line to the Master Note's index, and update
the "Now current" line if versions changed. **Never edit a previous session's file** — new files
only, so nothing can be overwritten by sync conflicts.

**The vault is the ONLY canonical location for the Master Note and the Sessions folder.** Do not
mirror them into the repo. On Budget X this is not merely a convention — it is **machine-enforced**
(see "The repo carries code only"), and a commit that tries will be refused.

---

## PROJECT

**Budget X** is Bruce's personal/household budgeting app on Anvil — accounts, budgets, categories,
transactions, CSV import, reporting. Live at **https://budget-x.anvil.app**, Anvil app id
**`7CPSHQA3GUEYMLO5`**.

**It is not IAMS.** It inherits IAMS's *working method* — the trigger, the loop, the reviewer gate,
the deploy path, the verification rules — and **almost none of its domain**.

**There is no regulatory regime on this app.** No SACAA, ICAO or any other authority. No mandatory
audit log, no signature locks, no four-layer RBAC, no hard-delete prohibition in law. **Do not
import IAMS's four non-negotiables into a Budget X spec "to be safe"** — they are real cost and
they buy nothing here.

What replaces them, as preference rather than regulation:

- **Soft-delete by preference.** No legal rule, but a budgeting app that loses a year of
  transactions to a mis-click is a bad app. Prefer `active = False` / `status = 'archived'`.
- **Read-back is the only proof of a write.** With no audit log there is no second trail, so a
  write is proven by fetching the record back independently — never by the endpoint's own
  `ok:true`.
- **All authority server-side** (target state). Every protected endpoint re-validates the session
  token and re-checks permission whatever the client claims. Client-side permission data is
  cosmetic.
- **Never test against Bruce's real budget data.** This app holds one person's finances and has no
  audit log to reconstruct them from.

**Final outcome: a phone-first budgeting app that is correct about money.** Arithmetic — totals,
rollups, variance — is the thing that has to be right, and it is checked by recomputation, never by
observing that a number rendered.

---

## THE STACK — how work actually gets shipped (2026-08-19, at clone)

The app lives in the private repo **`brucerfraser/budgetx`**, cloned on Bruce's Mac at
`/Users/brucefraser/BudgetX`. Two remotes:

- **`anvil`** — `ssh://…@anvil.works:2222/7CPSHQA3GUEYMLO5.git`. **This is the deploy path.**
- **`origin`** — `github.com/brucerfraser/budgetx`. Offsite backup and Cowork's reading window. It
  feeds Anvil nothing.

**The GitHub↔Anvil sync is deliberately UNLINKED** (Bruce, 2026-08-19). This is the single biggest
difference from IAMS, where Anvil syncs GitHub automatically in both directions. Here **the Mac is
the only bridge**: Bruce's editor edits reach GitHub only by someone on that Mac fetching `anvil`
and pushing `origin`. **Treat `origin` as potentially stale until a round has fetched `anvil`.**

**Two arms, different reach. This is the whole architecture:**

| | Cowork (this project) | Code (on Bruce's Mac) |
|---|---|---|
| Read the repo | yes — `~/BudgetX` is a connected folder | yes, native |
| Write files into `~/BudgetX` | **yes** | yes, native |
| **`git push`** | **NO — blocked by the sandbox git proxy** | **yes**, to both remotes |
| Browser-test the live app | joint review only | yes, unattended (Playwright) |
| Read the Obsidian vault | yes | **often NOT — never assume** |
| Write application code | **NO — see below** | **yes, all of it** |

### The boundary: Cowork designs, Code builds — and on Budget X that is stricter than on IAMS

**On IAMS, Cowork writes the actual code into the repo. On Budget X it does not.** Design stops at
the spec; Code implements every line. **This is a deliberate inversion of the IAMS rule — do not
carry the old habit across.** Do not leave half-finished modules in the tree, and do not "just
sketch" a server module to save Code time.

The trade the inversion makes: prose-to-code translation loses fidelity, but Budget X has no
regulatory clause that must survive translation word-for-word, and it has something IAMS did not —
**a mandatory independent reviewer gate on every round**. Precision moves from the code into the
acceptance criteria. That is where your effort goes.

**Session-start checklist**

1. Confirm the **Obsidian vault** and **`~/BudgetX`** folders are connected.
2. **Do NOT look for a way to attach the repo to the task, or to push.** It does not exist in
   Cowork. Do not retry the push, do not hunt for a connector, do not suggest the GitHub REST API.
   Settled — see the last section.
3. **`git -C ~/BudgetX fetch anvil && git merge --ff-only anvil/master`** before reading anything as
   current. `origin` alone is not enough on this app.
4. Read counts, module names, table names and versions **from the repo**, never from this file, the
   Master Note, or memory. Both are snapshots and the migration is deliberately changing most of
   them.
5. Secrets: `.secrets/budgetx.env` in the repo root is a **local convenience, gitignored**; the
   vault (`Projects/STARAPP_SECRETS.md`) remains source of truth. **Never ask Bruce to paste a
   secret, never echo one, never commit one.** Pushes from the Mac use the SSH key on Bruce's Anvil
   account and need no token handling at all.

**Repo state at clone, 2026-08-19** — verified, and expected to change:

- **5 server modules** — `ServerModule1`, `account_work`, `budget_work`, `csv_handler`,
  `transaction_work`. ~520 lines, **22 `@anvil.server.callable`, zero HTTP endpoints**.
- **9 tables** in `anvil.yaml` `db_schema`: accounts, budgets, categories, files, settings,
  sub_categories, test_csv, transactions, users.
- **~1,612 lines of client-side business logic** in `client_code/F_Global_Logic/` — `Reporting.py`
  (1,046), `Global.py` (208), `BUDGET.py` (176), `Transaction.py` (94), `Responsive.py` (88).
- **Two complete parallel UI trees** — `F_Components` (desktop) and `F_Components_Mobile`. Every
  screen is currently built twice.
- Startup form is `Frame`. No scheduled tasks. Services in use: Anvil Users, Files, Tables.
- **No rounds have run yet. The next round is Session 01.**

### How a round runs

1. **Cowork writes the spec** to **`docs/specs/spec_<NN>.md`** — the WHY, what to change, what must
   NOT change, and numbered acceptance criteria **AC-1 … AC-n**. Complete and self-contained.
2. **Bruce approves, and the spec is locked.** This is the sign-off gate — the only human step, and
   the right one to keep.
3. **Bruce pastes one line into Code: `Read Claude.md, Trigger <NN>`.** Nothing else. **There is no
   further brief and nothing will be added if Code asks.** Everything Code needs is `CLAUDE.md`
   plus the spec — which is the single most important constraint on how you write.
   `Read Claude.md, Trigger <NN> continue` resumes a round parked at a human checkpoint; the
   continuation folds into the same debrief.
4. **Code runs the loop unattended** and does not come back for permission. Bruce approved the
   spec; that was the gate. He expects to brief at night and wake to a working app.
5. **Code writes `DEBRIEF_S<NN>.md` at the repo root** and pushes it.
6. **Cowork transcribes the debrief into the vault** as `Session <NN>` and updates the Master Note
   index.

**One number joins everything:** `spec_<NN>` → `DEBRIEF_S<NN>` → vault `Session <NN>`. Round numbers
may carry a letter (`03a`, `03b`) — the letter is part of the number, everywhere, always. A lettered
round is a full round in its own right.

### THE LOOP, in full

**Code → Push → Deploy → Basic test → Fix → { spec review / visual review → Fix } ×3 → Complete.**

Note the shape, which differs from IAMS's: **basic testing comes BEFORE the review cycle**, and
**the ×3 cap applies to the review cycle only**, not the whole round.

- **Code** — implement against the spec, bump the module `vN` header stamp and add a one-line
  history entry, **pyflakes** every touched `.py`, `node --check` every touched JS.
- **Push** — commit, `git push anvil master`, then mirror the same commit to `origin`. **Never
  force-push, to either remote.**
- **Deploy** — confirm the deployed version. Measured on IAMS: ≤16 s push-to-live. No editor, no
  browser automation, no waiting.
- **Basic test** — drive the live app as the **dedicated test account, never Bruce's own login**,
  and confirm the change is present and nothing obvious is broken. Code's own check, before anyone
  reviews it.
- **Fix** — root-cause, never patch over.
- **Review** — the gate, and not Code's to mark. See below.
- **Complete** — only when every AC is PASS, stated as a count ("9/9 PASS").

### The reviewer gate — this is what replaces IAMS's So-what gate

A suite goes green on code that solves the wrong problem, and unattended at 02:00 that is exactly
what ships. **On Budget X the defence is an independent reviewer, dispatched on EVERY round by
default, in a fresh read-only context.** Agent definitions live in `.claude/agents/` — `fixer`,
`spec-reviewer`, `visual-reviewer`.

What that demands of your specs:

- **Every outcome is a checkable condition.** "The dashboard should feel faster" is not an AC.
  *"Log in as the test account, open Budget → Categories, confirm the rollup shown equals the sum
  of its sub-category rows recomputed from the transactions table"* is. **If Code cannot tell
  whether a criterion holds, it must STOP** — so an unmeasurable criterion does not produce a
  lenient pass, it produces a stalled round.
- **A criterion with four sub-conditions is four things to prove.** Number them.
- **Evidence means observed behaviour**, not the presence of code that looks like it should work.
  An outcome that cannot be verified is a **FAIL**.
- **Partial credit does not exist.** No "mostly", no "acceptable", no "passes apart from".
- **Green tests are not the goal; the stated purpose of the change is the goal.** "No errors" is
  not a pass. **An honest partial beats a confident overstatement.**
- On any FAIL: fix, then **re-run the FULL review from AC-1** — never only the failures, because
  repairs regress neighbours. **Three full cycles maximum**, then stop and report the outstanding
  FAILs with the reviewer's evidence.
- Repairs are made by the **`fixer`** in its own context — not by the orchestrator (which then
  marks its own homework) and not by the reviewer (which stops being independent the moment it
  edits).
- **A reviewer is never weaker than what it reviews, and never the same context.** If either is
  about to happen, stop and report it — a review that cannot fail is worse than none, because it
  manufactures confidence.
- **If the harness refuses to dispatch a subagent**, that is stated prominently in the debrief and
  the review outcome is **FAIL**. A refusal is not permission to skip the gate.
- **Freeze promotes while a reviewer is running.** A reviewer cannot certify a build that changes
  underneath it. Build and stage freely; promote nothing until it hands back.

**Split rounds rather than growing them.** A spec combining heavy server work with several major
user-facing surfaces is **two rounds**: a backend round reviewed at the API level, then a round
reviewed by driven interaction and visual evidence. Review sweeps halve, regressions localise, and
the three-cycle cap stays protection rather than a stop-loss. Apply this at spec-writing time.

### Verification rules inherited from IAMS — they were expensive to learn

Method, not domain, so they carry across unchanged. Write them into criteria where they bite.

- **Present is not reachable.** IAMS shipped a dashboard that could not scroll vertically and it
  survived one self-check plus three review cycles, because every capture enlarged the viewport.
  An interaction a user cannot avoid must be **driven, not photographed** — scrollTop must MOVE,
  content below the fold must be REACHED, at desktop and 390 px, both themes. **Tall-viewport
  captures are disallowed as sole evidence.**
- **Verification effort runs in user order:** can you reach it → does it work → is it right → is it
  polished. Field-perfect evidence on an unreachable panel is worthless.
- **Reviewer independence is not method diversity.** Where two reviewers run, give them different
  mandates — one drives interactions, one audits evidence — and dispatch **visual → commit its
  verdict → then spec**, so the spec reviewer never judges visual ACs whose evidence does not yet
  exist.
- **Verify the artefact, not your model of it.** Geometry computed from your own model is a
  description of intent, not of output. When a criterion is about what something *is*, the evidence
  is the thing itself, read back after it was produced. Ask too what has already been shelved or
  cached — a fix can be deployed and invisible because stored bytes predate it.
- **`ok:true` is not evidence of a write.** Read the record back from an **independent** fetch, not
  the handle you wrote through. *(Anvil Row handles cache per handle: `get()` and `search()` return
  different cached views of one record.)*
- **A default is not a default if something stored shadows it.** Settings lookups that merge a
  stored override must fill keys the stored entry lacks and never overwrite one it has. Budget X
  has a `settings` table — check this on every settings-backed default.
- **390 px is the primary viewport.** This is a phone-first app.

### How each kind of change deploys

- **Server modules** — edit `server_code/*.py` and `git push anvil master`. **Bump `vN` + add a
  history line every time. pyflakes before every push.**
- **Schema — tables AND columns — needs Bruce's click.** See below; this is the one thing that will
  park a round.
- **Client HTML** — once the spine exists (Session 01): `/build/upload` then `/build/promote` into
  `app_versions`, which doubles as version control and changelog. **Until then there is no build
  pipeline** — the app is classic Anvil Forms.
- **Rollback** — before every promote, write the outgoing `app_versions` row (slug · version · row
  id) into the round's rollback ledger; server-side rollback is the previous commit SHA. **Never
  promote before that line is written.**

### The one thing that will park a round: schema

**A pushed schema NEVER applies on its own, in either direction. It always waits for a human click
in the Anvil editor.** This is a platform property, not a bug — do not hunt for an API around it.

- **Therefore a round that touches schema CANNOT close unattended.** Code says so in the debrief,
  hands Bruce the click, and marks any dependent criterion **BLOCKED** — never as passed. **When
  you write a spec that touches schema, expect it back `AWAITING-BRUCE` mid-round, and write the
  criteria so the non-schema work can still be judged.**
- The mismatch indicator is a **⚠ in the DATA tab** beside `Default Database`; green ✓ when clear.
  It is **not** in Version History.
- **RED / LEFT = the source code is correct** → migrate the database to match git.
  **BLUE / RIGHT = the database is correct** → rewrite the source to match it. **Never take the
  blue side unattended** — it silently reverts the change the round intended.
- **A schema push forces reconciliation of the WHOLE schema, not just the change.** Diff the LIVE
  schema against `anvil.yaml` and declare every drifted column first. Reading the file is not
  reading the schema.
- **`anvil.yaml` must be parsed, not grepped** — `db_schema` does not run to `services:`, and a
  misplaced block fails silently with the panel still green. Otherwise do not hand-edit it.
- Verbatim panel wording: **`docs/anvil_schema_panel.md`** (carried from IAMS; re-capture the first
  time Budget X shows the panel and correct the file if it differs).

### What comes back — the debrief

`DEBRIEF_S<NN>.md` at the repo root. **Its second line is exactly one of:**

```
**STATUS:** INTERIM          -> work in progress. Bruce is NOT pinged.
**STATUS:** AWAITING-BRUCE   -> parked, needs him. He IS pinged.
**STATUS:** FINAL — n/n PASS -> every AC judged. He IS pinged.
```

Watch that line and ping his phone off it. `AWAITING-BRUCE` is always paired with an
`## AWAITING BRUCE` section naming **exactly** what he must do, where, and what happens next — one
instruction, no ambiguity, because he may be reading it on a phone between meetings. **FINAL is
never written while any criterion is unjudged or a re-review is unreported** — a debrief claiming a
re-review it does not contain is worse than an INTERIM one, because it stops the watch.

It carries: one verdict line per AC with evidence, plus the count · corrections to the spec ·
new facts worth holding · findings not fixed, with file and line · what could not be verified and
why · promotions with their rollback rows · which model actually ran each role · an honest record
of anything Code got wrong and corrected, and any live data it touched.

**Corrections are expected output, not failure.** When reality diverges from the spec, Code adds a
dated addendum at the bottom of the same spec file. It never edits your approved text in place and
never silently deviates.

**Code cannot reach the vault and does not write it. You do.** If a debrief states a vault fact,
treat it as unverified.

### `CLAUDE.md` at the repo root

What Code reads and obeys. It carries the standing rules **inline** — the loop, the reviewer gate,
deploy mechanics, verification rules, model assignment — because **a Code session frequently cannot
reach the vault and has been caught inventing a plausible substitute rather than saying so** (IAMS
S61: a fabricated vault path and "119 tables" against a real 115).

**Amend `CLAUDE.md` only when a STANDING RULE changes.** Session history and current versions stay
in the vault and are never mirrored into the repo — two live copies of one actively-edited file is
the IAMS S54 clobber. Current-state facts ride in the disposable per-round spec.

---

## THE REPO CARRIES CODE ONLY — machine-enforced

**Every byte committed here lands inside Anvil.** On 2026-08-19 the IAMS app stopped opening in the
Anvil IDE — all browsers, that app only, a full day of development access lost — because rounds of
committed build/review evidence had grown the synced tree to ~894 MB / 7,566 files, ~7× past the
~95 MB where Anvil's own forum documents repos breaking.

- **Evidence never enters the repo.** `scratch/` and `docs/evidence/` are gitignored; verdicts are
  recorded as small committed `.md` files, the artefacts behind them stay on disk.
- **`tools/githooks/` pre-commit and pre-push refuse** forbidden paths, media file types, blobs over
  2 MB, trees over 25 MB or 500 files (`tools/repo_guard.py` holds the budgets and allowlist).
  One-time per clone: `git config core.hooksPath tools/githooks` — **verify it is set before the
  first commit of any session.**
- **Never `git add -A`, never `git add scratch/`, never `-f` past the ignore.** A spec that says
  "commit evidence" is wrong; it says "write the verdict file, leave the evidence on disk".
- **This is why the Master Note and Sessions folder stay in the vault.** Not preference — the hooks
  will refuse them.

---

## WHERE THIS APP IS GOING — the migration

Budget X was built as a classic Anvil app (Forms + `@anvil.server.callable`). Bruce's decision,
2026-08-19: **reshape it like IAMS** — server modules exposing HTTP endpoints, business logic
server-side, and a **single responsive client written as HTML by Code**, served from the database
and versioned through build/promote. That collapses the two UI trees into one and puts the logic
where authority belongs. Anvil Users stays the credential store (Bruce's ruling, 2026-08-19) — the
API spine issues session tokens *on top of* it rather than replacing it.

Staged so the app never stops working:

| Round | Scope |
|---|---|
| **01** | The spine — `api_http`/`ApiError` helpers, session tokens over Anvil Users, `/me`, `/build/upload\|promote\|list\|version`, an `app_versions` table, a landing route. Invisible to users; existing Forms keep running untouched. |
| **02** | One screen end to end — the smallest one — to prove the pipeline on something real. |
| **03+** | Screen by screen, retiring each desktop/mobile Form pair as its replacement lands. |
| **later** | `Reporting.py` (1,046 lines) is its own round. It is not a side-quest. |

**Until the spine exists there are no version pings, no `tools/api.py`, and no API-level acceptance
evidence.** Round 01's criteria must be provable some other way — Playwright against the published
app, plus reading records back through the Anvil app itself — and the spec must say which.

**Once the spine exists**, most verification is HTTP: log in as a test account, get a token, call
the endpoint. Faster, repeatable, and better evidence than a screenshot. Reserve the browser for
genuinely visual outcomes — does it render, does it lay out at phone width, does the interaction
actually work.

---

## Model assignment

| Role | Model |
|---|---|
| **Orchestrator** — reads the spec, plans, dispatches, writes the debrief | Fable |
| **Builder** | Sonnet or Opus, orchestrator's choice |
| **`fixer`** | Opus |
| **`spec-reviewer`** | Opus |
| **`visual-reviewer`** | Fable |

**Opus when the change touches:** a write path · the auth/token spine · schema or migrations ·
money arithmetic, budget rollups or reporting maths · anything where *"it returned `ok:true`"* is
not the same as *"it wrote"*. **Sonnet is fine for:** localised client work, CSS and layout, copy,
a bounded UI fix, tooling, mechanical refactors with no behavioural intent. **If unsure, Opus** —
the cost is asymmetric. **If a model is out of credit, fall back to Opus and carry on**; no round
stalls and no gate is skipped for want of credits.

**MIGRATION-PHASE EXCEPTION (Bruce, 2026-08-19 — temporary).** For the duration of the
classic→HTML migration only: **Opus orchestrator with Sonnet builders**, ground out over however
many days it takes. His reasoning: nobody is using this app yet, so a slow cheap round costs little
and a defect is bounded. **It reverts to the table above on completion, and the debrief of the round
that ends the migration says so.** Three things it does **not** relax: a reviewer is never weaker
than what it reviews and never the session that wrote it; the spine and the money still get Opus;
every AC is still proven by observed behaviour — cheap models do not get cheap evidence.

---

## OPERATING RULES (Bruce)

- **No Anvil IDE interaction** unless something genuinely needs checking. Anvil access is on
  **Bruce's own account**, so the separation a second account would give is replaced by an evidence
  trail: **every action taken inside the editor is logged in the debrief** — UTC timestamp, what was
  clicked, why, outcome — including exploratory runs and runs that did nothing. **Never click
  through a schema migration**; that click is Bruce's, deliberately.
- Bruce's own Chrome (`claude-in-chrome`) is for **joint live review only**, never the automated
  loop.
- **Specs are complete and self-contained**, never fragments — Code gets nothing else. Where you do
  touch a file, prefer surgical edits over fragile whole-block replacements.
- **Test with the dedicated test account, never Bruce's own login.** Budget X has no role
  distinction yet, so there is **one** test account rather than IAMS's permitted/forbidden pair;
  add a second the round a permission boundary first exists. Test mail reaching Bruce's own inbox
  is by design (a `+` alias) and must never be pointed elsewhere.
- **Never against real budget data.** Create `ZZ`-prefixed throwaway records of the same shape and
  drive those. If a criterion appears to need a live record, stop and report it **BLOCKED**.
- Version scheme: `0.x.x` is wireframe/local-only; anything promoted live starts at `1.0.0` or
  higher. **Never promote a `0.x` build.**
- Verify counts, names and versions **from the repo**. Never repeat a number from a brief, from this
  file, or from memory as fact.

---

## SETTLED — DO NOT RE-LITIGATE

- **Cowork cannot push, and cannot be made to.** Not the token (it authenticates a clone fine). Not
  Anvil's plan. Not fixable from the Mac — the block is server-side. Not a connector — GitHub's
  integration is read-only by design and no GitHub MCP server exists in the directory. **Routing
  around the proxy via the GitHub REST API is declined**: the authorised-repo set is a security
  control.
- A Cowork task **cannot spawn or message a Code session**. Dispatch can route to Code, but the
  handoff of context is not reliable — which is exactly why the contract is a file (`spec_<NN>.md`)
  and a one-line trigger, not a conversation.
- **Anvil's git SSH is unreachable from the sandbox** — Cowork gets HTTPS only. It works fine
  **from the Mac**, where the key lives, and that is the deploy path.
- **The GitHub↔Anvil sync stays UNLINKED.** Anvil auto-pulling divergent history is the failure
  class that broke the IAMS IDE. **Never relink without an explicit ruling from Bruce.**
- **The schema click is a platform property.** Not a permissions problem, not something an endpoint
  can do. Stop looking.
- **Anvil's built-in AI agents were considered and rejected** — no vault, no Master Note, no project
  discipline.
- **Budget X is not IAMS.** No regulatory regime, its own round numbering from 01, and Cowork does
  not write its application code.
