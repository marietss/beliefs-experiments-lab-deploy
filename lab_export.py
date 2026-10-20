"""Read-only normalized lab_export_v1 datasets, sourced from stored primitives.

No settlement, matching selection, payoff finalization or legacy export imports.
Only metadata/keys/status are derived. Economic values are copied verbatim as
validated canonical n/d text. See LAB_EXPORT_README.md for joins and nulls.
"""
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
import csv
import json

import lab_cash
import lab_route
from lab_matching import validate_matrix
from lab_persistence import decode_fraction, encode_fraction

SCHEMA = 'lab_export_v1'
BASE = ('schema_version', 'session_code')
BLOCK = BASE + ('global_block', 'section', 'local_block', 'treatment', 'underlying_branch', 'is_policy', 'app_name')
PERSON = BLOCK + ('participant_code', 'group_id')
HEADERS = {
    'session': BASE + ('config_name', 'configured_size', 'branch', 'rho', 'matching_seed', 'matching_seed_type',
        'matching_version', 'paid_block', 'conversion', 'fixed_fee', 'rounding', 'ambiguity_thresholds_json',
        'app_sequence_json', 'payment_configured', 'server_currency', 'lab_payment_mode_active',
        'complete', 'coverage_issues_json', 'observed_counts_json'),
    'membership': PERSON + ('participant_id_in_session', 'id_in_group', 'group_size', 'matching_version'),
    'group_period': BLOCK + ('group_id', 'period', 'app_round', 'group_size', 'app_group_id', 'equipment_total',
        'group_mean', 'final_equipment_total', 'settlement_complete'),
    'period': PERSON + ('app_round', 'period', 'global_period', 'equipment_before', 'voluntary_retirement',
        'equipment_after_voluntary', 'voluntary_cost', 'wallet_before', 'wallet_after', 'final_equipment',
        'main_fine', 'follow_up_fine', 'forced_retirement', 'forced_retirement_cost', 'own_transfer',
        'decision_submitted', 'settlement_complete'),
    'reports': PERSON + ('report_1', 'report_2', 'reports_submitted', 'group_reports_complete'),
    'messages': BLOCK + ('group_id', 'report_1_total', 'public_report_mean', 'public_report_complete'),
    'main_group': BLOCK + ('group_id', 'equipment_total', 'group_mean', 'threshold', 'threshold_hidden_before_main',
        'enforcement_rule', 'group_main_enforcement_applied', 'fine_pool', 'rho', 'recipient_count',
        'actual_redistributed_pool', 'settlement_complete'),
    'main': PERSON + ('equipment_after_voluntary', 'main_fine', 'wallet_before_period', 'voluntary_cost',
        'wallet_before_main_fine', 'wallet_after_main_fine', 'is_policy_recipient', 'own_transfer',
        'wallet_after_policy', 'wallet_after_main_settlement'),
    'completion': PERSON + ('pre_forced_equipment', 'follow_up_fine', 'forced_retirement', 'forced_retirement_cost',
        'final_equipment', 'final_block_wallet', 'settlement_complete', 'feedback_submitted', 'block_barrier_complete'),
    'ledger': BASE + ('participant_code', 'global_block', 'final_block_wallet', 'ledger_version'),
    'payment': BASE + ('participant_code', 'finalized', 'paid_block', 'selected_wallet', 'conversion', 'fixed_fee',
        'variable_eur', 'pre_round_eur', 'final_eur_cents', 'final_eur', 'rounding', 'currency',
        'admin_payoff_points', 'admin_payoff_stored', 'admin_cash_eur'),
}
KEYS = {
    'session': ('session_code',),
    'membership': ('session_code', 'participant_code', 'global_block'),
    'group_period': ('session_code', 'group_id', 'period'),
    'period': ('session_code', 'participant_code', 'global_block', 'period'),
    'reports': ('session_code', 'participant_code', 'global_block'),
    'messages': ('session_code', 'group_id'),
    'main_group': ('session_code', 'group_id'),
    'main': ('session_code', 'participant_code', 'global_block'),
    'completion': ('session_code', 'participant_code', 'global_block'),
    'ledger': ('session_code', 'participant_code', 'global_block'),
    'payment': ('session_code', 'participant_code'),
}


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'))


def _exact(value):
    decode_fraction(value)
    return value


def _maybe(obj, name):
    return obj.field_maybe_none(name)


def _cash_text(cents):
    whole, tail = divmod(abs(cents), 100)
    return f'{"-" if cents < 0 else ""}{whole}.{tail:02d}'


