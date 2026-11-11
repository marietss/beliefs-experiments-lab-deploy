# Laboratory operation — lab_design_v1

This is Task 14 configuration/runtime documentation, not a release or human-pilot verdict.
The supported application runtime is **Python 3.12.6, otree==6.0.15**. Do not
upgrade either during collection. `.python-version` now matches the interpreter
used for the lab tests. Install `requirements.txt` in an isolated environment.
oTree's transitive dependencies are pinned by oTree 6.0.15 itself (the installed
set is listed below). No framework/dependency upgrade was made in Task 14.

## Three separate modes

- Default `OTREE_CONFIG_MODE=production`: only `lab_E_18`, `lab_E_24`,
  `lab_A_18`, `lab_A_24`, `lab_M_18`, `lab_M_24` are launchable templates.
- `OTREE_CONFIG_MODE=development`: only the retained `dev_lab_*` fixtures.
  These include illustrative paid blocks/seeds/thresholds and standalone routes;
  **never use them for data collection**. For full payment tests also set
  `OTREE_LAB_PAYMENTS=1`. Tests may use `OTREE_IN_MEMORY=1` only in temporary copies.
- `OTREE_CONFIG_MODE=legacy`: only retained online configurations, their original
  defaults and `my_room`. Unset `OTREE_LAB_PAYMENTS` for GBP. Use a separate
  process/database from EUR collection. Legacy gameplay/instructions are retained.

Production sequences are `fixed → endogenous/ambiguity/messages → policy → lab_payment`.
General instructions, unpaid slider practice and quizzes are embedded in `fixed`;
branch/policy instructions and quizzes are embedded in those apps. Do not add the
legacy `general_instructions` app to these sequences. Production display names
contain only branch and size, never study parameters. No new treatment labels
are sent to participants.

## Prepare the server before collection

Supply these to the process supervisor's private environment, not committed files:

```text
OTREE_CONFIG_MODE=production
OTREE_LAB_PAYMENTS=1
OTREE_PRODUCTION=1
OTREE_AUTH_LEVEL=STUDY
DATABASE_URL=<persistent PostgreSQL connection URL>
OTREE_ADMIN_PASSWORD=<private admin password>
OTREE_SECRET_KEY=<private stable secret of at least 32 characters>
OTREE_LAB_CONFIG_FILE=<absolute path to private study JSON file>
```

Keep the same stable secret across restarts and supervised processes. Never print
credentials, place them in participant URLs, or store real environment files in Git.
Production startup rejects missing secrets/EUR flags, wrong Python/oTree, absent
psycopg2, SQLite/missing database URLs and any `OTREE_IN_MEMORY` value. URL validation
is a guard, **not a connectivity or durability test**. Provision and independently
verify PostgreSQL connectivity, storage persistence, backups and restore procedure
on the actual collection host before use. Do not run destructive reset commands
against a collection database. Keep existing sessions and parameters after restart.

`requirements.txt` retains `psycopg2>=2.8.4`; no untested PostgreSQL-driver pin was
invented. The local test installation has **no psycopg2/libpq connection tested**.
The collection environment must install the driver, record its exact version,
libpq/server versions and installation artifact, and test the real database.
This is a remaining deployment verification item; in-memory tests do not resolve it.
The tested installed Python/oTree dependencies are:

```text
Python 3.12.6; otree 6.0.15
 aiofiles 0.6.0; itsdangerous 1.1.0; MarkupSafe 1.1.1
 python-multipart 0.0.5; SQLAlchemy 1.3.22; Starlette 0.14.1
 uvicorn 0.13.4; websockets 10.1; WTForms 2.3.3; WTForms-SQLAlchemy 0.2
```

The Procfile is `web: otree prodserver`. Installed oTree's `prodserver` aliases
`prodserver1of2`: it runs the ASGI server and starts `otree timeoutsubprocess`.
`prodserver2of2` in **6.0.15** is explicitly a legacy sleep/no-op, so that redundant
worker entry was removed. Supervise the web process and its child, supply the same
environment on restart, expose the server through the lab network/reverse proxy,
and verify its actual process tree. No production process or database was started
by this coding task; devserver/bot success is not evidence of production readiness.

## Supply study parameters ex ante

Store a private UTF-8 JSON object outside the repository, mapping intended config
names to study parameters. A file can prepare one or several templates; unlisted
templates stay visible but **cannot create a session** until supplied with valid
parameters. No paid block, seed, or A threshold has a production default.

Each entry must supply `paid_block` (JSON integer 1–9, not bool) and `matching_seed`
(nonblank string or integer). For A also supply `ambiguity_thresholds` with exactly
string keys `"4"` through `"9"`, each a JSON integer 33–47. Values are chosen externally;
the experiment never draws them. E/M must omit this map or supply `{}`.

