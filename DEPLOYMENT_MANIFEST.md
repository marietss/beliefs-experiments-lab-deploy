# Deployment manifest

Source commit `fdfa63e29d342176eb5e23d8babfc48e9583e900`, tag `pre-pilot-2026-10-20`.
Files are read from the tagged Git objects, not copied indiscriminately from the
working tree. The sole source-working-tree exception is the authentic supplied
BLESS logo. Present: copied the original untracked source PNG (not part of the tag); SHA-256 `bd94c0e7b64c8d150585ad50b38931c78b56ed0acd6e38eba533c5540eca3ae6`.

## Included runtime roles

* `fixed/`, `endogenous/`, `ambiguity/`, `messages/`, `policy/`, `lab_payment/`:
  active app models/controllers, presentation/settlement helpers, gameplay templates,
  Rules, receipt and pilot transitions. App `tests.py` files are excluded.
* Root `lab_*.py` allowlist below: exact rules, persistence, matching, routes,
  reports, thresholds, policy, presentation, comprehension, cash, production guards
  and runtime custom exports. `lab_bot_checks.py` is excluded.
* `general_instructions/`: template dependencies of Practice/comprehension and
  retained instruction Page classes; no legacy Python app is included. Long pages
  are inactive; quiz review dependencies remain accessible.
* `stage_game_section1/` and `instructions_section1/`: only legacy CSS included by
  active templates, not old experiment apps or screenshots.
* `_templates/`: Italian framework notification and section-continuation template.
* `_static/`: statically referenced local CSS/JS and Chart.js 4.4.8 with license/source
  attribution; authentic BLESS PNG. No remote asset dependency is introduced.
* `_rooms/`: exact anonymous 18/24-seat room files.
* `requirements.txt`, `.python-version`, `Procfile`, `.gitignore`, `settings.py`:
  original runtime pins/command, production-only menu and private environment handling.

## Intentional pilot differences

Only five substantive app `__init__.py` files receive page-sequence changes; fixed
also gets the splash wrapper on the unchanged readiness callback. Fixed reuses the
existing standalone `LabPractice`; all SectionInstructions and General overview/quiz
pages are inactive. Source/branch sections get a participant-clicked continuation
after the original final BlockEndWait. BlockStart/BlockEnd templates are minimal.
No experimental engine, export/payment implementation, quiz logic or chart assets
are modified. Settings retain the source production values/guards while omitting
DEV/legacy configuration lists and the old literal fallback secret. External study
parameters remain mandatory before session creation, without illustrative A values.

## Excluded categories

All unit/browser/UI/bot tests, `lab_bot_checks.py`, source audit/review/restoration
reports, screenshots, audit directories and outputs, temporary files, logs, caches,
IDE metadata, local databases, credentials/private JSON, legacy online Python apps,
unused chart scripts, and Git history of the development repository. In particular:
`coordination_audit_output/`, `timing_audit_output/`, `test_simulated_environment.py`.
No source files were edited. No tests, staging, commits, pushes or installations run.

## Exact runtime file allowlist

