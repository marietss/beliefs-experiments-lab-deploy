# Laboratory recalibration update — 4 November 2026

## Status and repository boundary

Implemented and verified in `/Users/andrea/PycharmProjects/beliefs-experiments-lab`, branch `italian-instructions-policy-update`, against HEAD `e485d679e535d0dffaec8e40018b3fbfe0bc6b3e`. HEAD has not changed. Nothing was staged, committed, pushed, migrated or deployed. No other repository was accessed or changed. The three excluded untracked audit/helper items were neither read nor modified.

Final targeted results: **351 distinct tests passed; 1 external-original-document comparison skipped** because the researcher's original DOCX was unavailable. This counts each named test once using its latest result, plus the 61 disjoint pure tests. Reruns overlap; their counts must not be added to infer unique coverage. Initial stale-fixture failures and their resolutions are documented below. No unresolved failure remains in the selected validation set. This is not a claim that every historical test in the repository was run.

## Calibration and canonical implementation

| Parameter | Previous lab value | New value / behavior | Canonical implementation |
|---|---|---|---|
| Initial equipment / wallet | 100 / 1000 | unchanged | `lab_rules.py` |
| Main period / block length | 5 / 10 | unchanged | `lab_rules.py` |
| Voluntary and forced retirement cost | 0.075 × d² | **0.10 × d²**, per period, exact `Fraction(1,10)` | `lab_rules.retirement_cost`; existing F and shared threshold settlement |
| Main fine | 175 + 0.5 K | unchanged; own zero exempt | `lab_rules.main_fine` |
| Follow-up fine | 275 | **75**, only for positive remaining equipment, plus separate forced retirement cost | `lab_rules.follow_up_enforcement` |
| E/M threshold | 45 | **40**, strict group average > threshold safe | `lab_rules.main_enforcement_applies` |
| A/P(A) support | 40–50 | **integer 33–47 inclusive**, externally supplied | `lab_rules.py`, `lab_config.validate_lab_config` |
| Fixed payment | €7.50 | **€8.00** | `lab_cash.FEE`, production and complete DEV session configurations |
| Point conversion / rounding | €0.01, final HALF_UP | unchanged; signed wallet, no floor or cap | `lab_cash.calculate_payment`, `euro_cents` |
| Policy share | production forced 1/3 | **configurable**, default exact 1/3 | existing `lab_policy.configured_rho`; obsolete production restriction removed |

No parallel payoff implementation was introduced. `fixed` still uses the existing canonical rules; E/A/M and Policy still use `lab_threshold` / existing policy settlement. Enforcement uses integer six-person totals, not the rounded displayed mean. `lab_policy.py`, `lab_threshold.py`, `lab_matching.py`, `lab_reports.py`, settlement controllers, survey, bucket runtime, payment selection and export runtime were not changed.

Payment rendering reads the exact fee from the finalized payment record rather than a separate hardcoded 750-cent display. The admin reconciliation now subtracts the canonical fixed fee (800 cents) from final cents. The pre-existing always-paid bucket bonus remains separate and is added exactly once; it does not enter a block wallet or the 1-of-9 selection.

Production design version: `lab_design_recalibration_20261104`. Quiz version: `lab_comprehension_recalibrated_20261104_pairs_v4`. Use newly created sessions for this calibration; this change does not migrate or reinterpret historical session records.

## Benchmarks verified

| Path | Cost | Main fine | Follow-up / forced cost | Final block wallet | Base payment (before separate bucket bonus) |
|---|---:|---:|---:|---:|---:|
| Early: 20 each in periods 1–5 | 200 | 0 | 0 / 0 | 800 | €16.00 |
| Successful Late: 10 each in periods 1–10 | 100 | 0 | 0 / 0 | 900 | €17.00 |
| Failed Late: same retirement, enforced at K=50 | 100 | 200 | 0 / 0 | 700 | €15.00 |
| No retirement in F | 0 | 225 | 75 / 1000 | −300 | €5.00 |

The first four paths were run through actual oTree group settlement callbacks, not just a second formula. An additional dynamic-programming test enumerates all feasible integer retirement choices period by period using canonical economic functions and proves the minimum wallet is −300. The payment test checks the one-cent slope for every integer wallet from −400 to 2000, deliberately beyond the feasible minimum and above €20, proving there is no floor/cap. Fractional wallets and positive/negative half-cent rounding remain covered.

