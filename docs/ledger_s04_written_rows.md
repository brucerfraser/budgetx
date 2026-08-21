# Budget X — Session 04 written-rows ledger

Every row this round created, updated, archived or restored, in any table (AC-11.1).
**Written as the writes happen**, by `scratch/s04/zz_rows.py` and the orchestrator's own
drivers, appended to `scratch/s04/ledger/entries.jsonl` before the next call is made — so
a crash mid-run still leaves a truthful ledger. This file is rendered from that log.

Any entry marked **RECONSTRUCTED** was not captured at write time; it says why.
Each `/cat/reorder` or `/subcat/reorder` call is **one entry carrying the whole before and
after sequence**, per AC-11.1.

| # | UTC | table | id | change | before | after | note |
|---|---|---|---|---|---|---|---|
| 1 | 2026-08-21T14:25:22.428346+00:00 | `transactions` | `74f7a3a5-c7f9-4671-98c7-bf6781453b03` | archived | `{"active": true}` | `{"active": false}` | spec_04 Addendum 17 — the round-03 'ZZ S03 cents probe' was the ONLY transaction in 2026-08, so bxDefaultMonth opened every screen on a month holding one stale test row and zero budget rows: exactly the defect §0 ruling 1 exists to prevent. Soft, reversible via /txn/restore, done BEFORE the reviewers drive. |
| 2 | 2026-08-21T14:25:44.041097+00:00 | `categories` | `47c09e56-2479-4a1a-8052-f10292ff40c1` | created | — | `{"active": true, "category_id": "47c09e56-2479-4a1a-8052-f10292ff40c1", "colour_back": "#3A4A42", "colour_text": "#E1E3DF", "name": "ZZ S04 Cat", "order": 13}` | §3.13 row 1 — ZZ S04 Cat |
| 3 | 2026-08-21T14:25:45.103255+00:00 | `categories` | `3b481020-b58b-4024-804b-e1a1446bc103` | created | — | `{"active": true, "category_id": "3b481020-b58b-4024-804b-e1a1446bc103", "colour_back": "#3A4A42", "colour_text": "#E1E3DF", "name": "ZZ S04 Cat B", "order": 14}` | §3.13 row 2 — ZZ S04 Cat B |
| 4 | 2026-08-21T14:25:48.782493+00:00 | `sub_categories` | `2f973007-0347-4eff-98dc-1278606e3df1` | created | — | `{"active": true, "belongs_to": "47c09e56-2479-4a1a-8052-f10292ff40c1", "icon": null, "name": "ZZ S04 Sub A", "order": 0, "roll_over": false, "roll_over_date": null, "sub_…` | §3.13 row 3 — ZZ S04 Sub A |
| 5 | 2026-08-21T14:25:49.939034+00:00 | `sub_categories` | `ee8f3130-5183-4ab8-940d-d3cbad80911b` | created | — | `{"active": true, "belongs_to": "47c09e56-2479-4a1a-8052-f10292ff40c1", "icon": null, "name": "ZZ S04 Sub B", "order": 1, "roll_over": true, "roll_over_date": "2025-01-01"…` | §3.13 row 4 — ZZ S04 Sub B |
| 6 | 2026-08-21T14:25:51.158040+00:00 | `sub_categories` | `7b4140a0-c9c1-476b-9447-583110e198ec` | created | — | `{"active": true, "belongs_to": "47c09e56-2479-4a1a-8052-f10292ff40c1", "icon": null, "name": "ZZ S04 Sub C", "order": 2, "roll_over": false, "roll_over_date": null, "sub_…` | §3.13 row 5 — ZZ S04 Sub C |
| 7 | 2026-08-21T14:25:52.343941+00:00 | `sub_categories` | `4c5e64d7-4782-43a1-92ac-35117aadd965` | created | — | `{"active": true, "belongs_to": "47c09e56-2479-4a1a-8052-f10292ff40c1", "icon": null, "name": "ZZ S04 Sub D", "order": 3, "roll_over": false, "roll_over_date": null, "sub_…` | §3.13 row 6 — ZZ S04 Sub D |
| 8 | 2026-08-21T14:25:55.706265+00:00 | `sub_categories` | `e0bb741b-fe58-4b96-923c-552bca90cd6c` | created | — | `{"active": true, "belongs_to": "8f0c500b-66de-4a0f-e863-3180989309a9", "icon": null, "name": "ZZ S04 Income Sub", "order": 4, "roll_over": false, "roll_over_date": null, …` | §3.13 row 7 — proves the server flips the sign for income (AC-2.2); ARCHIVED AT ROUND CLOSE so Bruce's income list is left as it was found |
| 9 | 2026-08-21T14:25:59.887622+00:00 | `budgets` | `2f973007-0347-4eff-98dc-1278606e3df1|2025-10` | amount set | — | `{"amount_cents": -10000, "month": "2025-10", "notes": "", "sub_category_id": "2f973007-0347-4eff-98dc-1278606e3df1"}` | §3.13 row 8 — ZZ S04 Sub A 2025-10 |
| 10 | 2026-08-21T14:26:01.244521+00:00 | `budgets` | `ee8f3130-5183-4ab8-940d-d3cbad80911b|2025-10` | amount set | — | `{"amount_cents": -50000, "month": "2025-10", "notes": "", "sub_category_id": "ee8f3130-5183-4ab8-940d-d3cbad80911b"}` | §3.13 row 8 — ZZ S04 Sub B 2025-10 |
| 11 | 2026-08-21T14:26:02.476753+00:00 | `budgets` | `7b4140a0-c9c1-476b-9447-583110e198ec|2025-10` | amount set | — | `{"amount_cents": -20000, "month": "2025-10", "notes": "", "sub_category_id": "7b4140a0-c9c1-476b-9447-583110e198ec"}` | §3.13 row 8 — ZZ S04 Sub C 2025-10 |
| 12 | 2026-08-21T14:26:03.641739+00:00 | `budgets` | `4c5e64d7-4782-43a1-92ac-35117aadd965|2025-10` | amount set | — | `{"amount_cents": -30000, "month": "2025-10", "notes": "", "sub_category_id": "4c5e64d7-4782-43a1-92ac-35117aadd965"}` | §3.13 row 8 — ZZ S04 Sub D 2025-10 |
| 13 | 2026-08-21T14:26:04.753866+00:00 | `budgets` | `2f973007-0347-4eff-98dc-1278606e3df1|2025-11` | amount set | — | `{"amount_cents": -10000, "month": "2025-11", "notes": "", "sub_category_id": "2f973007-0347-4eff-98dc-1278606e3df1"}` | §3.13 row 8 — ZZ S04 Sub A 2025-11 |
| 14 | 2026-08-21T14:26:05.836204+00:00 | `budgets` | `ee8f3130-5183-4ab8-940d-d3cbad80911b|2025-11` | amount set | — | `{"amount_cents": -50000, "month": "2025-11", "notes": "", "sub_category_id": "ee8f3130-5183-4ab8-940d-d3cbad80911b"}` | §3.13 row 8 — ZZ S04 Sub B 2025-11 |
| 15 | 2026-08-21T14:26:07.043056+00:00 | `budgets` | `7b4140a0-c9c1-476b-9447-583110e198ec|2025-11` | amount set | — | `{"amount_cents": -20000, "month": "2025-11", "notes": "", "sub_category_id": "7b4140a0-c9c1-476b-9447-583110e198ec"}` | §3.13 row 8 — ZZ S04 Sub C 2025-11 |
| 16 | 2026-08-21T14:26:08.240541+00:00 | `budgets` | `4c5e64d7-4782-43a1-92ac-35117aadd965|2025-11` | amount set | — | `{"amount_cents": -30000, "month": "2025-11", "notes": "", "sub_category_id": "4c5e64d7-4782-43a1-92ac-35117aadd965"}` | §3.13 row 8 — ZZ S04 Sub D 2025-11 |
| 17 | 2026-08-21T14:26:09.407180+00:00 | `budgets` | `2f973007-0347-4eff-98dc-1278606e3df1|2025-12` | amount set | — | `{"amount_cents": -10000, "month": "2025-12", "notes": "", "sub_category_id": "2f973007-0347-4eff-98dc-1278606e3df1"}` | §3.13 row 8 — ZZ S04 Sub A 2025-12 |
| 18 | 2026-08-21T14:26:10.503703+00:00 | `budgets` | `ee8f3130-5183-4ab8-940d-d3cbad80911b|2025-12` | amount set | — | `{"amount_cents": -50000, "month": "2025-12", "notes": "", "sub_category_id": "ee8f3130-5183-4ab8-940d-d3cbad80911b"}` | §3.13 row 8 — ZZ S04 Sub B 2025-12 |
| 19 | 2026-08-21T14:26:11.711308+00:00 | `budgets` | `7b4140a0-c9c1-476b-9447-583110e198ec|2025-12` | amount set | — | `{"amount_cents": -20000, "month": "2025-12", "notes": "", "sub_category_id": "7b4140a0-c9c1-476b-9447-583110e198ec"}` | §3.13 row 8 — ZZ S04 Sub C 2025-12 |
| 20 | 2026-08-21T14:26:12.828713+00:00 | `budgets` | `4c5e64d7-4782-43a1-92ac-35117aadd965|2025-12` | amount set | — | `{"amount_cents": -30000, "month": "2025-12", "notes": "", "sub_category_id": "4c5e64d7-4782-43a1-92ac-35117aadd965"}` | §3.13 row 8 — ZZ S04 Sub D 2025-12 |
| 21 | 2026-08-21T14:26:13.990484+00:00 | `budgets` | `e0bb741b-fe58-4b96-923c-552bca90cd6c|2025-12` | amount set | — | `{"amount_cents": 100000, "month": "2025-12", "notes": "", "sub_category_id": "e0bb741b-fe58-4b96-923c-552bca90cd6c"}` | §3.13 row 8 — income sub, chosen month |
| 22 | 2026-08-21T14:26:15.391441+00:00 | `budgets` | `2f973007-0347-4eff-98dc-1278606e3df1|2027-06` | amount set | — | `{"amount_cents": -10000, "month": "2027-06", "notes": "", "sub_category_id": "2f973007-0347-4eff-98dc-1278606e3df1"}` | §3.13 row 9 — far-future source month |
| 23 | 2026-08-21T14:26:16.577415+00:00 | `budgets` | `4c5e64d7-4782-43a1-92ac-35117aadd965|2027-06` | amount set | — | `{"amount_cents": -30000, "month": "2027-06", "notes": "", "sub_category_id": "4c5e64d7-4782-43a1-92ac-35117aadd965"}` | §3.13 row 9 — far-future source month |
| 24 | 2026-08-21T14:26:17.712073+00:00 | `budgets` | `7b4140a0-c9c1-476b-9447-583110e198ec|2027-06` | amount set | — | `{"amount_cents": -20000, "month": "2027-06", "notes": "", "sub_category_id": "7b4140a0-c9c1-476b-9447-583110e198ec"}` | §3.13 row 9 — archived sub's source row, so open-month can be shown to SKIP it |
| 25 | 2026-08-21T14:26:18.955802+00:00 | `budgets` | `2f973007-0347-4eff-98dc-1278606e3df1|2026-01` | amount set | — | `{"amount_cents": -10000, "month": "2026-01", "notes": "", "sub_category_id": "2f973007-0347-4eff-98dc-1278606e3df1"}` | §3.13 row 11 — month after the chosen one, no transactions against it |
| 26 | 2026-08-21T14:26:20.185066+00:00 | `budgets` | `ee8f3130-5183-4ab8-940d-d3cbad80911b|2026-01` | amount set | — | `{"amount_cents": -50000, "month": "2026-01", "notes": "", "sub_category_id": "ee8f3130-5183-4ab8-940d-d3cbad80911b"}` | §3.13 row 11 — month after the chosen one, no transactions against it |
| 27 | 2026-08-21T14:26:21.370711+00:00 | `budgets` | `4c5e64d7-4782-43a1-92ac-35117aadd965|2026-01` | amount set | — | `{"amount_cents": -30000, "month": "2026-01", "notes": "", "sub_category_id": "4c5e64d7-4782-43a1-92ac-35117aadd965"}` | §3.13 row 11 — month after the chosen one, no transactions against it |
| 28 | 2026-08-21T14:26:25.353389+00:00 | `transactions` | `aaee4da2-992e-4fca-8e1e-479e009e73c2` | created | — | `{"account": "5f7fae72-2", "active": true, "amount_cents": -150000, "category": "2f973007-0347-4eff-98dc-1278606e3df1", "date": "2025-12-15", "description": "ZZ S04 A 30x …` | §3.13 row 10 — ZZ S04 A 30x over part 1 |
| 29 | 2026-08-21T14:26:26.503582+00:00 | `transactions` | `f6514bb5-07bc-4104-be4c-8446c5a66fc4` | created | — | `{"account": "5f7fae72-2", "active": true, "amount_cents": -160000, "category": "2f973007-0347-4eff-98dc-1278606e3df1", "date": "2025-12-15", "description": "ZZ S04 A 30x …` | §3.13 row 10 — ZZ S04 A 30x over part 2 |
| 30 | 2026-08-21T14:26:28.273507+00:00 | `transactions` | `0209be56-0780-4ddf-ad6e-5c88fc7dcc8d` | created | — | `{"account": "5f7fae72-2", "active": true, "amount_cents": -20000, "category": "ee8f3130-5183-4ab8-940d-d3cbad80911b", "date": "2025-12-15", "description": "ZZ S04 B withi…` | §3.13 row 10 — ZZ S04 B within budget |
| 31 | 2026-08-21T14:26:32.530832+00:00 | `transactions` | `1970f8c5-a998-426c-8146-a137a15eff12` | created | — | `{"account": "5f7fae72-2", "active": true, "amount_cents": -10000, "category": "ee8f3130-5183-4ab8-940d-d3cbad80911b", "date": "2025-12-15", "description": "ZZ S04 B withi…` | §3.13 row 10 — ZZ S04 B within budget 2 |
| 32 | 2026-08-21T14:26:36.575182+00:00 | `transactions` | `63c818dd-7b4a-47ba-a72d-148ff6eedbd2` | created | — | `{"account": "5f7fae72-2", "active": true, "amount_cents": -25000, "category": "7b4140a0-c9c1-476b-9447-583110e198ec", "date": "2025-12-15", "description": "ZZ S04 C archi…` | §3.13 row 10 — ZZ S04 C archived, non-zero total |
| 33 | 2026-08-21T14:26:38.702493+00:00 | `transactions` | `fe4ac2ed-0e78-40c8-aebf-424b0502ad18` | created | — | `{"account": "5f7fae72-2", "active": true, "amount_cents": -70000, "category": "4c5e64d7-4782-43a1-92ac-35117aadd965", "date": "2025-12-15", "description": "ZZ S04 D 3x ov…` | §3.13 row 10 — ZZ S04 D 3x over part 1 |
| 34 | 2026-08-21T14:26:40.549805+00:00 | `transactions` | `b0e8dd12-9f9e-4f3c-9e7c-28b5a75c20ec` | created | — | `{"account": "5f7fae72-2", "active": true, "amount_cents": -50000, "category": "4c5e64d7-4782-43a1-92ac-35117aadd965", "date": "2025-12-15", "description": "ZZ S04 D 3x ov…` | §3.13 row 10 — ZZ S04 D 3x over part 2 |
| 35 | 2026-08-21T14:26:42.121946+00:00 | `transactions` | `41a10837-4434-4705-b4a2-b39c1974116f` | created | — | `{"account": "5f7fae72-2", "active": true, "amount_cents": 40000, "category": "e0bb741b-fe58-4b96-923c-552bca90cd6c", "date": "2025-12-15", "description": "ZZ S04 income a…` | §3.13 row 10 — ZZ S04 income arrives short part 1 |
| 36 | 2026-08-21T14:26:43.695457+00:00 | `transactions` | `86311fe9-b12d-4e0b-ba86-66399cfb139a` | created | — | `{"account": "5f7fae72-2", "active": true, "amount_cents": 20000, "category": "e0bb741b-fe58-4b96-923c-552bca90cd6c", "date": "2025-12-15", "description": "ZZ S04 income a…` | §3.13 row 10 — ZZ S04 income arrives short part 2 |
| 37 | 2026-08-21T14:26:48.283124+00:00 | `sub_categories` | `7b4140a0-c9c1-476b-9447-583110e198ec` | archived | `{"active": true, "order": 2}` | `{"active": false, "order": -1}` | §3.13 row 5 — left archived; the AC-6.4 exclusion proof |

