"""Integrated development route and server-only global matching handoffs.

No economic settlement, wallet ledger, page rendering or payment lives here.
Standalone apps retain their tested local installers. Integrated sessions use
one canonical block-keyed store, with selection/installation only at creation
(block 1) or the preceding all-session block barrier (blocks 2–9).
oTree set_players commits internally: persist selection before installation,
leave source completion false until all ten targets are verified, and on retry
preserve verified Group rows while rebuilding only still-unused targets.
"""

from lab_config import validate_lab_config
from lab_matching import ALGORITHM_VERSION, canonical_participants, validate_matrix, select_matching, matching_section
from lab_persistence import encode_fraction
from lab_policy import configured_rho
import lab_rules as rules

MATRICES_KEY = 'lab_group_matrices_v1'
BRANCH_APPS = {'E': 'endogenous', 'A': 'ambiguity', 'M': 'messages'}


def full_sequence(branch):
    if branch not in BRANCH_APPS:
        raise ValueError('The full laboratory route requires branch E, A or M.')
    return ['fixed', BRANCH_APPS[branch], 'policy']


def validate_route(config, app_name):
    """Accept the exact standalone route or exact configured integrated route."""
    from lab_production import is_production, validate_config
    if is_production(config):
        from otree import settings
        validate_config(config, currency=settings.REAL_WORLD_CURRENCY_CODE, use_points=settings.USE_POINTS)
    sequence = config.get('app_sequence')
    if sequence == [app_name]:
        return False
    substantive = full_sequence(config['branch'])
    if sequence not in (substantive, substantive + ['lab_payment']) or app_name not in sequence:
        raise ValueError('Use the exact standalone route or fixed → configured branch app → policy.')
    return True


def is_integrated(config):
    # Detection only; every entry point subsequently validates the exact route.
    return len(config.get('app_sequence', ())) > 1


def needs_initial_readiness(player):
    return not is_integrated(player.session.config) or player.subsession.get_folder_name() == 'fixed'


def _app(name):
    # Installed oTree's explicit model lookup; never infer identity from app IDs.
    from otree.common import get_models_module
    return get_models_module(name)


def block_location(config, block):
    section = matching_section(block)  # strict 1–9, including bool rejection
    name = 'fixed' if section == 'F' else 'policy' if section == 'P(Z)' else BRANCH_APPS[config['branch']]
    first = (block - rules.section_offset(section) - 1) * rules.PERIODS_PER_BLOCK + 1
    return name, first


def block_subsession(session, block, *, last=False):
    name, first = block_location(session.config, block)
    return _app(name).Subsession.objects_get(session=session, round_number=first + (9 if last else 0))


def _snapshot(config, people):
    return dict(version=ALGORITHM_VERSION, seed=config['matching_seed'], participants=list(people),
                branch=config['branch'], app_sequence=list(config['app_sequence']),
                rho=encode_fraction(configured_rho(config)), thresholds=dict(config['ambiguity_thresholds']))


def _participants(subsession, config):
    players = subsession.get_players()
    if len(players) != config['lab_session_size'] or subsession.session.num_participants != config['lab_session_size']:
        raise ValueError('Created participant count must equal configured lab_session_size.')
    return canonical_participants(p.participant.code for p in players)


def matching_state(subsession):
    config = validate_lab_config(subsession.session.config)
    name = subsession.get_folder_name()
    if not validate_route(config, name):
        raise ValueError('Global matrices are for the integrated route only.')
    people = _participants(subsession, config)
    state = subsession.session.vars.get(MATRICES_KEY)
    expected = _snapshot(config, people)
    if (state is None or any(state.get(key) != value for key, value in expected.items())
            or type(state.get('seed')) is not type(config['matching_seed'])):
        raise ValueError('Integrated route/matching configuration changed or was not initialized.')
    return state, people


