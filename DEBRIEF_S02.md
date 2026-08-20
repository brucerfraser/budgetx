# DEBRIEF S02 — the shell: login, entry, and the two-client pattern
**STATUS:** FINAL — 14/14 PASS

**Round:** 02 · **Spec:** `docs/specs/spec_02.md` (APPROVED AND LOCKED, + Addenda 1–7)
**Commits reviewed:** `59fd557` (cycle 1) · `b11a1c7` (cycle 2) · **Deployed and live**, pushed to
`anvil`, mirrored to `origin`.

**Two independent gates, both green.** `visual-reviewer` **21/21**; `spec-reviewer` **13/14** at
cycle 1 and **14/14** at cycle 2 on the full AC-1…AC-14. **Nothing here is marked PASS by the
session that wrote the code** — and where a reviewer contradicted me, the reviewer won and this
file says so.

---

## What is live

Three HTML clients, served from the database, promoted at **v1.1.1**:

| slug | what | URL |
|---|---|---|
| `x` | login + entry, both form factors | `https://budget-x.anvil.app/_/api/x` |
| `d-dash` | desktop shell, 1280-first | `…/_/api/x?slug=d-dash` |
| `m-dash` | phone shell, 390-first | `…/_/api/x?slug=m-dash` |

The app root still serves the Forms app (startup `Frame`, 1,070,184 bytes). **This round is still
invisible to anyone visiting the app root**, exactly as §2.1 requires.

Server side: **`ServerAppData` v1** (new, `GET /app/bootstrap`), **`ServerBuildTools` v2**,
`tools/api.py`. `ServerApi` untouched and still v1.

---

## Models that actually ran each role

| Role | Model | Note |
|---|---|---|
| Orchestrator | **Opus** | migration-phase exception |
| Builder S — server | **Opus** | spec §3.0; the spine and the write path |
| Builder D — canon + `x` + `d-dash` | **Sonnet** | localised client work |
| Builder M — `m-dash` | **Sonnet** | localised client work |
| `fixer` | **Opus** | two repairs, own context, twice |
| `visual-reviewer` | **Fable** | fresh read-only context |
| `spec-reviewer` | **Opus** | fresh read-only context, **a new one per cycle** |

No model was out of credit; no role was downgraded. **No reviewer was weaker than what it
reviewed, and no reviewer was the session that wrote the code.**

---

## Visual review — cycle 1, committed before the spec reviewer was dispatched

**`visual-reviewer`, Fable, fresh read-only context. 21/21 PASS.** It confirmed the served bytes
hashed to the promoted v1.1.1 rows before judging, so it reviewed the live artefact and not a
stale one. It wrote its own instruments rather than re-running mine — which is the point, since
three contexts sharing one verification style pass the same blind spot three times.

