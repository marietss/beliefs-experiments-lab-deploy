# Laboratory design specification

This document is the current source of truth for the intended laboratory design. The laboratory repository was cloned from the online/Prolific experiment; the original experiment remains conceptually separate, and laboratory development belongs here. This specification records intended behavior, not a claim that it is already implemented. Creating this document does not change experimental code.

**Status conventions:** fixed decisions are requirements; configurable parameters are supplied through `session_config`; defaults are current starting values; implementation preferences may use the stated fallback when simplicity and reliability require it. Unspecified details are not settled here.

## 1. Session and treatment architecture

- **Fixed:** groups contain six participants. Each session contains nine blocks in the deliberately fixed order `F, F, F → Z, Z, Z → P(Z), P(Z), P(Z)`, because each stage builds on the preceding one.
- **Configurable:** session size is 18 or 24; the session branch `Z` is `E` (Endogenous deadline), `A` (Ambiguity), or `M` (Public Messages). Treatment assignment comes from `session_config`, not hard-coded assignment.

| Session branch | Blocks 1–3 | Blocks 4–6 | Blocks 7–9 |
| --- | --- | --- | --- |
| E | F, F, F | E, E, E | P(E), P(E), P(E) |
| A | F, F, F | A, A, A | P(A), P(A), P(A) |
| M | F, F, F | M, M, M | P(M), P(M), P(M) |

**Preferred architecture:** distinct substantive-treatment apps named `fixed`, `endogenous`, `ambiguity`, `messages`, and `policy`. The `policy` app reads the session branch and implements P(E), P(A), or P(M). If this inheritance makes implementation substantially harder or more fragile, separate `policy_endogenous`, `policy_ambiguity`, and `policy_messages` apps are acceptable. Reliability and transparency take priority over avoiding duplication.

## 2. Core game

**Fixed current parameters:** `K0 = 100`, `W0 = 1000`, and `T = 5`, giving ten decision periods per block. Retirement decisions are integer units only. The existing retirement slider remains the sole participant decision control during a period.

For retirement of `d` units in a period:

`C(d) = 0.10 × d²`.

Calculate this cost separately for each period's retirement. Retiring 10 units in each of two periods costs less than retiring 20 units in one period. The experimental wallet is an accounting balance that may become negative; it does not constrain decisions through available liquidity.

## 3. Main-Check fine

The Main Check occurs after period 5. Let `K_i,T` denote participant i's remaining equipment at that check. When enforcement applies and `K_i,T > 0`:

`Main fine = 175 + 0.5 × K_i,T`.

Participants with `K_i,T = 0` are exempt from the Main fine.

## 4. Fixed environment F

At the Main Check, every participant with positive equipment pays the Main fine; participants at zero do not. Display group-average equipment even though it does not determine the fine. Explain this in the instructions without adding repeated reminders to the normal decision screen.

## 5. Endogenous environment E

**Fixed known threshold:** `kappa = 37`. Let `Kbar_g,T` be the six-person group's average equipment at the Main Check.

- The no-fine condition is strictly `Kbar_g,T > 37`.
- If `Kbar_g,T <= 37`, every participant with positive remaining equipment pays the Main fine.
- Participants at zero remain exempt.

Keep the threshold visible on the normal decision screen as in the existing pilot.

## 6. Ambiguity environment A

A uses E's economic logic with an ambiguous threshold: the no-fine condition is strictly `Kbar_g,T > realised threshold`; otherwise participants with positive equipment pay the Main fine, and participants at zero remain exempt.

- **Fixed support:** integer thresholds from 33 through 42 inclusive.
- **Configurable:** every A or P(A) block has its own preselected hidden threshold supplied through `session_config`. The experiment must not generate these values internally. Values may differ between blocks.
- Hide the realised threshold during periods 1–5. Reveal it only after period-5 decisions are locked.
- Tell participants the possible range, without probabilities over its values.

## 7. Belief / plan elicitation

Before period 1 of every block, elicit exactly two unincentivised integer values from 0 to 100:

1. Own expected/planned remaining equipment at the Main Check.
2. Expected group-average remaining equipment at the Main Check, including oneself.

Elicit these once at the beginning of each block. The Reports page has a maximum of **120 seconds**, with earlier submission permitted. If it expires before submission, explicitly record both reports as integer **0**; partially selected values are not retained. Once valid reports are submitted, timeout/replay must not overwrite them. Every block starts with fresh reports. A timeout-generated Report 1 zero participates normally in the six-person M/P(M) public information; Report 2, including timeout zero, remains private. Exact participant-facing terminology, including “expect” versus “plan,” remains open; beliefs are unincentivised.

## 8. Public Messages environment M

