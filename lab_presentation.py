"""Read-only lab presentation shared by F and E. Exact state stays in canonical rational fields.

Integer point values are displayed as integers. Other values are rounded
half-up to exactly two decimal places for display only.
Chart coordinates are floats for drawing only; they never feed settlement.
"""

from fractions import Fraction
import json

import lab_rules as rules
from lab_persistence import decode_fraction


def points(value):
    """Participant display only; never use this text for economic calculations."""
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    hundredths = (abs(value.numerator) * 200 + value.denominator) // (2 * value.denominator)
    sign = '-' if value < 0 and hundredths else ''
    whole, tail = divmod(hundredths, 100)
    return f'{sign}{whole}.{tail:02d}'


def mean_display(value):
    return points(value)


def chart_context(player, *, include_current=False, equipment=None):
    """Allowlist own observations and stored aggregate means, never peer rows.

    Histories reset every block. Equipment is post-voluntary/pre-enforcement,
    so period 10 remains distinguishable from forced final equipment zero.
    There is no invented period-0 group observation.
    """
    first = player.round_number - player.period + 1
    last = player.round_number if include_current else player.round_number - 1
    own = [{'period': 0, 'equipment': rules.K0}]
    group = []
    if last >= first:
        for row in player.in_rounds(first, last):
            if not row.period_settled or not row.group.settlement_complete:
                raise ValueError('Chart history requires settled periods.')
            own.append(dict(period=row.period, equipment=row.voluntary_equipment_after))
            group.append(dict(period=row.period, equipment=float(decode_fraction(row.group_mean))))
    config = dict(
        periods=rules.PERIODS_PER_BLOCK, period=player.period,
        mainPeriod=rules.MAIN_CHECK_PERIOD, followUpPeriod=rules.FOLLOW_UP_PERIOD,
        ownHistory=own, groupHistory=group,
        costMilliPoints=int(rules.COST_FACTOR * 1000),
    )
    if equipment is not None:
        config['equipment'] = equipment
    return dict(chart_config_json=json.dumps(config, separators=(',', ':')))


def outcome_context(player):
    context = {key: points(decode_fraction(getattr(player, key))) for key in (
        'voluntary_cost', 'wallet_after', 'main_fine', 'follow_up_fine',
        'forced_retirement_cost',
    )}
    context.update(
        group_mean=mean_display(decode_fraction(player.group_mean)),
        main_fine_applied=decode_fraction(player.main_fine) > 0,
        follow_up_fine_applied=decode_fraction(player.follow_up_fine) > 0,
        **chart_context(player, include_current=True),
    )
    return context


def block_summary(player):
    first = player.round_number - player.period + 1
    rows = player.in_rounds(first, player.round_number)
    return dict(
        wallet=points(decode_fraction(player.final_block_wallet)),
        total_voluntary_cost=points(sum((decode_fraction(p.voluntary_cost) for p in rows), Fraction(0))),
        total_main_fine=points(sum((decode_fraction(p.main_fine) for p in rows), Fraction(0))),
        follow_up_fine=points(decode_fraction(player.follow_up_fine)),
        forced_retirement_cost=points(decode_fraction(player.forced_retirement_cost)),
    )