Cost checks include d=0,1,10,20,25,50,100 and every d=0…100 for all app frontend payloads. Ten units cost 10; twenty cost 40; two separate tens cost 20. Integer bounds, irreversible equipment, zero exemption, signed wallets and idempotent settlement remain enforced.

| Main equipment profile | Exact mean | E/M | A safe thresholds |
|---|---:|---|---|
| Six at 50 | 50 | safe | 33–47 |
| Five at 50, one at 0 | 250/6 | safe | 33–41 |
| Four at 50, two at 0 | 200/6 | enforced | 33 only |
| Three at 50, three at 0 | 25 | enforced | none |

Equality is enforced at E/M 40 and every integer A threshold 33…47. Totals 239, 240 and 241 verify comparison around E/M equality without display rounding. Main fines at K=50 and100 are 200 and225. Policy tests cover actual Main pools, no fines, no recipients, equal splitting, exact fractional transfers, rho=0,1/3,1/2,1, no double charging and exclusion of Follow-up charges.

## Instructions, comprehension and frontend

- Active paired comprehension remains F 6 questions and E/A/M/Policy 4 each; two per server page, original IDs/order/answer keys and error counters retained. F cost feedback now states 0.10, split 10+10 =20 versus 20 at once =40. Follow-up options/feedback say75 and the separate quadratic cost. E/M prompts/feedback use40, including equality; A's correct support option/feedback says33–47 with no probabilities.
- Policy's default one-third questions and feasible actual-fine examples remain valid. If a different rho is configured, the share option, transfer answer, distractors and explanatory feedback now reflect that share rather than teaching one-third incorrectly.
- Retained lab instruction bodies, examples, rule fragments and unpaid preview templates were recalibrated, including cost25=62.5, wallet937.5 and the illustrative final calculation800−75−62.5=662.5. No booklet, practice page or rules popup was restored to production flow.
- Current result notes use canonical context values, so their threshold/fine/wallet displays update without new result logic or wording duplication.
- All five Decision accessibility labels now state0.10. Shared preview data already use `lab_rules.COST_FACTOR`; retained unpaid practice data now use that same value rather than a literal75 milli-points.
- A real frontend issue was corrected: the Decision cost chart had a fixed800-point ceiling. Its ceiling is now derived from the canonical cost coefficient and the existing0–100 equipment domain, giving1000 points. Cache versions were updated wherever that script is loaded. No graph structure or control was redesigned.
- Timings remain30-second Decision,20-second ordinary Result,60-second P5/P10 Result with early Continue. Existing BLESS screens, footer removal, Report1 anonymous values/mean, private Report2, ambiguity reveal, QR/privacy toggle and group/session barriers remain intact.

**Paper handout limitation:** substantive instructions are still supplied on paper. The external DOCX/PDF was not rewritten or copied. The researcher must update its numerical calibration before using it with this build. `lab_printed_questions.py` now correctly calls its economically changed wording an adaptation; the original document hash remains provenance, not a claim of literal agreement with the old handout.

## Configuration

- A configurations require exactly string keys `"4"`…`"9"` (three A and three P(A) blocks). Every value must be a genuine integer33…47. Booleans, floats including33.0, strings, missing keys, extra keys and out-of-support values are rejected with clear errors.
- No internal draw, missing-threshold default or support truncation was introduced. Complete DEV maps are explicitly supplied sample values; production templates still contain no usable threshold/paid-block/seed defaults.
- Six production and six complete DEV routes retain `fixed → endogenous/ambiguity/messages → policy → bucket → survey → lab_payment`, nine strategic blocks. The external paid block stays1…9 and hidden until payment.
- Production rho remains subject to exact-value consistency/range validation. When changing its value, supply both numeric `rho` and the matching existing `rho_exact` companion; the current default is1/3. PostgreSQL, environment, authentication, EUR and exact attendance guards were preserved.

## Tests and commands

Tests involving oTree were run in disposable copies containing tracked source files plus `test_lab_recalibration.py`, with the excluded helper/output items omitted. `/tmp/run_recalibration.py` copies the current source, removes `DATABASE_URL`, `PYTHONPATH` and `OTREE_LAB_STUDY_CONFIG` from its child environment, and sets `OTREE_CONFIG_MODE=development OTREE_LAB_PAYMENTS=1 OTREE_IN_MEMORY=1 PYTHONDONTWRITEBYTECODE=1`. It then runs `python3 -B -m unittest -v` with the supplied arguments. No live/local source database was reset. Production guard tests explicitly exercise rejection paths; this was not a live PostgreSQL deployment verification.

