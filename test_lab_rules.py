"""Focused tests for pure lab mapping and economics, without legacy imports."""

from decimal import Decimal, localcontext
from fractions import Fraction
import unittest

import lab_rules as rules


class MappingTests(unittest.TestCase):
    def test_round_boundaries(self):
        cases = [(1, 1, 1), (5, 1, 5), (10, 1, 10), (11, 2, 1),
                 (20, 2, 10), (21, 3, 1), (30, 3, 10)]
        for round_number, block, period in cases:
            with self.subTest(round_number=round_number):
                self.assertEqual(rules.local_block_for_round(round_number), block)
                self.assertEqual(rules.period_for_round(round_number), period)

    def test_all_rounds_have_three_ten_period_blocks(self):
        self.assertEqual(rules.BLOCKS_PER_SECTION, 3)
        self.assertEqual(rules.PERIODS_PER_BLOCK, 10)
        self.assertEqual(rules.ROUNDS_PER_APP, 30)
        self.assertEqual(rules.TOTAL_BLOCKS, 9)
        for block in (1, 2, 3):
            periods = [rules.period_for_round(r) for r in range(1, 31)
                       if rules.local_block_for_round(r) == block]
            self.assertEqual(periods, list(range(1, 11)))

    def test_explicit_section_global_blocks(self):
        for section, offset in (('F', 0), ('Z', 3), ('P(Z)', 6)):
            with self.subTest(section=section):
                self.assertEqual(rules.section_offset(section), offset)
                self.assertEqual([rules.global_block(b, section) for b in (1, 2, 3)],
                                 list(range(offset + 1, offset + 4)))
                for r in (1, 10, 11, 20, 21, 30):
                    self.assertEqual(rules.global_block_for_round(r, section),
                                     offset + rules.local_block_for_round(r))

    def test_invalid_rounds(self):
        for value in (0, 31, -1, 120, 1.0, 1.5, '1', True, False, None, Decimal(1)):
            for helper in (rules.local_block_for_round, rules.period_for_round):
                with self.subTest(value=value, helper=helper.__name__):
                    with self.assertRaisesRegex(ValueError, 'round_number'):
                        helper(value)
            with self.assertRaisesRegex(ValueError, 'round_number'):
                rules.global_block_for_round(value, 'F')

    def test_invalid_blocks_and_sections(self):
        for block in (0, 4, -1, True, False, 1.0, '1', None):
            with self.subTest(block=block):
                with self.assertRaisesRegex(ValueError, 'local_block'):
                    rules.global_block(block, 'F')
        for section in (None, 1, True, '', 'E', 'fixed', 'risk', ['F']):
            with self.subTest(section=section):
                with self.assertRaisesRegex(ValueError, 'section'):
                    rules.section_offset(section)
                with self.assertRaisesRegex(ValueError, 'section'):
                    rules.global_block(1, section)

    def test_checks_use_validated_periods(self):
        self.assertEqual(rules.T, 5)
        self.assertEqual([p for p in range(1, 11) if rules.is_main_period(p)], [5])
        self.assertEqual([p for p in range(1, 11) if rules.is_follow_up_period(p)], [10])
        for helper in (rules.is_main_period, rules.is_follow_up_period):
            for value in (0, 11, 15, True, False, 5.0, '5', None):
                with self.subTest(helper=helper.__name__, value=value):
                    with self.assertRaisesRegex(ValueError, 'period'):
                        helper(value)


class RetirementAndCostTests(unittest.TestCase):
    def test_zero_full_and_sequential_irreversible_retirement(self):
        self.assertEqual(rules.K0, 100)
        self.assertEqual(rules.equipment_after_retirement(100, 0), 100)
        self.assertEqual(rules.equipment_after_retirement(100, 100), 0)
        self.assertEqual(rules.equipment_after_retirement(0, 0), 0)
        remaining = rules.equipment_after_retirement(100, 25)
        self.assertEqual(rules.equipment_after_retirement(remaining, 10), 65)

    def test_invalid_current_equipment(self):
        for equipment in (-1, 101, True, False, 50.0, '50', None, Decimal(50)):
            with self.subTest(equipment=equipment):
                with self.assertRaisesRegex(ValueError, 'current_equipment'):
                    rules.equipment_after_retirement(equipment, 0)

    def test_invalid_retirement(self):
        for amount in (-1, 51, True, False, 1.0, '1', None):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(ValueError, 'retirement'):
                    rules.equipment_after_retirement(50, amount)
        with self.assertRaises(ValueError):
            rules.equipment_after_retirement(0, 1)

    def test_exact_per_period_cost_benchmarks(self):
        for amount, expected in ((0, '0'), (1, '0.10'), (10, '10'), (20, '40'),
                                 (25, '62.5'), (50, '250'), (100, '1000')):
            with self.subTest(amount=amount):
                cost = rules.retirement_cost(amount)
                self.assertIsInstance(cost, Fraction)
                self.assertEqual(cost, Fraction(expected))

    def test_split_retirement_is_not_cumulative_square(self):
        split_cost = rules.retirement_cost(10) + rules.retirement_cost(10)
        self.assertEqual(split_cost, 20)
        self.assertLess(split_cost, rules.retirement_cost(20))

    def test_invalid_cost_inputs(self):
        for amount in (-1, 101, True, False, 1.0, '1', None):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(ValueError, 'retirement'):
                    rules.retirement_cost(amount)


