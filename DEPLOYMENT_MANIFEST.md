# Deployment runtime manifest

Authoritative source: `73cff2fd38bc90492af82559200844aad38aa85d` on `italian-instructions-policy-update`.
Previous deployment: `3e1877496ab990d15a78334aba2335ff7d2ff7e7`.
All source files below were read with `git show COMMIT:path`; no uncommitted
source content, tests, audit material, credentials or treatment schedules were copied.

## Runtime roles

- Seven active apps: fixed, endogenous, ambiguity, messages, policy, survey, lab_payment.
- Python import closure: exact rules, configuration validation, matching, persistence,
  reports, presentation, paired comprehension, printed-question bank, flow gates,
  cash accounting and runtime exports.
- Active-page template/include closure, including shared AdminSplash,
  ComprehensionPair, BlockSummary, MainOutcomeNote and the framework end notice.
- Referenced local CSS/JS, BLESS PNG, Chart.js distribution and its license/source note.
- Original requirements, Python version, Procfile and both participant-label files.

Inactive instruction/practice/review classes remain in exact source controllers but
are absent from page_sequence. Their unused templates/assets are not runtime roots.
The two retained legacy CSS directories contain only styles included by active pages.
`otree/Page.html` and `otree/WaitPage.html` are supplied by pinned oTree 6.0.15.
The source-exact `_templates/otree/Base_UserFacing.html` participant override hides
only oTree branding; framework Bootstrap/JavaScript remain provided by oTree.

## Explicit deployment-only differences

- settings.py retains the existing production-only configuration and guard, mandatory
  environment secret, EUR, six templates and external JSON loader. It is byte-identical to the previous deployment settings, including
  use_secure_urls=False for both Rooms and the same production safeguards. DEV/legacy menus, illustrative threshold
  schedules and the source legacy fallback secret are intentionally omitted.
- .gitignore is retained unchanged from the previous deployment.
- This manifest, README_DEPLOYMENT.md and DEPLOYMENT_PRIVATE_CONFIG.md are deployment
  documentation. No experimental implementation is customized for deployment.

## Exclusions

All test_*.py, app tests.py (including survey/tests.py), survey/README.md,
lab_bot_checks.py, audit directories, review reports, screenshots, logs, caches,
IDE files, databases, .env files, credentials, private JSON, the GPS PDF and unused
legacy instruction/practice/Rules/transition assets are excluded.

## Complete manifest

112 source-exact runtime files and five deployment-specific files (117 total).

