# Private deployment configuration

Only names and purposes are recorded here. Supply actual values outside Git.

| Variable / file field | Purpose |
|---|---|
| OTREE_CONFIG_MODE=production | Only supported deployment menu. |
| OTREE_LAB_PAYMENTS=1 | Required EUR payment mode. |
| OTREE_PRODUCTION=1 | Production server mode. |
| OTREE_AUTH_LEVEL=STUDY | Protect native study/admin pages. |
| DATABASE_URL | Private persistent PostgreSQL database connection URL. |
| OTREE_ADMIN_PASSWORD | Nonblank private admin password. |
| OTREE_SECRET_KEY | Stable private key, at least 32 characters. |
| OTREE_LAB_CONFIG_FILE | Path to private study JSON outside this repository. |
| JSON paid_block | Externally selected integer 1–9, hidden until the receipt. |
| JSON matching_seed | Explicit private matching seed. |
| JSON rho, rho_exact | Current Policy share: 1/3, with consistent exact companion. |
| JSON ambiguity_thresholds | A/P(A): externally supplied integer thresholds 40–50 for blocks 4–9; E/M use an empty map. Never commit realized schedules. |
| JSON triplet_id, recruitment_batch | Optional private research labels. |

The private JSON root maps production configuration names to parameter objects:
lab_E_18, lab_E_24, lab_A_18, lab_A_24, lab_M_18, lab_M_24.
Without explicit study parameters these templates intentionally cannot create sessions.
The existing supported session-creation API may supply the same parameters instead.

Python 3.12.6, oTree 6.0.15 and psycopg2 are checked by the unchanged production
guard. OTREE_IN_MEMORY and SQLite are forbidden for production collection.
Do not put passwords, tokens, private keys, database dumps, future A realizations,
.env files or credential files in Git. Provision access-controlled private files
and environment variables on the server.
