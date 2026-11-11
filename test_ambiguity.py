"""Actual six-human A ORM/callback/HTTP tests; disposable project only."""

from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

import test_fixed  # existing one-time oTree setup for combined lab tests
from otree.database import db
from otree.session import create_session
from otree.bots.runner import make_bots
from lab_matching import select_matching
from lab_persistence import decode_fraction
import lab_rules as rules
import ambiguity
import endogenous


MAP = {'4': 42, '5': 33, '6': 41, '7': 42, '8': 40, '9': 33}


def make_session(size=18, thresholds=None, **overrides):
    fields = dict(ambiguity_thresholds=dict(MAP if thresholds is None else thresholds), **overrides)
    return create_session(f'dev_lab_ambiguity_{size}', num_participants=size,
                          modified_session_config_fields=fields)


def subsession(session, round_number=1):
    return ambiguity.Subsession.objects_get(session=session, round_number=round_number)


def ready(session):
    ambiguity.SessionReady.after_all_players_arrive(subsession(session))


def reports(group):
    for p in group.get_players():
        p.expected_own_equipment_main = p.expected_group_average_main = 50
        ambiguity.Reports.before_next_page(p, False)
    ambiguity.ReportsWait.after_all_players_arrive(group)


def decide(group, amounts=None):
    for p, d in zip(group.get_players(), [0] * 6 if amounts is None else amounts):
        p.retirement = d
        ambiguity.Decision.before_next_page(p, False)


def run_period(group, amounts=None):
    if group.period == 1:
        reports(group)
    decide(group, amounts)
    ambiguity.PeriodWait.after_all_players_arrive(group)


def finish_block(session, local_block, main_equipment=None):
    first = (local_block - 1) * 10 + 1
    for r in range(first, first + 10):
        for group in subsession(session, r).get_groups():
            run_period(group, [100 - main_equipment] * 6 if r == first and main_equipment is not None else None)
    end = subsession(session, first + 9)
    for p in end.get_players():
        ambiguity.BlockEnd.before_next_page(p, False)
    ambiguity.BlockEndWait.after_all_players_arrive(end)


