"""Six-human F backend (Task 4), with read-only F presentation (Task 5).

oTree 6.0.15 WaitPages run group callbacks with `group` and session callbacks
with `subsession`. Its set_group_matrix deletes Group rows. Only creation
installs Block 1; only the preceding block barrier installs Blocks 2/3, while
those destination rounds are unused. Later creating_session calls initialize
metadata only, never overwrite matching. Integrated handoffs use lab_route;
standalone routes retain their original initialization.

All rational fields use lab_persistence's canonical n/d text. They are not
Currency/payoff fields; this app neither selects nor converts cash payment.
Request transactions/WaitPage completion in oTree protect callback execution;
explicit markers and deterministic replay verification protect retries.
"""

import json
from fractions import Fraction

from otree.api import BaseConstants, BaseSubsession, BaseGroup, BasePlayer, Page, WaitPage, models

from lab_config import validate_lab_config
from lab_matching import ALGORITHM_VERSION, canonical_participants, select_matching, validate_matrix
from lab_persistence import encode_fraction, decode_fraction
import lab_rules as rules
import lab_route
import lab_instructions as instructions
import lab_cash
from . import presentation


MATCHING_KEY = 'lab_fixed_matching_v1'


class C(BaseConstants):
    NAME_IN_URL = 'fixed'
    PLAYERS_PER_GROUP = rules.GROUP_SIZE
    NUM_ROUNDS = rules.ROUNDS_PER_APP


class Subsession(BaseSubsession):
    grouping_installed = models.BooleanField(initial=False)
    readiness_complete = models.BooleanField(initial=False)
    block_barrier_complete = models.BooleanField(initial=False)


class Group(BaseGroup):
    global_block = models.IntegerField(initial=0)
    period = models.IntegerField(initial=0)
    reports_complete = models.BooleanField(initial=False)
    equipment_total = models.IntegerField(initial=0)  # post-voluntary, pre-forced
    group_mean = models.LongStringField(initial='', blank=True)
    final_equipment_total = models.IntegerField(initial=0)  # post-enforcement
    settlement_complete = models.BooleanField(initial=False)
    settlement_record = models.LongStringField(initial='', blank=True)


class Player(BasePlayer):
    # Instruction process measures only; populated on the section's first round.
    comprehension_attempts = models.IntegerField(initial=0)
    comprehension_errors = models.IntegerField(initial=0)
    comprehension_passed = models.BooleanField(initial=False)
    comprehension_question_errors = models.LongStringField(initial='{}', blank=True)
    comprehension_1 = models.StringField(initial='', blank=True)
    comprehension_2 = models.StringField(initial='', blank=True)
    comprehension_3 = models.StringField(initial='', blank=True)
    comprehension_4 = models.StringField(initial='', blank=True)
    comprehension_5 = models.StringField(initial='', blank=True)
    comprehension_6 = models.StringField(initial='', blank=True)
    comprehension_7 = models.StringField(initial='', blank=True)
    comprehension_8 = models.StringField(initial='', blank=True)
    comprehension_9 = models.StringField(initial='', blank=True)
    general_attempts = models.IntegerField(initial=0)
    general_errors = models.IntegerField(initial=0)
    general_passed = models.BooleanField(initial=False)
    general_question_errors = models.LongStringField(initial='{}', blank=True)
    general_1 = models.StringField(initial='', blank=True)
    general_2 = models.StringField(initial='', blank=True)
    general_3 = models.StringField(initial='', blank=True)
    general_4 = models.StringField(initial='', blank=True)
    general_5 = models.StringField(initial='', blank=True)
    general_6 = models.StringField(initial='', blank=True)
    general_7 = models.StringField(initial='', blank=True)
    general_8 = models.StringField(initial='', blank=True)
    global_block = models.IntegerField(initial=0)
    local_block = models.IntegerField(initial=0)
    period = models.IntegerField(initial=0)
    block_entered = models.BooleanField(initial=False)
    expected_own_equipment_main = models.IntegerField(min=0, max=100)
    expected_group_average_main = models.IntegerField(min=0, max=100)
    reports_submitted = models.BooleanField(initial=False)
    retirement = models.IntegerField(min=0, max=100)
    locked_retirement = models.IntegerField(blank=True)
    decision_submitted = models.BooleanField(initial=False)
    start_equipment = models.IntegerField(initial=0)
    voluntary_equipment_after = models.IntegerField(initial=0)
    voluntary_cost = models.LongStringField(initial='', blank=True)
    wallet_before = models.LongStringField(initial='', blank=True)
    wallet_after = models.LongStringField(initial='', blank=True)
    group_mean = models.LongStringField(initial='', blank=True)
    main_fine = models.LongStringField(initial='', blank=True)
    follow_up_fine = models.LongStringField(initial='', blank=True)
    forced_retirement = models.IntegerField(initial=0)
    forced_retirement_cost = models.LongStringField(initial='', blank=True)
    final_equipment = models.IntegerField(initial=0)
    final_block_wallet = models.LongStringField(initial='', blank=True)
    period_settled = models.BooleanField(initial=False)
    block_feedback_submitted = models.BooleanField(initial=False)