Chrome was the installed headless Chrome. The initial sandbox attempt could not launch Chrome; browser checks were rerun with the approved process permission and passed. DOM/interaction checks use real rendered templates, including current payment at1366×768,1366×900 and650×900. The six-route export reconstruction is backend end-to-end; only the E18 native bot replay traversed all90 periods through actual HTTP page flow in this task.

| Validation / exact runner arguments (prefix below) | Outcome |
|---|---|
| `python3 -B -m unittest -q test_lab_rules test_lab_config test_lab_cash` | 61 passed (`/tmp/recalibration-pure-final.log`) |
| `test_lab_recalibration test_lab_instructions test_lab_comprehension_pairs test_lab_printed_flow test_lab_bucket` (before adding the extra semantic question test and native smoke) |44 run:40 passed,3 stale expectations,1 external DOCX skip; all3 corrected/rechecked below |
| `test_lab_instructions.LabInstructionTests.test_fixed_has_no_economic_threshold_and_follow_up_is_complete test_lab_instructions.LabInstructionTests.test_general_structure_payment_rematching_and_exact_examples_both_sizes test_lab_printed_flow.PrintedFlowTests.test_six_production_sequences_and_counts test_lab_printed_flow.PrintedFlowTests.test_protected_economics_reports_M_graphs_payment_and_exports_are_unchanged` |4 passed; restores all43 applicable feature tests to passing (`feature-rechecks`) |
| `test_fixed.FixedBackendTests test_endogenous.EndogenousBackendTests test_ambiguity.AmbiguityBackendTests test_messages.MessagesBackendTests test_messages.PublicReportTests test_policy.PolicyPrimitiveTests test_policy.PolicyBackendTests test_lab_production.ProductionConfigTests test_lab_payment.PaymentBackendTests` |109 run:98 passed,9 stale-fixture failures,1 stale A-map error,1 mistyped class selector; all resolved below. The actual class is `PolicyArithmeticTests`, not `PolicyPrimitiveTests`. |
| Backend focused rerun, exact command below |18 passed: all10 genuine failed cases corrected,7 actual Policy arithmetic tests,1 additional receipt recheck. Across these runs115 distinct real backend tests have passing final outcomes. |
| `test_lab_export` |14 passed. All six E/A/M ×18/24 sessions completed9 blocks/90 periods; independent CSV reconstruction of costs, exact totals, fines, transfers, signed wallets, final cash, group membership and messages. |
| `test_fixed_browser test_endogenous_browser test_ambiguity_browser test_messages_browser test_policy_browser test_lab_decision_ui test_lab_payment_browser` |35 passed (`browser-unrestricted`) |
| `test_lab_decision_ui` after correcting the800-point ceiling |10 passed (`cost-axis-browser`), overlapping previous35 |
| `test_lab_route_http test_lab_route.RouteValidationTests test_lab_payment.PaymentHTTPTests` |7 run:6 passed,1 historical title-case expectation failed; corrected route test rerun below |
| `test_lab_route_http` |1 passed: real HTTP F→E/A/M and E/A/M→Policy boundaries, slow sixth member, session barrier, existing summary, admin release, pair questions, fresh messages, pre-Main secrecy and Main settlement. |
| `test_fixed_ui test_endogenous_ui test_messages_ui test_policy_ui test_lab_canonical_instructions test_lab_legacy_text.LegacyTextTests.test_adapted_examples_are_exact` |55 run:38 passed,17 historical UI/fixture mismatches; corrected and covered by61-test rerun below. Policy HTTP and adapted historical-example tests passed in this first run. |
| `test_fixed_ui.FixedUITests test_endogenous_ui.EndogenousUITests test_messages_ui.MessagesUITests test_messages_ui.PublicMessageUITests test_policy_ui.PolicyUITests test_ambiguity_ui.AmbiguityUITests test_lab_canonical_instructions` |61 passed, including all corrected cases and8 additional A secrecy/rendering tests (`ui-text-final`) |
| `test_lab_recalibration.CalibrationBenchmarks` |6 passed, including exhaustive worst-wallet paths, all specified threshold mixtures, instruction keys/values and no-floor/no-cap conversion |
| `test_lab_recalibration.NativeRouteSmoke test_lab_printed_flow.PrintedFlowTests.test_protected_economics_reports_M_graphs_payment_and_exports_are_unchanged` |2 passed. Native E18 complete90-period replay → bucket50 Blue → all survey pages → terminal payment, exact/admin agreement for18 participants. |
| `test_lab_instructions_browser test_lab_canonical_instructions_browser test_lab_ui_parity_browser test_lab_survey.SurveyTests.test_http_required_inputs_bounds_minimum_lengths_and_preserved_choices test_lab_reports_footer_timing.PilotRefinementTests.test_footer_hidden_on_all_representative_participant_pages_not_admin` |11 run:9 passed,1 stale practice-cost assertion,1 mock missing existing bucket component; corrected/rechecked below |
| `test_lab_canonical_instructions_browser.CanonicalInstructionBrowserTests.test_F_practice_is_sixth_page_and_still_unpaid test_lab_reports_footer_timing.PilotRefinementTests.test_footer_hidden_on_all_representative_participant_pages_not_admin` |2 passed (`instruction-browser-rechecks`) |

