"""Common six-human policy backend, deliberately parallel to the tested F architecture.

oTree 6.0.15 WaitPages run group callbacks with `group` and session callbacks
with `subsession`. Its set_group_matrix deletes Group rows. Standalone creation
installs Block 7; integrated routes defer it to the upstream app barrier.
Only the preceding block barrier installs Blocks 8/9, while
those destination rounds are unused. Later creating_session calls initialize
metadata only, never overwrite matching. Integrated handoffs use lab_route;
standalone routes retain their original initialization.

All rational fields use lab_persistence's canonical n/d text. They are not
Currency/payoff fields; this app neither selects nor converts cash payment.
Request transactions/WaitPage completion in oTree protect callback execution;
explicit markers and deterministic replay verification protect retries.
"""

from otree.api import BaseConstants, BaseSubsession, BaseGroup, BasePlayer, Page, WaitPage, models

from lab_config import validate_lab_config
from lab_matching import canonical_participants, select_matching
from lab_threshold import ThresholdSection
import lab_rules as rules
import lab_route
import lab_instructions as instructions
import lab_comprehension as comprehension
import lab_flow as flow
from . import presentation
import lab_reports as public_reports
from lab_persistence import encode_fraction, decode_fraction
from lab_policy import configured_rho
from .settlement import apply_policy


MATCHING_KEY = 'lab_policy_matching_v1'
CONFIG_KEY = 'lab_policy_config_v1'
SECTION = 'P(Z)'
FIRST_BLOCK = rules.global_block(1, SECTION)
LAST_BLOCK = rules.global_block(rules.BLOCKS_PER_SECTION, SECTION)


class C(BaseConstants):
    NAME_IN_URL = 'policy'
    PLAYERS_PER_GROUP = rules.GROUP_SIZE
    NUM_ROUNDS = rules.ROUNDS_PER_APP


class Subsession(BaseSubsession):
    underlying_branch = models.StringField(initial='')
    grouping_installed = models.BooleanField(initial=False)
    readiness_complete = models.BooleanField(initial=False)
    block_barrier_complete = models.BooleanField(initial=False)


class Group(BaseGroup):
    underlying_branch = models.StringField(initial='')
    rho = models.LongStringField(initial='', blank=True)
    fine_pool = models.LongStringField(initial='', blank=True)
    recipient_count = models.IntegerField(initial=0)
    redistributed_pool = models.LongStringField(initial='', blank=True)
    global_block = models.IntegerField(initial=0)
    period = models.IntegerField(initial=0)
    reports_complete = models.BooleanField(initial=False)
    public_report_mean = models.LongStringField(initial='', blank=True)
    public_report_total = models.IntegerField(initial=0)
    public_report_record = models.LongStringField(initial='', blank=True)
    public_report_complete = models.BooleanField(initial=False)
    threshold = models.IntegerField(initial=rules.KNOWN_THRESHOLD)
    main_enforcement_applied = models.BooleanField(blank=True)
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
    underlying_branch = models.StringField(initial='')
    is_policy_recipient = models.BooleanField(initial=False)
    own_transfer = models.LongStringField(initial='', blank=True)
    wallet_after_voluntary_cost = models.LongStringField(initial='', blank=True)
    wallet_after_main_fine = models.LongStringField(initial='', blank=True)
    wallet_after_policy = models.LongStringField(initial='', blank=True)
    global_block = models.IntegerField(initial=0)
    local_block = models.IntegerField(initial=0)
    period = models.IntegerField(initial=0)
    block_entered = models.BooleanField(initial=False)
    expected_own_equipment_main = models.IntegerField(min=0, max=100)
    expected_group_average_main = models.IntegerField(min=0, max=100)
    reports_submitted = models.BooleanField(initial=False)
    locked_own_report = models.IntegerField(blank=True)
    locked_group_report = models.IntegerField(blank=True)
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
    applied_main_threshold = models.IntegerField(blank=True)
    main_enforcement_applied = models.BooleanField(blank=True)
    follow_up_fine = models.LongStringField(initial='', blank=True)
    forced_retirement = models.IntegerField(initial=0)
    forced_retirement_cost = models.LongStringField(initial='', blank=True)
    final_equipment = models.IntegerField(initial=0)
    final_block_wallet = models.LongStringField(initial='', blank=True)
    period_settled = models.BooleanField(initial=False)
    block_feedback_submitted = models.BooleanField(initial=False)