def _metadata(target):
    target.global_block = rules.global_block_for_round(target.round_number, 'F')
    target.period = rules.period_for_round(target.round_number)
    if isinstance(target, Player):
        target.local_block = rules.local_block_for_round(target.round_number)


def validated_session(subsession):
    config = validate_lab_config(subsession.session.config)
    lab_route.validate_route(config, 'fixed')
    players = subsession.get_players()
    expected = config['lab_session_size']
    if subsession.session.num_participants != expected or len(players) != expected:
        raise ValueError('Created participant count must equal configured lab_session_size.')
    people = canonical_participants(p.participant.code for p in players)
    return config, people


def _matching_state(subsession):
    if lab_route.is_integrated(subsession.session.config):
        return lab_route.matching_state(subsession)
    config, people = validated_session(subsession)
    state = subsession.session.vars.get(MATCHING_KEY)
    if state is None:
        raise ValueError('Fixed matching state has not been initialized.')
    if (state['version'] != ALGORITHM_VERSION or state['participants'] != list(people)
            or type(state['seed']) is not type(config['matching_seed'])
            or state['seed'] != config['matching_seed']):
        raise ValueError('Fixed matching configuration changed after initialization.')
    return state, people


def stored_matrix(subsession, block):
    state, people = _matching_state(subsession)
    return validate_matrix(state['matrices'][str(block)], people)


def _actual_matrix(subsession):
    return validate_matrix(
        [[p.participant.code for p in g.get_players()] for g in subsession.get_groups()],
        [p.participant.code for p in subsession.get_players()],
    )


def _install_block(source, block, *, at_creation=False):
    """Private installer; never recreate a used/current destination group."""
    if lab_route.is_integrated(source.session.config):
        return lab_route.install_block(source, block, at_creation=at_creation)
    if block not in (1, 2, 3):
        raise ValueError('Only fixed Blocks 1–3 may be installed.')
    if block == 1:
        if not at_creation or source.round_number != 1:
            raise ValueError('Block 1 installation is creation-only.')
    elif (at_creation or source.round_number != (block - 1) * rules.PERIODS_PER_BLOCK
          or not source.block_barrier_complete):
        raise ValueError('Next matching requires the preceding session block barrier.')
    state, people = _matching_state(source)
    prior = {b: state['matrices'][str(b)] for b in range(1, block)}
    key = str(block)
    if key in state['matrices']:
        matrix = validate_matrix(state['matrices'][key], people)
    else:
        matrix = select_matching(people, state['seed'], block, prior)
    first = (block - 1) * rules.PERIODS_PER_BLOCK + 1
    targets = source.in_rounds(first, first + rules.PERIODS_PER_BLOCK - 1)
    # Preflight ALL destination rounds before mutating any of them.
    for target in targets:
        if target.grouping_installed:
            if _actual_matrix(target) != matrix:
                raise ValueError('Installed membership disagrees with stored matching.')
            continue  # retry: preserve all Group rows, even if now used
        if any(g.reports_complete or g.settlement_complete for g in target.get_groups()):
            raise ValueError('Cannot regroup a used destination round.')
        for p in target.get_players():
            if (p.block_entered or p.reports_submitted or p.decision_submitted or p.period_settled
                    or p.field_maybe_none('retirement') is not None
                    or p.field_maybe_none('expected_own_equipment_main') is not None
                    or p.field_maybe_none('expected_group_average_main') is not None):
                raise ValueError('Cannot regroup a used destination round.')
            pp = p.participant
            if (not at_creation and pp._current_app_name == 'fixed'
                    and pp._round_number is not None and pp._round_number >= first):
                raise ValueError('Participant already entered a destination round.')
    if key not in state['matrices']:
        # Reassign the entire JSON value; no reliance on nested mutation tracking.
        updated = {**state, 'matrices': {**state['matrices'], key: [list(g) for g in matrix]}}
        source.session.vars[MATCHING_KEY] = updated
    for target in targets:
        if target.grouping_installed:
            continue
        by_code = {p.participant.code: p for p in target.get_players()}
        target.set_group_matrix([[by_code[code] for code in group] for group in matrix])
        for group in target.get_groups():
            _metadata(group)
        target.grouping_installed = True


