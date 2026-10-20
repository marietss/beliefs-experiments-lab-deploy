"""Six-human A backend, deliberately parallel to the tested F architecture.

oTree 6.0.15 WaitPages run group callbacks with `group` and session callbacks
with `subsession`. Its set_group_matrix deletes Group rows. Standalone creation
installs Block 4; integrated routes defer it to the upstream app barrier.
Only the preceding block barrier installs Blocks 5/6, while
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
from . import presentation


MATCHING_KEY = 'lab_ambiguity_matching_v1'
SECTION = 'Z'
FIRST_BLOCK = rules.global_block(1, SECTION)
LAST_BLOCK = rules.global_block(rules.BLOCKS_PER_SECTION, SECTION)


class C(BaseConstants):
    NAME_IN_URL = 'ambiguity'
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
    threshold = models.IntegerField(blank=True)
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
    if isinstance(target, Player):
        target.local_block = rules.local_block_for_round(target.round_number)
    else:
        target.threshold = threshold_for_round(target.subsession)


def validated_session(subsession):
    config = validate_lab_config(subsession.session.config)
    if config['branch'] != 'A':
        raise ValueError('The ambiguity app requires branch A.')
    lab_route.validate_route(config, 'ambiguity')
    players = subsession.get_players()
    expected = config['lab_session_size']
    if subsession.session.num_participants != expected or len(players) != expected:
        raise ValueError('Created participant count must equal configured lab_session_size.')
    people = canonical_participants(p.participant.code for p in players)
    return config, people


THRESHOLDS_KEY = 'lab_ambiguity_thresholds_v1'


def threshold_for_round(subsession):
    """Read only the current configured block from the immutable snapshot."""
    config, _ = validated_session(subsession)
    stored = subsession.session.vars.get(THRESHOLDS_KEY)
    if stored is None or stored != dict(version=1, values=config['ambiguity_thresholds']):
        raise ValueError('Ambiguity threshold configuration changed or was not initialized.')
    block = rules.global_block_for_round(subsession.round_number, SECTION)
    return stored['values'][str(block)]


engine = ThresholdSection(
    app_name='ambiguity', matching_key=MATCHING_KEY, branch='A',
    validated_session=validated_session, metadata=_metadata,
    threshold_for_round=threshold_for_round,
    matcher=lambda *args: select_matching(*args),
)

_matching_state = engine._matching_state
stored_matrix = engine.stored_matrix
_actual_matrix = engine._actual_matrix
_install_block = engine._install_block
require_block_ready = engine.require_block_ready
current_state = engine.current_state
_six_players = engine._six_players
complete_reports = engine.complete_reports
settle_period = engine.settle_period
complete_block = engine.complete_block


def creating_session(subsession):
    config, _ = validated_session(subsession)
    if subsession.round_number == 1 and THRESHOLDS_KEY not in subsession.session.vars:
        subsession.session.vars[THRESHOLDS_KEY] = dict(version=1, values=dict(config['ambiguity_thresholds']))
    threshold_for_round(subsession)  # fail closed on changed or missing configuration
    engine.creating_session(subsession)


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


class SectionComprehension(Page):
    template_name = 'general_instructions/LabQuiz.html'
    form_model = 'player'
    is_displayed = staticmethod(lambda player: player.round_number == 1)
    get_form_fields = staticmethod(instructions.quiz_fields)
    vars_for_template = staticmethod(instructions.page_quiz_context)
    error_message = staticmethod(instructions.check_answers)


class BlockStart(Page):
    @staticmethod
    def vars_for_template(player):
        return presentation.support_context()

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


page_sequence = [SessionReady, SectionComprehension, BlockStart, Reports, ReportsWait, Decision,
                 PeriodWait, Result, BlockEnd, BlockEndWait, SectionContinue]