M retains E's economic rules and known threshold of 37. It adds no third elicitation question. After all six group members submit their start-of-block elicitation, calculate:

`public average = mean of the six own Main-Check equipment reports`.

Reveal only this anonymous group average, never individual reports. Keep it visible throughout the block, preferably integrated into the existing graph/display without another action control. In M and P(M), participants must know before submitting that their own report contributes anonymously to the displayed group average.

## 9. Policy P

P adds a redistribution layer to E, A, or M and retains all features of that underlying environment. It applies only to Main-Check fines.

Define:

- `FinePool_g`: sum of Main-Check fines actually paid by the six group members.
- `N_zero`: number of group members with `K_i,T = 0`.
- `rho`: configurable share of `FinePool_g` to redistribute.

When `N_zero > 0`, each participant at zero receives `rho × FinePool_g / N_zero`; other participants receive no redistribution. If `N_zero = 0`, nobody receives redistribution. If `FinePool_g = 0`, there is nothing to redistribute.

The policy reallocates a share of fines already deducted; fine payers pay nothing extra for redistribution. No Follow-up fine enters the pool.

**Configurable, current default:** `rho = 0.3`. Supply it through `session_config` and make it easy to change for pilots.

## 10. Follow-up Check

The Follow-up Check occurs after period 10. A participant with positive remaining equipment pays a fixed Follow-up fine of 75, and all remaining equipment is automatically retired. Automatic retirement costs `0.10 × remaining_equipment²`. Policy redistribution never applies to this fine.

## 11. Information and decision screens

Preserve the existing pilot decision screen as much as possible, including the pilot-style A screen. Keep only one decision control: the retirement slider. Do not add a Main-Check countdown.

- Show only aggregate information about other participants, never individual identities or actions.
- Display actual group-average equipment when appropriate, including in F.
- Group averages may be displayed to two decimal places; payoff and enforcement calculations must use underlying values rather than displayed rounded values.
- At period 1, show no previous-period group-average information, consistent with the pilot.
- Preserve E's existing visible threshold presentation.
- In M/P(M), keep the public average of start-of-block own reports visible throughout the block.

## 12. Main-Check feedback

After period 5, show at least:

- Own equipment and actual group-average equipment.
- Relevant threshold/comparison value and whether the Main-Check condition was satisfied.
- Own Main fine and resulting wallet.

For A/P(A), reveal the block's hidden threshold here, after decisions are locked.

In P blocks, provisionally also show:

- Total Main-Check fines paid by the group.
- Redistribution percentage `rho`.
- Number of firms at zero.
- Total amount redistributed.
- Own redistribution received.
- Resulting wallet.

These policy displays may be simplified after pilot testing, but store all underlying quantities.

## 13. Synchronisation

Within each block, participants remain in the same six-person group. After decisions in periods 1–4 and 6–10, synchronise within that group. **After period-5 decisions, use a whole-session WaitPage for all configured 18 or 24 participants before Main settlement or feedback.** Settle each existing six-person group separately at this barrier, with unchanged economic rules. No ambiguity threshold is revealed before it completes. This barrier does not rematch: the same six participants continue together in periods 6–10. Ordinary post-Result waits remain group-level.

At the end of every ten-period block, all participants enter a session-wide WaitPage. Nobody starts the next block until all 18 or 24 session participants have completed the current block. Perform between-block rematching only after this barrier. Participant-controlled Block Start pages have a maximum of **60 seconds**; Block End summary pages have a maximum of **30 seconds** after each of the nine blocks. Both permit earlier Continue and automatically progress on timeout. These timeouts do not change initialization, wallets, matching or barriers. The separate first-block/section experimenter-controlled gates remain untimed.

## 14. Rematching

Rematch participants between every block.

**Preferred rule, if simple and robust:** random rematching that mildly minimises repeated pairings within each three-block treatment section. Reset matching-history penalties at each section transition: F pairings do not incur penalties in E/A/M, and E/A/M pairings do not incur penalties in P. Do not add many participant-level columns solely for matching.

**Acceptable fallback:** plain random rematching if constraints materially complicate implementation or make it fragile. Matching may differ across otherwise similar E/A/M sessions.

## 15. Session triplets

The intended design permits broadly comparable triplets `(E1, A1, M1)`, `(E2, A2, M2)`, and so on. Within a triplet, keep practical operational characteristics similar where possible, including session size, payment parameters, recruitment timing, and paid-block position. Final sample size and number of sessions/triplets will be determined through power analysis.

## 16. Payment

Exactly one of the nine blocks is payoff-relevant. `paid_block` is supplied externally through `session_config`, with values 1–9. Participants learn the selected block only at the end.

**Current payment rule:**

`EUR payment = 8.00 + 0.01 × wallet_in_paid_block`.

