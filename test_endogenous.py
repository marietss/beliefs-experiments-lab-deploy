"""Actual six-human ORM/callback/HTTP tests; run in a disposable project copy."""

import ast
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

# Reuse the existing disposable-project setup exactly once across F/E tests.
# Repeated setup() loads an on-disk oTree DB twice into its in-memory DB.
import test_fixed
from otree.api import WaitPage
from otree.database import db
from otree.session import create_session
from otree.bots.runner import make_bots
from lab_matching import select_matching
from lab_persistence import decode_fraction
import lab_rules as rules
import endogenous


def make_session(size=18):
    return create_session(f'dev_lab_endogenous_{size}', num_participants=size)


def subsession(session, round_number=1):
    return endogenous.Subsession.objects_get(session=session, round_number=round_number)


def ready(session):
    endogenous.SessionReady.after_all_players_arrive(subsession(session))


def reports(group):
    for p in group.get_players():
        p.expected_own_equipment_main = p.expected_group_average_main = 50
        endogenous.Reports.before_next_page(p, False)
    endogenous.ReportsWait.after_all_players_arrive(group)


def decide(group, amounts=None):
    for p, amount in zip(group.get_players(), [0] * 6 if amounts is None else amounts):
        p.retirement = amount
        endogenous.Decision.before_next_page(p, False)


def run_period(group, amounts=None):
    if group.period == 1:
        reports(group)
    decide(group, amounts)
    endogenous.PeriodWait.after_all_players_arrive(group)


def finish_block(session, local_block):
    first = (local_block - 1) * 10 + 1
    for r in range(first, first + 10):
        for group in subsession(session, r).get_groups():
            run_period(group)
    end = subsession(session, first + 9)
    for p in end.get_players():
        endogenous.BlockEnd.before_next_page(p, False)
    endogenous.BlockEndWait.after_all_players_arrive(end)