class MainEnforcementTests(unittest.TestCase):
    def test_main_fine_amounts_and_zero_exemption(self):
        for equipment, expected in ((0, '0'), (1, '175.5'), (50, '200'), (100, '225')):
            with self.subTest(equipment=equipment):
                self.assertEqual(rules.main_fine(equipment), Fraction(expected))

    def test_invalid_main_equipment(self):
        for equipment in (-1, 101, True, False, 1.0, '1', None):
            with self.subTest(equipment=equipment):
                with self.assertRaisesRegex(ValueError, 'equipment'):
                    rules.main_fine(equipment)

    def test_f_always_enforces_without_threshold(self):
        self.assertTrue(rules.main_enforcement_applies('F'))
        for total in (0, 239, 240, 241, 600):
            self.assertTrue(rules.main_enforcement_applies('F', group_total=total))
        self.assertEqual(rules.main_fine(0), 0)
        self.assertEqual(rules.main_fine(100), 225)

    def test_e_m_strict_exact_total_comparison(self):
        for branch in ('E', 'M'):
            # Means 239/6 < 40, 240/6 == 40, and 241/6 > 40.
            for total, expected in ((0, True), (239, True), (240, True),
                                    (241, False), (600, False)):
                with self.subTest(branch=branch, total=total):
                    self.assertEqual(rules.main_enforcement_applies(
                        branch, group_total=total,
                    ), expected)

    def test_ambiguity_external_support_and_strict_comparison(self):
        for threshold in range(33, 48):
            for difference, expected in ((-1, True), (0, True), (1, False)):
                with self.subTest(threshold=threshold, difference=difference):
                    self.assertEqual(rules.main_enforcement_applies(
                        'A', group_total=6 * threshold + difference,
                        ambiguity_threshold=threshold,
                    ), expected)

    def test_a_at_40_matches_e_m(self):
        for total in (0, 239, 240, 241, 600):
            actual = rules.main_enforcement_applies(
                'A', group_total=total, ambiguity_threshold=40,
            )
            for branch in ('E', 'M'):
                self.assertEqual(actual, rules.main_enforcement_applies(branch, group_total=total))

    def test_invalid_ambiguity_thresholds_and_unexpected_overrides(self):
        for value in (None, 32, 48, True, False, 40.0, '40', Decimal(40)):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'ambiguity_threshold'):
                    rules.main_enforcement_applies('A', group_total=240, ambiguity_threshold=value)
        for branch in ('F', 'E', 'M'):
            with self.assertRaisesRegex(ValueError, 'ambiguity_threshold'):
                rules.main_enforcement_applies(branch, group_total=240, ambiguity_threshold=40)

    def test_missing_invalid_totals_and_unsupported_branches(self):
        for branch in ('E', 'A', 'M'):
            for total in (None, -1, 601, True, False, 240.0, '240', Decimal(240)):
                with self.subTest(branch=branch, total=total):
                    kwargs = {'ambiguity_threshold': 40} if branch == 'A' else {}
                    with self.assertRaisesRegex(ValueError, 'group_total'):
                        rules.main_enforcement_applies(branch, group_total=total, **kwargs)
        for branch in (None, True, '', 'risk', 'Z', 'P(E)', ['E']):
            with self.subTest(branch=branch):
                with self.assertRaisesRegex(ValueError, 'branch'):
                    rules.main_enforcement_applies(branch, group_total=240)