Thus 100 experimental points correspond to €1. Round final cash payment to euro cents. Do not currently implement a €5 minimum floor or a €20 maximum cap.

Preserve existing pilot block-wallet feedback unless a concrete incentive or implementation reason requires a change; flag any such issue during the audit.

## 17. Session configuration

Important `session_config` parameters include at least:

| Parameter | Requirement / current default |
| --- | --- |
| Session size | 18 or 24 participants |
| Session branch / treatment assignment | E, A, or M; determines the fixed nine-block sequence |
| `paid_block` | Externally supplied integer 1–9 |
| `rho` | Supplied redistribution share; current default 30% (3/10) |
| Ambiguity threshold sequence | Preselected integer 33–42 for every A/P(A) block, where applicable |
| Matching seed | Preferably configurable for reproducibility |

Treatment assignment must not be hard-coded. This table specifies configuration responsibilities without settling unspecified key names or data structures.

## 18. Attendance / lab operation

The laboratory session size is determined ex ante through `session_config` and is exactly either 18 or 24 participants. The configured value determines whether the session contains three or four groups of six. Do not implement a runtime attendance rule that chooses between these session sizes.

If the configured number of active participants is not available, the session must not proceed under that configuration. Handling reserves or replacing no-shows before the experiment starts is an administrative matter outside the experiment code. Do not introduce simulated-player replacements for the main laboratory experiment.

## Open / configurable items

- Final sample size and number of sessions/triplets, following power analysis.
- Exact participant-facing wording of expectation/plan questions.
- Whether constrained rematching remains sufficiently simple or plain random rematching is preferable.
- Possible later adjustment of `rho` from its current default of 30% (3/10).
- Final detailed interface simplifications after laboratory pilots.

## Recalibration verification (November 2026)

The current calibration is 0.10 points per squared unit retired in each period,
E/M threshold 37, A/P(A) integer support 33–42, Follow-up fine 75, and base
payment €8.00 + 0.01 × selected-block wallet. No floor or cap is applied.

| Benchmark | Final wallet | Base EUR payment |
| --- | ---: | ---: |
| Early: 20 retired in each of periods 1–5 | 800 | 16.00 |
| Successful Late: 10 retired in each period, no Main fine | 900 | 17.00 |
| Failed Late: 10 retired in each period, Main fine 200 | 700 | 15.00 |
| No retirement in F: 225 Main + 75 Follow-up + 1000 forced cost | -300 | 5.00 |

**Pre-existing implementation differences retained:** the finalized pilot also
includes the always-paid individual bucket task after Policy and before the
survey. Its separate bonus is added once to the base payment above; it does not
enter the nine-block selection or wallets. The current M/P(M) display includes
six anonymous own Main-Check reports and their mean (not mean only as the older
Section 8 wording states). Report 2 remains private and reports do not affect
settlement. Neither mechanism is changed by this recalibration.

Participants continue to receive substantive instructions on paper. Retained
instruction templates and the active paired comprehension questions are updated;
no instruction booklet or review control is reintroduced. The external printed
document must also be revised before use with this calibration.

## Pilot refinements — 11 November 2026

Internal M/messages identifiers refer to the treatment now called S. Known E/S thresholds are 37; A/P(A) support is 33–42, externally configured and hidden until the existing Main reveal.

After the initial admin-controlled splash and readiness barrier, participants receive one 60-second practice of the Fixed Decision interface, followed by the untimed, admin-only “Il periodo di prova è concluso” page. Only the existing monitor advancement releases participants into the comprehension flow. Practice only previews choices; it stores no real retirement, wallet or outcome.

After every completed-block session barrier, BlockEnd shows the actual closing wallet, a fixed section benchmark (F 800; E/A/S 900; P(E)/P(S) 1095; P(A) 1100), and the five other managers’ actual closing wallets, each labelled Altro manager, without a number. The larger summary sentence reads “Il tuo portafoglio alla fine del blocco è di X punti. Il portafoglio massimo ottenibile è di Y punti.” The participant’s X punti is bold. No Main-equipment column is shown.

Each comprehension item's option display order is shuffled independently by participant and stable question ID, and remains identical on reload/retry. Scoring uses unchanged option keys. Each app's first-round `comprehension_question_errors` JSON stores a separate count for every question ID; `comprehension_errors` retains the total and `comprehension_attempts` the submission count. These Player fields are available in standard export.

The first substantive questionnaire page contains the purpose, strategy description, strategy change and information-used textareas. The first three require 20 non-whitespace characters; information-used requires 5. The numeric rating fields `experiment_liking` and `experiment_clarity` are removed from the model and fresh-database exports. All other fields, including the legacy optional improvement columns, remain. Preferences I asks future orientation, giving, then risk, with the risk explanation inside its own question.
