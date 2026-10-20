"""M/P(M) report locking, exact aggregation and read-only block lookup.

Only the report barrier writes the public aggregate. The replay record contains
report-1 primitives and identities SERVER-SIDE; presentation exposes only sorted values.
Report 2 is validated and locked privately, and never enters the aggregate.
"""

from fractions import Fraction
import json

from lab_persistence import encode_fraction, decode_fraction
import lab_rules as rules


def lock(player):
    values = (player.expected_own_equipment_main, player.expected_group_average_main)
    if any(type(v) is not int or not 0 <= v <= 100 for v in values):
        raise ValueError('Both reports must be integers from 0 through 100.')
    if player.reports_submitted:
        if values != (player.locked_own_report, player.locked_group_report):
            raise ValueError('These block-start reports have already been locked.')
        return
    player.locked_own_report, player.locked_group_report = values
    player.reports_submitted = True


def complete(group, *, validate_reports):
    players = sorted(group.get_players(), key=lambda p: p.participant.code)
    if len(players) != rules.GROUP_SIZE or len({p.participant.code for p in players}) != rules.GROUP_SIZE:
        raise ValueError('Public reports require exactly six distinct participants.')
    for p in players:
        if p.period != 1 or not p.reports_submitted:
            raise ValueError('All six locked block-start reports are required.')
        # Validate both locked answers before any marker is changed.
        for field, locked in (('expected_own_equipment_main', 'locked_own_report'),
                              ('expected_group_average_main', 'locked_group_report')):
            value = p.field_maybe_none(locked)
            if type(value) is not int or not 0 <= value <= 100 or getattr(p, field) != value:
                raise ValueError('A locked block-start report is missing or inconsistent.')
    total = sum(p.locked_own_report for p in players)
    mean = encode_fraction(Fraction(total, rules.GROUP_SIZE))
    record = json.dumps(dict(version=1, block=group.global_block,
                             report1=[[p.participant.code, p.locked_own_report] for p in players]),
                        sort_keys=True, separators=(',', ':'))
    if group.public_report_complete:
        if (not group.reports_complete or group.public_report_mean != mean
                or group.public_report_total != total or group.public_report_record != record):
            raise ValueError('Inconsistent replay of the public report aggregate.')
        return
    if group.reports_complete or group.public_report_mean or group.public_report_record:
        raise ValueError('Unexpected partial public report aggregation.')
    validate_reports(group)  # shared readiness/report validation; no public disclosure in E/A
    group.public_report_total = total
    group.public_report_mean = mean
    group.public_report_record = record
    group.public_report_complete = True  # last write; report WaitPage transaction commits together


def read(player):
    """Read the current block's stored mean; never average on a render/reload."""
    first = player.round_number - player.period + 1
    owner = player.in_round(first).group
    if not owner.reports_complete or not owner.public_report_complete:
        raise ValueError('The public report mean is unavailable before the report barrier.')
    return decode_fraction(owner.public_report_mean)


def read_public_plans(player):
    """Read anonymous Report-1 values only after the existing report barrier."""
    read(player)
    first = player.round_number - player.period + 1
    owner = player.in_round(first).group
    record = json.loads(owner.public_report_record)
    return sorted(value for _, value in record['report1'])
