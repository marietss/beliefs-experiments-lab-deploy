# Deployment runtime manifest

Authoritative source: `4f942176157996146603d0417324659f344d3754` on `italian-instructions-policy-update`.
Previous deployment: `0976a77ed8aab53b00ff7f81e19d9400c606737b`.
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

## Explicit deployment-only differences

- settings.py retains the existing production-only configuration and guard, mandatory
  environment secret, EUR, six templates and external JSON loader. Its sole change
  from the previous deployment settings is use_secure_urls=False for the two Rooms,
  matching source production behavior. DEV/legacy menus, illustrative threshold
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

109 source-exact runtime files and five deployment-specific files (114 total).

| File | Provenance |
|---|---|
| `.python-version` | exact `4f94217` |
| `Procfile` | exact `4f94217` |
| `_rooms/lab_18.txt` | exact `4f94217` |
| `_rooms/lab_24.txt` | exact `4f94217` |
| `_static/ambiguity/charts.js` | exact `4f94217` |
| `_static/endogenous/charts.js` | exact `4f94217` |
| `_static/fixed/comparable-charts.js` | exact `4f94217` |
| `_static/fixed/decision-charts.js` | exact `4f94217` |
| `_static/fixed/decision-interface.css` | exact `4f94217` |
| `_static/fixed/decision.js` | exact `4f94217` |
| `_static/fixed/display-numbers.js` | exact `4f94217` |
| `_static/fixed/equipment-graph.css` | exact `4f94217` |
| `_static/fixed/equipment-presentation.js` | exact `4f94217` |
| `_static/fixed/instructions-parity.css` | exact `4f94217` |
| `_static/fixed/interface.css` | exact `4f94217` |
| `_static/fixed/parity.css` | exact `4f94217` |
| `_static/fixed/reports.css` | exact `4f94217` |
| `_static/fixed/reports.js` | exact `4f94217` |
| `_static/fixed/vendor/Chart.js-LICENSE.txt` | exact `4f94217` |
| `_static/fixed/vendor/SOURCE.txt` | exact `4f94217` |
| `_static/fixed/vendor/chart.umd-4.4.8.js` | exact `4f94217` |
| `_static/global/bless.png` | exact `4f94217` |
| `_static/messages/charts.js` | exact `4f94217` |
| `_static/policy/charts.js` | exact `4f94217` |
| `_static/survey/survey.css` | exact `4f94217` |
| `_static/survey/survey.js` | exact `4f94217` |
| `_templates/lab/AdminSplash.html` | exact `4f94217` |
| `_templates/lab/BlockSummary.html` | exact `4f94217` |
| `_templates/lab/ComprehensionPair.html` | exact `4f94217` |
| `_templates/lab/MainOutcomeNote.html` | exact `4f94217` |
| `_templates/otree/OutOfRangeNotification.html` | exact `4f94217` |
| `ambiguity/BlockStart.html` | exact `4f94217` |
| `ambiguity/ChartScripts.html` | exact `4f94217` |
| `ambiguity/Decision.html` | exact `4f94217` |
| `ambiguity/DecisionEquipmentGraph.html` | exact `4f94217` |
| `ambiguity/EquipmentGraph.html` | exact `4f94217` |
| `ambiguity/Reports.html` | exact `4f94217` |
| `ambiguity/Result.html` | exact `4f94217` |
| `ambiguity/__init__.py` | exact `4f94217` |
| `ambiguity/presentation.py` | exact `4f94217` |
| `endogenous/BlockStart.html` | exact `4f94217` |
| `endogenous/ChartScripts.html` | exact `4f94217` |
| `endogenous/Decision.html` | exact `4f94217` |
| `endogenous/DecisionEquipmentGraph.html` | exact `4f94217` |
| `endogenous/EquipmentGraph.html` | exact `4f94217` |
| `endogenous/Reports.html` | exact `4f94217` |
| `endogenous/Result.html` | exact `4f94217` |
| `endogenous/__init__.py` | exact `4f94217` |
| `endogenous/presentation.py` | exact `4f94217` |
| `fixed/BlockStart.html` | exact `4f94217` |
| `fixed/ChartScripts.html` | exact `4f94217` |
| `fixed/ComparableStyles.html` | exact `4f94217` |
| `fixed/Decision.html` | exact `4f94217` |
| `fixed/DecisionEquipmentGraph.html` | exact `4f94217` |
| `fixed/EquipmentGraph.html` | exact `4f94217` |
| `fixed/Reports.html` | exact `4f94217` |
| `fixed/Result.html` | exact `4f94217` |
| `fixed/__init__.py` | exact `4f94217` |
| `fixed/presentation.py` | exact `4f94217` |
| `general_instructions/LabComparableStyles.html` | exact `4f94217` |
| `general_instructions/LabReportSliders.html` | exact `4f94217` |
| `general_instructions/instructions.css` | exact `4f94217` |
| `instructions_section1/instructions.css` | exact `4f94217` |
| `lab_cash.py` | exact `4f94217` |
| `lab_comprehension.py` | exact `4f94217` |
| `lab_config.py` | exact `4f94217` |
| `lab_export.py` | exact `4f94217` |
| `lab_flow.py` | exact `4f94217` |
| `lab_instructions.py` | exact `4f94217` |
| `lab_matching.py` | exact `4f94217` |
| `lab_payment/Payment.html` | exact `4f94217` |
| `lab_payment/__init__.py` | exact `4f94217` |
| `lab_persistence.py` | exact `4f94217` |
| `lab_policy.py` | exact `4f94217` |
| `lab_presentation.py` | exact `4f94217` |
| `lab_printed_questions.py` | exact `4f94217` |
| `lab_production.py` | exact `4f94217` |
| `lab_reports.py` | exact `4f94217` |
| `lab_route.py` | exact `4f94217` |
| `lab_rules.py` | exact `4f94217` |
| `lab_threshold.py` | exact `4f94217` |
| `messages/BlockStart.html` | exact `4f94217` |
| `messages/BlockWait.html` | exact `4f94217` |
| `messages/ChartScripts.html` | exact `4f94217` |
| `messages/Decision.html` | exact `4f94217` |
| `messages/DecisionEquipmentGraph.html` | exact `4f94217` |
| `messages/EquipmentGraph.html` | exact `4f94217` |
| `messages/Reports.html` | exact `4f94217` |
| `messages/Result.html` | exact `4f94217` |
| `messages/__init__.py` | exact `4f94217` |
| `messages/presentation.py` | exact `4f94217` |
| `messages/public_reports.py` | exact `4f94217` |
| `policy/BlockStart.html` | exact `4f94217` |
| `policy/BlockWait.html` | exact `4f94217` |
| `policy/ChartScripts.html` | exact `4f94217` |
| `policy/Decision.html` | exact `4f94217` |
| `policy/DecisionEquipmentGraph.html` | exact `4f94217` |
| `policy/EquipmentGraph.html` | exact `4f94217` |
| `policy/Reports.html` | exact `4f94217` |
| `policy/Result.html` | exact `4f94217` |
| `policy/__init__.py` | exact `4f94217` |
| `policy/presentation.py` | exact `4f94217` |
| `policy/settlement.py` | exact `4f94217` |
| `requirements.txt` | exact `4f94217` |
| `stage_game_section1/decision.css` | exact `4f94217` |
| `stage_game_section1/pilot.css` | exact `4f94217` |
| `survey/SurveyPage.html` | exact `4f94217` |
| `survey/SurveySliders.html` | exact `4f94217` |
| `survey/__init__.py` | exact `4f94217` |
| `settings.py` | production-only configuration described above |
| `.gitignore` | unchanged deployment exclusions |
| `DEPLOYMENT_MANIFEST.md` | deployment documentation |
| `DEPLOYMENT_PRIVATE_CONFIG.md` | private configuration names only |
| `README_DEPLOYMENT.md` | deployment operation/provenance |