def _block_metadata(session, block, app):
    section = ('F', 'Z', 'P(Z)')[(block - 1) // 3]
    branch = session.config['branch']
    return dict(schema_version=SCHEMA, session_code=session.code, global_block=block,
                section=section, local_block=(block - 1) % 3 + 1,
                treatment='F' if section == 'F' else branch if section == 'Z' else f'P({branch})',
                underlying_branch=branch, is_policy=section == 'P(Z)', app_name=app)


def _payment_row(player, base):
    pp = player.participant
    row = dict.fromkeys(HEADERS['payment'])
    row.update(base, participant_code=pp.code, finalized=False)
    record = pp.vars.get(lab_cash.PAYMENT_KEY)
    if record is None:
        if player.finalized or Decimal(player.payoff) != 0:
            raise ValueError('Payment marker/payoff exists without canonical payment record.')
        return row
    if record.get('finalized') is not True or not player.finalized:
        raise ValueError('Inconsistent finalized payment marker.')
    ledger = lab_cash.validate_wallets(pp.vars.get(lab_cash.WALLETS_KEY, {}), complete=True)
    block = record['paid_block']
    if type(block) is not int or not 1 <= block <= 9 or ledger[str(block)] != record['selected_wallet']:
        raise ValueError('Payment selected wallet disagrees with ledger.')
    if any(_maybe(player, key) != record[key] for key in player.RECORD_FIELDS):
        raise ValueError('Payment model disagrees with canonical finalized primitives.')
    for key in ('selected_wallet', 'conversion', 'fixed_fee', 'variable_eur', 'pre_round_eur'):
        _exact(record[key])
    if (record['paid_block'] != player.session.vars[lab_cash.CONFIG_KEY]['paid_block']
            or any(record[k] != player.session.vars[lab_cash.CONFIG_KEY][k] for k in ('conversion', 'fixed_fee', 'rounding', 'currency'))):
        raise ValueError('Payment record disagrees with configured payment snapshot.')
    cents = record['final_eur_cents']
    if type(cents) is not int:
        raise ValueError('Final payment cents must be a strict integer.')
    admin_points = Fraction(Decimal(pp.payoff))
    admin_cash = Fraction(Decimal(pp.payoff_plus_participation_fee()))
    if admin_points != record['admin_payoff_points'] or Decimal(player.payoff) != record['admin_payoff_points'] or admin_cash != Fraction(cents, 100):
        raise ValueError('Stored admin payment disagrees with finalized payment.')
    row.update({key: record[key] for key in (
        'finalized', 'paid_block', 'selected_wallet', 'conversion', 'fixed_fee', 'variable_eur',
        'pre_round_eur', 'final_eur_cents', 'rounding', 'currency', 'admin_payoff_points')})
    row.update(final_eur=_cash_text(cents), admin_payoff_stored=encode_fraction(admin_points),
               admin_cash_eur=encode_fraction(admin_cash))
    return row


def export_session(session, *, require_complete=False):
    """Return all tables as ordered lists of dicts; never modify any model/vars.

    Full substantive routes only (with or without terminal lab_payment). An
    unfinished route exports only submitted reports and settled outcomes;
    future default groups/blank Player fields never become observations.
    """
    from otree.common import get_models_module
    from otree import settings
    sequence = session.config['app_sequence']
    expected = lab_route.full_sequence(session.config['branch'])
    if sequence not in (expected, expected + ['lab_payment']):
        raise ValueError('Normalized lab exports require a full F → branch → policy route.')
    apps = {name: get_models_module(name) for name in expected}
    subs = {name: {ss.round_number: ss for ss in app.Subsession.objects_filter(session=session)} for name, app in apps.items()}
    state, people = lab_route.matching_state(subs['fixed'][1])  # validation/read only
    if any(type(key) is not str or key not in lab_cash.BLOCK_KEYS for key in state['matrices']):
        raise ValueError('Invalid global matrix key in stored matching state.')
    bundle = {name: [] for name in HEADERS}
    base = dict(schema_version=SCHEMA, session_code=session.code)
    by_round = {}
    participants = {}
    for name, app in apps.items():
        rounds = defaultdict(list)
        for p in app.Player.objects_filter(session=session).order_by('round_number', 'id'):
            rounds[p.round_number].append(p)
            participants[p.participant.code] = p.participant
        by_round[name] = rounds
    if set(participants) != set(people):
        raise ValueError('Export participant identities disagree with matching snapshot.')
    completion_wallets = {}
    for block in range(1, 10):
        if str(block) not in state['matrices']:
            continue
        name, first = lab_route.block_location(session.config, block)
        matrix = validate_matrix(state['matrices'][str(block)], people)
        targets = [subs[name][r] for r in range(first, first + 10)]
        if not all(ss.grouping_installed for ss in targets):
            if any(p.period_settled or p.reports_submitted or p.decision_submitted
                   for r in range(first, first + 10) for p in by_round[name][r]):
                raise ValueError('Experimental data exists in an incompletely prepared block.')
            continue
        meta = _block_metadata(session, block, name)
        public = meta['treatment'] in ('M', 'P(M)')
        policy = meta['is_policy']
        membership = {code: rank for rank, group in enumerate(matrix, 1) for code in group}
        for r in range(first, first + 10):
            ss, rows = subs[name][r], by_round[name][r]
            groups = defaultdict(list)
            for p in rows:
                if (p.global_block != block or p.local_block != meta['local_block'] or p.period != r-first+1):
                    raise ValueError('Stored player block/period metadata is inconsistent.')
                groups[p.group.id].append(p)
            actual = validate_matrix([[p.participant.code for p in group] for group in groups.values()], people)
            if actual != matrix:
                raise ValueError('Stored round membership disagrees with selected block matrix.')
            for players in sorted(groups.values(), key=lambda ps: membership[ps[0].participant.code]):
                players.sort(key=lambda p: p.participant.code)
                group = players[0].group
                if group.global_block != block or group.period != r-first+1:
                    raise ValueError('Stored group block/period metadata is inconsistent.')
                if policy and (group.underlying_branch != meta['underlying_branch']
                        or any(p.underlying_branch != meta['underlying_branch'] for p in players)
                        or group.rho != state['rho']):
                    raise ValueError('Policy branch/rho primitives disagree with session snapshot.')
                gid = f'{session.code}:B{block}:G{membership[players[0].participant.code]}'
                gm = dict(meta, group_id=gid)
                if r == first:
                    for p in players:
                        person = dict(gm, participant_code=p.participant.code)
                        bundle['membership'].append(dict(person, participant_id_in_session=p.participant.id_in_session,
                            id_in_group=p.id_in_group, group_size=len(players), matching_version=state['version']))
                        if p.reports_submitted:
                            a, b = _maybe(p, 'expected_own_equipment_main'), _maybe(p, 'expected_group_average_main')
                            if any(type(v) is not int or not 0 <= v <= 100 for v in (a,b)):
                                raise ValueError('Submitted report is missing or invalid.')
                            if hasattr(type(p), 'locked_own_report'):
                                locked = (_maybe(p,'locked_own_report'), _maybe(p,'locked_group_report'))
                                # P(E)/P(A) define these shared fields but only
                                # M/P(M) fill them. Do not invent private locks.
                                if (public or locked != (None,None)) and locked != (a,b):
                                    raise ValueError('Submitted reports disagree with locked reports.')
                            bundle['reports'].append(dict(person, report_1=a, report_2=b, reports_submitted=True,
                                                          group_reports_complete=group.reports_complete))
                    if public and group.public_report_complete:
                        if not group.reports_complete:
                            raise ValueError('Public message exists before report barrier completion.')
                        bundle['messages'].append(dict(gm, report_1_total=group.public_report_total,
                            public_report_mean=_exact(group.public_report_mean), public_report_complete=True))
                    if not public and getattr(group, 'public_report_complete', False):
                        raise ValueError('Unexpected public message in a non-M treatment.')
                if not group.settlement_complete:
                    if any(p.period_settled for p in players):
                        raise ValueError('Partial participant settlement without group completion.')
                    continue
                if not all(p.period_settled and p.decision_submitted for p in players):
                    raise ValueError('Completed group has unsettled participant outcomes.')
                mean = _exact(group.group_mean)
                bundle['group_period'].append(dict(gm, period=group.period, app_round=r, group_size=len(players),
                    app_group_id=group.id, equipment_total=group.equipment_total, group_mean=mean,
                    final_equipment_total=group.final_equipment_total, settlement_complete=True))
                if group.period == 5:
                    threshold = None if block <= 3 else _maybe(group, 'threshold')
                    enforced = None if block <= 3 else _maybe(group, 'main_enforcement_applied')
                    if block > 3 and (type(threshold) is not int or type(enforced) is not bool):
                        raise ValueError('Settled Main threshold/enforcement primitive is missing.')
                    if block > 3 and meta['underlying_branch']=='A' and threshold != state['thresholds'][str(block)]:
                        raise ValueError('Stored A Main threshold disagrees with external block configuration.')
                    bundle['main_group'].append(dict(gm, equipment_total=group.equipment_total, group_mean=mean,
                        threshold=threshold, threshold_hidden_before_main=block>3 and session.config['branch']=='A',
                        enforcement_rule='own_positive_equipment' if block<=3 else 'group_total_lte_six_times_threshold',
                        group_main_enforcement_applied=enforced, fine_pool=_exact(group.fine_pool) if policy else None,
                        rho=_exact(group.rho) if policy else None, recipient_count=group.recipient_count if policy else None,
                        actual_redistributed_pool=_exact(group.redistributed_pool) if policy else None, settlement_complete=True))
                for p in players:
                    person = dict(gm, participant_code=p.participant.code)
                    if p.locked_retirement != p.retirement or p.group_mean != mean:
                        raise ValueError('Locked decision/stored mean disagrees with settled primitives.')
                    values = {key: _exact(getattr(p,key)) for key in ('voluntary_cost','wallet_before','wallet_after',
                               'main_fine','follow_up_fine','forced_retirement_cost')}
                    transfer = _exact(p.own_transfer) if policy else None
                    bundle['period'].append(dict(person, app_round=r, period=p.period, global_period=(block-1)*10+p.period,
                        equipment_before=p.start_equipment, voluntary_retirement=p.locked_retirement,
                        equipment_after_voluntary=p.voluntary_equipment_after, final_equipment=p.final_equipment,
                        forced_retirement=p.forced_retirement, own_transfer=transfer,
                        decision_submitted=True, settlement_complete=True, **values))
                    if p.period == 5:
                        if block>3 and (p.applied_main_threshold != threshold or p.main_enforcement_applied != enforced):
                            raise ValueError('Participant/group Main primitives disagree.')
                        bundle['main'].append(dict(person, equipment_after_voluntary=p.voluntary_equipment_after,
                            main_fine=values['main_fine'], wallet_before_period=values['wallet_before'], voluntary_cost=values['voluntary_cost'],
                            wallet_before_main_fine=_exact(p.wallet_after_voluntary_cost) if policy else None,
                            wallet_after_main_fine=_exact(p.wallet_after_main_fine) if policy else values['wallet_after'],
                            is_policy_recipient=p.is_policy_recipient if policy else None, own_transfer=transfer,
                            wallet_after_policy=_exact(p.wallet_after_policy) if policy else None,
                            wallet_after_main_settlement=values['wallet_after']))
                    if p.period == 10:
                        final = _exact(p.final_block_wallet)
                        ledger = lab_cash.validate_wallets(p.participant.vars.get(lab_cash.WALLETS_KEY, {}))
                        if ledger.get(str(block)) != final or final != values['wallet_after']:
                            raise ValueError('Block completion wallet disagrees with canonical ledger.')
                        completion_wallets[(p.participant.code, block)] = final
                        bundle['completion'].append(dict(person, pre_forced_equipment=p.voluntary_equipment_after,
                            follow_up_fine=values['follow_up_fine'], forced_retirement=p.forced_retirement,
                            forced_retirement_cost=values['forced_retirement_cost'], final_equipment=p.final_equipment,
                            final_block_wallet=final, settlement_complete=True, feedback_submitted=p.block_feedback_submitted,
                            block_barrier_complete=ss.block_barrier_complete))
    for code in sorted(participants):
        pp = participants[code]
        ledger = lab_cash.validate_wallets(pp.vars.get(lab_cash.WALLETS_KEY, {}))
        for block in sorted(map(int, ledger)):
            if completion_wallets.get((code, block)) != ledger[str(block)]:
                raise ValueError('Ledger entry has no matching settled block-completion primitive.')
            bundle['ledger'].append(dict(base, participant_code=code, global_block=block,
                final_block_wallet=ledger[str(block)], ledger_version=lab_cash.WALLETS_KEY))
    payment_config = session.vars.get(lab_cash.CONFIG_KEY)
    if 'lab_payment' in sequence:
        if payment_config != lab_cash.config_snapshot(session.config):
            raise ValueError('Payment configuration disagrees with stored payment snapshot.')
        for p in get_models_module('lab_payment').Player.objects_filter(session=session).order_by('participant_id'):
            bundle['payment'].append(_payment_row(p,base))
    else:
        for code in sorted(participants):
            row = dict.fromkeys(HEADERS['payment']); row.update(base, participant_code=code, finalized=False)
            bundle['payment'].append(row)
    # Sort every table by its documented primary key; no clocks/randomness/caches.
    for table, rows in bundle.items():
        rows.sort(key=lambda row: tuple(row[key] for key in KEYS[table]))
    issues = coverage_issues(bundle, session.config['lab_session_size'], session.config['branch'])
    bundle['session'].append(dict(base, config_name=session.config['name'], configured_size=session.config['lab_session_size'],
        branch=session.config['branch'], rho=_exact(state['rho']), matching_seed=str(state['seed']),
        matching_seed_type=type(state['seed']).__name__, matching_version=state['version'],
        paid_block=payment_config['paid_block'] if payment_config else session.config['paid_block'],
        conversion=payment_config['conversion'] if payment_config else encode_fraction(lab_cash._configured_number(session.config['real_world_currency_per_point'])),
        fixed_fee=payment_config['fixed_fee'] if payment_config else encode_fraction(lab_cash._configured_number(session.config['participation_fee'])),
        rounding=payment_config['rounding'] if payment_config else None, ambiguity_thresholds_json=_json(state['thresholds']),
        app_sequence_json=_json(sequence), payment_configured=payment_config is not None,
        server_currency=settings.REAL_WORLD_CURRENCY_CODE,
        lab_payment_mode_active=settings.REAL_WORLD_CURRENCY_CODE=='EUR', complete=not issues,
        coverage_issues_json=_json(issues), observed_counts_json=_json({k:len(v) for k,v in bundle.items() if k!='session'})))
    if require_complete and issues:
        raise ValueError('Incomplete laboratory session: ' + '; '.join(issues))
    return bundle


def coverage_issues(bundle, size, branch):
    """Pure structural coverage validation; never reconstruct economic outcomes."""
    issues = []
    codes = {r['participant_code'] for r in bundle['payment']}
    if len(codes) != size:
        issues.append('payment participant count')
    block_keys = {(code, block) for code in codes for block in range(1,10)}
    period_keys = {(code, block, period) for code,block in block_keys for period in range(1,11)}
    for table in ('membership','reports','main','completion','ledger'):
        rows = bundle[table]
        if {(r['participant_code'],r['global_block']) for r in rows} != block_keys or len(rows)!=size*9:
            issues.append(f'{table}: expected {size*9} participant-block records')
    if {(r['participant_code'],r['global_block'],r['period']) for r in bundle['period']} != period_keys or len(bundle['period'])!=size*90:
        issues.append(f'period: expected {size*90} participant-period records')
    groups = {r['group_id'] for r in bundle['membership']}
    if len(groups)!=size//6*9 or len(bundle['main_group'])!=size//6*9 or {r['group_id'] for r in bundle['main_group']}!=groups:
        issues.append('incomplete Main group records')
    if {(r['group_id'],r['period']) for r in bundle['group_period']} != {(gid,p) for gid in groups for p in range(1,11)} or len(bundle['group_period'])!=size//6*90:
        issues.append('incomplete group-period records')
    if any(not r['finalized'] for r in bundle['payment']) or len(bundle['payment'])!=size:
        issues.append('payment not finalized for all participants')
    if any(not r['group_reports_complete'] for r in bundle['reports']):
        issues.append('report barrier pending')
    if any(not r['block_barrier_complete'] for r in bundle['completion']):
        issues.append('block barrier pending')
    expected_messages = {r['group_id'] for r in bundle['membership'] if r['treatment'] in ('M','P(M)')}
    if {r['group_id'] for r in bundle['messages']} != expected_messages or len(bundle['messages']) != len(expected_messages):
        issues.append('public messages incomplete or unexpected')
    for table, rows in bundle.items():
        if len({tuple(row[k] for k in KEYS[table]) for row in rows}) != len(rows):
            raise ValueError(f'Duplicate primary key in {table}.')
    return issues


def csv_rows(bundle, table):
    """Pure table adapter: None becomes blank only at CSV serialization."""
    yield list(HEADERS[table])
    for row in bundle[table]:
        if set(row) != set(HEADERS[table]):
            raise ValueError(f'Unexpected/missing fields in {table}.')
        yield [int(row[key]) if type(row[key]) is bool else row[key] for key in HEADERS[table]]


def custom_rows(players, table):
    """oTree 6 custom_export_* adapter. Deduplicate sessions, never participants."""
    sessions = {p.session.code: p.session for p in players}
    yield list(HEADERS[table])
    for code in sorted(sessions):
        bundle = export_session(sessions[code])
        yield from list(csv_rows(bundle,table))[1:]


def write_csvs(bundle, directory):
    """Write an already-built snapshot to explicit output files; no database access."""
    from pathlib import Path
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for table in HEADERS:
        with (directory / f'{SCHEMA}_{table}.csv').open('w', newline='', encoding='utf-8') as fp:
            csv.writer(fp).writerows(csv_rows(bundle,table))