def creating_session(subsession):
    if lab_route.is_integrated(subsession.session.config):
        return lab_route.initialize(subsession, _metadata)
    config, people = validated_session(subsession)
    for player in subsession.get_players():
        _metadata(player)
    for group in subsession.get_groups():
        _metadata(group)
    if subsession.round_number == 1:
        if MATCHING_KEY not in subsession.session.vars:
            subsession.session.vars[MATCHING_KEY] = dict(
                version=ALGORITHM_VERSION, seed=config['matching_seed'],
                participants=list(people), matrices={},
            )
        _install_block(subsession, 1, at_creation=True)


def require_block_ready(player):
    if lab_route.is_integrated(player.session.config):
        return lab_route.require_block_ready(player)
    if not player.subsession.grouping_installed:
        raise ValueError('Block matching has not been installed.')
    first = player.round_number - player.period + 1
    if player.global_block == 1:
        ready = player.subsession.in_round(1).readiness_complete
    else:
        ready = player.subsession.in_round(first - 1).block_barrier_complete
    if not ready:
        raise ValueError('The session has not cleared the preceding readiness/block barrier.')


def current_state(player):
    """Read exact settled previous-period state; reset independently each block."""
    require_block_ready(player)
    if player.period == 1:
        return rules.K0, rules.W0
    previous = player.in_round(player.round_number - 1)
    if not previous.period_settled or not previous.group.settlement_complete:
        raise ValueError('Previous period has not been settled.')
    return previous.final_equipment, decode_fraction(previous.wallet_after)


def _six_players(group):
    players = sorted(group.get_players(), key=lambda p: p.participant.code)
    if len(players) != C.PLAYERS_PER_GROUP or len({p.participant.code for p in players}) != 6:
        raise ValueError('A fixed group must contain exactly six distinct humans.')
    return players


def complete_reports(group):
    players = _six_players(group)
    for player in players:
        require_block_ready(player)
        if player.period != 1 or not player.reports_submitted:
            raise ValueError('All six block-start reports are required.')
        for name in ('expected_own_equipment_main', 'expected_group_average_main'):
            value = player.field_maybe_none(name)
            if type(value) is not int or not 0 <= value <= 100:
                raise ValueError('Reports must be integers from 0 through 100.')
    group.reports_complete = True