## Removed obsolete deployment files

- `_static/fixed/instructions-parity.js`
- `_static/fixed/main-outcomes.css`
- `_static/fixed/practice-interface.css`
- `_static/fixed/practice.js`
- `_templates/lab/SectionContinue.html`
- `ambiguity/BlockEnd.html`
- `ambiguity/Rules.html`
- `endogenous/BlockEnd.html`
- `endogenous/Rules.html`
- `fixed/BlessReady.html`
- `fixed/BlessSplash.html`
- `fixed/BlessSplashBody.html`
- `fixed/BlockEnd.html`
- `fixed/Rules.html`
- `general_instructions/LabCanonicalAmbiguityBody.html`
- `general_instructions/LabCanonicalCosts.html`
- `general_instructions/LabCanonicalEndogenousBody.html`
- `general_instructions/LabCanonicalFixedBody.html`
- `general_instructions/LabCanonicalKnownMain.html`
- `general_instructions/LabCanonicalMessagesBody.html`
- `general_instructions/LabCanonicalPolicyBody.html`
- `general_instructions/LabCanonicalPracticeBody.html`
- `general_instructions/LabCanonicalPracticeScripts.html`
- `general_instructions/LabCanonicalSame.html`
- `general_instructions/LabCanonicalSectionBody.html`
- `general_instructions/LabCanonicalSectionReview.html`
- `general_instructions/LabComparableNavigation.html`
- `general_instructions/LabGeneralBody.html`
- `general_instructions/LabMainAmbiguityOutcomes.html`
- `general_instructions/LabMainKnownOutcomes.html`
- `general_instructions/LabOverview.html`
- `general_instructions/LabPlannedMeanExplanation.html`
- `general_instructions/LabPractice.html`
- `general_instructions/LabQuiz.html`
- `general_instructions/LabSection.html`
- `messages/BlockEnd.html`
- `messages/Rules.html`
- `policy/BlockEnd.html`
- `policy/BranchRules.html`
- `policy/Rules.html`