def _metadata(target):
    target.global_block = rules.global_block_for_round(target.round_number, SECTION)
    target.period = rules.period_for_round(target.round_number)
    state = resolved_config(target.subsession)
    target.underlying_branch = state['branch']
    if isinstance(target, Player):
        target.local_block = rules.local_block_for_round(target.round_number)
    else:
        target.rho = state['rho']
        target.threshold = threshold_for_round(target.subsession)


def validated_session(subsession):
    config = validate_lab_config(subsession.session.config)
    lab_route.validate_route(config, 'policy')
    players = subsession.get_players()
    expected = config['lab_session_size']
    if subsession.session.num_participants != expected or len(players) != expected:
        raise ValueError('Created participant count must equal configured lab_session_size.')
    people = canonical_participants(p.participant.code for p in players)
    return config, people


def _config_snapshot(config):
    return dict(version=1, branch=config['branch'], rho=encode_fraction(configured_rho(config)),
                thresholds=dict(config['ambiguity_thresholds']))


def resolved_config(subsession):
    config, _ = validated_session(subsession)
    stored = subsession.session.vars.get(CONFIG_KEY)
    if stored is None or stored != _config_snapshot(config):
        raise ValueError('Policy branch/rho/threshold configuration changed or was not initialized.')
    return stored


def threshold_for_round(subsession):
    state = resolved_config(subsession)
    if state['branch'] == 'A':
        block = rules.global_block_for_round(subsession.round_number, SECTION)
        return state['thresholds'][str(block)]
    return rules.KNOWN_THRESHOLD


# Explicit branch dispatch, ordinary helper instances, no generated model/page classes.
engines = {branch: ThresholdSection(
    app_name='policy', matching_key=MATCHING_KEY, branch=branch, section=SECTION,
    validated_session=validated_session, metadata=_metadata,
    threshold_for_round=threshold_for_round, matcher=lambda *args: select_matching(*args),
    settlement_layer=apply_policy,
) for branch in ('E', 'A', 'M')}


def engine_for(subsession):
    return engines[resolved_config(subsession)['branch']]


def stored_matrix(subsession, block):
    return engine_for(subsession).stored_matrix(subsession, block)


def _actual_matrix(subsession):
    return engine_for(subsession)._actual_matrix(subsession)


def _install_block(subsession, block, *, at_creation=False):
    return engine_for(subsession)._install_block(subsession, block, at_creation=at_creation)


def creating_session(subsession):
    config, _ = validated_session(subsession)
    if subsession.round_number == 1 and CONFIG_KEY not in subsession.session.vars:
        subsession.session.vars[CONFIG_KEY] = _config_snapshot(config)
    state = resolved_config(subsession)
    subsession.underlying_branch = state['branch']
    engine_for(subsession).creating_session(subsession)


def require_block_ready(player):
    return engine_for(player.subsession).require_block_ready(player)


def current_state(player):
    return engine_for(player.subsession).current_state(player)


def complete_reports(group):
    engine = engine_for(group.subsession)
    if group.underlying_branch == 'M':
        public_reports.complete(group, validate_reports=engine.complete_reports)
    else:
        engine.complete_reports(group)


def settle_period(group):
    state = resolved_config(group.subsession)
    if group.rho != state['rho'] or group.underlying_branch != state['branch']:
        raise ValueError('Policy group configuration disagrees with the persisted session contract.')
    return engine_for(group.subsession).settle_period(group)


def complete_block(subsession):
    return engine_for(subsession).complete_block(subsession)


class SectionSplash(Page):
    template_name = 'lab/AdminSplash.html'
    is_displayed = staticmethod(lambda player: player.round_number == 1)
    vars_for_template = staticmethod(flow.section_splash)
    error_message = staticmethod(flow.admin_only)


class SessionReady(WaitPage):
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


class SectionInstructions(Page):
    template_name = 'general_instructions/LabSection.html'
    is_displayed = staticmethod(lambda player: player.round_number == 1)
    vars_for_template = staticmethod(instructions.context)


class SectionComprehension(comprehension.pair_page(1)):
    pass


class SectionComprehension2(comprehension.pair_page(2)):
    pass