class FollowUpAndWalletTests(unittest.TestCase):
    def test_follow_up_at_zero(self):
        outcome = rules.follow_up_enforcement(0)
        self.assertEqual(outcome.pre_forced_equipment, 0)
        self.assertEqual(outcome.follow_up_fine, 0)
        self.assertEqual(outcome.forced_retirement, 0)
        self.assertEqual(outcome.forced_retirement_cost, 0)
        self.assertEqual(outcome.final_equipment, 0)

    def test_follow_up_preserves_pre_forced_state_and_exact_cost(self):
        for equipment, cost in ((1, '0.10'), (25, '62.5'), (100, '1000')):
            with self.subTest(equipment=equipment):
                outcome = rules.follow_up_enforcement(equipment)
                self.assertEqual(outcome.pre_forced_equipment, equipment)
                self.assertEqual(outcome.follow_up_fine, 75)
                self.assertEqual(outcome.forced_retirement, equipment)
                self.assertEqual(outcome.forced_retirement_cost, Fraction(cost))
                self.assertEqual(outcome.final_equipment, 0)

    def test_follow_up_after_voluntary_decision(self):
        remaining = rules.equipment_after_retirement(50, 25)
        outcome = rules.follow_up_enforcement(remaining)
        self.assertEqual(outcome.pre_forced_equipment, 25)
        self.assertEqual(rules.wallet_after_deductions(
            1000, rules.retirement_cost(25), outcome.follow_up_fine,
            outcome.forced_retirement_cost,
        ), Fraction('800'))

    def test_invalid_follow_up_equipment(self):
        for equipment in (-1, 101, True, False, 1.0, '1', None):
            with self.subTest(equipment=equipment):
                with self.assertRaisesRegex(ValueError, 'equipment'):
                    rules.follow_up_enforcement(equipment)

    def test_no_voluntary_retirement_in_f_ends_at_minus_300(self):
        equipment, wallet = rules.K0, rules.W0
        self.assertEqual(wallet, 1000)
        for period in range(1, 11):
            equipment = rules.equipment_after_retirement(equipment, 0)
            wallet = rules.wallet_after_deductions(wallet, rules.retirement_cost(0))
            if rules.is_main_period(period):
                self.assertTrue(rules.main_enforcement_applies('F'))
                wallet = rules.wallet_after_deductions(wallet, rules.main_fine(equipment))
            if rules.is_follow_up_period(period):
                outcome = rules.follow_up_enforcement(equipment)
                wallet = rules.wallet_after_deductions(
                    wallet, outcome.follow_up_fine, outcome.forced_retirement_cost,
                )
                equipment = outcome.final_equipment
        self.assertEqual(wallet, -300)
        self.assertEqual(equipment, 0)

    def test_signed_wallet_no_clipping_or_liquidity_constraint(self):
        self.assertEqual(rules.wallet_after_deductions(-250), -250)
        self.assertEqual(rules.wallet_after_deductions(-250, 1), -251)
        self.assertEqual(rules.wallet_after_deductions(5000), 5000)
        # Even a zero wallet does not restrict full voluntary retirement.
        self.assertEqual(rules.equipment_after_retirement(100, 100), 0)
        self.assertEqual(rules.wallet_after_deductions(0, rules.retirement_cost(100)), -1000)

    def test_exact_money_types_and_no_display_rounding(self):
        with localcontext() as context:
            context.prec = 2  # Rational arithmetic must ignore Decimal precision.
            result = rules.wallet_after_deductions(
                Decimal('1000'), rules.retirement_cost(25), Decimal('0.10'), Fraction(1, 3),
            )
        self.assertIsInstance(result, Fraction)
        self.assertEqual(result, Fraction(1000) - Fraction('62.5') - Fraction('0.10') - Fraction(1, 3))
        self.assertEqual(rules.retirement_cost(1), Fraction(1, 10))

    def test_invalid_money_inputs(self):
        values = (True, False, '1', 1.0, float('nan'), float('inf'), None,
                  Decimal('NaN'), Decimal('sNaN'), Decimal('Infinity'), Decimal('-Infinity'))
        for value in values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'wallet'):
                    rules.wallet_after_deductions(value)
                with self.assertRaisesRegex(ValueError, 'deduction'):
                    rules.wallet_after_deductions(1000, value)
        with self.assertRaisesRegex(ValueError, 'nonnegative'):
            rules.wallet_after_deductions(1000, -1)


if __name__ == '__main__':
    unittest.main()
