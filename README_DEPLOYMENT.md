# Finalized BLESS pilot runtime

Source repository: `/Users/andrea/PycharmProjects/beliefs-experiments-lab`
Source branch: `italian-instructions-policy-update`
Authoritative source commit: `f9b3e446111df5d01cf5fbffb7ca17176031a37e`
Previous deployment commit: `1e26a059d10a9ce8b1a8b78c8686340e267e1ec4`.

This repository contains only the runtime closure of the finalized pilot and
production deployment configuration. See DEPLOYMENT_MANIFEST.md for every file,
its provenance, exclusions and the sole runtime configuration difference.
Future changes must first be developed/tested in the full source repository,
then deliberately synchronized here. Never commit secrets or private schedules.

## Environment and launch

Use Python **3.12.6**, **oTree 6.0.15**, the requirements-file **psycopg2** driver
and persistent PostgreSQL. Provision the private environment and external study
parameters described in DEPLOYMENT_PRIVATE_CONFIG.md. The startup guard is unchanged.
No dependency, database or system service is installed or modified by this snapshot.
Use a separate safe database for local smoke checks, never the collection database.

After provisioning all private variables, launch from this directory:

```sh
OTREE_CONFIG_MODE=production OTREE_LAB_PAYMENTS=1 OTREE_PRODUCTION=1 OTREE_AUTH_LEVEL=STUDY otree prodserver
```

DATABASE_URL, OTREE_ADMIN_PASSWORD, OTREE_SECRET_KEY and the optional external
OTREE_LAB_CONFIG_FILE path must already be provisioned privately. Unconfigured
production templates require parameters through the existing supported creation API.
The Procfile remains `web: otree prodserver`. There is no DEV/legacy menu or
in-memory/SQLite production fallback. Configure supervision, HTTPS, database backups
and recovery on the actual server before collection.

## Room operation

Open the same common URL on every lab computer: `<server-origin>/room/lab_18/`
or `<server-origin>/room/lab_24/`. Participants enter their assigned label from
the retained room file. use_secure_urls=False matches the finalized source; no
individual link hash is required. Labels still control admission; knowledge of a
valid label permits using that label, so distribute seat labels appropriately.
Native admin access remains protected by OTREE_AUTH_LEVEL=STUDY.

## Participant flow

Initial BLESS splash (no form, button or timer; admin Advance slowest participant(s))
→ readiness barrier → Section-1 comprehension (three pairs) → session-wide wait
→ first-block admin splash → block-start barrier → two forecasts → report barrier.

Each block has ten periods: Decision (30 seconds, timeout submits zero) → six-person
settlement barrier → Result (20 seconds in ordinary periods; 60-second maximum with early Continua at
Periods 5 and 10) → group result barrier. After Period 10 the session-wide block
barrier precedes the anonymous six-firm BlockSummary, then participant Continua.

Blocks 2/3 in each section use a normal block-start Continua followed by a
session-wide barrier before forecasts. New Sections 2/3 have an admin instruction-
waiting splash, two comprehension pairs, a session-wide comprehension barrier,
and a first-block admin splash. Paper instructions remain the source of rules;
no long instruction booklet, Practice, or rule-review popup is in the active flow.

Routes: fixed → endogenous/ambiguity/messages → corresponding policy → survey
→ lab_payment. There are nine blocks total. The individual survey has six pages,
20 stored answer fields (including the conditional low-clarity follow-up), no waits
and no effect on payment. The final receipt initially shows earnings and provides
a reversible hide/show toggle to a closing BLESS splash; it has no submit/Continue.

M/P(M) display exactly the source's six anonymous Report-1 plans and their mean.
Report 2 and identities remain private. A reveals only the current settled Main
threshold; future thresholds remain external/private. Costs, fines, transfers,
matching, paid block, exact payment and exports are the source implementation.

The authentic logo exists at `_static/global/bless.png` and is copied from the
committed source. No replacement/generated logo or GPS PDF is included.

The survey uses city_birth and current_city, plus optional university_status_other
for Altro. Prepare the updated oTree database schema before collecting pilot data;
this synchronization does not alter an existing database. Participant oTree
branding is hidden by the source participant-base template override.
