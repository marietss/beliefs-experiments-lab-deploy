"""Shared E/A/M non-model backend, extracted from the tested E implementation.

Apps keep explicit models and pages. Dependencies are supplied explicitly:
validation, metadata assignment, one-block threshold lookup and seeded matching.
No app import, dynamic model/page generation, rendering or threshold drawing.
Matching/settlement transactions and barrier ordering remain the E contract.
Policy supplies section P(Z) and a settlement layer inside the same replay
marker; ordinary E/A/M keep the default Z section and no extra layer.
"""

import json
from fractions import Fraction
from lab_matching import ALGORITHM_VERSION, validate_matrix
from lab_persistence import encode_fraction, decode_fraction
import lab_rules as rules
import lab_route
import lab_cash


class ThresholdSection:
    def __init__(self, *, app_name, matching_key, branch, validated_session,
                 metadata, threshold_for_round, matcher, section='Z', settlement_layer=None):
        if branch not in ('E', 'A', 'M'):
            raise ValueError('ThresholdSection supports E, A or M only.')
        self.app_name = app_name
        self.matching_key = matching_key
        self.branch = branch
        self.validated_session = validated_session
        self._metadata = metadata
        self.threshold_for_round = threshold_for_round
        self.matcher = matcher
        self.section = section
        self.settlement_layer = settlement_layer
        self.first_block = rules.global_block(1, self.section)
        self.last_block = rules.global_block(rules.BLOCKS_PER_SECTION, self.section)

    def _matching_state(self, subsession):
        if lab_route.is_integrated(subsession.session.config):
            return lab_route.matching_state(subsession)
        config, people = self.validated_session(subsession)
        state = subsession.session.vars.get(self.matching_key)
        if state is None:
            raise ValueError('Threshold matching state has not been initialized.')
        if (state['version'] != ALGORITHM_VERSION or state['participants'] != list(people)
                or type(state['seed']) is not type(config['matching_seed'])
                or state['seed'] != config['matching_seed']):
            raise ValueError('Threshold matching configuration changed after initialization.')
        return state, people

    def stored_matrix(self, subsession, block):
        state, people = self._matching_state(subsession)
        return validate_matrix(state['matrices'][str(block)], people)

    def _actual_matrix(self, subsession):
        return validate_matrix(
            [[p.participant.code for p in g.get_players()] for g in subsession.get_groups()],
            [p.participant.code for p in subsession.get_players()],
        )

    def _install_block(self, source, block, *, at_creation=False):
        """Private installer; never recreate a used/current destination group."""
        if lab_route.is_integrated(source.session.config):
            return lab_route.install_block(source, block, at_creation=at_creation)
        if type(block) is not int or not self.first_block <= block <= self.last_block:
            raise ValueError(f'Only section Blocks {self.first_block}–{self.last_block} may be installed.')
        local_block = block - rules.section_offset(self.section)
        if block == self.first_block:
            if not at_creation or source.round_number != 1:
                raise ValueError(f'Block {self.first_block} installation is creation-only.')
        elif (at_creation or source.round_number != (local_block - 1) * rules.PERIODS_PER_BLOCK
              or not source.block_barrier_complete):
            raise ValueError('Next matching requires the preceding session block barrier.')
        state, people = self._matching_state(source)
        prior = {b: state['matrices'][str(b)] for b in range(self.first_block, block)}
        key = str(block)
        if key in state['matrices']:
            matrix = validate_matrix(state['matrices'][key], people)
        else:
            matrix = self.matcher(people, state['seed'], block, prior)
        first = (local_block - 1) * rules.PERIODS_PER_BLOCK + 1
        targets = source.in_rounds(first, first + rules.PERIODS_PER_BLOCK - 1)
        # Preflight ALL destination rounds before mutating any of them.
        for target in targets:
            if target.grouping_installed:
                if self._actual_matrix(target) != matrix:
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
                if (not at_creation and pp._current_app_name == self.app_name
                        and pp._round_number is not None and pp._round_number >= first):
                    raise ValueError('Participant already entered a destination round.')
        if key not in state['matrices']:
            # Reassign the entire JSON value; no reliance on nested mutation tracking.
            updated = {**state, 'matrices': {**state['matrices'], key: [list(g) for g in matrix]}}
            source.session.vars[self.matching_key] = updated
        for target in targets:
            if target.grouping_installed:
                continue
            by_code = {p.participant.code: p for p in target.get_players()}
            target.set_group_matrix([[by_code[code] for code in group] for group in matrix])
            for group in target.get_groups():
                self._metadata(group)
            target.grouping_installed = True

    def creating_session(self, subsession):
        if lab_route.is_integrated(subsession.session.config):
            return lab_route.initialize(subsession, self._metadata)
        config, people = self.validated_session(subsession)
        for player in subsession.get_players():
            self._metadata(player)
        for group in subsession.get_groups():
            self._metadata(group)
        if subsession.round_number == 1:
            if self.matching_key not in subsession.session.vars:
                subsession.session.vars[self.matching_key] = dict(
                    version=ALGORITHM_VERSION, seed=config['matching_seed'],
                    participants=list(people), matrices={},
                )
            self._install_block(subsession, self.first_block, at_creation=True)

    def require_block_ready(self, player):
        if lab_route.is_integrated(player.session.config):
            return lab_route.require_block_ready(player)
        if not player.subsession.grouping_installed:
            raise ValueError('Block matching has not been installed.')
        first = player.round_number - player.period + 1
        if player.local_block == 1:
            ready = player.subsession.in_round(1).readiness_complete
        else:
            ready = player.subsession.in_round(first - 1).block_barrier_complete
        if not ready:
            raise ValueError('The session has not cleared the preceding readiness/block barrier.')

    def current_state(self, player):
        """Read exact settled previous-period state; reset independently each block."""
        self.require_block_ready(player)
        if player.period == 1:
            return rules.K0, rules.W0
        previous = player.in_round(player.round_number - 1)
        if not previous.period_settled or not previous.group.settlement_complete:
            raise ValueError('Previous period has not been settled.')
        return previous.final_equipment, decode_fraction(previous.wallet_after)

    def _six_players(self, group):
        players = sorted(group.get_players(), key=lambda p: p.participant.code)
        if len(players) != rules.GROUP_SIZE or len({p.participant.code for p in players}) != 6:
            raise ValueError('A threshold-section group must contain exactly six distinct humans.')
        return players

    def complete_reports(self, group):
        players = self._six_players(group)
        for player in players:
            self.require_block_ready(player)
            if player.period != 1 or not player.reports_submitted:
                raise ValueError('All six block-start reports are required.')
            for name in ('expected_own_equipment_main', 'expected_group_average_main'):
                value = player.field_maybe_none(name)
                if type(value) is not int or not 0 <= value <= 100:
                    raise ValueError('Reports must be integers from 0 through 100.')
        group.reports_complete = True

    def settle_period(self, group):
        players = self._six_players(group)
        # Phase 1: every decision is submitted and locked; compute all voluntary ends.
        prepared = []
        for player in players:
            start, wallet = self.current_state(player)
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
        mean = encode_fraction(Fraction(total, rules.GROUP_SIZE))
        # Common Main condition is known only AFTER all six voluntary outcomes.
        at_main = rules.is_main_period(group.period)
        threshold = self.threshold_for_round(group.subsession)
        enforcement = rules.main_enforcement_applies(
            self.branch, group_total=total,
            ambiguity_threshold=threshold if self.branch == 'A' else None,
        ) if at_main else None
        # Phase 3: apply threshold checks to each participant, assigning from original inputs.
        outcomes = []
        for player, start, wallet, after, cost in prepared:
            main = rules.main_fine(after) if enforcement else Fraction(0)
            follow = rules.follow_up_enforcement(after) if rules.is_follow_up_period(player.period) else None
            follow_fine = follow.follow_up_fine if follow else Fraction(0)
            forced_cost = follow.forced_retirement_cost if follow else Fraction(0)
            final_wallet = rules.wallet_after_deductions(wallet, cost, main, follow_fine, forced_cost)
            outcomes.append(dict(
                start_equipment=start, voluntary_equipment_after=after,
                voluntary_cost=encode_fraction(cost), wallet_before=encode_fraction(wallet),
                wallet_after=encode_fraction(final_wallet), group_mean=mean,
                main_fine=encode_fraction(main), follow_up_fine=encode_fraction(follow_fine),
                applied_main_threshold=threshold if at_main else None,
                main_enforcement_applied=enforcement,
                forced_retirement=follow.forced_retirement if follow else 0,
                forced_retirement_cost=encode_fraction(forced_cost),
                final_equipment=follow.final_equipment if follow else after,
                final_block_wallet=encode_fraction(final_wallet) if follow else '',
                period_settled=True,
            ))
        group_values = dict(equipment_total=total, group_mean=mean,
                            threshold=threshold, main_enforcement_applied=enforcement,
                            final_equipment_total=sum(row['final_equipment'] for row in outcomes))
        # Optional policy layer runs after all actual fines, before the same atomic marker.
        if self.settlement_layer is not None:
            self.settlement_layer(group, prepared, outcomes, group_values)
        record = json.dumps(dict(
            version=1, block=group.global_block, period=group.period, group=group_values,
            players=[dict(code=p.participant.code, retirement=p.locked_retirement, **outcome)
                     for p, outcome in zip(players, outcomes)],
        ), sort_keys=True, separators=(',', ':'))
        if group.settlement_complete:
            if (group.settlement_record != record
                    or any(group.field_maybe_none(key) != value for key, value in group_values.items())
                    or any(p.field_maybe_none(key) != value for p, row in zip(players, outcomes)
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

    def complete_block(self, subsession):
        if lab_route.is_integrated(subsession.session.config):
            return lab_route.complete_block(subsession)
        self.validated_session(subsession)
        if not rules.is_follow_up_period(rules.period_for_round(subsession.round_number)):
            raise ValueError('Block barrier is only available after period 10.')
        if (not all(g.settlement_complete for g in subsession.get_groups())
                or not all(p.block_feedback_submitted and p.period_settled for p in subsession.get_players())):
            raise ValueError('All session participants must finish block feedback before rematching.')
        subsession.block_barrier_complete = True
        block = rules.global_block_for_round(subsession.round_number, self.section)
        if block < self.last_block:
            self._install_block(subsession, block + 1)
