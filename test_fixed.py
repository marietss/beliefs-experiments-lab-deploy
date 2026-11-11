"""Real oTree ORM/callback/HTTP tests. Run in a disposable project directory.

oTree initializes a database on import/setup. Use an isolated copy (including
fixed and pure helpers) to keep runtime databases outside the working project.
"""

import ast
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

from otree.main import setup
setup()

from otree.api import WaitPage
from otree.database import db
from otree.session import create_session
from otree.bots.runner import make_bots
from lab_matching import select_matching
from lab_persistence import decode_fraction, encode_fraction
import fixed


def make_session(size=18):
    return create_session(f'dev_lab_fixed_{size}', num_participants=size)


def subsession(session, round_number=1):
    return fixed.Subsession.objects_get(session=session, round_number=round_number)


def ready(session):
    fixed.SessionReady.after_all_players_arrive(subsession(session))


def reports(group):
    for p in group.get_players():
        p.expected_own_equipment_main = 50
        p.expected_group_average_main = 50
        fixed.Reports.before_next_page(p, False)
    fixed.ReportsWait.after_all_players_arrive(group)


def decide(group, amounts=None):
    amounts = amounts or [0] * 6
    for p, amount in zip(group.get_players(), amounts):
        p.retirement = amount
        fixed.Decision.before_next_page(p, False)


def run_period(group, amounts=None):
    if group.period == 1:
        reports(group)
    decide(group, amounts)
    fixed.PeriodWait.after_all_players_arrive(group)


def finish_block(session, block):
    start = (block - 1) * 10 + 1
    for r in range(start, start + 10):
        for group in subsession(session, r).get_groups():
            run_period(group)
    end = subsession(session, start + 9)
    for p in end.get_players():
        fixed.BlockEnd.before_next_page(p, False)
    fixed.BlockEndWait.after_all_players_arrive(end)


