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
import messages


def make_session(size=18):
    return create_session(f'dev_lab_messages_{size}', num_participants=size)


def subsession(session, round_number=1):
    return messages.Subsession.objects_get(session=session, round_number=round_number)


def ready(session):
    messages.SessionReady.after_all_players_arrive(subsession(session))


def reports(group, own=None, private=None):
    for p, first, second in zip(group.get_players(), [50] * 6 if own is None else own, [50] * 6 if private is None else private):
        p.expected_own_equipment_main = first
        p.expected_group_average_main = second
        messages.Reports.before_next_page(p, False)
    messages.ReportsWait.after_all_players_arrive(group)


def decide(group, amounts=None):
    for p, amount in zip(group.get_players(), [0] * 6 if amounts is None else amounts):
        p.retirement = amount
        messages.Decision.before_next_page(p, False)


def run_period(group, amounts=None):
    if group.period == 1:
        reports(group)
    decide(group, amounts)
    messages.PeriodWait.after_all_players_arrive(group)


def finish_block(session, local_block):
    first = (local_block - 1) * 10 + 1
    for r in range(first, first + 10):
        for group in subsession(session, r).get_groups():
            run_period(group)
    end = subsession(session, first + 9)
    for p in end.get_players():
        messages.BlockEnd.before_next_page(p, False)
    messages.BlockEndWait.after_all_players_arrive(end)