Templates explicitly use the current share `rho=0.3` plus canonical
`rho_exact="3/10"`. Verify it for each study launch. To change the configured share,
supply **both** numeric `rho` and matching canonical `rho_exact`; inconsistent
pairs fail. Decimal numeric values alone are not a way to approximate thirds.
Optional text `triplet_id` and `recruitment_batch` are admin/research metadata only.

This is a format illustration, **not launch values** (replace every placeholder;
it deliberately is not executable JSON):

```text
{
  "lab_A_18": {
    "paid_block": <externally selected integer>,
    "matching_seed": "<approved reproducible study seed>",
    "rho": 0.3,
    "rho_exact": "3/10",
    "ambiguity_thresholds": {
      "4": <integer>, "5": <integer>, "6": <integer>,
      "7": <integer>, "8": <integer>, "9": <integer>
    },
    "triplet_id": "<optional non-identifying study set>"
  }
}
```

Unknown config/parameter keys, duplicate JSON keys and invalid supplied entries
fail startup without echoing secret values. Routes, branch, size, fee/rate and
design version cannot be changed through this file. Restart the supervised server
after updating its file for a **future** session. Each created session stores its
own parameters; never edit them during play. oTree's create-session API can also
supply the same parameter fields in `modified_session_config_fields` before
creation; use admin authentication and the exact template participant count.
Never mutate `app_sequence` at runtime. A missing/invalid parameter fails before play.

Production creation revalidates the name/branch/route, design version, exact
18/24 count (both session count and actual records), EUR, exact rho, paid block,
seed, A map and fixed lab constants. Obsolete overrides (e.g. old starting wallet,
cost factor, T or section lengths) are rejected when inconsistent.

## Attendance and anonymous seats

Use room `lab_18` or `lab_24` matching the chosen configuration. The room has exactly
18 or 24 anonymous labels `S01`…`S18/S24`, with secure seat-specific URLs. Obtain
these URLs from the authenticated room admin page, place only the appropriate
seat URL on each lab machine, and check each seat is used once. Labels are
operational identifiers, not personal data; participant code remains research
identity. Do not enter names, emails or recruitment IDs.

Room labels and created records do not prove attendance. Count actual humans
**before allowing any session start/readiness**, confirm exactly the configured
18/24 are present, and verify all browser connections. Attach the matching room
to the created session (the framework also supports room_name at creation).
Do not create 24 then continue with 18, choose size at runtime, bypass a WaitPage,
advance missing participants, enable timeouts, or create simulated replacements.
For a no-show, stop and resolve reserves/replacement administratively before
beginning; if the configured count cannot be met, do not start that session.

The genuine initial all-session readiness barrier remains mandatory. Opening a
seat URL is not independent proof of a human; staff must check attendance.
Within blocks only groups synchronize; between blocks the whole session waits.

## Launch checklist

Before creating a session:

- Select the approved branch E/A/M and the fixed 18/24 template and matching room.
- Supply the external paid block and reproducible matching seed; verify rho/exact
  companion. For A check all six external thresholds, including policy Blocks 7–9.
- Check production/EUR mode, stable secret/admin authentication, real PostgreSQL
  connectivity/backups and supervised server/timeout subprocess.
- Verify the selected launch menu contains six production templates, not DEV or online routes.
- Use exactly the template's participant count; demo defaults are not attendance enforcement.

Before participants begin:

- Confirm physical attendance, correct anonymous seat URLs, and all connections.
- Load the instruction/practice/decision assets on every machine. Chart.js 4.4.8
  is local at `_static/fixed/vendor/chart.umd-4.4.8.js` (SHA-256 in vendor/SOURCE.txt).
  All lab app and instruction assets are served locally, without CDN access.
- Check initial readiness; no missing human may be replaced or skipped.

After the session:

- Verify every participant has nine exact ledger entries, finalized EUR payment,
  and admin totals agreeing with receipts. Payment remains €8.00 + 0.01 × selected
  wallet, final cent rounding only, with signed wallets and no floor/cap.
- Download the eleven normalized `lab_export_v1` exports and the standard wide
  oTree export. Preserve database backups, exports and the exact study configuration
  securely. Never reset/delete the database merely to prepare the next session.

## Version and exact accounting

`lab_design_version=lab_design_v1` and optional study-set fields are stored in
session.config and the immutable `lab_production_config_v1` server snapshot.
They flow into **existing standard oTree wide-export** `session.config.*` columns;
join these by session.code to the existing normalized session table. The eleven
`lab_export_v1` tables/headers and their semantics are unchanged. That table retains
actual production config_name, seed, rho, A map, matching version and payment settings.
No study metadata is supplied to participant templates.

Lab wallets/transfers remain exact reduced n/d strings. `POINTS_DECIMAL_PLACES=2`
is intentionally unchanged: it applies to legacy Currency/admin display, not
experimental accounting. Finalization assigns integer cash-settlement equivalent
points after exact EUR-cent rounding and verifies admin reconciliation, as before.