| AC | Verdict | Evidence (abridged — the reviewer's own measurements) |
|---|---|---|
| **AC-4.2** | PASS | form visible+enabled at 1280×800 and 390×844; body `rgb(25,28,26)`, submit `rgb(30,185,128)` |
| **AC-4.3** | PASS | wrong password and synthetic unknown address both render exactly `Email or password incorrect` in the same in-page element, indistinguishable; no token stored; blank submit shows `Enter your email and password`; zero native dialogs fired |
| **AC-5.1** | PASS | six items in order; DASHBOARD `rgb(0,82,53)`; four items `aria-disabled`, opacity .4, no href; force-clicking each left the URL unchanged |
| **AC-5.2** | PASS | email equals `/me`'s independent answer; 7 rows equal the independent `/app/bootstrap` active set |
| **AC-5.3** | PASS | storage cleared, back on the form, **old token 401s from `/me`** — revoked server-side |
| **AC-5.4** | PASS | overflow forced at **1280×500** (method recorded): `scrollTop` **0→350**, last card reached, sidebar fixed throughout |
| **AC-6.1** | PASS | both bars `position:fixed`; DOM bounding boxes identical before/after a driven scroll — top `[0,0,390,56]`, bottom `[0,772,390,72]` |
| **AC-6.2** | PASS | SIGN OUT 320×48; sign-out works and the old token 401s |
| **AC-6.3** | PASS | last card bottom **669.2 px** vs bottom-bar top **772 px** — clear of the bar |
| **AC-6.4** | PASS | at the real 390×844: `scrollTop` **0→46**, below-fold content reached. No tall-viewport capture used anywhere |
| **AC-6.5** | PASS | desktop link clicked, landed on `?slug=d-dash` |
| **AC-7.4** | PASS | `body` `rgb(25,28,26)` and primary `rgb(30,185,128)` on all three pages, both widths |
| **AC-9** | PASS | baseline sha256 matched the locked value and predates the first promote; its own fresh capture identical on every observable, both widths; mobile Reports/Settings show the same pre-existing dialog in both captures; console errors 1→1 |
| **AC-13.1** | PASS | exactly one `/auth/login` per attempt, one `/app/bootstrap` per shell open; **the shells never call `/me`** |
| **AC-13.3** | PASS | timed `responseEnd`→`[data-account]` in DOM: desktop **32.8–74.2 ms**, phone **18.8–32.5 ms** |
| **AC-13.5** | PASS | bootstrap route held unanswered: 4 shimmer rows at 600 ms both widths, page not blank |
| **AC-14.1** | PASS | `bx-fade-rise 0.2s`; shots 136.9 ms (desktop) and **22.3 ms** (phone) apart differ; caught mid-animation, opacity 0→0.587 |
| **AC-14.2** | PASS | reduced motion: `animationDuration` 0s, opacity 1 immediately, nothing hidden |
| **AC-14.3** | PASS | zero `alert(`/`confirm(`/`prompt(` in the served bytes; zero dialog events across every drive |
| **AC-14.4** | PASS | login card radius 18 px + `--shadow-2`; account cards 18 px + `--shadow-1` on `--surface-1` |
| **AC-14.5** | PASS | 8 bar-box samples while `document.getAnimations()` was non-empty **and** content was scroll-thrashed: exactly one distinct box per bar |

### The reviewer's one substantive caveat, and what I did about it

It flagged that **the live `accounts` table holds zero archived rows**, so AC-5.2/AC-6.3's
`archived: false` filter was never actually exercised — the equality held because there was
nothing to exclude. That is a fair catch and a gate that cannot fail is worth nothing.

**Closed, without touching business data.** I injected two synthetic rows into the bootstrap
**response** via a Playwright route mock — the live table is untouched — and re-drove both shells:

```
live accounts: 7, archived among them: 0
d-dash   rendered 8 cards | synthetic ACTIVE present=True | synthetic ARCHIVED absent=True -> PASS
m-dash   rendered 8 cards | synthetic ACTIVE present=True | synthetic ARCHIVED absent=True -> PASS
```

7 live + 1 synthetic active rendered; the synthetic archived row appears nowhere in the page. The
filter is real on both shells.

### What the reviewer says is not beautiful yet (none of it fails an AC)

1. **`--error` red fails contrast.** `rgb(214,77,71)` on `--surface-1` is ~**3.6:1**, under WCAG
   AA's 4.5:1. It reads, but this app's user is a person squinting at a phone in sunlight.
   **Not fixed this round** — `--error` is in the §3.4 token block, which is locked verbatim by
   AC-7.3, so changing it needs your ruling. Recommend it for round 03.
2. **The desktop content column is marooned** — ~520 px of content in a ~1020 px area. Defensible
   for a shell, but round 03 should decide the desktop grid rather than inherit it.
3. **Mobile cards are handsome but hollow** — ~100 px for one name. They fill when money arrives.
4. **The phone page only overflows by 46 px**, so the desktop link sits just above the bottom bar.
   Worth watching once real content lands.

Otherwise it reports the design language landing: staggered shimmer, smooth row stagger,
dark-only holding even under a light `prefers-color-scheme`, and a consistent Eczar/pill/soft-shadow
language across all three pages.

---

## Spec review — cycle 1: **13/14 PASS**

**`spec-reviewer`, Opus, fresh read-only context, full AC-1…AC-14.** It confirmed the served bytes
hashed identically at the start and end of its review and that `anvil/master` = `origin/master` =
`59fd557`, so it judged a stable artefact. **It re-drove every criterion itself, including all 21
in the visual reviewer's mandate, and reached the same verdict on all 21** — the two gates agree
without either relying on the other.

| AC | Verdict | The short of it |
|---|---|---|
| **AC-1** | PASS | key-set exact, counts equal an independent `/build/counts`, **13** auth-failure shapes all uniform-401 with zero data keys, **AST scan** of the pushed source found no write call, counts identical across three bootstrap calls |
| **AC-2** | PASS | upload forging `uploaded_by`, `record_uid`, `sha256`, `bytes`, `is_current`, `promoted_at`, `active` → read-back shows **`build-api`**, server-computed sha256, server UUID, `is_current:False`. All 21 list entries carry `uploaded_by`, none carries `html` |
| **AC-3** | PASS | stdout+stderr of login/whoami/build-list and **six** deliberate failures = 4,269 chars: zero secret literals, zero 64-hex, zero ≥32-hex runs; successful TEST2 login after every failure |
| **AC-4** | PASS | served bytes hash to the promoted row; both widths; wrong password and unknown address indistinguishable; correct login lands on the right slug with 64-hex token; stored-token skip and garbage-token clear |
| **AC-5** | PASS | six items, highlight, four inert; email = `/me`, **7 rows matched by name AND `acc_id`**; SIGN OUT revocation confirmed by an independent `/build/session` read-back (`revoked_at` set, `active:false`); scroll driven 0→50 and 50→350 |
| **AC-6** | PASS | bars byte-identical across scroll at **390×844, 390×600 and 390×500**; 320×48 target; at 390×600 **four items below the bar became fully visible after driving scrollTop 0→290** |
| **AC-7** | PASS | zero `<script src=`, only the two font origins, no img/iframe/@import/`url(http)`; **all six blocks equal the canon by HASH**; token block verbatim; palette live |
| **AC-8** | PASS | both shells bounce with storage cleared; exactly one non-serving API response per bounce, uniform 401, zero data keys |
| **AC-9** | PASS | baseline predates the first commit by ~11 min; observables reproduced exactly; mobile Reports/Settings same pre-existing dialog, no worse; console 1→1 |
| **AC-10** | PASS | pyflakes clean; `node --check` passed **and a deliberately broken control file was rejected**, proving the checker was live; hooks executable and dated before the first commit; diff exactly the seven paths, `client_code/` tree hash **identical** at all three commits; **all six ledger rows reconcile against the live table** |
| **AC-11** | PASS | all nine counts identical at 07:09:58Z, 07:11:29Z, 07:11:34Z and 07:54:12Z vs the 05:59:49Z start; `anvil.yaml` diff 0 lines |
| **AC-12** | PASS | splitting both CLAUDE.md versions into 12 sections: **exactly one changed**, eleven byte-identical |
| **AC-13** | **FAIL** | 13.1/13.2/13.3/13.5 all hold. **13.4 fails: the cold-start figure was absent from the debrief.** See below |
| **AC-14** | PASS | rAF sampling caught opacity stepping 0→0.227→…→1; CDP screencast frames 13–15 ms apart differed by 90,038 px desktop / 65,583 px mobile; reduced motion resolves `animationName` to none with opacity constant at 1; bars byte-identical while 9 of 20 frames were mid-animation |

### The one FAIL, stated plainly

**AC-13 failed on a missing number in this file, not on a defect.** AC-13.4 requires "one recorded
cold-start figure after ≥ 10 min idle" and "all figures go in the debrief"; the version of this
debrief the reviewer judged said verbatim *"Cold start (≥10 min idle) is NOT yet measured"*. The
criterion was unmet as written, and the reviewer was right to fail it rather than wave it through.

It also **checked my >1 s attribution and confirmed it**: TLS handshake p50 555–624 ms, and
`/build/version` — which touches no table — costs 1032 ms fresh / 417 ms reused, so bootstrap adds
only ~317 ms over that floor while returning 78 rows. Its own warm figures (n=22), taken at a
different hour than mine, came out faster: reused p50 `/x` 454 ms, `/app/bootstrap` 519 ms,
`/auth/login` 566 ms.

---

## Spec review — cycle 2: **14/14 PASS**

The only repair between cycles was **adding the cold-start figure to this file**. No promoted byte
changed: `x`, `d-dash` and `m-dash` are the same v1.1.1 records cycle 1 judged, same sha256. I
deliberately did not fold in the `data-primary` hook or any other cosmetic finding, because
changing the artefact would have invalidated two clean gates to fix things that fail no criterion.

**The full review re-ran from AC-1 regardless** — never only the failure, because repairs regress
neighbours. Fresh read-only context, Opus, its own instruments.

```
AC-1  PASS   AC-2  PASS   AC-3  PASS   AC-4  PASS   AC-5  PASS
AC-6  PASS   AC-7  PASS   AC-8  PASS   AC-9  PASS   AC-10 PASS
AC-11 PASS   AC-12 PASS   AC-13 PASS   AC-14 PASS
```

**14/14 PASS.** It confirmed the artefact did not move underneath it: the same three v1.1.1 rows,
served bytes hashing to them, and `anvil/master` = `origin/master` = `HEAD` = `b11a1c7`, at both
08:21:42Z and 09:17:25Z.

A few of its checks went beyond either earlier pass and are worth keeping: an **AST walk** of the
pushed `ServerAppData.py` (rather than a regex) confirming no write call and no subscript
assignment anywhere · an upload forging **seven** server-owned fields at once, all of which
read back server-computed · confirmation that **no row anywhere** in `app_versions` carries
`uploaded_by: "EVIL"` · all **20** custom properties in the token block compared value-for-value ·
**CDP screencast** frames rather than `page.screenshot`, which is too slow to catch a 200 ms
animation · and asserting the primary element **exists** before reading its colour, so AC-7.4
could not pass vacuously.

### The reviewer falsified a claim I had made, and it was right

Recorded prominently because it is the most important thing I got wrong this round.

With two cold-start readings (2957 ms, 1752 ms) I wrote that a cold first request costs
"**1.8–3.0 s**" and that the penalty was "**Anvil spinning a worker up, not the network**". The
reviewer took a **third** reading after its own 11-minute idle: **661 ms**, with a **negative**
penalty — the follow-up requests on the warm connection were slower than the "cold" one — and a
646 ms handshake as the dominant term.

Both my claims were wrong. I had even written "a single cold request is not a stable quantity" and
then reasoned as though it were. **The cold-start section above has been rewritten to the honest
result: 0.66–2.96 s across three readings, cause not established.** The correction was made after
the cycle-2 verdict and does not disturb it — AC-13.4 was judged on the recorded figures and on
the >1 s attribution, which the reviewer independently confirmed (handshake 561 ms, no-table
endpoint 1073 ms), not on my narrative around them.

---

## My own basic test, before either reviewer

Run against the promoted v1.1.1: **49/49 checks PASS** (`scratch/s02/drive_clients.py`), plus
**24/24** on the API harness and **21/21** on the served-bytes harness
(`scratch/s02/verify_api.py`), and **AC-3 PASS**.

---

## Speed — AC-13.4, measured honestly

**Two instruments, because they answer different questions.** `n=20` each, warm.

**A. Fresh TCP+TLS connection per request** — every p50 over 1 s:

| endpoint | p50 | p95 |
|---|---|---|
| `GET /x?slug=d-dash` | 1227 ms | 1920 ms |
| `GET /app/bootstrap` | 1301 ms | 1526 ms |
| `POST /auth/login` | 1218 ms | 1632 ms |

**The cause, isolated by measurement rather than asserted:**

| probe | p50 |
|---|---|
| TCP+TLS handshake alone, no HTTP | **565 ms** |
| `GET /build/version` — touches no table, 93 bytes | **1050 ms** |
| `GET /me` — one indexed row | 1048 ms (**−2 ms** vs that floor) |
| `GET /app/bootstrap` — 78 rows, 16,081 bytes | 1278 ms (**+228 ms**) |
| `GET /x?slug=d-dash` — 18,160 bytes | 1247 ms (**+197 ms**) |

An endpoint that does essentially nothing costs 1050 ms. **The >1 s figure is the platform and
network floor, not page or query behaviour** — this round's own work adds ~200 ms on top.

**B. One connection reused — what a browser actually does.** No p50 exceeds 1 s:

| endpoint | p50 | p95 |
|---|---|---|
| `GET /build/version` (floor) | 473 ms | 1048 ms |
| `POST /auth/login` | **527 ms** | 617 ms |
| `GET /me` | 543 ms | 962 ms |
| `GET /x?slug=d-dash` | **687 ms** | 1299 ms |
| `GET /app/bootstrap` | **713 ms** | 876 ms |

Once the HTML arrives the page costs **37 ms desktop / 33 ms mobile** to render. **Nothing a user
feels is waiting on our code.**

### This is platform latency, so it comes to you with options rather than silently accepted

1. **Accept it.** ~700 ms steady state with a 37 ms render is a good app on a link this long.
2. **Distance is the dominant term** — 565 ms of pure handshake says the server is far from South
   Africa. If Anvil offers a nearer region on your plan, that is the single biggest lever.
3. **Trim the bootstrap payload** — 16 KB / 78 rows costs ~240 ms. Smallest lever; later rounds
   want that data anyway.

### Cold start, after ≥10 minutes of enforced idle — **three readings, and no established cause**

The idle **is** the measurement, so each reading owns an uninterrupted window in which nothing
else may touch the app. `GET /x?slug=d-dash`, fresh connection, each after ≥10 min idle:

| reading | idle | first request | next requests, same connection | penalty |
|---|---|---|---|---|
| spec review cycle 1, 08:04:36Z | 10 min 23 s | 1752 ms | 426 ms | +1326 ms |
| mine, 08:07:54Z→08:18:57Z | 11 min 0 s | **2957 ms** | 469 / 514 / 522 ms | +2489 ms |
| spec review cycle 2, 09:16:36Z | 11 min 0 s | **661 ms** | 739 / 873 / 831 ms | **−78 ms** |

**Range 0.66–2.96 s. Cause not established.** I got this wrong in an earlier version of this file
and the cycle-2 reviewer caught it — the correction is the honest result, so it stands here in
place of what I wrote.

**What I claimed from the first two readings, and why it was wrong.** With 2957 ms and 1752 ms in
hand I wrote that a cold first request costs "1.8–3.0 s" and that the penalty, being much larger
than the ~565 ms TLS handshake, was "Anvil spinning a worker up, not the network". The third
reading falsifies both: 661 ms is a third of my lower bound, and its penalty was **negative** —
the three follow-up requests on the already-warm connection were *slower* than the "cold" one,
while the 646 ms handshake was the dominant term. **A penalty that vanishes in one reading out of
three is not a spin-up signature; it is variance in a single-sample measurement.** I had noted
"a single cold request is not a stable quantity" and then immediately reasoned as though it were.

**What is actually established**, because it was measured independently three times and agrees
every time:

- **The fresh-connection >1 s p50 is a platform floor, not our code.** TCP+TLS handshake alone
  p50 **555–646 ms**; `GET /build/version`, which reads no table and returns 93 bytes, p50
  **1032–1073 ms**. `/app/bootstrap` adds only ~230–320 ms on top of that while returning 78 rows.
- **Once a connection is warm, everything is sub-second** — reused-connection p50s across three
  independent runs: `/x` 454–718 ms, `/app/bootstrap` 519–823 ms, `/auth/login` 566–639 ms.
- **The page itself costs 33–41 ms desktop and 20–33 ms mobile** once its HTML has arrived.

**What to tell a user:** the first page of a session takes somewhere between about half a second
and three seconds, unpredictably, and everything after it is sub-second. If the cold end of that
range matters to you, it needs a proper repeated-sample experiment across a day — **three
single-sample readings cannot support a number, and I should not have offered one.**

---

## The rollback ledger — written as part of each promote, not reconstructed

| # | slug | version | record_uid promoted | previously current | promoted (UTC) |
|---|---|---|---|---|---|
| 1 | `x` | 1.1.0 | `9e773a06-8861-478a-ba69-264219a2b46c` | `dddea60c-a062-4311-84c9-984d41fc3315` (v1.0.1) | 06:20:40Z |
| 2 | `d-dash` | 1.1.0 | `a14225e8-6e0f-4d25-b563-b29a25f8477a` | — (new slug) | 06:20:44Z |
| 3 | `m-dash` | 1.1.0 | `f6de19e5-bd99-45fd-bd12-a30ed3011e7b` | — (new slug) | 06:20:48Z |
| 4 | `x` | **1.1.1** | `bf9dae3e-fb80-4271-8ef7-9d3fd61598dc` | `9e773a06-…` (v1.1.0) | 06:32:14Z |
| 5 | `d-dash` | **1.1.1** | `d0f6379e-b240-4352-bc54-36106572d47e` | `a14225e8-…` (v1.1.0) | 06:32:18Z |
| 6 | `m-dash` | **1.1.1** | `6c6d0867-7fd2-4aeb-87a6-fa1fa66741e5` | `f6de19e5-…` (v1.1.0) | 06:32:22Z |

**Live now: rows 4–6.** To roll back a slug, promote its row from the "previously current" column.
`x` rolls all the way back to the S01 placeholder `dddea60c-…`.

**Promotes were frozen from the moment the visual reviewer was dispatched.** Rows 4–6 went live at
06:32Z; the reviewer was dispatched afterwards and nothing moved under it.

---

## Corrections to the spec — expected output, not failure

**Seven addenda**, all in `docs/specs/spec_02.md` §11, none edited in place:

1. **§3.3 vs §6 contradicted each other** on which account `tools/api.py login` drives. §3.3 said
   "everything else unchanged" (the tool read `TEST1_*`); §6 said "drive everything as TEST2".
   Resolved in favour of §6, the safety rule — TEST1 has a single-use failed-login budget.
   `--account {1,2}`, default **2**.
2. **§3.6 says "add the slug table from the blueprint" — the blueprint is not in this repo.** It
   lives in Cowork's vault, which Code cannot reach. The table in `CLAUDE.md` is a
   **reconstruction from spec_02's own contents**, flagged as such. If the blueprint differs,
   CLAUDE.md's is the one to correct.
3. **There is no `node` on this machine.** AC-10.2 was run with the real node Playwright ships
   (`…/playwright/driver/node`, **v24.15.0**), verified to accept `--check` and to reject a syntax
   error.
4. **§3.2 says two changes to `ServerBuildTools`; AC-10.5 requires a third** — "both stamps match
   `/build/version`" is unprovable unless `/build/version` reports `ServerAppData` at all. Added;
   it still touches no table.
5. **§4 does not say what a NULL column serialises to**, and three of its columns are nullable.
   Recorded: `order` null→`0` (sorting last), `str` fields null→`""`, only `icon` and
   `roll_over_date` nullable, whole floats collapse to int. Also: **row order is not part of the
   contract**, and the fixture is not in the endpoint's order — flagged so a reviewer diffing row
   order against the fixture does not misread it. Also the version bump to 1.1.1 and the
   render-blocking fonts defect (below).
6. **AC-10.4's allowed-path list omits `DEBRIEF_S02.md`, which §9 of the same spec mandates** — so
   as written, a compliant round cannot satisfy it. Both review cycles judged it on substance and
   passed it. Future specs should name the debrief in any "diff touches only" criterion.
7. **AC-13.4 asks for "one recorded cold-start figure", and one figure cannot support a
   conclusion here** — three readings spread 661–2957 ms. A future spec wanting a usable
   cold-start number must ask for repeated samples across a period, the way the warm clause
   already asks for ≥20 requests.

---

## New facts worth holding

**A render-blocking `<link rel="stylesheet">` in `<head>` defers execution of every later
`<script>` — including one at the end of `<body>`.** Because all three clients load Google Fonts,
the single `/app/bootstrap` fetch could not start until the fonts request returned:

| page | fonts link | responseEnd → shell proof rendered |
|---|---|---|
| `d-dash` v1.1.0 | render-blocking | **970 ms** |
| `d-dash` v1.1.1 | non-blocking | **44 ms** |

**Every later screen round must copy the non-blocking pattern** (`media="print"` +
`onload="this.media='all'"` + `<noscript>` fallback). A page that loads fonts the obvious way
silently costs about a second. Found by Builder M on its own page and flagged up; the other two
were repaired by `fixer`.

**Three instrument traps, recorded because a reviewer will hit them too:**

- **AC-13.3 must not be timed from `page.goto()`** — that includes the 0.4–1.5 s HTML download the
  criterion explicitly excludes. Time from the navigation entry's `responseEnd`.
- **A 401 body cannot be read from Playwright's `response` event during a bounce** — the page
  navigates away and the body becomes unresolvable, which reads as a FAIL of a passing page. Use
  `page.route` + `route.fetch()`. And the serving route `/x` is itself under `/_/api`, so the
  page's own HTML passes through the same handler — and that HTML contains the words "email" and
  "accounts".
- **AC-7.2 must be compared by HASH, not containment.** `m-dash`'s template put the END marker on
  its own line, so the extracted block was `canon + "\n"`. Containment passed; the hash caught it.
  **A containment check would have shipped this.**

**Both textual scans in this round forced code to stop spelling what they scan for.**
`ServerAppData` avoids writing the write-call patterns in its own DESIGN NOTES (AC-1.4 scans the
source), and `bx_core.js` had to reword the comment *documenting* the no-dialog ban because
AC-14.3 greps the served bytes for `alert(` — the line promising compliance read as three
violations of it.

**Deploy:** `git push anvil master` was live in **4 seconds**. `tools/githooks/` kept its
executable bits across every push this round — re-checked after each.

---

## Things I got wrong and corrected

Recorded because the record has to stay true.

1. **I reported a passing endpoint as a FAIL.** My first harness read `Content-Type` from
   `dict(r.headers)`, which is case-sensitive; Anvil returns `content-type` lowercase, so
   AC-1.1 showed an empty Content-Type. The endpoint was correct all along. Caught by reading the
   raw headers instead of trusting my own instrument.
2. **I reported three compliant pages as AC-7.1 failures** — my external-link pattern required a
   trailing slash, and the pages carry `rel="preconnect"` to the bare font origins.
3. **My inline-JS extractor captured an HTML comment as a script tag.** All three pages document
   the pipeline in comments that mention `<script>` literally; the naive regex swallowed the
   rest of the file and `node --check` failed on `m-dash`. The page was fine. Comments are now
   stripped first.
4. **A gate of mine passed vacuously.** AC-7.4 on `d-dash` accepted "element not found" as a pass —
   `d-dash`'s SIGN OUT carries `data-nav="signout"`, not `data-primary`. Rewritten so not-found is
   a FAIL, and extended to all three pages; all three do compute to `rgb(30,185,128)`.
5. **My first AC-8.2 filter counted the page's own HTML as a leaked data key**, because `/x` is
   itself under `/_/api` and the HTML contains "email".

Items 1–3 and 5 were instrument defects that would each have sent a fixer after working code;
item 4 was a gate that could not fail. All five were found by checking the artefact rather than
trusting the instrument.

---

## Live data touched

**None.** All nine business-table counts are identical at round start (05:59:49Z) and round end
(06:48:39Z): accounts 7 · budgets 58 · categories 14 · sub_categories 57 · transactions 1300 ·
settings 1 · files 8 · test_csv 5 · users 3. `anvil.yaml` is **byte-identical** to its round-start
copy — no schema change of any kind, so this round closed unattended as §2.5 required.

Throwaway build rows were created on `zz-rev-s02` only, which §9 allows. The archived-filter proof
injected synthetic rows into an HTTP **response**, never into a table.

Anvil wrote nothing to the repo this round — `git fetch anvil` showed no platform-authored
changes, and no service was enabled.

---

## Findings I did not fix

From both reviewers. None of these fails a criterion; each has a file and a reason.

- **`--error` contrast ~3.6:1**, below WCAG AA (`client_src/bx_core.css`, the `--error` token).
  The §3.4 token block is locked verbatim by AC-7.3, so **changing it needs your ruling.** Round 03.
- **`d-dash` has no `data-primary` hook** — its sidebar SIGN OUT carries `data-nav="signout"` only,
  so `document.querySelector('[data-primary]')` returns `null` there while it resolves on `x` and
  `m-dash`. **This inconsistency is mine**: I asked Builder D for `data-nav` on all six sidebar
  items and Builder M for `data-primary` on its SIGN OUT, and never reconciled the two. AC-7.4
  passes anyway (the button computes to `rgb(30,185,128)`), and I deliberately did **not** re-cut
  the artefact for it — the pages were frozen under review and a cosmetic hook change is not worth
  invalidating two full gates. **Make the hook set uniform before round 03 copies it.**
- **The desktop SIGN OUT button is 228×41 px**, under the 44 px minimum that AC-6.2 imposes on
  mobile (where it measures 320×48). No criterion applies at desktop, so this is not a failure —
  but if 44 px is a design-language rule rather than a mobile-only one, `bx_core.css`'s desktop
  sidebar button does not honour it. Your call which it is.
- **Desktop content column ~520 px in a ~1020 px area** (`d-dash`). Round 03 should set the
  desktop grid rather than inherit this.
- **`tools/api.py` ignores a `BUILD_SECRET` environment override**, reading only
  `.secrets/budgetx.env` — so the tool cannot be pointed at a second environment without editing
  that file. Harmless today; it matters the first time there is a staging app.
- **`docs/cowork_project_instructions.md` is modified in the working tree and I did not commit
  it.** That edit predates this session by ~11 hours (mtime 2026-08-19T19:08:25Z, last committed
  at `b5fc1a9`); the spec reviewer verified that independently rather than taking my word, and
  confirmed AC-10.4 is unaffected. It is not mine to commit or revert. **It does leave the working
  tree diverged from both remotes, and round 03 inherits that** — worth resolving deliberately.
- **A trailing space on the bearer token is accepted** (`Authorization: Bearer <valid> ` → 200).
  The token is genuine so the behaviour is correct, not a leak; recorded only because it is the
  single 200 in the reviewer's 401-probe matrix and a future reader should not misread it.
- **The Forms app's mobile Transactions screen cannot scroll at all.** At 390×844 *and* 390×500,
  the document and every candidate container report `scrollHeight == clientHeight` — there is no
  scrollable region to drive. Identical to the pre-round baseline and nothing is below the fold
  today, so it is **not this round's defect**, but the screen is laid out in a fixed-height region
  that will **clip rather than scroll** the moment it has more rows. Worth knowing before round 03
  replaces it — and it is the same shape as the IAMS dashboard defect that survived three review
  cycles.
- **`tools/api.py session <bogus>` prints `null` and exits 0** (`tools/api.py:242`). A not-found
  session is not an error, so the exit code is defensible, but a caller cannot distinguish "no such
  session" from a successful lookup.

---

## What I could not verify

- **`archived: true` has never travelled the live server path.** The `accounts` table holds 7 rows
  and **0 archived**, so `GET /app/bootstrap` has only ever emitted `archived: false`. My route-mock
  proof injects synthetic rows into the *response*, so it proves both clients filter correctly but
  exercises nothing in `serialise_account`. The spec reviewer judged AC-5.2 and AC-6.3 on their
  literal text — equality with the `archived:false` set — which holds, and passed them; it
  independently reached the same conclusion I did about the gap. **Closing it properly needs a real
  archived account, which is a business-table write and therefore BLOCKED this round.** The first
  round that opens a write path to `accounts` should create a `ZZ`-prefixed account, archive it,
  and re-check.

---

## For Spec 03 — what this round hands forward

Round 03 is **Transactions** (`d-trans` / `m-trans`), and it is the first round to copy the
pattern this one established. Collected here so nothing has to be reconstructed from the prose
above.

### Decisions only Bruce can make

1. **`--error` contrast.** `rgb(214,77,71)` on `--surface-1` computes to ~3.6:1, under WCAG AA's
   4.5:1. The token is inside the §3.4 block that AC-7.3 locks **verbatim**, so it cannot be
   changed without amending that block. Change it, or accept it deliberately.
2. **Is 44 px a design-language rule or a mobile-only one?** Mobile SIGN OUT is 320×48; the
   desktop sidebar button is 228×41. No criterion applies at desktop today.
3. **The desktop grid.** `d-dash` puts ~520 px of content in a ~1020 px area. Round 03 should
   decide the desktop layout rather than inherit that.

### Carry into spec_03 as written rules

- **Every client must use the non-blocking fonts pattern** — `media="print"` +
  `onload="this.media='all'"` + `<noscript>` fallback. The obvious `<link rel="stylesheet">`
  silently costs ~1 s, because it defers execution of every later `<script>`, including one at
  the end of `<body>`. This round measured 970 ms → 44 ms.
- **AC-7.2-style embed checks must say "compared by hash"**, never containment. Containment
  passed a block that was `canon + "\n"`.
- **Any "the diff touches only" criterion must list `DEBRIEF_S<NN>.md`** — §9 mandates the
  debrief, so AC-10.4 as written could not be satisfied by a compliant round (Addendum 6).
- **A cold-start criterion must ask for repeated samples across a period**, not "one recorded
  figure" — three readings this round spread 661–2957 ms (Addendum 7).
- **Give the reviewers the instrument traps up front.** The five in Addendum 5 cost me four false
  FAILs against working code; handing them to both reviewers meant neither repeated them.
- **`data-*` test hooks are part of the deliverable**, not an afterthought — they are what makes
  §7's "reproducible by anyone, including the reviewers" true. Specify the hook set in the spec so
  it is uniform across both clients from the start.

### Loose ends round 03 should close

- **Make the hook set uniform**: `d-dash` has no `data-primary` (its SIGN OUT carries
  `data-nav="signout"` only), while `x` and `m-dash` do. My inconsistency; not fixed because the
  pages were frozen under review and it fails no criterion.
- **The Forms app's mobile Transactions screen cannot scroll at all** — `scrollHeight ==
  clientHeight` at 390×844 and 390×500. Nothing is below the fold today, so it is not a defect
  yet, but it will **clip rather than scroll** the moment it has more rows. **Round 03 replaces
  exactly this screen**, so build `m-trans` with a real scroller and prove it with a driven
  `scrollTop`, not a screenshot.
- **Prove the `archived` path end to end.** `accounts` holds 7 rows and **0 archived**, so
  `archived: true` has never travelled the live server path — only a route-mocked response. The
  first round that opens a write path to `accounts` should create a `ZZ`-prefixed account, archive
  it, and re-check.
- **`docs/cowork_project_instructions.md` is uncommitted in the working tree** (Bruce's own edit,
  ~11 h before this round). It leaves the tree diverged from both remotes and round 03 inherits
  that. Commit or discard it deliberately.

### What round 03 can rely on

`GET /app/bootstrap` is the one-fetch-per-page-open contract and is frozen: future rounds may
**add** keys, never rename or repurpose one. `bx_core.css` / `bx_core.js` are the canon — embed
them verbatim and hash-check every copy. The two-client pattern, the fixtures-decouple-the-builders
plan, and the disjoint-ownership table all worked and are worth repeating unchanged.