## Per table

- **`budgets`** — 19 entries (0 creations, 19 other writes)
- **`categories`** — 2 entries (2 creations, 0 other writes)
- **`sub_categories`** — 6 entries (5 creations, 1 other writes)
- **`transactions`** — 10 entries (9 creations, 1 other writes)

**Total ledger entries: 37.**

## Promote / rollback ledger (AC-10.6) — written as part of each promote

| slug | version | record_uid | bytes | sha256 | previous current | UTC |
|---|---|---|---|---|---|---|
| `x` | 1.3.0 | `20434238-e75c-4253-b555-7671179f15f2` | 134285 | `08cf13544d1fd99c…` | `66bf92c3-e342-47a1-87bc-205a8b96805a` (1.2.2) | 2026-08-21T14:27:33.308399+00:00 |
| `d-dash` | 1.3.0 | `822b9a38-4760-4de4-ac2d-f05ad8fb588d` | 136510 | `e59503b067761f71…` | `be1c8c3e-c104-44fb-a130-7c0b8646dbc5` (1.2.2) | 2026-08-21T14:27:41.213897+00:00 |
| `m-dash` | 1.3.0 | `887c36f6-6b56-4fc3-a717-9efbe0dafb2b` | 137497 | `a4a4613b389c6a59…` | `f1cb63d1-e4f0-4133-b389-ce4159466bdd` (1.2.2) | 2026-08-21T14:27:46.090239+00:00 |
| `d-trans` | 1.3.0 | `ceaae997-1898-4646-ae62-b6c7139df8f6` | 187658 | `5dbea30beaa3350c…` | `3eff7bcb-77ff-47ad-8cbb-402b42003d3a` (1.2.3) | 2026-08-21T14:27:51.160820+00:00 |
| `m-trans` | 1.3.0 | `530b61be-1d65-411c-8760-f1885b61af61` | 200503 | `cb4dba83cce448a2…` | `731e2b29-7573-49a0-8d4d-173aa6dfbb67` (1.2.2) | 2026-08-21T14:27:56.398346+00:00 |
| `d-budget` | 1.3.0 | `8a85ed6e-ba93-4862-b37b-9cb600f44d22` | 194716 | `4316243418986974…` | — | 2026-08-21T14:28:01.372792+00:00 |
| `m-budget` | 1.3.0 | `eef48d4c-48c7-43b4-b276-185782aec6ef` | 204550 | `dc33eb675baa41db…` | — | 2026-08-21T14:28:06.411201+00:00 |

All seven reconciled against `/build/list` (current `record_uid` == promoted) and against
the **served bytes** (`sha256` of `GET /x?slug=…` == the promoted bytes). Both PASS.
