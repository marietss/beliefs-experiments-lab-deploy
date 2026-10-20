"""Policy layer inside the shared atomic settlement, before its replay marker.

The shared engine has already prepared all six voluntary outcomes, the exact
group comparison and actual Main fines. This layer never changes those fines
or their common enforcement condition. All assignments are deterministic from
the same pre-settlement primitives, including on callback retry.
"""

from fractions import Fraction

from lab_persistence import encode_fraction, decode_fraction
from lab_policy import redistribute
import lab_rules as rules


def apply_policy(group, prepared, outcomes, group_values):
    rho = decode_fraction(group.rho)
    at_main = rules.is_main_period(group.period)
    if at_main:
        allocation = redistribute([row[3] for row in prepared],
                                  [decode_fraction(row['main_fine']) for row in outcomes], rho)
        pool, count, redistributed = allocation.fine_pool, allocation.recipient_count, allocation.redistributed_pool
        transfers, recipients = allocation.transfers, allocation.recipients
    else:
        pool = redistributed = Fraction(0)
        count = 0
        transfers, recipients = (Fraction(0),) * 6, (False,) * 6
    for prepared_row, outcome, transfer, eligible in zip(prepared, outcomes, transfers, recipients):
        _, _, wallet_before, _, cost = prepared_row
        after_cost = wallet_before - cost
        after_fine = after_cost - decode_fraction(outcome['main_fine'])
        # Ordinary/Follow-up outcomes are already complete; only Main adds money.
        final = decode_fraction(outcome['wallet_after']) + transfer
        outcome.update(
            wallet_after_voluntary_cost=encode_fraction(after_cost),
            wallet_after_main_fine=encode_fraction(after_fine),
            wallet_after_policy=encode_fraction(after_fine + transfer),
            is_policy_recipient=eligible, own_transfer=encode_fraction(transfer),
            wallet_after=encode_fraction(final),
        )
        if rules.is_follow_up_period(group.period):
            outcome['final_block_wallet'] = encode_fraction(final)
    group_values.update(underlying_branch=group.underlying_branch, rho=group.rho,
                        fine_pool=encode_fraction(pool), recipient_count=count,
                        redistributed_pool=encode_fraction(redistributed))
