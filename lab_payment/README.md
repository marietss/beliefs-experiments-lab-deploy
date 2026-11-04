Laboratory payment routes
====================================

For production startup, explicit study parameters and attendance procedure, see
[LAB_OPERATOR_README.md](../LAB_OPERATOR_README.md). The default launch menu now
contains only the six production templates. For development tests use
`OTREE_CONFIG_MODE=development OTREE_LAB_PAYMENTS=1 otree devserver`.
oTree 6.0.15 has one process-wide cash currency; this flag selects EUR while
the default remains GBP for the retained legacy online server. Do not mix
cash-paying GBP and EUR sessions in one process. Full lab payment routes fail
at creation if the server is not in EUR mode. Standalone lab routes still
have zero conversion/fee. Production startup additionally validates PostgreSQL, secrets and the supported runtime.

The six `dev_lab_full_{E,A,M}_{18,24}` routes end in `lab_payment` and use
0.01 EUR/point plus a 8.00 EUR fee. `paid_block` remains an explicit external
configuration value, snapshotted at creation and hidden until this final app.

`participant.vars['lab_block_wallets_v1']` is the canonical ledger: string keys
1…9, canonical reduced signed `numerator/denominator` values. Only completed
period-10 settlement callbacks write it. Identical writes are idempotent;
conflicts fail. Finalization requires exactly all nine entries and a completed
Block-9 session barrier. No missing value is reconstructed.

`lab_final_payment_v1` retains selected block/wallet, exact rate/fee, exact
variable and pre-round EUR, integer final cents, HALF_UP version, and the
separate `admin_payoff_points`. The final app's Player mirrors these primitives.
Final cash is rounded once using exact integer arithmetic, ties away from zero
(decimal HALF_UP), including signed totals. No floor/cap is applied.

oTree converts Currency via float and quantizes points. Repeating wallets
therefore cannot safely be assigned directly to participant payoff. Instead,
the final app assigns integer *cash-settlement equivalent points* equal to
`final_eur_cents - 800`. At the configured 0.01 rate, with the 8.00 fee, admin
cash exactly equals the canonical rounded total; this agreement is checked on
every finalization/reload. These admin points are not the experimental wallet.
The selected experimental wallet remains exact in the ledger/receipt record.
`POINTS_DECIMAL_PLACES` is unchanged; it is not used for lab economic accounting.
The Player payoff setter adjusts participant payoff by delta, rather than
adding a second payment, and also keeps oTree automatic payoff tabulation valid.

The receipt reveals only the selected block, own exact wallet, fee, exact
variable component, and rounded total. It has no questionnaire, recruitment ID,
completion code, external redirect, or payment randomization claim.