All argument-only rows above use `python3 -B /tmp/run_recalibration.py <arguments>`. Logs are `/tmp/recalibration-*.log`. The exact focused backend command was:

```sh
python3 -B /tmp/run_recalibration.py \
  test_fixed.FixedBackendTests.test_six_locked_decisions_before_any_settlement \
  test_ambiguity.AmbiguityBackendTests.test_follow_up_zero_and_positive_negative_wallet \
  test_ambiguity.AmbiguityBackendTests.test_full_production_threshold_map_required_before_play \
  test_ambiguity.AmbiguityBackendTests.test_main_replay_and_reload_do_not_change_outcomes_or_reveal \
  test_ambiguity.AmbiguityBackendTests.test_snapshot_is_stable_and_changed_configuration_fails_closed \
  test_messages.PublicReportTests.test_message_has_no_economic_effect \
  test_policy.PolicyArithmeticTests \
  test_policy.PolicyBackendTests.test_branch_rho_threshold_snapshot_and_standalone_guard \
  test_policy.PolicyBackendTests.test_six_locked_decisions_before_fines_or_transfers \
  test_policy.PolicyBackendTests.test_waitpages_and_unfinished_session_cannot_rematch \
  test_lab_production.ProductionConfigTests.test_room_seats_process_and_local_assets \
  test_lab_payment.PaymentBackendTests.test_negative_selected_wallet_receipt_and_admin_reload
```

Additional verification: compile every modified/new Python file with `compile(Path(file).read_text(), file, 'exec')` (49 files, passed, no bytecode writes); `node --check _static/fixed/decision-charts.js` (passed); `git diff --check` (passed). No installed dependency/package was modified.

### Initial failures diagnosed, rather than hidden

Old numerical fixtures expected the previous costs,45 threshold,40–50 support,275 fine,7.50 fee or old wallets. These were updated to independent new expectations. Previously stale UI tests also expected removed Report prose, old M disclosure wording, old heading case, no BlockEnd summary, summaries before the session barrier, secure Room URLs,20/10 timers and old source checksums. Tests now inspect the current participant templates and finish the actual session barrier before rendering summaries. CSS/script words are no longer misidentified as participant-visible threshold leakage. Current production UI, Room configuration and timing were not changed to satisfy those tests.

The first complete native bot run reached payment but the old payment bot then tried to submit the terminal receipt. `lab_payment/tests.py` now checks its existing GET HTML and finalized records without inventing a submit button; the entire native replay then passed. Reviewed source/wording hashes in current flow tests were updated. The original external DOCX comparison is limited to unrecalibrated questions, and skipped here because that original file is absent. No economic test was disabled.

An earlier combined backend run using superseded test-copy contents was interrupted and replaced; it is not counted as passing. The quiet pure-suite result plus the final named-test index yields351 unique passed tests and1 skipped comparison.

## Remaining numerical references

No economically active stale calibration was found in the six lab routes, shared payoff code, active questions, current frontend payloads or lab payment. A textual number alone is not sufficient evidence of a stale parameter. The following table lists every remaining first-party match for old cost/fee/fine/support/threshold signatures, with current line locations; vendor/minified libraries, unrelated numeric CSS, hash digest substrings and excluded audit output were omitted. Historical audits are records of past builds, not this calibration's specification.

