"""M-only presentation: the stored anonymous report mean and anonymous planned values."""

import json

import lab_presentation as shared
import lab_rules as rules
import lab_reports
from . import public_reports

points = shared.points
block_summary = shared.block_summary


def public_context(player):
    return dict(public_report_mean=shared.mean_display(public_reports.read(player)))


def _information(context, player, threshold):
    mean = public_reports.read(player)
    config = json.loads(context['chart_config_json'])
    # Float coordinates are display-only. Exact n/d persistence is untouched.
    config.update(threshold=threshold, publicReportMean=float(mean), publicReportPlans=lab_reports.read_public_plans(player))
    return dict(context, threshold=threshold, public_report_mean=shared.mean_display(mean),
                chart_config_json=json.dumps(config, separators=(',', ':')))


def chart_context(player, *, equipment=None):
    return _information(shared.chart_context(player, equipment=equipment), player, rules.KNOWN_THRESHOLD)


def outcome_context(player):
    at_main = rules.is_main_period(player.period)
    context = _information(shared.outcome_context(player), player,
                           player.applied_main_threshold if at_main else rules.KNOWN_THRESHOLD)
    if at_main:
        context.update(main_enforcement_applied=player.main_enforcement_applied,
                       target_satisfied=not player.main_enforcement_applied)
    return context
