# BLESS laboratory pilot runtime

Source: `/Users/andrea/PycharmProjects/beliefs-experiments-lab`  
Source branch: `lab-conversion`  
Source commit: `fdfa63e29d342176eb5e23d8babfc48e9583e900`  
Source tag: `pre-pilot-2026-10-20` (points to that exact commit).

This is the minimal production runtime plus the explicitly requested pilot flow.
Develop and test future changes in the full source repository first, then deliberately
synchronize reviewed changes here. This construction has not run tests or a server.
Do not treat it as a verified deployment or commit secrets.

## Runtime and launch

Provision Python **3.12.6** (the existing production guard requires this exact patch),
oTree **6.0.15**, the requirements-file PostgreSQL driver, a persistent PostgreSQL
study database, private environment values and external JSON described in
`DEPLOYMENT_PRIVATE_CONFIG.md`. Requirements are copied unchanged; nothing was installed.
Use a separate safe database for local inspection, never the collection database.

After privately provisioning all required variables, from this directory:

```sh
OTREE_CONFIG_MODE=production OTREE_LAB_PAYMENTS=1 OTREE_PRODUCTION=1 OTREE_AUTH_LEVEL=STUDY otree prodserver
```

`DATABASE_URL`, `OTREE_ADMIN_PASSWORD`, `OTREE_SECRET_KEY` and
`OTREE_LAB_CONFIG_FILE` must already be exported privately. The Procfile is unchanged:
`web: otree prodserver`. No in-memory/SQLite fallback or DEV/legacy menu is included.
Configure server process supervision/restart, HTTPS/access controls, database backups
and a tested recovery procedure before live collection. No connectivity, persistence,
backup, supervision or browser checks have been performed by this construction task.

Create the intended six-template session with its exact 18/24 participants. Rooms
`lab_18` and `lab_24` retain anonymous seat labels and secure URLs. Check attendance
and all seats before release; no simulated replacements, size downgrades or early starts.

## Pilot participant sequence

* Non-demo: BLESS splash is the existing all-session `fixed.SessionReady` WaitPage.
* Demo: BLESS page with Continua, then the same initial readiness barrier.
* Existing standalone F Practice, unchanged UI/mechanics.
* F comprehension (6 questions / 3 panels), then F blocks 1.1–1.3.
* After the block-3 all-session barrier: explicit section continuation with Continua.
* Assigned E (4 / 2), A (6 / 3) or M (6 / 3) comprehension, then blocks 2.1–2.3.
* After the block-6 all-session barrier: explicit section continuation with Continua.
* Route-specific Policy comprehension (6 / 3), then blocks 3.1–3.3.
* Existing final payment/receipt after block 9 and its barrier.

Within blocks the original Reports → ReportsWait → Decision → PeriodWait → Result
sequence is retained; BlockStart and BlockEnd are minimal participant-clicked pages,
followed by the unchanged all-session BlockEndWait. Reports occur at the original
block-start timing. Gameplay Rules remain available. Long General/Section instruction
pages and General quiz are not in the active page sequence. Quiz review dependencies
remain available; question wording, answers, feedback, scoring and counters are unchanged.

**Initial release is attendance-driven, not experimenter-controlled:** for non-demo
sessions the BLESS WaitPage automatically releases when every configured participant
reaches the existing readiness barrier. There is no administrator release switch and
no new controller. Arrange entry accordingly. After substantive sections, all participants
first pass the original all-session boundary synchronization, then stay on a normal
page without a timeout until they deliberately click Continua. The experimenter gives
verbal permission; the software does not enforce that verbal instruction.

## Treatment/data preservation

Exact arithmetic, reports, matching/handoffs, period and block barriers, thresholds,
fines, redistribution, paid-block selection, payment and eleven `lab_export_v1`
datasets retain their tagged implementations. M/P(M) still disclose all six anonymous
Report-1 values and their anonymous mean; identities and Report 2 remain private.
Only participant-flow wrappers, minimal transition templates, splash and the
production-only settings selection differ. Payment, graphs and Italian gameplay UI
are not replaced with historical versions. Preserve the database and export after
completion before any cleanup.

## BLESS logo

Exact runtime path: `_static/global/bless.png`. Present: copied the original untracked source PNG (not part of the tag); SHA-256 `bd94c0e7b64c8d150585ad50b38931c78b56ed0acd6e38eba533c5540eca3ae6`.
No generated or substitute logo is used.

See `DEPLOYMENT_MANIFEST.md` for the complete runtime allowlist and intentional deviations.