class EndogenousBackendTests(unittest.TestCase):
    def tearDown(self):
        db.rollback()

    def main_group(self):
        session = make_session()
        ready(session)
        for r in range(1, 5):
            run_period(subsession(session, r).get_groups()[0])
        return subsession(session, 5).get_groups()[0]

    def test_exact_counts_and_all_round_metadata(self):
        for size in (18, 24):
            session = make_session(size)
            for r in range(1, 31):
                ss = subsession(session, r)
                self.assertEqual(len(ss.get_players()), size)
                self.assertEqual(len(ss.get_groups()), size // 6)
                for p in ss.get_players():
                    self.assertEqual((p.global_block, p.local_block, p.period),
                                     (rules.global_block_for_round(r, 'Z'), (r - 1) // 10 + 1, (r - 1) % 10 + 1))
                    self.assertEqual(p.group.threshold, rules.KNOWN_THRESHOLD)

    def test_reject_inexact_session_size(self):
        for size in (6, 12, 24, 30):
            with self.assertRaisesRegex(ValueError, 'lab_session_size'):
                create_session('dev_lab_endogenous_18', num_participants=size)
            db.rollback()

    def test_branch_and_standalone_contract(self):
        for change, message in [({'branch': 'M'}, 'branch E'),
                                ({'app_sequence': ['fixed', 'endogenous']}, 'standalone')]:
            session = make_session()
            session.config = {**session.config, **change}
            with self.assertRaisesRegex(ValueError, message):
                endogenous.validated_session(subsession(session))

    def test_block4_empty_history_canonical_install_and_creation_retry(self):
        for size in (18, 24):
            with patch('endogenous.select_matching', wraps=select_matching) as select:
                session = make_session(size)
                self.assertEqual(select.call_count, 1)
                self.assertEqual(select.call_args.args[2:], (4, {}))
            ss = subsession(session)
            people = [p.participant.code for p in ss.get_players()]
            matrix = select_matching(people, session.config['matching_seed'], 4, {})
            self.assertEqual(endogenous.stored_matrix(ss, 4), matrix)
            self.assertEqual(set(session.vars[endogenous.MATCHING_KEY]['matrices']), {'4'})
            for r in range(1, 11):
                self.assertEqual(endogenous._actual_matrix(subsession(session, r)), matrix)
            ids = [g.id for g in ss.get_groups()]
            endogenous.creating_session(ss)
            self.assertEqual(ids, [g.id for g in ss.get_groups()])
            self.assertFalse(subsession(session, 11).grouping_installed)

    def test_readiness_reports_and_six_submissions_required(self):
        session = make_session()
        group = subsession(session).get_groups()[0]
        p = group.get_players()[0]
        with self.assertRaisesRegex(ValueError, 'readiness'):
            endogenous.current_state(p)
        ready(session)
        p.retirement = 0
        with self.assertRaisesRegex(ValueError, 'Reports'):
            endogenous.Decision.before_next_page(p, False)
        reports(group)
        for p in group.get_players()[:5]:
            p.retirement = 1
            endogenous.Decision.before_next_page(p, False)
        with self.assertRaisesRegex(ValueError, 'six decisions'):
            endogenous.settle_period(group)
        self.assertFalse(group.settlement_complete)
        self.assertTrue(all(not p.period_settled and not p.wallet_after for p in group.get_players()))
        p = group.get_players()[5]
        p.retirement = 0
        endogenous.Decision.before_next_page(p, False)
        endogenous.settle_period(group)
        self.assertEqual(group.equipment_total, 595)
        self.assertEqual(decode_fraction(group.group_mean), Fraction(595, 6))
        self.assertEqual(decode_fraction(group.get_players()[0].voluntary_cost), Fraction(1, 10))
        self.assertFalse(subsession(session).get_groups()[1].settlement_complete)

    def test_main_below_threshold_mixed_zero_and_positive(self):
        group = self.main_group()
        equipment = [0, 20, 40, 60, 70, 49]
        run_period(group, [100 - k for k in equipment])
        self.assertEqual(group.equipment_total, 239)
        self.assertEqual(decode_fraction(group.group_mean), Fraction(239, 6))
        self.assertTrue(group.main_enforcement_applied)
        for p, k in zip(group.get_players(), equipment):
            self.assertTrue(p.main_enforcement_applied)
            self.assertEqual(p.applied_main_threshold, 40)
            self.assertEqual(decode_fraction(p.main_fine), rules.main_fine(k))
            self.assertEqual(decode_fraction(p.wallet_after), 1000 - rules.retirement_cost(100 - k) - rules.main_fine(k))

    def test_main_exact_equality_is_enforcement(self):
        group = self.main_group()
        run_period(group, [60] * 6)
        self.assertEqual(group.equipment_total, 240)
        self.assertEqual(decode_fraction(group.group_mean), 40)
        self.assertTrue(group.main_enforcement_applied)
        self.assertTrue(all(p.main_enforcement_applied and decode_fraction(p.main_fine) == Fraction('195')
                            for p in group.get_players()))

    def test_main_above_threshold_no_fines_for_anyone(self):
        group = self.main_group()
        run_period(group, [100, 80, 60, 40, 30, 49])  # total 241
        self.assertEqual(group.equipment_total, 241)
        self.assertFalse(group.main_enforcement_applied)
        self.assertTrue(all(not p.main_enforcement_applied and decode_fraction(p.main_fine) == 0
                            for p in group.get_players()))

    def test_pivotal_sixth_participant_included_once(self):
        for own in (0, 1, 2):
            group = self.main_group()
            equipment = [100, 100, 39, 0, 0, own]
            run_period(group, [100 - k for k in equipment])
            self.assertEqual(group.equipment_total, 239 + own)
            self.assertEqual(decode_fraction(group.group_mean), Fraction(239 + own, 6))
            self.assertEqual(group.main_enforcement_applied, own <= 1)

    def test_main_cannot_settle_or_decide_enforcement_before_sixth_choice(self):
        group = self.main_group()
        for p in group.get_players()[:5]:
            p.retirement = 60
            endogenous.Decision.before_next_page(p, False)
        with self.assertRaisesRegex(ValueError, 'six decisions'):
            endogenous.settle_period(group)
        self.assertIsNone(group.field_maybe_none('main_enforcement_applied'))
        self.assertTrue(all(not p.main_fine for p in group.get_players()))
        p = group.get_players()[5]
        p.retirement = 60
        endogenous.Decision.before_next_page(p, False)
        endogenous.settle_period(group)
        self.assertTrue(group.main_enforcement_applied)

    def test_main_retry_and_reload_exactly_once_and_tamper_detection(self):
        group = self.main_group()
        run_period(group, [60] * 6)
        record = group.settlement_record
        wallets = [p.wallet_after for p in group.get_players()]
        endogenous.settle_period(group)
        self.assertEqual(record, group.settlement_record)
        self.assertEqual(wallets, [p.wallet_after for p in group.get_players()])
        p = group.get_players()[0]
        context = endogenous.Result.vars_for_template(p)
        db.commit()
        db.expire_all()
        self.assertEqual(context, endogenous.Result.vars_for_template(p))
        endogenous.settle_period(group)
        self.assertEqual(record, group.settlement_record)
        group.main_enforcement_applied = False
        with self.assertRaisesRegex(ValueError, 'Inconsistent replay'):
            endogenous.settle_period(group)

    def test_ordinary_retry_with_no_main_event(self):
        session = make_session()
        ready(session)
        group = subsession(session).get_groups()[0]
        run_period(group, [1] * 6)
        before = group.settlement_record
        endogenous.settle_period(group)
        self.assertEqual(before, group.settlement_record)
        self.assertIsNone(group.field_maybe_none('main_enforcement_applied'))

    def test_follow_up_independent_of_threshold_negative_wallet(self):
        session = make_session()
        ready(session)
        for r in range(1, 11):
            run_period(subsession(session, r).get_groups()[0])
        group = subsession(session, 10).get_groups()[0]
        for p in group.get_players():
            self.assertEqual((p.voluntary_equipment_after, p.forced_retirement, p.final_equipment), (100, 100, 0))
            self.assertEqual(decode_fraction(p.follow_up_fine), 75)
            self.assertEqual(decode_fraction(p.forced_retirement_cost), 1000)
            self.assertEqual(decode_fraction(p.final_block_wallet), -75)
            self.assertIsNone(p.field_maybe_none('main_enforcement_applied'))
        record = group.settlement_record
        endogenous.settle_period(group)
        self.assertEqual(record, group.settlement_record)

    def test_zero_participants_keep_submitting_and_synchronizing(self):
        session = make_session()
        ready(session)
        for r in range(1, 11):
            group = subsession(session, r).get_groups()[0]
            run_period(group, [100, 0, 0, 0, 0, 0] if r == 1 else None)
            p = group.get_players()[0]
            self.assertTrue(p.decision_submitted and p.period_settled)
            self.assertEqual(p.final_equipment, 0)
        self.assertEqual(decode_fraction(p.follow_up_fine), 0)
        self.assertEqual(decode_fraction(p.forced_retirement_cost), 0)
        self.assertEqual(decode_fraction(p.final_block_wallet), 0)

    def test_rematch_history_4_then_45_no_F_history_and_only_future_rows(self):
        for size in (18, 24):
            session = make_session(size)
            ready(session)
            ss = subsession(session)
            # An unrelated F key must not be read or validated by E.
            session.vars['lab_fixed_matching_v1'] = {'intentionally': 'not E history'}
            ids = {r: [g.id for g in subsession(session, r).get_groups()] for r in range(1, 11)}
            with patch('endogenous.select_matching', wraps=select_matching) as select:
                finish_block(session, 1)
                self.assertEqual(select.call_args.args[2], 5)
                self.assertEqual(set(select.call_args.args[3]), {4})
                calls = select.call_count
                endogenous.complete_block(subsession(session, 10))
                self.assertEqual(select.call_count, calls)
                finish_block(session, 2)
                self.assertEqual(select.call_args.args[2], 6)
                self.assertEqual(set(select.call_args.args[3]), {4, 5})
                finish_block(session, 3)
                self.assertEqual(select.call_count, 2)
            self.assertEqual(set(session.vars[endogenous.MATCHING_KEY]['matrices']), {'4', '5', '6'})
            self.assertTrue(subsession(session, 30).block_barrier_complete)
            for r, group_ids in ids.items():
                self.assertEqual(group_ids, [g.id for g in subsession(session, r).get_groups()])
            for local, block in enumerate((4, 5, 6), 1):
                matrix = endogenous.stored_matrix(ss, block)
                for r in range((local - 1) * 10 + 1, local * 10 + 1):
                    self.assertEqual(endogenous._actual_matrix(subsession(session, r)), matrix)
                for p in subsession(session, (local - 1) * 10 + 1).get_players():
                    self.assertEqual((p.start_equipment, decode_fraction(p.wallet_before)), (100, 1000))

    def test_missing_section_history_and_unsafe_regrouping_rejected(self):
        session = make_session()
        source = subsession(session, 10)
        with self.assertRaisesRegex(ValueError, 'barrier'):
            endogenous._install_block(source, 5)
        source.block_barrier_complete = True
        destination = subsession(session, 20).get_players()[0]
        destination.retirement = 0
        with self.assertRaisesRegex(ValueError, 'used destination'):
            endogenous._install_block(source, 5)
        self.assertFalse(subsession(session, 11).grouping_installed)
        self.assertEqual(set(session.vars[endogenous.MATCHING_KEY]['matrices']), {'4'})
        destination.retirement = None
        state = session.vars[endogenous.MATCHING_KEY]
        session.vars[endogenous.MATCHING_KEY] = {**state, 'matrices': {}}
        with self.assertRaises(KeyError):
            endogenous._install_block(source, 5)

    def test_genuine_waitpages_and_no_legacy_dependencies(self):
        self.assertEqual((endogenous.C.NUM_ROUNDS, endogenous.C.PLAYERS_PER_GROUP), (30, 6))
        for page in (endogenous.SessionReady, endogenous.ReportsWait, endogenous.PeriodWait, endogenous.BlockEndWait):
            self.assertTrue(issubclass(page, WaitPage))
        self.assertTrue(endogenous.SessionReady.wait_for_all_groups)
        self.assertTrue(endogenous.BlockEndWait.wait_for_all_groups)
        self.assertFalse(endogenous.PeriodWait.wait_for_all_groups)
        tree = ast.parse(Path(endogenous.__file__).read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and (name.startswith('stage_game_') or name == 'simulated_environment' or name == 'fixed') for name in imports))
        self.assertFalse(hasattr(endogenous, 'DecisionWait'))


class EndogenousHTTPBarrierTests(unittest.TestCase):
    """Drive actual oTree HTTP/WaitPage machinery, with one group far ahead."""

    def test_initial_session_report_period_and_block_barriers(self):
        session = make_session()
        ss = subsession(session)
        bots = make_bots(session_pk=session.id, case_number=0, use_browser_bots=False)
        db.commit()
        by_code = {bot.participant_code: bot for bot in bots}
        for bot in bots:
            bot.open_start_url()
            self.assertFalse(bot.on_wait_page())  # administrator-controlled splash
        for bot in bots[:-1]:
            bot.submit(bot.get_next_submit())  # authenticated admin advancement
            self.assertTrue(bot.on_wait_page())
        self.assertFalse(ss.readiness_complete)
        bots[-1].submit(bots[-1].get_next_submit())
        db.expire_all()  # requests use independent ORM sessions/identity maps
        self.assertTrue(ss.readiness_complete)

        def submit(bot):
            self.assertFalse(bot.on_wait_page())
            db.expire_all()
            bot.submit(bot.get_next_submit())
            db.expire_all()

        # Complete the quiz retry/correct flow before testing partial report barriers.
        for bot in bots:
            for _ in range(4):
                submit(bot)  # rejected/correct submissions for each server pair

        for bot in bots:
            submit(bot)  # admin releases first block; all-session start barrier

        groups = [[by_code[p.participant.code] for p in g.get_players()] for g in ss.get_groups()]
        first_group = ss.get_groups()[0]
        for bot in groups[0][:-1]:
            submit(bot)  # invalid report attempt
            submit(bot)  # valid reports -> group wait
            self.assertTrue(bot.on_wait_page())
        self.assertFalse(first_group.reports_complete)
        for _ in range(2):
            submit(groups[0][-1])
        self.assertTrue(first_group.reports_complete)
        for bot in groups[0][:-1]:
            submit(bot)  # Decision, no settlement yet
        self.assertFalse(first_group.settlement_complete)
        submit(groups[0][-1])
        self.assertTrue(first_group.settlement_complete)
        self.assertFalse(ss.get_groups()[1].settlement_complete)
        for bot in groups[0]:
            submit(bot)  # Result period 1

        def finish_remaining_periods(group_bots, start):
            for period in range(start, 11):
                for bot in group_bots:
                    submit(bot)  # Decision
                for bot in group_bots:
                    submit(bot)  # Result

        finish_remaining_periods(groups[0], 2)
        self.assertTrue(groups[0][0].on_wait_page())
        self.assertFalse(subsession(session, 10).block_barrier_complete)
        self.assertFalse(subsession(session, 11).grouping_installed)
        for group_bots in groups[1:]:
            for bot in group_bots:
                for _ in range(2):
                    submit(bot)  # invalid Reports, valid Reports
            finish_remaining_periods(group_bots, 1)
        self.assertTrue(subsession(session, 10).block_barrier_complete)
        self.assertTrue(subsession(session, 11).grouping_installed)
        self.assertFalse(groups[0][0].on_wait_page())
        next_player = next(p for p in subsession(session, 11).get_players()
                           if p.participant.code == groups[0][0].participant_code)
        self.assertEqual(next_player.period, 1)
