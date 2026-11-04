# First Decision timing and removal of completed-block summaries — 4 November 2026

## Repository and baseline

Work was confined to `/Users/andrea/PycharmProjects/beliefs-experiments-lab-deploy`, branch `low-thr`. Starting HEAD: `e25f91e1d9e40d95a3b91fd5977b06ed075e9c2b`; starting `git status --short` was empty. The current working tree, including its already integrated recalibration and P5 session barrier, was used as the baseline. A read-only snapshot was saved under `/tmp/low-thr-baseline-20261104` for comparison.

No other repository was accessed. Nothing was staged, committed, pushed, merged or deployed. No production environment variable, database, dependency or deployment configuration was changed. Previous reports were preserved.

## Runtime implementation

Only these five runtime files changed:

- `fixed/__init__.py`
- `endogenous/__init__.py`
- `ambiguity/__init__.py`
- `messages/__init__.py`
- `policy/__init__.py`

Each `Decision` now implements the native oTree callback:

```python
@staticmethod
def get_timeout_seconds(player):
    return 40 if player.period == 1 else 30
```

`player.period` is the existing local period, computed by `lab_rules.period_for_round`: `(round_number - 1) % 10 + 1`. `local_block` is 1–3 within each strategic app; `global_block` adds the existing section offset, giving 1–9. No global-round list, new state field or additional economic handler was introduced.

Thus the first Decision of every block receives **40 seconds**; local periods 2–10 receive **30 seconds**. The unchanged `Decision.before_next_page` still locks retirement to zero on an unsubmitted timeout. Manual integer choices, validation and settlement are unchanged. Native timers retain elapsed time on reload; they do not restart at 40/30 on each GET.

Reports remain 120 seconds with their existing 0/0 timeout rule. Participant Block Start remains 60 seconds. Ordinary Results remain 20 seconds; P5/P10 Results remain 60 seconds with early Continue. Admin gates and all other timers remain unchanged. A search of active participant templates found no explicit old “30 seconds” prose requiring replacement; no extra timing text was added.

## Removed summary and preserved synchronization

Removed only the final `BlockEnd` entry from each strategic app's `page_sequence`. There is no replacement recap, empty page or additional Continue action.

The removed participant presentation was `lab/BlockSummary.html`:

- heading `Riepilogo del Blocco X.X`;
- anonymous six-company table with `TU` and `Altra azienda`;
- `Attrezzatura all'accertamento principale`;
- `Portafoglio finale`, including the participant's repeated final-block wallet;
- a separate Continue button.

The dormant class, template and read-only context helper remain for compatibility with existing test fixtures. They are not in any active lab page sequence or native page lookup. No block-level fields or stored data were deleted.

The active ending is now:

`Decision P10 → PeriodWait (group settlement) → Result P10 → BlockEndWait (whole session) → next block/section`, or after block 9, `bucket → survey → lab_payment`.

The unchanged `lab_flow.result_complete` already sets `block_feedback_submitted` when a participant leaves P10 Result. Therefore the separate summary was not required to record completion. `BlockEndWait.wait_for_all_groups = True` and its original `complete_block` callback are retained. Fast groups remain blocked until every configured participant has finished P10 Result. Only that barrier installs the next matching. The P5 `MainCheckWait` and all group-level waits are unchanged.

Ordinary Results, Main-Check feedback and Follow-up feedback remain available. Period-10 feedback still displays its existing wallet and sanctions; only the additional whole-block recap is removed.

## Data, economics, exports and payment

AST comparison of all five controllers proved that, after accounting for Decision duration and the omitted sequence entry, their code is unchanged. Byte comparisons against the starting tree confirmed unchanged economic helpers, settlement, matching, `lab_flow`, reports, configuration, participant templates, survey, bucket, payment and export modules.

The calibration remains K0=100, W0=1000, T=5, ten integer-decision periods, cost 0.10 d², Main fine 175+0.5 K with own-zero exemption, Follow-up fine 75 plus forced quadratic cost, E/M 40, external A/P(A) 33–47, strict exact mean comparison, configurable Policy rho, and one externally selected paid block. Base payment remains €8+0.01×selected wallet, with no floor/cap. The separate bucket bonus remains added once.

Verified benchmarks before bucket: Early 800→€16; successful Late 900→€17; failed Late 700→€15; worst wallet −300→€5. Export reconstruction still recovers period/block wallets, actual Main fines, Policy transfers, Follow-up charges, all nine ledger entries and final payments. Selected-block secrecy remains intact until final earnings.

## Test changes

Existing bots no longer yield the removed summary:

- `fixed/tests.py`
- `endogenous/tests.py`
- `ambiguity/tests.py`
- `messages/tests.py`

Existing route/timing expectations updated:

- `test_lab_instructions.py`
- `test_lab_printed_flow.py`
- `test_lab_reports_footer_timing.py`
- `test_lab_route_http.py`
- `test_lab_ui_timing_refinements.py`
- `test_policy.py`
- `test_lab_route.py` — move the legacy bot-only helper import into the one test that uses it; no helper was fabricated or imported from another repository.

New `test_lab_first_decision_block_summary.py` covers all local periods in all nine blocks, all six production and six complete DEV routes, native 40/30 timers, unchanged zero-on-timeout behavior, manual choices, Chrome countdown/Result rendering, and a complete native E18 route through bucket, survey, payment and standard export.

## Validation commands and outcomes

