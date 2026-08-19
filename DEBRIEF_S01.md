# DEBRIEF S01 — the API spine
**STATUS:** AWAITING-BRUCE

**Round:** 01 · **Date:** 2026-08-19 · **Spec:** `docs/specs/spec_01.md`
**Verdict:** NOT STARTED — parked before any code was written. 0 of 11 ACs judged.

---

## AWAITING BRUCE

**`docs/specs/spec_01.md` is still marked `DRAFT`. Nothing has been built.**

Line 3 of the spec reads:

> **Status:** DRAFT — awaiting Bruce's approval. **Do not build against a DRAFT.** On approval Bruce
> changes this line to `LOCKED` and pastes `Read Claude.md, Trigger 01` into Code.

The trigger arrived; the lock did not. Two independent signals say the spec is not approved:
the `Status:` line still says `DRAFT`, and the file is **untracked in git** — it has never been
committed.

**What to do — one edit:**

1. Open `docs/specs/spec_01.md`.
2. Change line 3 so it begins `**Status:** LOCKED` (replacing the `DRAFT — awaiting Bruce's approval.
   **Do not build against a DRAFT.**` text).
3. Reply: `Read Claude.md, Trigger 01`

If you did **not** intend to approve it yet, reply with what you want changed instead — the round
has consumed nothing and left no trace in the app.

---

## WHY THIS PARKED RATHER THAN PROCEEDING

`CLAUDE.md` defines the round's second step as reading "**the approved, locked brief**", and the spec
itself carries an explicit prohibition on building while it says DRAFT. I did not treat the arrival of
the trigger line as overriding the file, because `CLAUDE.md` also says: *"Do not infer the round's
intent from chat context."*

The asymmetry matters here specifically. This round is the **auth and token spine** — the one the
migration-phase cheap-model exception carves out — and it pushes a **schema change that requires your
migrate click**. Building an unapproved version of it would put an unreviewed token design under
everything for the next month, and would spend one of your schema clicks on it.

**This is a judgement call, and it is reversible in one line.** If the DRAFT marker is simply stale,
flipping it costs you seconds and the round runs to completion unattended from there.

---

## PRE-FLIGHT — everything else the spec assumes is TRUE

Checked so the round can run straight through once unlocked. None of this is an AC; it is
readiness, verified now rather than discovered at 2am.

| Spec assumption | Checked | Result |
|---|---|---|
| `git fetch anvil` + `--ff-only` merge clean | §THE TRIGGER 1 | **OK** — already up to date, no divergence |
| `core.hooksPath` set to `tools/githooks` | CLAUDE.md repo guard | **OK** — set |
| `.secrets/budgetx.env` exists | §5 | **OK** |
| `BUILD_SECRET` present (park if missing) | §5 | **OK** — key present, value not read or echoed |
| `TEST1_EMAIL` / `TEST1_PASSWORD` present | §5 | **OK** (`TEST2_*` also present, not needed) |
| `/.secrets/`, `/scratch/`, `/docs/evidence/` gitignored | repo-carries-code-only | **OK** — all three |
| Zero existing HTTP endpoints | §1 | **OK** — `grep http_endpoint server_code/` = 0 |
| 5 server modules, none named `ServerApi`/`ServerBuildTools` | §3 | **OK** — no collision |
| `tools/` holds only `githooks/` + `repo_guard.py` | §3.3 | **OK** — `tools/api.py` is a clean create |

Not yet checked (deferred to the build, they need the editor or a push): the App Secrets service state,
live-schema drift vs `anvil.yaml`, and the `db_schema` entry count.

---

## FACTS WORTH HOLDING

- **The spec's own `Status:` line is a second gate, distinct from the trigger.** Spec 01 encodes
  approval *in the file*, and the trigger line alone cannot satisfy it. Worth deciding once, for all
  future rounds, whether the locked-line convention stands — if it does, a trigger on a DRAFT spec will
  always park here.
- `docs/specs/spec_01.md` is **untracked**. Only this debrief was committed; the spec and the modified
  `docs/cowork_project_instructions.md` were left in your working tree untouched.

## REVIEWERS

**Not dispatched — correctly.** No code was written, so there is nothing to review. This is not a
skipped gate: the gate runs in full on the round that actually builds. No AC is marked PASS anywhere
in this debrief.

## LIVE DATA

**None touched.** No app write, no editor action, no deploy of application code, no test-account login.
The only change to the repo is this file.