def settle_period(group):
    players = _six_players(group)
    # Phase 1: every decision is submitted and locked; compute all voluntary ends.
    prepared = []
    for player in players:
        start, wallet = current_state(player)
        owner = player.in_round(player.round_number - player.period + 1)
        if not owner.group.reports_complete:
            raise ValueError('The group report barrier has not completed.')
        if (not player.decision_submitted
                or player.field_maybe_none('locked_retirement') != player.field_maybe_none('retirement')):
            raise ValueError('All six decisions must be submitted and locked before settlement.')
        retirement = player.field_maybe_none('locked_retirement')
        after = rules.equipment_after_retirement(start, retirement)
        prepared.append((player, start, wallet, after, rules.retirement_cost(retirement)))
    # Phase 2: shared post-voluntary total/mean, with each human included once.
    total = sum(row[3] for row in prepared)
    mean = encode_fraction(Fraction(total, C.PLAYERS_PER_GROUP))
    # Phase 3: apply F checks to each participant, assigning from original inputs.
    outcomes = []
    for player, start, wallet, after, cost in prepared:
        main = rules.main_fine(after) if rules.is_main_period(player.period) else Fraction(0)
        follow = rules.follow_up_enforcement(after) if rules.is_follow_up_period(player.period) else None
        follow_fine = follow.follow_up_fine if follow else Fraction(0)
        forced_cost = follow.forced_retirement_cost if follow else Fraction(0)
        final_wallet = rules.wallet_after_deductions(wallet, cost, main, follow_fine, forced_cost)
        outcomes.append(dict(
            start_equipment=start, voluntary_equipment_after=after,
            voluntary_cost=encode_fraction(cost), wallet_before=encode_fraction(wallet),
            wallet_after=encode_fraction(final_wallet), group_mean=mean,
            main_fine=encode_fraction(main), follow_up_fine=encode_fraction(follow_fine),
            forced_retirement=follow.forced_retirement if follow else 0,
            forced_retirement_cost=encode_fraction(forced_cost),
            final_equipment=follow.final_equipment if follow else after,
            final_block_wallet=encode_fraction(final_wallet) if follow else '',
            period_settled=True,
        ))
    group_values = dict(equipment_total=total, group_mean=mean,
                        final_equipment_total=sum(row['final_equipment'] for row in outcomes))
    record = json.dumps(dict(
        version=1, block=group.global_block, period=group.period, group=group_values,
        players=[dict(code=p.participant.code, retirement=p.locked_retirement, **outcome)
                 for p, outcome in zip(players, outcomes)],
    ), sort_keys=True, separators=(',', ':'))
    if group.settlement_complete:
        if (group.settlement_record != record
                or any(getattr(group, key) != value for key, value in group_values.items())
                or any(getattr(p, key) != value for p, row in zip(players, outcomes)
                       for key, value in row.items())):
            raise ValueError('Inconsistent replay of a settled period.')
        lab_cash.record_group(group)
        return
    if any(p.period_settled for p in players):
        raise ValueError('Unexpected partial period settlement.')
    for player, outcome in zip(players, outcomes):
        for key, value in outcome.items():
            setattr(player, key, value)
    for key, value in group_values.items():
        setattr(group, key, value)
    group.settlement_record = record
    group.settlement_complete = True  # last economic write; ledger shares callback transaction
    lab_cash.record_group(group)  # exact post-Follow-up ledger; no payment selection


def complete_block(subsession):
    if lab_route.is_integrated(subsession.session.config):
        return lab_route.complete_block(subsession)
    validated_session(subsession)
    if not rules.is_follow_up_period(rules.period_for_round(subsession.round_number)):
        raise ValueError('Block barrier is only available after period 10.')
    if (not all(g.settlement_complete for g in subsession.get_groups())
            or not all(p.block_feedback_submitted and p.period_settled for p in subsession.get_players())):
        raise ValueError('All session participants must finish block feedback before rematching.')
    subsession.block_barrier_complete = True
    block = rules.global_block_for_round(subsession.round_number, 'F')
    if block < rules.BLOCKS_PER_SECTION:
        _install_block(subsession, block + 1)


class DemoSplash(Page):
    template_name = 'fixed/BlessSplash.html'
    is_displayed = staticmethod(lambda player: player.round_number == 1 and player.session.is_demo)


class SessionReady(WaitPage):
    template_name = 'fixed/BlessReady.html'
    wait_for_all_groups = True
    body_text = 'Attendi che tutti i partecipanti della sessione siano pronti.'

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1 and lab_route.needs_initial_readiness(player)

    @staticmethod
    def after_all_players_arrive(subsession):
        validated_session(subsession)
        if lab_route.is_integrated(subsession.session.config) and subsession.get_folder_name() != 'fixed':
            lab_route.require_block_ready(subsession.get_players()[0])
        if not subsession.grouping_installed:
            raise ValueError('Initial matching must be installed before readiness.')
        subsession.readiness_complete = True


class LabOverview(Page):
    template_name = 'general_instructions/LabOverview.html'
    is_displayed = staticmethod(lambda player: player.round_number == 1)
    vars_for_template = staticmethod(instructions.context)


class LabPractice(Page):
    template_name = 'general_instructions/LabPractice.html'
    is_displayed = staticmethod(lambda player: player.round_number == 1)
    vars_for_template = staticmethod(instructions.context)