class AmbiguityBackendTests(unittest.TestCase):
    def tearDown(self):
        db.rollback()

    def main_group(self, k=42):
        session = make_session(thresholds={**MAP, '4': k})
        ready(session)
        for r in range(1, 5):
            run_period(subsession(session, r).get_groups()[0])
        return subsession(session, 5).get_groups()[0]

    def test_exact_counts_rounds_global_mapping_and_common_external_thresholds(self):
        for size in (18, 24):
            session = make_session(size)
            for r in range(1, 31):
                ss = subsession(session, r)
                self.assertEqual(len(ss.get_players()), size)
                self.assertEqual(len(ss.get_groups()), size // 6)
                for p in ss.get_players():
                    self.assertEqual((p.global_block, p.local_block, p.period),
                                     (rules.global_block_for_round(r, 'Z'), (r - 1) // 10 + 1, (r - 1) % 10 + 1))
                    self.assertEqual(p.group.threshold, MAP[str(p.global_block)])

    def test_inexact_size_rejected(self):
        for n in (6, 12, 24, 30):
            with self.assertRaisesRegex(ValueError, 'lab_session_size'):
                create_session('dev_lab_ambiguity_18', num_participants=n)
            db.rollback()

    def test_full_production_threshold_map_required_before_play(self):
        bad = [None, {}, {'4': 42, '5': 40, '6': 50},
               {**MAP, '4': True}, {**MAP, '4': 32}, {**MAP, '4': 48},
               {**MAP, '4': 42.0}, {**MAP, '10': 42}]
        for mapping in bad:
            with self.assertRaisesRegex(ValueError, 'ambiguity_thresholds'):
                if mapping is None:
                    create_session('dev_lab_ambiguity_18', num_participants=18,
                                   modified_session_config_fields={'ambiguity_thresholds': None})
                else:
                    make_session(thresholds=mapping)
            db.rollback()

    def test_no_branch_or_cross_app_fallback(self):
        with self.assertRaises(ValueError):
            make_session(branch='E')
        db.rollback()
        session = make_session()
        session.config = {**session.config, 'app_sequence': ['fixed', 'ambiguity']}
        with self.assertRaisesRegex(ValueError, 'standalone'):
            ambiguity.validated_session(subsession(session))

    def test_snapshot_is_stable_and_changed_configuration_fails_closed(self):
        session = make_session()
        before = dict(session.vars[ambiguity.THRESHOLDS_KEY])
        ambiguity.creating_session(subsession(session))
        self.assertEqual(before, session.vars[ambiguity.THRESHOLDS_KEY])
        session.config = {**session.config, 'ambiguity_thresholds': {**MAP, '4': 41}}
        with self.assertRaisesRegex(ValueError, 'configuration changed'):
            ambiguity.threshold_for_round(subsession(session))
        self.assertEqual(before, session.vars[ambiguity.THRESHOLDS_KEY])

    def test_all_support_values_exact_equality_enforces(self):
        for k in range(33, 43):
            with self.subTest(k=k):
                group = self.main_group(k)
                run_period(group, [100 - k] * 6)
                self.assertEqual(group.equipment_total, 6 * k)
                self.assertEqual(decode_fraction(group.group_mean), k)
                self.assertTrue(group.main_enforcement_applied)
                for p in group.get_players():
                    self.assertEqual(p.applied_main_threshold, k)
                    self.assertTrue(p.main_enforcement_applied)
                    self.assertEqual(decode_fraction(p.main_fine), Fraction(175) + Fraction(k, 2))

    def test_above_by_one_unit_and_below_for_33_40_47(self):
        for k in (33, 40, 42):
            for delta in (-1, 1):
                with self.subTest(k=k, delta=delta):
                    group = self.main_group(k)
                    equipment = [k] * 5 + [k + delta]
                    run_period(group, [100 - value for value in equipment])
                    self.assertEqual(group.equipment_total, 6 * k + delta)
                    self.assertEqual(group.main_enforcement_applied, delta < 0)
                    for p, own in zip(group.get_players(), equipment):
                        self.assertEqual(decode_fraction(p.main_fine), rules.main_fine(own) if delta < 0 else 0)

    def test_mixed_zero_exemption_and_each_human_included_once(self):
        group = self.main_group(40)
        equipment = [0, 20, 40, 50, 60, 70]  # total 240 = 6*40
        run_period(group, [100 - k for k in equipment])
        self.assertEqual(group.equipment_total, 240)
        self.assertTrue(group.main_enforcement_applied)
        for p, own in zip(group.get_players(), equipment):
            self.assertTrue(p.main_enforcement_applied)
            self.assertEqual(decode_fraction(p.main_fine), rules.main_fine(own))

    def test_enforcement_independent_of_display_rounding(self):
        group = self.main_group(42)
        decide(group, [53] * 5 + [52])  # 283/6, strictly above 42
        with patch('lab_presentation.mean_display', return_value='0'):
            ambiguity.settle_period(group)
            self.assertFalse(group.main_enforcement_applied)
            self.assertEqual(ambiguity.Result.vars_for_template(group.get_players()[0])['group_mean'], '0')
        self.assertEqual(group.equipment_total, 283)
        self.assertEqual(decode_fraction(group.group_mean), Fraction(283, 6))

    def test_five_or_six_locked_decisions_alone_never_reveal(self):
        group = self.main_group()
        players = group.get_players()
        for p in players[:5]:
            p.retirement = 53
            ambiguity.Decision.before_next_page(p, False)
        with self.assertRaisesRegex(ValueError, 'six decisions'):
            ambiguity.settle_period(group)
        self.assertFalse(group.settlement_complete)
        for p in players:
            self.assertNotIn('threshold', ambiguity.Decision.vars_for_template(p))
        players[-1].retirement = 53
        ambiguity.Decision.before_next_page(players[-1], False)
        self.assertFalse(group.settlement_complete)
        self.assertNotIn('threshold', ambiguity.Decision.vars_for_template(players[0]))
        with self.assertRaisesRegex(ValueError, 'before group settlement'):
            ambiguity.Result.vars_for_template(players[0])
        ambiguity.PeriodWait.after_all_players_arrive(group)
        self.assertEqual(ambiguity.Result.vars_for_template(players[0])['threshold'], 42)

    def test_main_replay_and_reload_do_not_change_outcomes_or_reveal(self):
        group = self.main_group(41)
        run_period(group, [54] * 6)
        p = group.get_players()[0]
        context = ambiguity.Result.vars_for_template(p)
        record, wallet = group.settlement_record, p.wallet_after
        ambiguity.settle_period(group)
        db.commit()
        db.expire_all()
        self.assertEqual(context, ambiguity.Result.vars_for_template(p))
        self.assertEqual((record, wallet), (group.settlement_record, p.wallet_after))
        p.applied_main_threshold = 48
        with self.assertRaisesRegex(ValueError, 'Inconsistent replay'):
            ambiguity.settle_period(group)

    def test_follow_up_zero_and_positive_negative_wallet(self):
        session = make_session()
        ready(session)
        for r in range(1, 11):
            group = subsession(session, r).get_groups()[0]
            run_period(group, [100,0,0,0,0,0] if r == 1 else None)
        zero, *positive = group.get_players()
        self.assertEqual(decode_fraction(zero.follow_up_fine), 0)
        self.assertEqual(decode_fraction(zero.forced_retirement_cost), 0)
        for p in positive:
            self.assertEqual((p.voluntary_equipment_after, p.forced_retirement, p.final_equipment), (100,100,0))
            self.assertEqual(decode_fraction(p.follow_up_fine), 75)
            self.assertEqual(decode_fraction(p.forced_retirement_cost), 1000)
            self.assertEqual(decode_fraction(p.final_block_wallet), -75)
        record = group.settlement_record
        ambiguity.settle_period(group)
        self.assertEqual(record, group.settlement_record)

    def test_three_block_thresholds_and_matching_reset_both_sizes(self):
        for size in (18,24):
            with patch('ambiguity.select_matching', wraps=select_matching) as select:
                session = make_session(size)
                self.assertEqual(select.call_args.args[2:], (4, {}))
                ready(session)
                session.vars['lab_fixed_matching_v1'] = {'not': 'Z history'}
                ids = [g.id for g in subsession(session).get_groups()]
                for local, block in enumerate((4,5,6), 1):
                    finish_block(session, local, main_equipment=45)
                    main = subsession(session, (local - 1)*10+5)
                    for p in main.get_players():
                        self.assertEqual(p.applied_main_threshold, MAP[str(block)])
                        self.assertEqual(p.main_enforcement_applied, 45 <= MAP[str(block)])
                    if local < 3:
                        self.assertEqual(set(select.call_args.args[3]), set(range(4,block+1)))
                        calls = select.call_count
                        ambiguity.complete_block(subsession(session, local*10))
                        self.assertEqual(select.call_count, calls)
                self.assertEqual(select.call_count, 3)
            self.assertEqual(ids, [g.id for g in subsession(session).get_groups()])
            self.assertEqual(set(session.vars[ambiguity.MATCHING_KEY]['matrices']), {'4','5','6'})
            for local, block in enumerate((4,5,6),1):
                matrix = ambiguity.stored_matrix(subsession(session), block)
                for r in range((local-1)*10+1,local*10+1):
                    self.assertEqual(ambiguity._actual_matrix(subsession(session,r)), matrix)
                    self.assertTrue(all(g.threshold == MAP[str(block)] for g in subsession(session,r).get_groups()))
                for p in subsession(session,(local-1)*10+1).get_players():
                    self.assertEqual((p.start_equipment, decode_fraction(p.wallet_before)), (100,1000))

    def test_shared_threshold_engine_not_duplicated_or_legacy(self):
        self.assertIs(type(ambiguity.engine), type(endogenous.engine))
        self.assertIs(ambiguity.settle_period.__func__, endogenous.settle_period.__func__)
        self.assertIs(ambiguity._install_block.__func__, endogenous._install_block.__func__)
        for path in ('ambiguity/__init__.py','lab_threshold.py'):
            source = Path(path).read_text()
            for term in ('random.', 'simulated_environment','generate_simulated_paths','period10_'):
                self.assertNotIn(term, source)