| File | Provenance |
|---|---|
| `.gitignore` | pilot-only change |
| `.python-version` | exact tagged copy |
| `DEPLOYMENT_PRIVATE_CONFIG.md` | new pilot file |
| `Procfile` | exact tagged copy |
| `README_DEPLOYMENT.md` | new pilot file |
| `_rooms/lab_18.txt` | exact tagged copy |
| `_rooms/lab_24.txt` | exact tagged copy |
| `_static/ambiguity/charts.js` | exact tagged copy |
| `_static/endogenous/charts.js` | exact tagged copy |
| `_static/fixed/comparable-charts.js` | exact tagged copy |
| `_static/fixed/decision-charts.js` | exact tagged copy |
| `_static/fixed/decision-interface.css` | exact tagged copy |
| `_static/fixed/decision.js` | exact tagged copy |
| `_static/fixed/display-numbers.js` | exact tagged copy |
| `_static/fixed/equipment-graph.css` | exact tagged copy |
| `_static/fixed/equipment-presentation.js` | exact tagged copy |
| `_static/fixed/instructions-parity.css` | exact tagged copy |
| `_static/fixed/instructions-parity.js` | exact tagged copy |
| `_static/fixed/interface.css` | exact tagged copy |
| `_static/fixed/main-outcomes.css` | exact tagged copy |
| `_static/fixed/parity.css` | exact tagged copy |
| `_static/fixed/practice-interface.css` | exact tagged copy |
| `_static/fixed/practice.js` | exact tagged copy |
| `_static/fixed/reports.css` | exact tagged copy |
| `_static/fixed/reports.js` | exact tagged copy |
| `_static/fixed/vendor/Chart.js-LICENSE.txt` | exact tagged copy |
| `_static/fixed/vendor/SOURCE.txt` | exact tagged copy |
| `_static/fixed/vendor/chart.umd-4.4.8.js` | exact tagged copy |
| `_static/global/bless.png` | original untracked logo (documented exception) |
| `_static/messages/charts.js` | exact tagged copy |
| `_static/policy/charts.js` | exact tagged copy |
| `_templates/lab/SectionContinue.html` | new pilot file |
| `_templates/otree/OutOfRangeNotification.html` | exact tagged copy |
| `ambiguity/BlockEnd.html` | pilot-only change |
| `ambiguity/BlockStart.html` | pilot-only change |
| `ambiguity/ChartScripts.html` | exact tagged copy |
| `ambiguity/Decision.html` | exact tagged copy |
| `ambiguity/DecisionEquipmentGraph.html` | exact tagged copy |
| `ambiguity/EquipmentGraph.html` | exact tagged copy |
| `ambiguity/Reports.html` | exact tagged copy |
| `ambiguity/Result.html` | exact tagged copy |
| `ambiguity/Rules.html` | exact tagged copy |
| `ambiguity/__init__.py` | pilot-only change |
| `ambiguity/presentation.py` | exact tagged copy |
| `endogenous/BlockEnd.html` | pilot-only change |
| `endogenous/BlockStart.html` | pilot-only change |
| `endogenous/ChartScripts.html` | exact tagged copy |
| `endogenous/Decision.html` | exact tagged copy |
| `endogenous/DecisionEquipmentGraph.html` | exact tagged copy |
| `endogenous/EquipmentGraph.html` | exact tagged copy |
| `endogenous/Reports.html` | exact tagged copy |
| `endogenous/Result.html` | exact tagged copy |
| `endogenous/Rules.html` | exact tagged copy |
| `endogenous/__init__.py` | pilot-only change |
| `endogenous/presentation.py` | exact tagged copy |
| `fixed/BlessReady.html` | new pilot file |
| `fixed/BlessSplash.html` | new pilot file |
| `fixed/BlessSplashBody.html` | new pilot file |
| `fixed/BlockEnd.html` | pilot-only change |
| `fixed/BlockStart.html` | pilot-only change |
| `fixed/ChartScripts.html` | exact tagged copy |
| `fixed/ComparableStyles.html` | exact tagged copy |
| `fixed/Decision.html` | exact tagged copy |
| `fixed/DecisionEquipmentGraph.html` | exact tagged copy |
| `fixed/EquipmentGraph.html` | exact tagged copy |
| `fixed/Reports.html` | exact tagged copy |
| `fixed/Result.html` | exact tagged copy |
| `fixed/Rules.html` | exact tagged copy |
| `fixed/__init__.py` | pilot-only change |
| `fixed/presentation.py` | exact tagged copy |
| `general_instructions/LabCanonicalAmbiguityBody.html` | exact tagged copy |
| `general_instructions/LabCanonicalCosts.html` | exact tagged copy |
| `general_instructions/LabCanonicalEndogenousBody.html` | exact tagged copy |
| `general_instructions/LabCanonicalFixedBody.html` | exact tagged copy |
| `general_instructions/LabCanonicalKnownMain.html` | exact tagged copy |
| `general_instructions/LabCanonicalMessagesBody.html` | exact tagged copy |
| `general_instructions/LabCanonicalPolicyBody.html` | exact tagged copy |
| `general_instructions/LabCanonicalPracticeBody.html` | exact tagged copy |
| `general_instructions/LabCanonicalPracticeScripts.html` | exact tagged copy |
| `general_instructions/LabCanonicalSame.html` | exact tagged copy |
| `general_instructions/LabCanonicalSectionBody.html` | exact tagged copy |
| `general_instructions/LabCanonicalSectionReview.html` | exact tagged copy |
| `general_instructions/LabComparableNavigation.html` | exact tagged copy |
| `general_instructions/LabComparableStyles.html` | exact tagged copy |
| `general_instructions/LabGeneralBody.html` | exact tagged copy |
| `general_instructions/LabMainAmbiguityOutcomes.html` | exact tagged copy |
| `general_instructions/LabMainKnownOutcomes.html` | exact tagged copy |
| `general_instructions/LabOverview.html` | exact tagged copy |
| `general_instructions/LabPlannedMeanExplanation.html` | exact tagged copy |
| `general_instructions/LabPractice.html` | exact tagged copy |
| `general_instructions/LabQuiz.html` | exact tagged copy |
| `general_instructions/LabReportSliders.html` | exact tagged copy |
| `general_instructions/LabSection.html` | exact tagged copy |
| `general_instructions/instructions.css` | exact tagged copy |
| `instructions_section1/instructions.css` | exact tagged copy |
| `lab_cash.py` | exact tagged copy |
| `lab_config.py` | exact tagged copy |
| `lab_export.py` | exact tagged copy |
| `lab_instructions.py` | exact tagged copy |
| `lab_matching.py` | exact tagged copy |
| `lab_payment/Payment.html` | exact tagged copy |
| `lab_payment/__init__.py` | exact tagged copy |
| `lab_persistence.py` | exact tagged copy |
| `lab_policy.py` | exact tagged copy |
| `lab_presentation.py` | exact tagged copy |
| `lab_production.py` | exact tagged copy |
| `lab_reports.py` | exact tagged copy |
| `lab_route.py` | exact tagged copy |
| `lab_rules.py` | exact tagged copy |
| `lab_threshold.py` | exact tagged copy |
| `messages/BlockEnd.html` | pilot-only change |
| `messages/BlockStart.html` | pilot-only change |
| `messages/BlockWait.html` | exact tagged copy |
| `messages/ChartScripts.html` | exact tagged copy |
| `messages/Decision.html` | exact tagged copy |
| `messages/DecisionEquipmentGraph.html` | exact tagged copy |
| `messages/EquipmentGraph.html` | exact tagged copy |
| `messages/Reports.html` | exact tagged copy |
| `messages/Result.html` | exact tagged copy |
| `messages/Rules.html` | exact tagged copy |
| `messages/__init__.py` | pilot-only change |
| `messages/presentation.py` | exact tagged copy |
| `messages/public_reports.py` | exact tagged copy |
| `policy/BlockEnd.html` | pilot-only change |
| `policy/BlockStart.html` | pilot-only change |
| `policy/BlockWait.html` | exact tagged copy |
| `policy/BranchRules.html` | exact tagged copy |
| `policy/ChartScripts.html` | exact tagged copy |
| `policy/Decision.html` | exact tagged copy |
| `policy/DecisionEquipmentGraph.html` | exact tagged copy |
| `policy/EquipmentGraph.html` | exact tagged copy |
| `policy/Reports.html` | exact tagged copy |
| `policy/Result.html` | exact tagged copy |
| `policy/Rules.html` | exact tagged copy |
| `policy/__init__.py` | pilot-only change |
| `policy/presentation.py` | exact tagged copy |
| `policy/settlement.py` | exact tagged copy |
| `requirements.txt` | exact tagged copy |
| `settings.py` | pilot-only change |
| `stage_game_section1/decision.css` | exact tagged copy |
| `stage_game_section1/pilot.css` | exact tagged copy |

`DEPLOYMENT_MANIFEST.md` is the new manifest itself. The two other deployment documents
are included in the table. This is a construction/provenance record, not a test report.