class ComprehensionWait(WaitPage):
    wait_for_all_groups = True
    body_text = 'Attendi che tutti i partecipanti completino le domande di comprensione.'
    is_displayed = staticmethod(lambda player: player.round_number == 1)
    after_all_players_arrive = staticmethod(flow.comprehension_complete)


class FirstBlockSplash(Page):
    template_name = 'lab/AdminSplash.html'
    is_displayed = staticmethod(lambda player: player.period == 1 and player.local_block == 1)
    vars_for_template = staticmethod(flow.first_block_splash)
    error_message = staticmethod(flow.admin_only)


class BlockStart(Page):
    @staticmethod
    def vars_for_template(player):
        return presentation.start_context(player)

    @staticmethod
    def is_displayed(player):
        return player.period == 1 and player.local_block > 1

    @staticmethod
    def before_next_page(player, timeout_happened):
        require_block_ready(player)
        player.block_entered = True


class BlockStartWait(WaitPage):
    wait_for_all_groups = True
    body_text = 'Attendi che tutti i partecipanti siano pronti per il nuovo blocco.'
    is_displayed = staticmethod(lambda player: player.period == 1)
    after_all_players_arrive = staticmethod(flow.start_block)


class Reports(Page):
    vars_for_template = staticmethod(presentation.start_context)
    form_model = 'player'
    form_fields = ['expected_own_equipment_main', 'expected_group_average_main']

    @staticmethod
    def is_displayed(player):
        return player.period == 1

    @staticmethod
    def before_next_page(player, timeout_happened):
        require_block_ready(player)
        if player.underlying_branch == 'M':
            public_reports.lock(player)
        else:
            player.reports_submitted = True


class ReportsWait(WaitPage):
    @staticmethod
    def is_displayed(player):
        return player.period == 1

    after_all_players_arrive = staticmethod(complete_reports)


class Decision(Page):
    timeout_seconds = 30
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
        if timeout_happened and not player.decision_submitted:
            player.retirement = 0
        if player.underlying_branch == 'M':
            public_reports.read(player)  # no partial report disclosure
        if Decision.error_message(player, dict(retirement=player.retirement)):
            raise ValueError('Invalid or inconsistent decision submission.')
        owner = player.in_round(player.round_number - player.period + 1)
        if not owner.group.reports_complete:
            raise ValueError('Reports are not complete.')
        player.locked_retirement = player.retirement
        player.decision_submitted = True  # no economic settlement here


class PeriodWait(WaitPage):
    template_name = 'policy/BlockWait.html'
    vars_for_template = staticmethod(presentation.wait_context)
    after_all_players_arrive = staticmethod(settle_period)


def feedback_context(player):
    if not player.period_settled or not player.group.settlement_complete:
        raise ValueError('Results cannot be displayed before group settlement.')
    return presentation.outcome_context(player)


class Result(Page):
    @staticmethod
    def get_timeout_seconds(player):
        return 60 if rules.is_main_period(player.period) or rules.is_follow_up_period(player.period) else 20

    before_next_page = staticmethod(flow.result_complete)
    @staticmethod
    def vars_for_template(player):
        return feedback_context(player)


class ResultWait(WaitPage):
    body_text = 'Attendi che tutti i manager del tuo gruppo completino il periodo.'
    is_displayed = staticmethod(lambda player: not rules.is_follow_up_period(player.period))
    after_all_players_arrive = staticmethod(flow.results_complete)


class BlockEnd(Page):
    template_name = 'lab/BlockSummary.html'
    @staticmethod
    def is_displayed(player):
        return rules.is_follow_up_period(player.period)

    @staticmethod
    def vars_for_template(player):
        feedback_context(player)
        return flow.block_summary_context(player)

    @staticmethod
    def before_next_page(player, timeout_happened):
        feedback_context(player)
        player.block_feedback_submitted = True


class BlockEndWait(WaitPage):
    template_name = 'policy/BlockWait.html'
    vars_for_template = staticmethod(presentation.wait_context)
    wait_for_all_groups = True

    @staticmethod
    def is_displayed(player):
        return rules.is_follow_up_period(player.period)

    after_all_players_arrive = staticmethod(complete_block)


page_sequence = [SectionSplash, SessionReady, SectionComprehension, SectionComprehension2, ComprehensionWait,
                 FirstBlockSplash, BlockStart, BlockStartWait, Reports, ReportsWait, Decision,
                 PeriodWait, Result, ResultWait, BlockEndWait, BlockEnd]
