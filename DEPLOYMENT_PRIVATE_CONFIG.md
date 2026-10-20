# Private deployment configuration

No credential values or private treatment realizations are included.

| Variable / private field | Purpose |
|---|---|
| `OTREE_CONFIG_MODE=production` | Only supported deployment menu; six production templates. |
| `OTREE_LAB_PAYMENTS=1` | Required EUR mode. |
| `OTREE_PRODUCTION=1` | Production server mode. |
| `OTREE_AUTH_LEVEL=STUDY` | Protect study/admin access. |
| `DATABASE_URL` | Private persistent PostgreSQL connection URL; never use a development database for collection. |
| `OTREE_ADMIN_PASSWORD` | Nonblank private admin password. |
| `OTREE_SECRET_KEY` | Stable private secret of at least 32 characters. |
| `OTREE_LAB_CONFIG_FILE` | Absolute path to private study JSON outside this repository. |
| JSON `paid_block` | Externally selected integer 1–9, hidden until final receipt. |
| JSON `matching_seed` | Explicit private matching seed; no DEV default. |
| JSON `rho`, `rho_exact` | Consistent Policy fraction; current design `1/3` with canonical exact companion. |
| JSON `ambiguity_thresholds` | A/P(A): external integer thresholds 40–50 for global blocks 4–9, keys `"4"` through `"9"`. E/M: empty map. Never put realizations in public files. |
| JSON `triplet_id`, `recruitment_batch` | Optional server-only labels. |

The JSON root maps selected production config names to parameter objects. Names:
`lab_E_18`, `lab_E_24`, `lab_A_18`, `lab_A_24`, `lab_M_18`, `lab_M_24`.
Unconfigured templates intentionally cannot create sessions. The unchanged validator
also permits explicit parameters through the existing oTree session-creation API;
use the private file for the pilot. No illustrative threshold map is supplied.

Provision values privately in the process environment and a restricted, readable
external JSON file. Do not place credentials, tokens, database dumps, `.env` files,
server keys or future treatment values in Git. `.gitignore` is a precaution, not
permission to store private files here. Do not set `OTREE_IN_MEMORY` in production.