class GeneralComprehension(Page):
    template_name = 'general_instructions/LabQuiz.html'
    form_model = 'player'
    is_displayed = staticmethod(lambda player: player.round_number == 1)
    get_form_fields = staticmethod(lambda player: instructions.quiz_fields(player, general=True))
    vars_for_template = staticmethod(lambda player: instructions.page_quiz_context(player, general=True))
    error_message = staticmethod(lambda player, values: instructions.check_answers(player, values, general=True))


class SectionInstructions(Page):
    template_name = 'general_instructions/LabSection.html'
    is_displayed = staticmethod(lambda player: player.round_number == 1)
    vars_for_template = staticmethod(instructions.context)


class SectionComprehension(Page):
    template_name = 'general_instructions/LabQuiz.html'
    form_model = 'player'
    is_displayed = staticmethod(lambda player: player.round_number == 1)
    get_form_fields = staticmethod(instructions.quiz_fields)
    vars_for_template = staticmethod(instructions.page_quiz_context)
    error_message = staticmethod(instructions.check_answers)


class BlockStart(Page):
    @staticmethod
    def is_displayed(player):
        return player.period == 1

    @staticmethod
    def before_next_page(player, timeout_happened):
        require_block_ready(player)
        player.block_entered = True


class Reports(Page):
    form_model = 'player'
    form_fields = ['expected_own_equipment_main', 'expected_group_average_main']

    @staticmethod
    def is_displayed(player):
        return player.period == 1

    @staticmethod
    def before_next_page(player, timeout_happened):
        require_block_ready(player)
        player.reports_submitted = True


class ReportsWait(WaitPage):
    @staticmethod
    def is_displayed(player):
        return player.period == 1

    after_all_players_arrive = staticmethod(complete_reports)


class Decision(Page):
    form_model = 'player'
    form_fields = ['retirement']

    @staticmethod
    def vars_for_template(player):
        equipment, wallet = current_state(player)
        return dict(equipment=equipment, wallet=presentation.points(wallet),
                    **presentation.chart_context(player, equipment=equipment))

    @staticmethod
    def error_message(player, values):
        try:
            rules.equipment_after_retirement(current_state(player)[0], values['retirement'])
            if player.decision_submitted and values['retirement'] != player.locked_retirement:
                return 'La decisione di questo periodo è già stata confermata.'
        except ValueError as exc:
            return "Seleziona un numero intero tra 0 e l’attrezzatura rimanente."

    @staticmethod
    def before_next_page(player, timeout_happened):
        if Decision.error_message(player, dict(retirement=player.retirement)):
            raise ValueError('Invalid or inconsistent decision submission.')
        owner = player.in_round(player.round_number - player.period + 1)
        if not owner.group.reports_complete:
            raise ValueError('Reports are not complete.')
        player.locked_retirement = player.retirement
        player.decision_submitted = True  # no economic settlement here


class PeriodWait(WaitPage):
    after_all_players_arrive = staticmethod(settle_period)


def feedback_context(player):
    if not player.period_settled or not player.group.settlement_complete:
        raise ValueError('Results cannot be displayed before group settlement.')
    return presentation.outcome_context(player)


class Result(Page):
    @staticmethod
    def vars_for_template(player):
        return feedback_context(player)


class BlockEnd(Page):
    @staticmethod
    def is_displayed(player):
        return rules.is_follow_up_period(player.period)

    @staticmethod
    def vars_for_template(player):
        feedback_context(player)
        return presentation.block_summary(player)

    @staticmethod
    def before_next_page(player, timeout_happened):
        feedback_context(player)
        player.block_feedback_submitted = True


class BlockEndWait(WaitPage):
    wait_for_all_groups = True

    @staticmethod
    def is_displayed(player):
        return rules.is_follow_up_period(player.period)

    after_all_players_arrive = staticmethod(complete_block)


class SectionContinue(Page):
    """Participant-clicked continuation after the existing section-end barrier."""
    template_name = 'lab/SectionContinue.html'
    is_displayed = staticmethod(lambda player: player.round_number == C.NUM_ROUNDS)


page_sequence = [DemoSplash, SessionReady, LabPractice, SectionComprehension, BlockStart, Reports, ReportsWait, Decision,
                 PeriodWait, Result, BlockEnd, BlockEndWait, SectionContinue]