| File and lines | Classification / reason deliberately retained |
|---|---|
| `CANONICAL_LAB_INSTRUCTIONS.md`: 115, 121, 190, 210, 213, 214, 234 | Historical audit/provenance documentation; intentionally records the earlier build. Current authority is LAB_DESIGN_SPEC.md and this report. |
| `ITALIAN_INSTRUCTIONS_REVIEW.md`: 47, 135 | Historical audit/provenance documentation; intentionally records the earlier build. Current authority is LAB_DESIGN_SPEC.md and this report. |
| `LAB_RELEASE_AUDIT.md`: 103, 106, 164, 168, 176, 216 | Historical audit/provenance documentation; intentionally records the earlier build. Current authority is LAB_DESIGN_SPEC.md and this report. |
| `LAB_conversion_audit.md`: 55, 106, 108, 123, 128, 143, 158, 160, 161, 211, 213, 214, 215, 216, 220, 221, 224, 226, 252, 319, 323 | Historical audit/provenance documentation; intentionally records the earlier build. Current authority is LAB_DESIGN_SPEC.md and this report. |
| `LEGACY_INSTRUCTION_TEXT_RESTORATION.md`: 49, 62, 65, 74, 77 | Historical audit/provenance documentation; intentionally records the earlier build. Current authority is LAB_DESIGN_SPEC.md and this report. |
| `UI_PARITY_RESTORATION.md`: 40, 47 | Historical audit/provenance documentation; intentionally records the earlier build. Current authority is LAB_DESIGN_SPEC.md and this report. |
| `_static/fixed/practice-charts.js`: 11, 16 | Unused historical practice asset; no template references it. Current retained practice loads comparable-charts with canonical cost data. |
| `bucket/BucketInstructions.html`: 7 | €0.05 is the unchanged Blue-ball payout, not the equipment retirement-cost coefficient. |
| `bucket/BucketTask.html`: 8 | €0.05 is the unchanged Blue-ball payout, not the equipment retirement-cost coefficient. |
| `general_instructions/LabMainAmbiguityOutcomes.html`: 10 | A hypothetical realized threshold45 is still valid within33–47; illustrates strict equality, not the known E/M threshold. |
| `instructions_section1/Section1FollowUpCheck.html`: 58, 60 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section1/__init__.py`: 33, 34, 96, 97, 298 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section1/practice_decision.js`: 7 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section1/tests.py`: 176, 187, 188 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section2/Section2Change.html`: 31, 32, 37 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section2/Section2Intro.html`: 60 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section2/__init__.py`: 32, 174 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section2/same_instructions_dialog.html`: 14 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section2/tests.py`: 57 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section3/Section3Information.html`: 23, 38 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section3/Section3Rule.html`: 50 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section3/Section3Structure.html`: 62 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section3/__init__.py`: 45, 53, 72, 137, 190, 194 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section3/same_instructions_dialog.html`: 12 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `instructions_section3/tests.py`: 93, 95 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section1/__init__.py`: 49, 53 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section1/decision.js`: 15 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section1/tests.py`: 319, 346, 363 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section2/Decision.html`: 132, 138, 144, 145, 149 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section2/FinalCapitalCheck.html`: 32 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section2/__init__.py`: 48, 52 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section2/decision.js`: 15 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section2/tests.py`: 301, 329 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section3/Decision.html`: 103, 108 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section3/FinalCapitalCheck.html`: 18 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section3/__init__.py`: 58, 62 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `stage_game_section3/tests.py`: 121, 122, 123, 288 | Retained online/legacy app or its test, absent from every complete lab route and not imported for lab settlement. Outside the lab calibration; preserved. |
| `test_lab_cash.py`: 25 | Deliberately invalid float / fraction-string serialization input, not a payoff parameter. |
| `test_lab_config.py`: 124, 126, 154 | 45 is a valid A test value; tests exercise wrong keys, branch/map mismatch or changed snapshots, not an E/M threshold. |
| `test_lab_decision_ui.py`: 179, 204, 294 | Arbitrary rounding fixtures and actual group total275/3; not the Follow-up fine or cost coefficient. |
| `test_lab_instructions.py`: 116, 134, 188 | Negative assertions forbidding obsolete participant copy, not expected live values. |
| `test_lab_payment.py`: 120 | 7.50 is intentionally rejected as a changed/inconsistent session fee. |
| `test_lab_persistence.py`: 24 | Deliberately invalid float / fraction-string serialization input, not a payoff parameter. |
| `test_lab_production.py`: 90, 108, 109 | Rejects old cost/threshold overrides and invalid E/M ambiguity maps. |
| `test_lab_recalibration.py`: 107, 108 | 275 deliberately combines Main200 plus new Follow-up75; test rejects this contaminated Policy pool. |
| `test_lab_ui_parity.py`: 123 | Negative assertions forbidding obsolete participant copy, not expected live values. |
| `test_policy.py`: 174 | 45 is a valid A test value; tests exercise wrong keys, branch/map mismatch or changed snapshots, not an E/M threshold. |

