"""Participant allowlists: unknown support before Main; own-block reveal after.

This module never reads session.config, the threshold snapshot or Group.threshold.
Only a completed current-block Main record can supply a revealed threshold.
"""

import json

import lab_presentation as shared
import lab_rules as rules

points = shared.points
block_summary = shared.block_summary


def support_context():
    return dict(support_low=rules.AMBIGUITY_THRESHOLD_LOW,
                support_high=rules.AMBIGUITY_THRESHOLD_HIGH,
                threshold_revealed=False)


def revealed_main(player, *, result=False):
    # Decision period 5 remains blind, even if revisited after settlement.
    if player.period < rules.MAIN_CHECK_PERIOD or (player.period == rules.MAIN_CHECK_PERIOD and not result):
        return None
    first = player.round_number - player.period + 1
    main = player.in_round(first + rules.MAIN_CHECK_PERIOD - 1)
    if (not main.period_settled or not main.group.settlement_complete
            or main.field_maybe_none('applied_main_threshold') is None
            or main.field_maybe_none('main_enforcement_applied') is None):
        raise ValueError('Main outcome is not available before synchronized settlement.')
    return main


def _information(context, player, *, result=False):
    info = support_context()
    config = json.loads(context['chart_config_json'])
    config.update(thresholdLow=info['support_low'], thresholdHigh=info['support_high'],
                  thresholdRevealed=False)
    main = revealed_main(player, result=result)
    if main is not None:
        info.update(threshold_revealed=True, threshold=main.applied_main_threshold)
        config.update(thresholdRevealed=True, threshold=main.applied_main_threshold)
    return dict(context, **info, chart_config_json=json.dumps(config, separators=(',', ':')))


def chart_context(player, *, equipment=None):
    return _information(shared.chart_context(player, equipment=equipment), player)


def outcome_context(player):
    context = _information(shared.outcome_context(player), player, result=True)
    if rules.is_main_period(player.period):
        context.update(main_enforcement_applied=player.main_enforcement_applied,
                       target_satisfied=not player.main_enforcement_applied)
    return context