def stored_matrix(subsession, block):
    matching_section(block)
    state, people = matching_state(subsession)
    return validate_matrix(state['matrices'][str(block)], people)


def actual_matrix(subsession):
    people = [p.participant.code for p in subsession.get_players()]
    return validate_matrix([[p.participant.code for p in g.get_players()] for g in subsession.get_groups()], people)


def initialize(subsession, metadata):
    """Metadata only downstream; never manufacture blocks 4 or 7 at creation."""
    from lab_production import is_production, validate_session
    if is_production(subsession.session.config):
        validate_session(subsession)
    config = validate_lab_config(subsession.session.config)
    name = subsession.get_folder_name()
    validate_route(config, name)
    if name == 'fixed' and subsession.round_number == 1 and MATRICES_KEY not in subsession.session.vars:
        if 'lab_payment' in config['app_sequence']:
            from lab_cash import initialize as initialize_payment
            initialize_payment(subsession.session)
        people = _participants(subsession, config)
        subsession.session.vars[MATRICES_KEY] = dict(_snapshot(config, people), matrices={})
    matching_state(subsession)
    for player in subsession.get_players():
        metadata(player)
    for group in subsession.get_groups():
        metadata(group)
    if name == 'fixed' and subsession.round_number == 1:
        install_block(subsession, 1, at_creation=True)


def _assert_finished(source):
    if (not all(g.settlement_complete for g in source.get_groups())
            or not all(p.period_settled and p.block_feedback_submitted for p in source.get_players())):
        raise ValueError('All session participants must finish block feedback before rematching.')


def _assert_unused(target, destination_name, first):
    # Configuration metadata (threshold/rho/branch/progress) is allowed. No
    # reports, economic observations, settlement or active wait may be deleted.
    group_flags = ('reports_complete', 'settlement_complete', 'public_report_complete')
    group_values = ('group_mean', 'settlement_record', 'public_report_mean', 'public_report_record',
                    'equipment_total', 'final_equipment_total', 'fine_pool', 'redistributed_pool',
                    'recipient_count', 'public_report_total')
    for group in target.get_groups():
        if hasattr(type(group), 'main_enforcement_applied') and group.field_maybe_none('main_enforcement_applied') is not None:
            raise ValueError('Cannot regroup a used destination round.')
        if any(getattr(group, key, False) for key in group_flags + group_values):
            raise ValueError('Cannot regroup a used destination round.')
    for p in target.get_players():
        if (p.block_entered or p.reports_submitted or p.decision_submitted or p.period_settled
                or p.block_feedback_submitted):
            raise ValueError('Cannot regroup a used destination round.')
        if any(getattr(p, key, 0) for key in ('start_equipment', 'voluntary_equipment_after', 'forced_retirement', 'final_equipment', 'is_policy_recipient')):
            raise ValueError('Cannot regroup a used destination round.')
        for key in ('retirement', 'locked_retirement', 'expected_own_equipment_main',
                    'expected_group_average_main', 'locked_own_report', 'locked_group_report'):
            if hasattr(type(p), key) and p.field_maybe_none(key) is not None:
                raise ValueError('Cannot regroup a used destination round.')
        for key in ('voluntary_cost', 'wallet_before', 'wallet_after', 'group_mean', 'main_fine',
                    'follow_up_fine', 'forced_retirement_cost', 'final_block_wallet', 'own_transfer',
                    'wallet_after_voluntary_cost', 'wallet_after_main_fine', 'wallet_after_policy'):
            if getattr(p, key, ''):
                raise ValueError('Cannot regroup a used destination round.')
        pp = p.participant
        sequence = p.session.config['app_sequence']
        current = pp._current_app_name
        if current in sequence:
            current_index, destination_index = sequence.index(current), sequence.index(destination_name)
            if (current_index > destination_index or (current_index == destination_index
                    and pp._round_number is not None and pp._round_number >= first)):
                raise ValueError('Participant already entered a destination round/WaitPage.')