| File | Provenance |
|---|---|
| `.python-version` | exact `f9b3e44` |
| `Procfile` | exact `f9b3e44` |
| `_rooms/lab_18.txt` | exact `f9b3e44` |
| `_rooms/lab_24.txt` | exact `f9b3e44` |
| `_static/ambiguity/charts.js` | exact `f9b3e44` |
| `_static/endogenous/charts.js` | exact `f9b3e44` |
| `_static/fixed/comparable-charts.js` | exact `f9b3e44` |
| `_static/fixed/decision-charts.js` | exact `f9b3e44` |
| `_static/fixed/decision-interface.css` | exact `f9b3e44` |
| `_static/fixed/decision.js` | exact `f9b3e44` |
| `_static/fixed/display-numbers.js` | exact `f9b3e44` |
| `_static/fixed/equipment-graph.css` | exact `f9b3e44` |
| `_static/fixed/equipment-presentation.js` | exact `f9b3e44` |
| `_static/fixed/instructions-parity.css` | exact `f9b3e44` |
| `_static/fixed/interface.css` | exact `f9b3e44` |
| `_static/fixed/parity.css` | exact `f9b3e44` |
| `_static/fixed/reports.css` | exact `f9b3e44` |
| `_static/fixed/reports.js` | exact `f9b3e44` |
| `_static/fixed/vendor/Chart.js-LICENSE.txt` | exact `f9b3e44` |
| `_static/fixed/vendor/SOURCE.txt` | exact `f9b3e44` |
| `_static/fixed/vendor/chart.umd-4.4.8.js` | exact `f9b3e44` |
| `_static/global/bless-splash.css` | exact `f9b3e44` |
| `_static/global/bless.png` | exact `f9b3e44` |
| `_static/global/payment-receipt-qr.png` | exact `73cff2f` |
| `_static/messages/charts.js` | exact `f9b3e44` |
| `_static/policy/charts.js` | exact `f9b3e44` |
| `_static/survey/survey.css` | exact `f9b3e44` |
| `_static/survey/survey.js` | exact `f9b3e44` |
| `_templates/lab/AdminSplash.html` | exact `f9b3e44` |
| `_templates/lab/BlockSummary.html` | exact `f9b3e44` |
| `_templates/lab/ComprehensionPair.html` | exact `f9b3e44` |
| `_templates/lab/MainOutcomeNote.html` | exact `f9b3e44` |
| `_templates/otree/Base_UserFacing.html` | exact `f9b3e44` |
| `_templates/otree/OutOfRangeNotification.html` | exact `f9b3e44` |
| `ambiguity/BlockStart.html` | exact `f9b3e44` |
| `ambiguity/ChartScripts.html` | exact `f9b3e44` |
| `ambiguity/Decision.html` | exact `f9b3e44` |
| `ambiguity/DecisionEquipmentGraph.html` | exact `f9b3e44` |
| `ambiguity/EquipmentGraph.html` | exact `f9b3e44` |
| `ambiguity/Reports.html` | exact `f9b3e44` |
| `ambiguity/Result.html` | exact `f9b3e44` |
| `ambiguity/__init__.py` | exact `f9b3e44` |
| `ambiguity/presentation.py` | exact `f9b3e44` |
| `endogenous/BlockStart.html` | exact `f9b3e44` |
| `endogenous/ChartScripts.html` | exact `f9b3e44` |
| `endogenous/Decision.html` | exact `f9b3e44` |
| `endogenous/DecisionEquipmentGraph.html` | exact `f9b3e44` |
| `endogenous/EquipmentGraph.html` | exact `f9b3e44` |
| `endogenous/Reports.html` | exact `f9b3e44` |
| `endogenous/Result.html` | exact `f9b3e44` |
| `endogenous/__init__.py` | exact `f9b3e44` |
| `endogenous/presentation.py` | exact `f9b3e44` |
| `fixed/BlockStart.html` | exact `f9b3e44` |
| `fixed/ChartScripts.html` | exact `f9b3e44` |
| `fixed/ComparableStyles.html` | exact `f9b3e44` |
| `fixed/Decision.html` | exact `f9b3e44` |
| `fixed/DecisionEquipmentGraph.html` | exact `f9b3e44` |
| `fixed/EquipmentGraph.html` | exact `f9b3e44` |
| `fixed/Reports.html` | exact `f9b3e44` |
| `fixed/Result.html` | exact `f9b3e44` |
| `fixed/__init__.py` | exact `f9b3e44` |
| `fixed/presentation.py` | exact `f9b3e44` |
| `general_instructions/LabComparableStyles.html` | exact `f9b3e44` |
| `general_instructions/LabReportSliders.html` | exact `f9b3e44` |
| `general_instructions/instructions.css` | exact `f9b3e44` |
| `instructions_section1/instructions.css` | exact `f9b3e44` |
| `lab_cash.py` | exact `f9b3e44` |
| `lab_comprehension.py` | exact `f9b3e44` |
| `lab_config.py` | exact `f9b3e44` |
| `lab_export.py` | exact `f9b3e44` |
| `lab_flow.py` | exact `f9b3e44` |
| `lab_instructions.py` | exact `f9b3e44` |
| `lab_matching.py` | exact `f9b3e44` |
| `lab_payment/Payment.html` | exact `73cff2f` |
| `lab_payment/__init__.py` | exact `f9b3e44` |
| `lab_persistence.py` | exact `f9b3e44` |
| `lab_policy.py` | exact `f9b3e44` |
| `lab_presentation.py` | exact `f9b3e44` |
| `lab_printed_questions.py` | exact `f9b3e44` |
| `lab_production.py` | exact `f9b3e44` |
| `lab_reports.py` | exact `f9b3e44` |
| `lab_route.py` | exact `f9b3e44` |
| `lab_rules.py` | exact `f9b3e44` |
| `lab_threshold.py` | exact `f9b3e44` |
| `messages/BlockStart.html` | exact `f9b3e44` |
| `messages/BlockWait.html` | exact `f9b3e44` |
| `messages/ChartScripts.html` | exact `f9b3e44` |
| `messages/Decision.html` | exact `f9b3e44` |
| `messages/DecisionEquipmentGraph.html` | exact `f9b3e44` |
| `messages/EquipmentGraph.html` | exact `f9b3e44` |
| `messages/Reports.html` | exact `f9b3e44` |
| `messages/Result.html` | exact `f9b3e44` |
| `messages/__init__.py` | exact `f9b3e44` |
| `messages/presentation.py` | exact `f9b3e44` |
| `messages/public_reports.py` | exact `f9b3e44` |
| `policy/BlockStart.html` | exact `f9b3e44` |
| `policy/BlockWait.html` | exact `f9b3e44` |
| `policy/ChartScripts.html` | exact `f9b3e44` |
| `policy/Decision.html` | exact `f9b3e44` |
| `policy/DecisionEquipmentGraph.html` | exact `f9b3e44` |
| `policy/EquipmentGraph.html` | exact `f9b3e44` |
| `policy/Reports.html` | exact `f9b3e44` |
| `policy/Result.html` | exact `f9b3e44` |
| `policy/__init__.py` | exact `f9b3e44` |
| `policy/presentation.py` | exact `f9b3e44` |
| `policy/settlement.py` | exact `f9b3e44` |
| `requirements.txt` | exact `f9b3e44` |
| `stage_game_section1/decision.css` | exact `f9b3e44` |
| `stage_game_section1/pilot.css` | exact `f9b3e44` |
| `survey/SurveyPage.html` | exact `f9b3e44` |
| `survey/SurveySliders.html` | exact `f9b3e44` |
| `survey/__init__.py` | exact `f9b3e44` |
| `settings.py` | deployment-specific; configuration unchanged, provenance documentation updated |
| `.gitignore` | deployment-specific; configuration unchanged, provenance documentation updated |
| `DEPLOYMENT_MANIFEST.md` | deployment-specific; configuration unchanged, provenance documentation updated |
| `DEPLOYMENT_PRIVATE_CONFIG.md` | deployment-specific; configuration unchanged, provenance documentation updated |
| `README_DEPLOYMENT.md` | deployment-specific; configuration unchanged, provenance documentation updated |

## Delta from previous deployment

Only lab_payment/Payment.html is updated and _static/global/payment-receipt-qr.png
is added, both copied byte-for-byte from source commit 73cff2f. The supplied QR
is neither regenerated nor altered. No other runtime file or production setting
changes. The payment summary uses two columns; hiding it keeps the shared QR and
receipt instructions visible. Payment arithmetic, selected block and exports are
unchanged. Tests, source READMEs, audit material and screenshots are not deployed.
This manifest supersedes the base snapshot provenance in README_DEPLOYMENT.md.
