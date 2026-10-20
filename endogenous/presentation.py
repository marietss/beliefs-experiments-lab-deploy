"""E presentation adds only the known threshold and stored Main condition."""

import json

import lab_presentation as shared
import lab_rules as rules

points = shared.points
block_summary = shared.block_summary


def _with_threshold(context, threshold):
    config = json.loads(context['chart_config_json'])
    config['threshold'] = threshold
    return dict(context, threshold=threshold,
                chart_config_json=json.dumps(config, separators=(',', ':')))


def chart_context(player, *, equipment=None):
    return _with_threshold(shared.chart_context(player, equipment=equipment), rules.KNOWN_THRESHOLD)


def outcome_context(player):
    at_main = rules.is_main_period(player.period)
    context = _with_threshold(shared.outcome_context(player),
                              player.applied_main_threshold if at_main else rules.KNOWN_THRESHOLD)
    if at_main:
        context.update(main_enforcement_applied=player.main_enforcement_applied,
                       target_satisfied=not player.main_enforcement_applied)
    return context