class FixedBackendTests(unittest.TestCase):
    def tearDown(self):
        db.rollback()

    def test_exact_18_24_counts_and_mapping_at_creation(self):
        for size in (18, 24):
            with self.subTest(size=size):
                session = make_session(size)
                for r in range(1, 31):
                    ss = subsession(session, r)
                    self.assertEqual(len(ss.get_players()), size)
                    self.assertEqual(len(ss.get_groups()), size // 6)
                    for p in ss.get_players():
                        self.assertEqual((p.global_block, p.local_block, p.period),
                                         ((r - 1) // 10 + 1, (r - 1) // 10 + 1, (r - 1) % 10 + 1))
                self.assertEqual(set(session.vars[fixed.MATCHING_KEY]['matrices']), {'1'})

    def test_reject_count_even_if_divisible_by_six(self):
        for size in (6, 12, 24, 30):
            with self.subTest(size=size):
                with self.assertRaisesRegex(ValueError, 'lab_session_size'):
                    create_session('dev_lab_fixed_18', num_participants=size)
                db.rollback()

    def test_first_matrix_seeded_and_identical_for_all_ten_rounds(self):
        for size in (18, 24):
            session = make_session(size)
            ss = subsession(session)
            people = [p.participant.code for p in ss.get_players()]
            expected = select_matching(people, session.config['matching_seed'], 1, {})
            self.assertEqual(fixed.stored_matrix(ss, 1), expected)
            for r in range(1, 11):
                self.assertTrue(subsession(session, r).grouping_installed)
                self.assertEqual(fixed._actual_matrix(subsession(session, r)), expected)
            self.assertFalse(subsession(session, 11).grouping_installed)
            # Initialization replay must preserve Group primary keys.
            ids = [g.id for g in ss.get_groups()]
            fixed.creating_session(ss)
            self.assertEqual(ids, [g.id for g in ss.get_groups()])

    def test_creation_matching_configuration_cannot_change(self):
        session = make_session()
        ss = subsession(session)
        session.config = {**session.config, 'matching_seed': 'changed'}
        with self.assertRaisesRegex(ValueError, 'configuration changed'):
            fixed.stored_matrix(ss, 1)

    def test_readiness_and_reports_are_required_before_decisions(self):
        session = make_session()
        p = subsession(session).get_players()[0]
        with self.assertRaisesRegex(ValueError, 'readiness'):
            fixed.current_state(p)
        ready(session)
        p.retirement = 0
        with self.assertRaisesRegex(ValueError, 'Reports'):
            fixed.Decision.before_next_page(p, False)
        p.expected_own_equipment_main = p.expected_group_average_main = 50
        fixed.Reports.before_next_page(p, False)
        with self.assertRaisesRegex(ValueError, 'six'):
            fixed.complete_reports(p.group)

    def test_six_locked_decisions_before_any_settlement(self):
        session = make_session()
        ready(session)
        group = subsession(session).get_groups()[0]
        reports(group)
        players = group.get_players()
        for p in players[:5]:
            p.retirement = 1
            fixed.Decision.before_next_page(p, False)
        with self.assertRaisesRegex(ValueError, 'six decisions'):
            fixed.settle_period(group)
        self.assertFalse(group.settlement_complete)
        self.assertTrue(all(not p.period_settled and p.wallet_after == '' for p in players))
        players[5].retirement = 0
        fixed.Decision.before_next_page(players[5], False)
        fixed.settle_period(group)
        self.assertEqual(group.equipment_total, 595)
        self.assertEqual(decode_fraction(group.group_mean), Fraction(595, 6))
        self.assertEqual(decode_fraction(players[0].voluntary_cost), Fraction(1, 10))
        self.assertEqual(decode_fraction(players[0].wallet_after), Fraction('999.9'))
        self.assertFalse(subsession(session).get_groups()[1].settlement_complete)

    def test_main_zero_exemption_and_positive_fine_at_high_group_mean(self):
        session = make_session()
        ready(session)
        for r in range(1, 5):
            run_period(subsession(session, r).get_groups()[0])
        group = subsession(session, 5).get_groups()[0]
        decide(group, [100, 50, 1, 0, 0, 0])
        fixed.settle_period(group)
        self.assertGreater(decode_fraction(group.group_mean), 45)
        expected = [0, 200, Fraction('224.5'), 225, 225, 225]
        for p, fine in zip(group.get_players(), expected):
            self.assertEqual(decode_fraction(p.main_fine), fine)
        self.assertEqual(group.equipment_total, 449)

    def test_main_all_positive_and_low_group_mean(self):
        session = make_session()
        ready(session)
        for r in range(1, 5):
            run_period(subsession(session, r).get_groups()[0])
        group = subsession(session, 5).get_groups()[0]
        run_period(group, [99] * 6)
        self.assertEqual(decode_fraction(group.group_mean), 1)
        self.assertTrue(all(decode_fraction(p.main_fine) == Fraction('175.5')
                            for p in group.get_players()))

    def test_follow_up_negative_wallet_and_separate_pre_forced_state(self):
        session = make_session()
        ready(session)
        for r in range(1, 11):
            run_period(subsession(session, r).get_groups()[0])
        group = subsession(session, 10).get_groups()[0]
        self.assertEqual(group.equipment_total, 600)
        self.assertEqual(group.final_equipment_total, 0)
        for p in group.get_players():
            self.assertEqual(p.voluntary_equipment_after, 100)
            self.assertEqual(p.forced_retirement, 100)
            self.assertEqual(p.final_equipment, 0)
            self.assertEqual(decode_fraction(p.follow_up_fine), 75)
            self.assertEqual(decode_fraction(p.forced_retirement_cost), 1000)
            self.assertEqual(decode_fraction(p.final_block_wallet), -300)

    def test_zero_equipment_keeps_deciding_and_synchronizing(self):
        session = make_session()
        ready(session)
        for r in range(1, 11):
            group = subsession(session, r).get_groups()[0]
            run_period(group, [100] * 6 if r == 1 else [0] * 6)
            self.assertTrue(all(p.decision_submitted and p.period_settled for p in group.get_players()))
            self.assertEqual(group.final_equipment_total, 0)
        for p in group.get_players():
            self.assertEqual(decode_fraction(p.main_fine), 0)
            self.assertEqual(decode_fraction(p.follow_up_fine), 0)
            self.assertEqual(decode_fraction(p.final_block_wallet), 0)

    def test_callback_retry_is_read_only_and_inconsistent_replay_rejected(self):
        session = make_session()
        ready(session)
        group = subsession(session).get_groups()[0]
        run_period(group, [1] * 6)
        record = group.settlement_record
        wallets = [p.wallet_after for p in group.get_players()]
        fixed.settle_period(group)
        self.assertEqual(group.settlement_record, record)
        self.assertEqual([p.wallet_after for p in group.get_players()], wallets)
        p = group.get_players()[0]
        p.wallet_after = encode_fraction(999)
        with self.assertRaisesRegex(ValueError, 'Inconsistent replay'):
            fixed.settle_period(group)

    def test_feedback_reload_does_not_mutate_state(self):
        session = make_session()
        ready(session)
        group = subsession(session).get_groups()[0]
        run_period(group)
        p = group.get_players()[0]
        record = group.settlement_record
        self.assertEqual(fixed.Result.vars_for_template(p), fixed.Result.vars_for_template(p))
        self.assertEqual(record, group.settlement_record)
        db.commit()
        pk = p.id
        db.expire_all()
        reloaded = fixed.Player.objects_get(id=pk)
        self.assertEqual(decode_fraction(reloaded.wallet_after), 1000)
        self.assertEqual(fixed.Result.vars_for_template(reloaded)['group_mean'], '100')

    def test_main_and_follow_up_retries_do_not_deduct_twice(self):
        session = make_session()
        ready(session)
        for r in range(1, 11):
            group = subsession(session, r).get_groups()[0]
            run_period(group)
            if r in (5, 10):
                record = group.settlement_record
                wallets = [p.wallet_after for p in group.get_players()]
                fixed.settle_period(group)
                self.assertEqual(group.settlement_record, record)
                self.assertEqual([p.wallet_after for p in group.get_players()], wallets)
                self.assertEqual(decode_fraction(wallets[0]), 775 if r == 5 else -300)

    def test_future_install_refuses_partial_or_used_destination(self):
        session = make_session()
        source = subsession(session, 10)
        with self.assertRaisesRegex(ValueError, 'barrier'):
            fixed._install_block(source, 2)
        source.block_barrier_complete = True
        destination = subsession(session, 20).get_players()[0]
        destination.retirement = 0
        ids = [g.id for g in subsession(session, 11).get_groups()]
        with self.assertRaisesRegex(ValueError, 'used destination'):
            fixed._install_block(source, 2)
        self.assertFalse(subsession(session, 11).grouping_installed)
        self.assertEqual(ids, [g.id for g in subsession(session, 11).get_groups()])
        self.assertEqual(set(session.vars[fixed.MATCHING_KEY]['matrices']), {'1'})

    def test_all_session_feedback_required_for_block_barrier(self):
        session = make_session()
        ready(session)
        end = subsession(session, 10)
        with self.assertRaisesRegex(ValueError, 'All session'):
            fixed.complete_block(end)
        self.assertFalse(end.block_barrier_complete)
        self.assertFalse(subsession(session, 11).grouping_installed)

    def test_rematching_history_stable_storage_only_future_rounds_and_no_fourth_block(self):
        for size in (18, 24):
            session = make_session(size)
            ready(session)
            original = {r: [g.id for g in subsession(session, r).get_groups()] for r in range(1, 11)}
            with patch('fixed.select_matching', wraps=select_matching) as select:
                finish_block(session, 1)
                self.assertEqual(set(select.call_args.args[3]), {1})
                first_call_count = select.call_count
                fixed.complete_block(subsession(session, 10))
                self.assertEqual(select.call_count, first_call_count)
                finish_block(session, 2)
                self.assertEqual(set(select.call_args.args[3]), {1, 2})
                finish_block(session, 3)
                self.assertEqual(select.call_count, 2)
            self.assertTrue(subsession(session, 30).block_barrier_complete)
            self.assertEqual(set(session.vars[fixed.MATCHING_KEY]['matrices']), {'1', '2', '3'})
            for r in range(1, 11):
                self.assertEqual(original[r], [g.id for g in subsession(session, r).get_groups()])
            for block in (1, 2, 3):
                expected = fixed.stored_matrix(subsession(session), block)
                for r in range((block - 1) * 10 + 1, block * 10 + 1):
                    self.assertEqual(fixed._actual_matrix(subsession(session, r)), expected)
            for r in (11, 21):
                for p in subsession(session, r).get_players():
                    self.assertEqual((p.start_equipment, decode_fraction(p.wallet_before)), (100, 1000))

    def test_genuine_waitpage_architecture_and_no_legacy_dependencies(self):
        self.assertEqual((fixed.C.PLAYERS_PER_GROUP, fixed.C.NUM_ROUNDS), (6, 30))
        for page in (fixed.SessionReady, fixed.ReportsWait, fixed.PeriodWait, fixed.BlockEndWait):
            self.assertTrue(issubclass(page, WaitPage))
        self.assertTrue(fixed.SessionReady.wait_for_all_groups)
        self.assertTrue(fixed.BlockEndWait.wait_for_all_groups)
        self.assertFalse(fixed.PeriodWait.wait_for_all_groups)
        tree = ast.parse(Path(fixed.__file__).read_text())
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertFalse(any(name and (name.startswith('stage_game_') or name == 'simulated_environment')
                             for name in imports))
        self.assertFalse(hasattr(fixed, 'DecisionWait'))


class FixedHTTPBarrierTests(unittest.TestCase):
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

        # Complete the economically inert practice before the paired comprehension flow.
        for bot in bots:
            submit(bot)  # practice timeout
            submit(bot)  # practice-completed Continue

        # Blank quiz retry -> correct printed quiz.
        for bot in bots:
            for _ in range(6):
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

        def finish_remaining_periods(group_bots, start, end=10):
            for period in range(start, end + 1):
                for bot in group_bots:
                    submit(bot)  # Decision
                for bot in group_bots:
                    submit(bot)  # Result

        finish_remaining_periods(groups[0], 2, 4)
        for bot in groups[0]: submit(bot)  # fast P5 decisions
        self.assertTrue(all(bot.on_wait_page() for bot in groups[0]))
        self.assertFalse(any(g.settlement_complete for g in subsession(session,5).get_groups()))
        for group_bots in groups[1:]:
            for bot in group_bots:
                for _ in range(2): submit(bot)  # invalid/valid Reports
            finish_remaining_periods(group_bots, 1, 4)
            for bot in group_bots: submit(bot)  # slow P5 decisions
        self.assertTrue(all(g.settlement_complete for g in subsession(session,5).get_groups()))
        for bot in groups[0]: submit(bot)  # P5 Result
        finish_remaining_periods(groups[0], 6)
        self.assertTrue(groups[0][0].on_wait_page())
        self.assertFalse(subsession(session, 10).block_barrier_complete)
        self.assertFalse(subsession(session, 11).grouping_installed)
        for group_bots in groups[1:]:
            for bot in group_bots: submit(bot)  # P5 Result
            finish_remaining_periods(group_bots, 6)
        self.assertTrue(subsession(session, 10).block_barrier_complete)
        self.assertTrue(subsession(session, 11).grouping_installed)
        self.assertFalse(groups[0][0].on_wait_page())
        next_player = next(p for p in subsession(session, 11).get_players()
                           if p.participant.code == groups[0][0].participant_code)
        self.assertEqual(next_player.period, 1)
