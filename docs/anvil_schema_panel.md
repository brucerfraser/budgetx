# The Anvil schema-mismatch panel — observed verbatim, 2026-08-10 (S65 AC-7a)

Captured by Bruce from the live editor while resolving the `zz_schema_probe` migration. **This is
the real wording, not a guess.** `SCHEMA_MISMATCH_MARKERS` in `tools/anvil_sync.py` was written
before any of this was seen and is known not to match — see DEBRIEF_S65 §7, finding 2.

---

## 1. Where the indicator lives — and why the tool never saw it

**A warning triangle ⚠ sits next to `Default Database` in the DATABASE sidebar header**, with the
tooltip **`Resolve schema mismatch…`**. When there is no mismatch it is a **green check ✓**.

**It is not on the Version History panel**, which is the only place `anvil_sync.py` looks. That is
the whole explanation for the false all-clear: the tool clicked Sync Git Remotes, read the Git Sync
dialog, saw nothing about schema, and exited 0 — because the schema indicator is in a different
part of the editor entirely.

**The check for a pending schema change is the sidebar indicator, not anything on the sync path.**

## 2. The panel

Reached by clicking that triangle. Header banner:

> **The 'Default Database' database schema does not match your app**

Two columns, left and right:

| | Left | Right |
|---|---|---|
| Column heading | **Source Code Schema** | **'Default Database' Schema** |
| Button (colour) | **The schema of the source code is correct** (RED/orange) | **The schema of 'Default Database' is correct** (BLUE) |
| Button subtitle | *View changes that will be made when you migrate 'Default Database'* | *Update the app's source code to match 'Default Database'* |
| Body line | *The source code of your app expects a database with the following schema:* | *The 'Default Database' database has the following schema:* |
| Direction | git → live database | live database → git |

**RED/LEFT = accept the git schema into the database.** BLUE/RIGHT = rewrite the source to match
the database. **An unattended session must never take the blue side** — it is not destructive to
data, but it silently reverts a schema change the round intended to make.

## 3. It is a per-difference diff, not one global click

The two columns are rendered as an aligned, row-by-row schema listing, and **every differing row
carries its own pair of arrows** — an orange **→** (push source → database) and a blue **←**
(pull database → source). Differences can therefore be resolved **individually and in either
direction**, which matters more than it sounds: an additive change can be applied without touching
a destructive one sitting in the same panel.

Observed in the same panel, both directions at once:

- `commercial_stage.pipeline_role — string` present on the **database** side only. This is the
  documented `anvil.yaml` drift: `ensure_columns` created it at runtime (S63) and it was never
  written back. Its arrows offer to reconcile it *into the source*.
- `zz_schema_probe` present on the **source** side only, offering to be created in the database.

## 4. The confirmation dialog — this is the machine-readable contract

Clicking through produces:

> **Migrate 'Default Database'?**
>
> The following changes will be applied to make 'Default Database' match the schema of your app:
>
> >     Create tables: **zz_schema_probe**
>
> Do you want to apply this migration to the 'Default Database' database?
>
> `[ Migrate ]` `[ Cancel ]`

**The operations are enumerated in plain text before anything is committed**, with `Migrate` and
`Cancel` as the only actions. That listing — not the panel, not the arrows — is the thing any
automation must read and classify.

**Observed forms so far** *(S66 additions dated 2026-08-10)*:

| Operation | Exact wording | Observed |
|---|---|---|
| create table | `Create tables: zz_schema_probe` | S65 7a, Bruce's click-through |
| column rename | `Delete column probe_text from table zz_schema_probe` **←newline→** `Add column probe_text_renamed to table zz_schema_probe` | S66 7b, captured by `anvil_sync.py` at 14:22Z |
| delete table | `Delete table: zz_schema_probe_ide` (one line per table, no stronger warning than an add — the enumerating dialog IS the confirmation) | S66 7d, captured at 15:00Z and 15:04Z |

**7b's empirical answer (2026-08-10):** after Bruce's migrate click on the rename, the row
survived but `probe_text_renamed` was **null** — the value `S66-7B-SURVIVE-ME` did not survive.
**A rename destroys the column's data.** Renames must never join an auto-click whitelist.

**7c's warning (2026-08-10):** a table created editor-side goes live in the DATABASE instantly,
commits only to Anvil's LOCAL branch, and does not push on its own. If the local branch has
meanwhile diverged from origin, the `Merge local changes into origin/master` resolution can LOSE
the schema addition from source entirely — observed: after the merge, no commit reached origin,
Anvil sat at origin's own head, and the next mismatch panel offered `Delete table:
zz_schema_probe_ide` as the red-side "correction". **An editor-created table can be stranded
DB-only and then destroyed by the very panel that is supposed to reconcile it.** The blue/right
side (write the DB back into source) is the recovery path for a stranded table someone wants to
keep.

**A RENAME IS ENUMERATED AS A DROP-PLUS-CREATE.** Anvil does not say "rename"; it says `Delete
column X from table T` + `Add column Y to table T` — which predicts the column's data does NOT
survive. (Empirical confirmation from the probe row's value is 7b's checkpoint answer.) Note the
add-wording is `Add column … to table …`, NOT the `Create tables:`/`Create columns:` shape —
`anvil_sync.py`'s classifier correctly treats it as `other` (fail-safe: only the observed
`Create …:` contract is `additive`; a rename must never be auto-clickable because its first half
is a delete).

The wording for type changes and table deletions is **still not known**. Capture each new form as
it appears and add it here.

## 6. S66 (2026-08-10) — where the indicator ACTUALLY lives in the current editor

- The Data tab is an **icon-only rail button** (no text, no `title` attr); its hover tooltip says
  `Data`. Rail order: App · Build with AI · **Data** · …
- Beside `Default Database`: **BOTH indicator icons are always in the DOM** — the ⚠ is
  `svg[data-icon="triangle-exclamation"]` (class `…syncIcon`), the ✓ is `svg[data-icon="check"]`
  (class `…syncIcon-inSync`) — and the inactive one is wrapped in a container with class
  `hidden`. **Only visibility distinguishes the states.** Matching markup text false-positives.
- The Data-tab banner wording is **`Schema Mismatch` / `Your app is expecting a schema that does
  not match this database.` / `Resolve...`** — different from the S65 panel wording, which
  appears only AFTER clicking `Resolve...` (the two-column panel of §2 then shows verbatim as
  documented).

## 5. After resolving

The sidebar triangle becomes a **green check ✓**. That is the reliable "no pending schema change"
signal.

---

**Standing consequence:** `anvil_sync.py` exit 0 has never meant "the schema applied", and now we
know it does not even mean "no schema change is pending". Until the tool reads the sidebar
indicator, a schema-touching round must be confirmed by probing the live database — e.g. a
read-only `/build/ensure_columns` call, which returns *"No table named X. Create the empty table
in the Anvil editor first, then retry."* when the table is absent.