Other deliberate numeric fixtures include `Fraction(3,40)` and46.875 in pure display/serialization tests, and45 as an equipment quantity or valid A threshold. The bucket300-second deadline, graph dimensions, opacity0.45 and colors remain unrelated to this recalibration. Original source-document hashes and historical checksum fixtures were not interpreted as economic values.

## Known design/document differences retained

1. The actual finalized M/P(M) mechanism already displays six anonymous own Main-Check reports plus their mean, while the older design specification's Section8 said mean only. The requested preservation of the existing mechanism takes precedence; Report2 remains private and settlement-independent. This discrepancy is explicitly recorded in LAB_DESIGN_SPEC.md rather than silently changing M.
2. The actual route already includes the always-paid bucket task. Accordingly, €5/€16/€17/€15 above are base experimental payments before that nonnegative separate bonus. Bucket economics, routing and integration were preserved, and the final native replay verifies it is paid once.
3. The external printed handout still requires researcher revision. No long instruction flow was introduced to compensate. Fresh sessions are required for this calibration; previous sessions were not migrated.
4. Local validation used oTree6.0.15 with isolated in-memory development databases and Chrome. No real-server deployment, production PostgreSQL session, or physical-lab monitor inspection is claimed.

## Complete changed-file manifest

Runtime / participant templates:

- `_static/fixed/decision-charts.js`
- `ambiguity/Decision.html`
- `ambiguity/Rules.html`
- `endogenous/Decision.html`
- `endogenous/Rules.html`
- `fixed/Decision.html`
- `fixed/Rules.html`
- `general_instructions/LabCanonicalAmbiguityBody.html`
- `general_instructions/LabCanonicalCosts.html`
- `general_instructions/LabCanonicalFixedBody.html`
- `general_instructions/LabCanonicalKnownMain.html`
- `general_instructions/LabCanonicalMessagesBody.html`
- `general_instructions/LabCanonicalPolicyBody.html`
- `general_instructions/LabCanonicalPracticeBody.html`
- `general_instructions/LabCanonicalPracticeScripts.html`
- `general_instructions/LabCanonicalSame.html`
- `general_instructions/LabCanonicalSectionReview.html`
- `general_instructions/LabComparableCosts.html`
- `general_instructions/LabComparableOption.html`
- `general_instructions/LabComparableSectionBody.html`
- `general_instructions/LabCosts.html`
- `general_instructions/LabGeneralBody.html`
- `general_instructions/LabMainKnownOutcomes.html`
- `general_instructions/LabSectionBody.html`
- `lab_cash.py`
- `lab_config.py`
- `lab_instructions.py`
- `lab_payment/__init__.py`
- `lab_printed_questions.py`
- `lab_production.py`
- `lab_rules.py`
- `messages/Decision.html`
- `messages/Rules.html`
- `policy/BranchRules.html`
- `policy/Decision.html`
- `settings.py`

Updated tests / bots:

- `ambiguity/tests.py`
- `endogenous/tests.py`
- `fixed/tests.py`
- `lab_payment/tests.py`
- `messages/tests.py`
- `test_ambiguity.py`
- `test_ambiguity_browser.py`
- `test_ambiguity_ui.py`
- `test_endogenous.py`
- `test_endogenous_browser.py`
- `test_endogenous_ui.py`
- `test_fixed.py`
- `test_fixed_browser.py`
- `test_fixed_ui.py`
- `test_lab_bucket.py`
- `test_lab_canonical_instructions.py`
- `test_lab_canonical_instructions_browser.py`
- `test_lab_cash.py`
- `test_lab_config.py`
- `test_lab_decision_ui.py`
- `test_lab_export.py`
- `test_lab_instructions.py`
- `test_lab_instructions_browser.py`
- `test_lab_legacy_text.py`
- `test_lab_payment.py`
- `test_lab_payment_browser.py`
- `test_lab_printed_flow.py`
- `test_lab_production.py`
- `test_lab_reports_footer_timing.py`
- `test_lab_route.py`
- `test_lab_route_http.py`
- `test_lab_rules.py`
- `test_lab_survey.py`
- `test_lab_ui_parity_browser.py`
- `test_messages.py`
- `test_messages_browser.py`
- `test_messages_ui.py`
- `test_policy.py`
- `test_policy_browser.py`
- `test_policy_ui.py`
- `test_lab_recalibration.py` (new:10 benchmark/settlement/native-smoke tests)