Tests ran using `python3 -B /tmp/run_low_thr.py <test names>`. The runner copies tracked files plus the new test from this repository into disposable directories, then uses the existing explicit development/EUR/in-memory profile. It does not relax production guards or touch a production database. No dependency installation was needed.

| Test arguments | Result |
|---|---|
| `test_lab_ui_timing_refinements.RefinementTests.test_session_main_barrier_18_all_environments test_lab_ui_timing_refinements.RefinementTests.test_session_main_barrier_24_all_environments test_lab_recalibration.CalibrationBenchmarks test_lab_recalibration.ActualSettlementBenchmarks` | 11 passed |
| `test_lab_first_decision_block_summary.FirstDecisionTests.test_local_period_timing_all_blocks_all_production_and_dev_routes test_lab_first_decision_block_summary.FirstDecisionTests.test_native_decision_timeout_zero_early_submission_and_period_results test_lab_route_http test_lab_printed_flow test_policy.PolicyBackendTests.test_waitpages_and_unfinished_session_cannot_rematch` | Initial run: 9 passed, 1 skipped, 2 test-infrastructure errors; both errors resolved and rechecked below |
| `test_lab_route_http test_lab_printed_flow.PrintedFlowTests.test_six_production_sequences_and_counts test_lab_production.ProductionConfigTests.test_six_templates_exact_routes_sizes_and_no_launch_placeholders test_lab_ui_timing_refinements.RefinementTests.test_block_start_early_and_timeout_without_block_summary` | 4 passed, overlapping initial coverage |
| `test_lab_printed_flow.PrintedFlowTests.test_admin_template_has_no_form_input_button_or_automatic_timer` | 1 passed |
| `test_lab_first_decision_block_summary.FirstDecisionTests.test_browser_countdown_and_preserved_main_followup_feedback test_lab_reports_footer_timing.PilotRefinementTests.test_native_timeouts_early_continue_and_economic_invariance test_lab_payment_browser` | 6 passed |
| `test_lab_first_decision_block_summary.FirstDecisionTests.test_full_native_E18_nine_blocks_bucket_survey_payment_and_export` | 1 passed, 184 seconds |
| `test_lab_cash` (in initial export/payment command) | 12 passed |
| `test_lab_export test_lab_payment` | 24 passed (14 export + 10 payment) |
| `test_lab_payment` (fresh-process confirmation) | 10 passed, entirely overlapping the preceding payment coverage |

The full native E18 test uses actual oTree HTTP page navigation and admin gates, not fabricated settlement flags. All 18 participants submit 90 Decisions, receive 9 Main and 9 Follow-up Results, encounter no BlockEnd page, finish 50 Blue bucket allocations through the existing server handler, submit all survey pages and reach final payment. All 9 block barriers complete. The selected Policy wallet remains 900, bucket bonus 250 cents and final payment 1950 cents. Every final-block wallet appears in standard wide export. Bucket dragging itself was not changed or re-tested in this task.

The 18/24 tests cover F/E/A/M/P(E)/P(A)/P(M): fast P5 groups cannot receive feedback until all session decisions finish; current-group settlements remain separate; groups stay fixed through P6–10; the end barrier still blocks fast participants and rematches only after the last arrival. Cross-app HTTP tests verify F→E/A/M and E/A/M→Policy without a summary step.

Chrome checks cover 40/30 countdowns and native timeout submission, preserved Main/Follow-up Results at 1366px and 650px widths, and the unchanged payment/QR privacy interface at 1366×768, 1366×900 and 650×900. Payment screenshots are under `/var/folders/4z/wd8n6vf138q_cz0kcr3pql2r0000gn/T/payment-receipt-ui-7f1djxav`.

Python `compile(...)` checks passed for all 17 changed/new Python files, without bytecode output. No JavaScript changed, so no JS syntax check was necessary. `git diff --check` passed. The index remained empty.

## Issues diagnosed and fixed

- A new full-route assertion initially required the rendered countdown to still equal 40 on a later GET. oTree correctly retained elapsed time (approximately 39.4). The test now separately verifies the configured 40/30 duration and the positive remaining time at or below that duration.
- The browser test initially accessed the native timer's function-local JavaScript variable as a global. It now inspects the rendered native timer initialization and triggers the real countdown completion handler.
- The imported legacy `lab_bot_checks.py` is absent from the starting deployment tree. Moving its import into its actual legacy test consumer allowed independent route/payment/export tests to load. The full native route here deliberately does not depend on those omitted bot artifacts. No economic assertion was removed or replaced with a stub.
- An old no-review-control assertion read absent `general_instructions/LabQuiz.html`. It now examines the active `_templates/lab/ComprehensionPair.html` with the same assertion.
- The original external DOCX comparison remains skipped because that file is unavailable; literal bank snapshot checks still pass.

## Scope and remaining concerns

Final distinct results: **67 tests passed, 1 skipped, 0 unresolved failures**. Reruns overlap and are not counted twice. The skip is the unavailable external original DOCX comparison, not a runtime or economic check. No participant-flow, synchronization, economic, export or payment defect remains in the checks performed.

These changes alter the page sequence. Validation used newly created sessions; resuming a session created under the previous page-index sequence was not tested. No live-server, production PostgreSQL, deployment or physical-monitor claim is made. Legacy tests that explicitly require absent development-only bot artifacts still require those artifacts; no files were copied from another repository.

Nothing was staged, committed, pushed, merged or deployed. HEAD and branch remain unchanged. The only untracked files added by this task are the new regression test and this report.
