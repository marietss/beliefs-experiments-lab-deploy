"""Focused tests of the standalone lab configuration contract."""

from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from types import MappingProxyType
import unittest

from lab_config import DEFAULT_RHO, validate_lab_config


def configuration(branch='E', **overrides):
    config = dict(
        lab_session_size=18,
        branch=branch,
        paid_block=1,
        rho=DEFAULT_RHO,
        matching_seed='lab-session-001',
    )
    if branch == 'A':
        config['ambiguity_thresholds'] = {
            '4': 33, '5': 35, '6': 40, '7': 44, '8': 46, '9': 47,
        }
    config.update(overrides)
    return config


class LabConfigTests(unittest.TestCase):
    def assert_invalid(self, field, value, branch='E'):
        config = configuration(branch)
        config[field] = value
        with self.assertRaisesRegex(ValueError, field):
            validate_lab_config(config)

    def test_valid_branches_sizes_and_payment_boundaries(self):
        for branch in ('E', 'A', 'M'):
            for size in (18, 24):
                for paid_block in (1, 9):
                    with self.subTest(branch=branch, size=size, paid_block=paid_block):
                        validated = validate_lab_config(configuration(
                            branch, lab_session_size=size, paid_block=paid_block,
                        ))
                        self.assertEqual(validated['branch'], branch)
                        self.assertEqual(validated['lab_session_size'], size)
                        self.assertEqual(validated['paid_block'], paid_block)

    def test_every_paid_block_is_valid(self):
        for block in range(1, 10):
            with self.subTest(block=block):
                self.assertEqual(
                    validate_lab_config(configuration(paid_block=block))['paid_block'], block,
                )

    def test_invalid_session_sizes(self):
        for value in (None, 0, 6, 12, 19, 30, True, False, '18', 18.0, 24.0):
            with self.subTest(value=value):
                self.assert_invalid('lab_session_size', value)

    def test_invalid_branches(self):
        for value in (None, '', 'e', 'risk', 'F', 'P(E)', 1, True, ['E']):
            with self.subTest(value=value):
                self.assert_invalid('branch', value)

    def test_invalid_paid_blocks(self):
        for value in (None, 0, 10, -1, True, False, '1', '9', 1.0, 9.0, 1.5):
            with self.subTest(value=value):
                self.assert_invalid('paid_block', value)

    def test_required_fields_cannot_be_omitted(self):
        for field in ('lab_session_size', 'branch', 'paid_block', 'rho', 'matching_seed'):
            with self.subTest(field=field):
                config = configuration()
                del config[field]
                with self.assertRaisesRegex(ValueError, field):
                    validate_lab_config(config)

    def test_rho_boundaries_default_and_numeric_precision(self):
        self.assertEqual(DEFAULT_RHO, Fraction(1, 3))
        for value in (0, 1 / 3, DEFAULT_RHO, 1, 0.0, 1.0,
                      Decimal('0'), Decimal('0.3333333333333333333333333333'),
                      Decimal('1')):
            with self.subTest(value=value):
                validated = validate_lab_config(configuration(rho=value))
                self.assertIs(validated['rho'], value)

    def test_invalid_rho_values(self):
        for value in (-0.01, 1.01, float('nan'), float('inf'), -float('inf'),
                      Decimal('NaN'), Decimal('sNaN'), Decimal('Infinity'),
                      Decimal('-Infinity'), Decimal('-0.01'), Decimal('1.01'),
                      10 ** 1000, True, False, '0.5', complex(0.5, 0), None):
            with self.subTest(value=value):
                self.assert_invalid('rho', value)

    def test_explicit_reproducible_seed_types(self):
        for seed in (0, 42, -7, 'session-A-18', '42'):
            with self.subTest(seed=seed):
                validated = validate_lab_config(configuration(matching_seed=seed))
                self.assertEqual(validated['matching_seed'], seed)
                self.assertIs(type(validated['matching_seed']), type(seed))

    def test_invalid_matching_seeds(self):
        for value in (None, '', '  \t\n', True, False, 42.0, float('nan'),
                      b'seed', [], {}, object()):
            with self.subTest(value=value):
                self.assert_invalid('matching_seed', value)

    def test_a_requires_threshold_mapping(self):
        config = configuration('A')
        del config['ambiguity_thresholds']
        with self.assertRaisesRegex(ValueError, 'ambiguity_thresholds'):
            validate_lab_config(config)

    def test_a_rejects_each_missing_threshold(self):
        for key in map(str, range(4, 10)):
            with self.subTest(key=key):
                thresholds = configuration('A')['ambiguity_thresholds']
                del thresholds[key]
                self.assert_invalid('ambiguity_thresholds', thresholds, 'A')

    def test_a_rejects_extra_or_nonstring_keys(self):
        for key in ('3', '10', '04', 4):
            with self.subTest(key=key):
                thresholds = configuration('A')['ambiguity_thresholds']
                thresholds[key] = 45
                self.assert_invalid('ambiguity_thresholds', thresholds, 'A')
        self.assert_invalid('ambiguity_thresholds', dict.fromkeys(range(4, 10), 45), 'A')

    def test_a_thresholds_must_be_strict_integers_in_support(self):
        for key in map(str, range(4, 10)):
            for value in (32, 48, True, False, 45.0, '45', None, Decimal('45')):
                with self.subTest(key=key, value=value):
                    thresholds = configuration('A')['ambiguity_thresholds']
                    thresholds[key] = value
                    self.assert_invalid('ambiguity_thresholds', thresholds, 'A')

    def test_every_threshold_in_support_is_valid(self):
        for value in range(33, 48):
            with self.subTest(value=value):
                thresholds = dict.fromkeys(map(str, range(4, 10)), value)
                self.assertEqual(validate_lab_config(configuration(
                    'A', ambiguity_thresholds=thresholds,
                ))['ambiguity_thresholds'], thresholds)

    def test_e_m_accept_omitted_or_empty_mapping(self):
        for branch in ('E', 'M'):
            with self.subTest(branch=branch):
                self.assertEqual(validate_lab_config(configuration(branch))['ambiguity_thresholds'], {})
                self.assertEqual(validate_lab_config(configuration(
                    branch, ambiguity_thresholds={},
                ))['ambiguity_thresholds'], {})

    def test_e_m_reject_nonempty_threshold_mappings(self):
        for branch in ('E', 'M'):
            for thresholds in ({'4': 45}, configuration('A')['ambiguity_thresholds']):
                with self.subTest(branch=branch, thresholds=thresholds):
                    self.assert_invalid('ambiguity_thresholds', thresholds, branch)

    def test_threshold_containers_must_be_mappings_for_all_branches(self):
        for branch in ('E', 'A', 'M'):
            for value in (None, [], [40, 41, 42, 43, 44, 45], '', False):
                with self.subTest(branch=branch, value=value):
                    self.assert_invalid('ambiguity_thresholds', value, branch)

    def test_accepts_read_only_mappings_without_mutation_or_aliasing(self):
        config = configuration('A', display_name='Future lab config')
        original = deepcopy(config)
        config['ambiguity_thresholds'] = MappingProxyType(config['ambiguity_thresholds'])
        validated = validate_lab_config(MappingProxyType(config))
        self.assertEqual(validated, original)
        validated['ambiguity_thresholds']['4'] = 50
        validated['paid_block'] = 9
        self.assertEqual(config, original)

    def test_repeat_validation_preserves_external_values(self):
        config = configuration('A')
        original = deepcopy(config)
        self.assertEqual(validate_lab_config(config), validate_lab_config(config))
        self.assertEqual(config, original)

    def test_config_must_be_a_mapping(self):
        for config in (None, [], 'E', 18):
            with self.subTest(config=config):
                with self.assertRaisesRegex(ValueError, 'mapping'):
                    validate_lab_config(config)


if __name__ == '__main__':
    unittest.main()