Documentation:

- `LAB_DESIGN_SPEC.md`
- `LAB_OPERATOR_README.md`
- `lab_payment/README.md`
- `LAB_recalibration_update.md` (new, this report)

## Git verification

`git diff --check`: passed. `git diff --cached --name-only`: empty. No commit/push. The tracked diff stat below excludes the two new untracked implementation-report/test files.

```text
 LAB_DESIGN_SPEC.md                                 | 44 ++++++++++++++----
 LAB_OPERATOR_README.md                             |  4 +-
 _static/fixed/decision-charts.js                   |  2 +-
 ambiguity/Decision.html                            |  4 +-
 ambiguity/Rules.html                               |  6 +--
 ambiguity/tests.py                                 |  2 +-
 endogenous/Decision.html                           |  4 +-
 endogenous/Rules.html                              | 12 ++---
 endogenous/tests.py                                | 12 ++---
 fixed/Decision.html                                |  4 +-
 fixed/Rules.html                                   |  4 +-
 fixed/tests.py                                     |  2 +-
 .../LabCanonicalAmbiguityBody.html                 |  4 +-
 general_instructions/LabCanonicalCosts.html        |  6 +--
 general_instructions/LabCanonicalFixedBody.html    | 10 ++--
 general_instructions/LabCanonicalKnownMain.html    |  4 +-
 general_instructions/LabCanonicalMessagesBody.html |  6 +--
 general_instructions/LabCanonicalPolicyBody.html   | 10 ++--
 general_instructions/LabCanonicalPracticeBody.html |  4 +-
 .../LabCanonicalPracticeScripts.html               |  2 +-
 general_instructions/LabCanonicalSame.html         |  2 +-
 .../LabCanonicalSectionReview.html                 |  2 +-
 general_instructions/LabComparableCosts.html       | 10 ++--
 general_instructions/LabComparableOption.html      |  2 +-
 general_instructions/LabComparableSectionBody.html | 20 ++++----
 general_instructions/LabCosts.html                 |  4 +-
 general_instructions/LabGeneralBody.html           |  2 +-
 general_instructions/LabMainKnownOutcomes.html     |  6 +--
 general_instructions/LabSectionBody.html           |  6 +--
 lab_cash.py                                        | 10 ++--
 lab_config.py                                      |  5 +-
 lab_instructions.py                                | 23 ++++++++--
 lab_payment/README.md                              |  4 +-
 lab_payment/__init__.py                            |  2 +-
 lab_payment/tests.py                               |  4 +-
 lab_printed_questions.py                           | 37 ++++++++-------
 lab_production.py                                  | 15 +++---
 lab_rules.py                                       | 14 +++---
 messages/Decision.html                             |  4 +-
 messages/Rules.html                                |  4 +-
 messages/tests.py                                  | 12 ++---
 policy/BranchRules.html                            |  4 +-
 policy/Decision.html                               |  4 +-
 settings.py                                        | 26 +++++------
 test_ambiguity.py                                  | 22 ++++-----
 test_ambiguity_browser.py                          |  8 ++--
 test_ambiguity_ui.py                               | 17 ++++---
 test_endogenous.py                                 | 42 ++++++++---------
 test_endogenous_browser.py                         |  8 ++--
 test_endogenous_ui.py                              | 52 +++++++++++----------
 test_fixed.py                                      | 14 +++---
 test_fixed_browser.py                              |  6 +--
 test_fixed_ui.py                                   | 41 ++++++++++++-----
 test_lab_bucket.py                                 |  4 +-
 test_lab_canonical_instructions.py                 | 25 +++++-----
 test_lab_canonical_instructions_browser.py         |  4 +-
 test_lab_cash.py                                   | 18 ++++----
 test_lab_config.py                                 |  6 +--
 test_lab_decision_ui.py                            | 20 ++++----
 test_lab_export.py                                 | 19 ++++----
 test_lab_instructions.py                           | 26 ++++++-----
 test_lab_instructions_browser.py                   |  4 +-
 test_lab_legacy_text.py                            | 12 ++---
 test_lab_payment.py                                | 18 ++++----
 test_lab_payment_browser.py                        | 24 +++++-----
 test_lab_printed_flow.py                           | 20 +++++---
 test_lab_production.py                             | 20 ++++----
 test_lab_reports_footer_timing.py                  |  2 +-
 test_lab_route.py                                  |  6 +--
 test_lab_route_http.py                             | 10 ++--
 test_lab_rules.py                                  | 52 ++++++++++-----------
 test_lab_survey.py                                 |  2 +-
 test_lab_ui_parity_browser.py                      |  6 +--
 test_messages.py                                   | 46 +++++++++----------
 test_messages_browser.py                           |  8 ++--
 test_messages_ui.py                                | 53 ++++++++++++----------
 test_policy.py                                     | 34 +++++++-------
 test_policy_browser.py                             | 18 ++++----
 test_policy_ui.py                                  | 37 ++++++++-------
 79 files changed, 582 insertions(+), 490 deletions(-)
```

