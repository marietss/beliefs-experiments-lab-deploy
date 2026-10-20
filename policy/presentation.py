"""Read-only allowlists for P(E), P(A), P(M), and Main policy aggregates.

No session config/map, matching matrix, peer row or realized Group.threshold
is ever placed in a context. A's value comes only from a settled own Main row.
All browser numbers are for display; exact model fields remain authoritative.
"""

import json

import lab_presentation as shared
import lab_reports
import lab_rules as rules
from lab_persistence import decode_fraction

points = shared.points
block_summary = shared.block_summary


def start_context(player):
    info = dict(is_ambiguity=player.underlying_branch == 'A',
                is_messages=player.underlying_branch == 'M',
                underlying_branch=player.underlying_branch,
                rho_display=str(decode_fraction(player.group.rho)))
    if info['is_ambiguity']:
        info.update(support_low=rules.AMBIGUITY_THRESHOLD_LOW,
                    support_high=rules.AMBIGUITY_THRESHOLD_HIGH, threshold_revealed=False)
    else:
        info.update(threshold=rules.KNOWN_THRESHOLD, threshold_revealed=True)
    return info


def revealed_main(player, *, result=False):
    if player.period < rules.MAIN_CHECK_PERIOD or (player.period == rules.MAIN_CHECK_PERIOD and not result):
        return None
    main = player.in_round(player.round_number - player.period + rules.MAIN_CHECK_PERIOD)
    if not main.period_settled or not main.group.settlement_complete:
        raise ValueError('Main outcome is not available before synchronized settlement.')
    return main


def wait_context(player):
    if player.underlying_branch == 'M':
        return dict(is_messages=True, public_report_mean=shared.mean_display(lab_reports.read(player)))
    return dict(is_messages=False)


def block_context(player):
    first = player.round_number - player.period + 1
    main = player.in_round(first + rules.MAIN_CHECK_PERIOD - 1)
    return dict(wait_context(player), total_policy_transfer=points(decode_fraction(main.own_transfer)))


def _information(context, player, *, result=False):
    info = start_context(player)
    config = json.loads(context['chart_config_json'])
    if info['is_ambiguity']:
        config.update(thresholdLow=rules.AMBIGUITY_THRESHOLD_LOW,
                      thresholdHigh=rules.AMBIGUITY_THRESHOLD_HIGH, thresholdRevealed=False)
        main = revealed_main(player, result=result)
        if main is not None:
            info.update(threshold_revealed=True, threshold=main.applied_main_threshold)
            config.update(thresholdRevealed=True, threshold=main.applied_main_threshold)
    else:
        config.update(thresholdRevealed=True, threshold=rules.KNOWN_THRESHOLD)
    if info['is_messages']:
        mean = lab_reports.read(player)
        info['public_report_mean'] = shared.mean_display(mean)
        config['publicReportMean'] = float(mean)
        config['publicReportPlans'] = lab_reports.read_public_plans(player)
    return dict(context, **info, chart_config_json=json.dumps(config, separators=(',', ':')))


def chart_context(player, *, equipment=None):
    return _information(shared.chart_context(player, equipment=equipment), player)


def outcome_context(player):
    context = _information(shared.outcome_context(player), player, result=True)
    if rules.is_main_period(player.period):
        group = player.group
        context.update(main_enforcement_applied=player.main_enforcement_applied,
                       target_satisfied=not player.main_enforcement_applied,
                       fine_pool=points(decode_fraction(group.fine_pool)),
                       recipient_count=group.recipient_count,
                       redistributed_pool=points(decode_fraction(group.redistributed_pool)),
                       own_transfer=points(decode_fraction(player.own_transfer)),
                       is_policy_recipient=player.is_policy_recipient,
                       wallet_after_main_fine=points(decode_fraction(player.wallet_after_main_fine)))
    return context