def install_block(source, block, *, at_creation=False, _from_barrier=False):
    """Validate all ten targets before any Group deletion or matrix write.

    Retries validate installed membership and preserve every Group row, even
    after play has begun. Missing/corrupt source-of-truth state fails closed.
    """
    state, people = matching_state(source)
    matching_section(block)
    if at_creation:
        if block != 1 or source.get_folder_name() != 'fixed' or source.round_number != 1:
            raise ValueError('Only integrated Block 1 is installed at creation.')
    else:
        previous = block_subsession(source.session, block - 1, last=True) if block > 1 else None
        if previous is None or source != previous or not (source.block_barrier_complete or _from_barrier):
            raise ValueError('Next matching requires the preceding session block barrier.')
        _assert_finished(source)
    name, first = block_location(source.session.config, block)
    destination_app = _app(name)
    target_first = block_subsession(source.session, block)
    destination_app.validated_session(target_first)
    if name == 'policy':
        policy_state = destination_app.resolved_config(target_first)
        if policy_state['branch'] != state['branch'] or target_first.underlying_branch != state['branch']:
            raise ValueError('Policy underlying branch disagrees with integrated route.')
    targets = target_first.in_rounds(first, first + rules.PERIODS_PER_BLOCK - 1)
    key = str(block)
    if key not in state['matrices'] and any(t.grouping_installed for t in targets):
        raise ValueError('Installed grouping has no stored global matching matrix.')
    section_start = rules.section_offset(matching_section(block)) + 1
    if any(str(b) not in state['matrices'] for b in range(section_start, block)):
        raise ValueError('Missing prior matching matrix in current section.')
    prior = {b: state['matrices'][str(b)] for b in range(section_start, block)}
    matrix = validate_matrix(state['matrices'][key], people) if key in state['matrices'] else None
    for target in targets:
        if canonical_participants(p.participant.code for p in target.get_players()) != people:
            raise ValueError('Destination participants differ from the configured persistent identities.')
        if target.grouping_installed:
            if actual_matrix(target) != matrix:
                raise ValueError('Installed membership disagrees with stored global matching.')
        else:
            _assert_unused(target, name, first)
    if matrix is None:
        matrix = validate_matrix(select_matching(people, state['seed'], block, prior), people)
    if key not in state['matrices']:
        source.session.vars[MATRICES_KEY] = {**state, 'matrices': {
            **state['matrices'], key: [list(g) for g in matrix],
        }}
    for target in targets:
        if not target.grouping_installed:
            by_code = {p.participant.code: p for p in target.get_players()}
            target.set_group_matrix([[by_code[code] for code in group] for group in matrix])
            for group in target.get_groups():
                destination_app._metadata(group)
            target.grouping_installed = True
    if any(actual_matrix(target) != matrix for target in targets):
        raise ValueError('All ten destination rounds must agree with stored matching.')
    if block in (4, 7):
        target_first.readiness_complete = True  # upstream session barrier, not another arrival barrier


def require_block_ready(player):
    matching_state(player.subsession)
    if not player.subsession.grouping_installed:
        raise ValueError('Block matching has not been installed by the preceding barrier.')
    if player.global_block == 1:
        ready = player.subsession.in_round(1).readiness_complete
    else:
        ready = block_subsession(player.session, player.global_block - 1, last=True).block_barrier_complete
    if not ready:
        raise ValueError('The session has not cleared the preceding readiness/block barrier.')


def complete_block(source):
    matching_state(source)
    block = source.get_players()[0].global_block
    if source != block_subsession(source.session, block, last=True):
        raise ValueError('Block barrier is only available after period 10.')
    _assert_finished(source)
    if block < rules.TOTAL_BLOCKS:
        install_block(source, block + 1, _from_barrier=True)
    # set_group_matrix/set_players can commit internally. Publish completion
    # only AFTER all ten destination rounds have been installed and verified.
    source.block_barrier_complete = True