Final `git status --short`:

```text
 M LAB_DESIGN_SPEC.md
 M LAB_OPERATOR_README.md
 M _static/fixed/decision-charts.js
 M ambiguity/Decision.html
 M ambiguity/Rules.html
 M ambiguity/tests.py
 M endogenous/Decision.html
 M endogenous/Rules.html
 M endogenous/tests.py
 M fixed/Decision.html
 M fixed/Rules.html
 M fixed/tests.py
 M general_instructions/LabCanonicalAmbiguityBody.html
 M general_instructions/LabCanonicalCosts.html
 M general_instructions/LabCanonicalFixedBody.html
 M general_instructions/LabCanonicalKnownMain.html
 M general_instructions/LabCanonicalMessagesBody.html
 M general_instructions/LabCanonicalPolicyBody.html
 M general_instructions/LabCanonicalPracticeBody.html
 M general_instructions/LabCanonicalPracticeScripts.html
 M general_instructions/LabCanonicalSame.html
 M general_instructions/LabCanonicalSectionReview.html
 M general_instructions/LabComparableCosts.html
 M general_instructions/LabComparableOption.html
 M general_instructions/LabComparableSectionBody.html
 M general_instructions/LabCosts.html
 M general_instructions/LabGeneralBody.html
 M general_instructions/LabMainKnownOutcomes.html
 M general_instructions/LabSectionBody.html
 M lab_cash.py
 M lab_config.py
 M lab_instructions.py
 M lab_payment/README.md
 M lab_payment/__init__.py
 M lab_payment/tests.py
 M lab_printed_questions.py
 M lab_production.py
 M lab_rules.py
 M messages/Decision.html
 M messages/Rules.html
 M messages/tests.py
 M policy/BranchRules.html
 M policy/Decision.html
 M settings.py
 M test_ambiguity.py
 M test_ambiguity_browser.py
 M test_ambiguity_ui.py
 M test_endogenous.py
 M test_endogenous_browser.py
 M test_endogenous_ui.py
 M test_fixed.py
 M test_fixed_browser.py
 M test_fixed_ui.py
 M test_lab_bucket.py
 M test_lab_canonical_instructions.py
 M test_lab_canonical_instructions_browser.py
 M test_lab_cash.py
 M test_lab_config.py
 M test_lab_decision_ui.py
 M test_lab_export.py
 M test_lab_instructions.py
 M test_lab_instructions_browser.py
 M test_lab_legacy_text.py
 M test_lab_payment.py
 M test_lab_payment_browser.py
 M test_lab_printed_flow.py
 M test_lab_production.py
 M test_lab_reports_footer_timing.py
 M test_lab_route.py
 M test_lab_route_http.py
 M test_lab_rules.py
 M test_lab_survey.py
 M test_lab_ui_parity_browser.py
 M test_messages.py
 M test_messages_browser.py
 M test_messages_ui.py
 M test_policy.py
 M test_policy_browser.py
 M test_policy_ui.py
?? LAB_recalibration_update.md
?? coordination_audit_output/
?? test_lab_recalibration.py
?? test_simulated_environment.py
?? timing_audit_output/
```