class MessagesBackendTests(unittest.TestCase):
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
                create_session('dev_lab_messages_18', num_participants=size)
            db.rollback()

    def test_branch_and_standalone_contract(self):
        for change, message in [({'branch': 'E'}, 'branch M'),
                                ({'app_sequence': ['fixed', 'messages']}, 'standalone')]:
            session = make_session()
            session.config = {**session.config, **change}
            with self.assertRaisesRegex(ValueError, message):
                messages.validated_session(subsession(session))

    def test_block4_empty_history_canonical_install_and_creation_retry(self):
        for size in (18, 24):
            with patch('messages.select_matching', wraps=select_matching) as select:
                session = make_session(size)
                self.assertEqual(select.call_count, 1)
                self.assertEqual(select.call_args.args[2:], (4, {}))
            ss = subsession(session)
            people = [p.participant.code for p in ss.get_players()]
            matrix = select_matching(people, session.config['matching_seed'], 4, {})
            self.assertEqual(messages.stored_matrix(ss, 4), matrix)
            self.assertEqual(set(session.vars[messages.MATCHING_KEY]['matrices']), {'4'})
            for r in range(1, 11):
                self.assertEqual(messages._actual_matrix(subsession(session, r)), matrix)
            ids = [g.id for g in ss.get_groups()]
            messages.creating_session(ss)
            self.assertEqual(ids, [g.id for g in ss.get_groups()])
            self.assertFalse(subsession(session, 11).grouping_installed)

    def test_readiness_reports_and_six_submissions_required(self):
        session = make_session()
        group = subsession(session).get_groups()[0]
        p = group.get_players()[0]
        with self.assertRaisesRegex(ValueError, 'readiness'):
            messages.current_state(p)
        ready(session)
        p.retirement = 0
        with self.assertRaisesRegex(ValueError, 'report barrier'):
            messages.Decision.before_next_page(p, False)
        reports(group)
        for p in group.get_players()[:5]:
            p.retirement = 1
            messages.Decision.before_next_page(p, False)
        with self.assertRaisesRegex(ValueError, 'six decisions'):
            messages.settle_period(group)
        self.assertFalse(group.settlement_complete)
        self.assertTrue(all(not p.period_settled and not p.wallet_after for p in group.get_players()))
        p = group.get_players()[5]
        p.retirement = 0
        messages.Decision.before_next_page(p, False)
        messages.settle_period(group)
        self.assertEqual(group.equipment_total, 595)
        self.assertEqual(decode_fraction(group.group_mean), Fraction(595, 6))
        self.assertEqual(decode_fraction(group.get_players()[0].voluntary_cost), Fraction(1, 10))
        self.assertFalse(subsession(session).get_groups()[1].settlement_complete)

    def test_main_below_threshold_mixed_zero_and_positive(self):
        group = self.main_group()
        equipment = [0, 20, 40, 60, 70, 31]
        run_period(group, [100 - k for k in equipment])
        self.assertEqual(group.equipment_total, 221)
        self.assertEqual(decode_fraction(group.group_mean), Fraction(221, 6))
        self.assertTrue(group.main_enforcement_applied)
        for p, k in zip(group.get_players(), equipment):
            self.assertTrue(p.main_enforcement_applied)
            self.assertEqual(p.applied_main_threshold, 37)
            self.assertEqual(decode_fraction(p.main_fine), rules.main_fine(k))
            self.assertEqual(decode_fraction(p.wallet_after), 1000 - rules.retirement_cost(100 - k) - rules.main_fine(k))

    def test_main_exact_equality_is_enforcement(self):
        group = self.main_group()
        run_period(group, [63] * 6)
        self.assertEqual(group.equipment_total, 222)
        self.assertEqual(decode_fraction(group.group_mean), 37)
        self.assertTrue(group.main_enforcement_applied)
        self.assertTrue(all(p.main_enforcement_applied and decode_fraction(p.main_fine) == Fraction('193.5')
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
            equipment = [100, 100, 21, 0, 0, own]
            run_period(group, [100 - k for k in equipment])
            self.assertEqual(group.equipment_total, 221 + own)
            self.assertEqual(decode_fraction(group.group_mean), Fraction(221 + own, 6))
            self.assertEqual(group.main_enforcement_applied, own <= 1)

    def test_main_cannot_settle_or_decide_enforcement_before_sixth_choice(self):
        group = self.main_group()
        for p in group.get_players()[:5]:
            p.retirement = 63
            messages.Decision.before_next_page(p, False)
        with self.assertRaisesRegex(ValueError, 'six decisions'):
            messages.settle_period(group)
        self.assertIsNone(group.field_maybe_none('main_enforcement_applied'))
        self.assertTrue(all(not p.main_fine for p in group.get_players()))
        p = group.get_players()[5]
        p.retirement = 63
        messages.Decision.before_next_page(p, False)
        messages.settle_period(group)
        self.assertTrue(group.main_enforcement_applied)

    def test_main_retry_and_reload_exactly_once_and_tamper_detection(self):
        group = self.main_group()
        run_period(group, [63] * 6)
        record = group.settlement_record
        wallets = [p.wallet_after for p in group.get_players()]
        messages.settle_period(group)
        self.assertEqual(record, group.settlement_record)
        self.assertEqual(wallets, [p.wallet_after for p in group.get_players()])
        p = group.get_players()[0]
        context = messages.Result.vars_for_template(p)
        db.commit()
        db.expire_all()
        self.assertEqual(context, messages.Result.vars_for_template(p))
        messages.settle_period(group)
        self.assertEqual(record, group.settlement_record)
        group.main_enforcement_applied = False
        with self.assertRaisesRegex(ValueError, 'Inconsistent replay'):
            messages.settle_period(group)

    def test_ordinary_retry_with_no_main_event(self):
        session = make_session()
        ready(session)
        group = subsession(session).get_groups()[0]
        run_period(group, [1] * 6)
        before = group.settlement_record
        messages.settle_period(group)
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
        messages.settle_period(group)
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
            with patch('messages.select_matching', wraps=select_matching) as select:
                finish_block(session, 1)
                self.assertEqual(select.call_args.args[2], 5)
                self.assertEqual(set(select.call_args.args[3]), {4})
                calls = select.call_count
                messages.complete_block(subsession(session, 10))
                self.assertEqual(select.call_count, calls)
                finish_block(session, 2)
                self.assertEqual(select.call_args.args[2], 6)
                self.assertEqual(set(select.call_args.args[3]), {4, 5})
                finish_block(session, 3)
                self.assertEqual(select.call_count, 2)
            self.assertEqual(set(session.vars[messages.MATCHING_KEY]['matrices']), {'4', '5', '6'})
            self.assertTrue(subsession(session, 30).block_barrier_complete)
            for r, group_ids in ids.items():
                self.assertEqual(group_ids, [g.id for g in subsession(session, r).get_groups()])
            for local, block in enumerate((4, 5, 6), 1):
                matrix = messages.stored_matrix(ss, block)
                for r in range((local - 1) * 10 + 1, local * 10 + 1):
                    self.assertEqual(messages._actual_matrix(subsession(session, r)), matrix)
                for p in subsession(session, (local - 1) * 10 + 1).get_players():
                    self.assertEqual((p.start_equipment, decode_fraction(p.wallet_before)), (100, 1000))

    def test_missing_section_history_and_unsafe_regrouping_rejected(self):
        session = make_session()
        source = subsession(session, 10)
        with self.assertRaisesRegex(ValueError, 'barrier'):
            messages._install_block(source, 5)
        source.block_barrier_complete = True
        destination = subsession(session, 20).get_players()[0]
        destination.retirement = 0
        with self.assertRaisesRegex(ValueError, 'used destination'):
            messages._install_block(source, 5)
        self.assertFalse(subsession(session, 11).grouping_installed)
        self.assertEqual(set(session.vars[messages.MATCHING_KEY]['matrices']), {'4'})
        destination.retirement = None
        state = session.vars[messages.MATCHING_KEY]
        session.vars[messages.MATCHING_KEY] = {**state, 'matrices': {}}
        with self.assertRaises(KeyError):
            messages._install_block(source, 5)

    def test_genuine_waitpages_and_no_legacy_dependencies(self):
        self.assertEqual((messages.C.NUM_ROUNDS, messages.C.PLAYERS_PER_GROUP), (30, 6))
        for page in (messages.SessionReady, messages.ReportsWait, messages.PeriodWait, messages.BlockEndWait):
            self.assertTrue(issubclass(page, WaitPage))
        self.assertTrue(messages.SessionReady.wait_for_all_groups)
        self.assertTrue(messages.BlockEndWait.wait_for_all_groups)
        self.assertFalse(messages.PeriodWait.wait_for_all_groups)
        tree = ast.parse(Path(messages.__file__).read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and (name.startswith('stage_game_') or name == 'simulated_environment' or name == 'fixed') for name in imports))
        self.assertFalse(hasattr(messages, 'DecisionWait'))


class MessagesHTTPBarrierTests(unittest.TestCase):
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
        self.assertFalse(first_group.public_report_complete)
        self.assertEqual(first_group.public_report_mean, '')
        for _ in range(2):
            submit(groups[0][-1])
        self.assertTrue(first_group.reports_complete)
        self.assertTrue(first_group.public_report_complete)
        self.assertEqual(decode_fraction(first_group.public_report_mean), Fraction(5,2))
        for bot in groups[0]:
            self.assertFalse(bot.on_wait_page())
            self.assertIn('"publicReportMean":2.5', bot.html)
            self.assertNotIn('id="public-report-mean"', bot.html)
            for peer in first_group.get_players():
                if peer.participant.code != bot.participant_code:
                    self.assertNotIn(peer.participant.code, bot.html)
        for bot in groups[0][:-1]:
            submit(bot)  # Decision, no settlement yet
        self.assertFalse(first_group.settlement_complete)
        self.assertNotIn('id="public-report-mean"', groups[0][0].html)
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

class PublicReportTests(unittest.TestCase):
    def tearDown(self):
        db.rollback()

    def group(self):
        session = make_session()
        ready(session)
        return subsession(session).get_groups()[0]

    def test_exact_aggregation_and_report2_exclusion(self):
        for own, expected in [([40]*6, Fraction(40)), ([0]*5+[1], Fraction(1,6)),
                              ([1,11,27,44,68,99], Fraction(125,3))]:
            for private in ([0]*6, [100]*6):
                group = self.group()
                reports(group, own, private)
                self.assertEqual(decode_fraction(group.public_report_mean), expected)
                self.assertEqual(group.public_report_total, sum(own))
                self.assertEqual(messages.public_reports.read(group.get_players()[0]), expected)
        self.assertEqual(group.public_report_mean, '125/3')

    def test_five_reports_and_sixth_submission_do_not_publish_before_callback(self):
        group = self.group()
        players = group.get_players()
        for p in players[:5]:
            p.expected_own_equipment_main = 0
            p.expected_group_average_main = 100
            messages.Reports.before_next_page(p, False)
        with self.assertRaisesRegex(ValueError, 'six'):
            messages.complete_reports(group)
        self.assertFalse(group.public_report_complete or group.reports_complete)
        self.assertEqual(group.public_report_mean, '')
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            messages.presentation.public_context(players[0])
        p = players[-1]
        p.expected_own_equipment_main = 1
        p.expected_group_average_main = 100
        messages.Reports.before_next_page(p, False)
        self.assertFalse(group.public_report_complete)
        messages.ReportsWait.after_all_players_arrive(group)
        self.assertTrue(group.public_report_complete)
        self.assertTrue(all(messages.public_reports.read(p) == Fraction(1,6) for p in players))

    def test_lock_retry_and_read_only_reload(self):
        group = self.group()
        reports(group, [0]*5+[1])
        p = group.get_players()[0]
        record = group.public_report_record
        messages.complete_reports(group)
        before = messages.Decision.vars_for_template(p)
        db.commit()
        db.expire_all()
        self.assertEqual(messages.Decision.vars_for_template(p), before)
        self.assertEqual(group.public_report_record, record)
        p.expected_own_equipment_main = 99
        with self.assertRaisesRegex(ValueError, 'locked'):
            messages.Reports.before_next_page(p, False)
        self.assertEqual(messages.public_reports.read(p), Fraction(1,6))
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            messages.complete_reports(group)

    def test_message_has_no_economic_effect(self):
        results = []
        for message in (0,100):
            group = self.group()
            reports(group, [message]*6, [100-message]*6)
            session = group.session
            for r in range(1,6):
                row = subsession(session,r).get_groups()[0]
                decide(row, [63]*6 if r==5 else None)
                messages.settle_period(row)
            results.append((row.equipment_total, row.main_enforcement_applied,
                            [(p.main_fine,p.wallet_after) for p in row.get_players()]))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0:2], (222,True))

    def test_current_rematched_group_owns_new_block_message(self):
        session = make_session()
        ready(session)
        for local in (1,2,3):
            first = (local-1)*10+1
            ss = subsession(session,first)
            for group in ss.get_groups():
                for p in group.get_players():
                    with self.assertRaisesRegex(ValueError, 'unavailable'):
                        messages.public_reports.read(p)
                values = [local*10 + p.participant.id_in_session for p in group.get_players()]
                reports(group, values, [100]*6)
                expected = Fraction(sum(values),6)
                for r in range(first,first+10):
                    # Same group within this block; lookup is through persistent participant.
                    p = group.get_players()[0].in_round(r)
                    self.assertEqual(messages.public_reports.read(p), expected)
            for r in range(first,first+10):
                for group in subsession(session,r).get_groups():
                    decide(group)
                    messages.settle_period(group)
            end = subsession(session,first+9)
            for p in end.get_players():
                messages.BlockEnd.before_next_page(p,False)
            messages.complete_block(end)
        self.assertEqual(set(session.vars[messages.MATCHING_KEY]['matrices']), {'4','5','6'})
