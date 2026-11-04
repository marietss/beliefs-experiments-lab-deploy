"""Pure exact-ledger/payment tests; no oTree imports or runtime database."""
from fractions import Fraction as F
import unittest
import lab_cash as cash


def wallets(value=0):
    return {str(b): cash.encode_fraction(value) for b in range(1, 10)}


class LedgerTests(unittest.TestCase):
    def test_exact_signed_idempotent_immutable_writes(self):
        old = {}
        new = cash.write_wallet(old, 5, F(-4499, 18))
        self.assertEqual(old, {})
        self.assertEqual(new, {'5': '-4499/18'})
        self.assertEqual(cash.write_wallet(new, 5, F(-4499, 18)), new)
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            cash.write_wallet(new, 5, F(-250))

    def test_strict_block_and_exact_wallet_types(self):
        for block in (True, False, '1', 1.0, 0, 10, None):
            with self.subTest(block=block), self.assertRaises(ValueError):
                cash.write_wallet({}, block, 0)
        for value in (True, 0.075, '3/40'):
            with self.assertRaises(ValueError): cash.write_wallet({}, 1, value)

    def test_reject_malformed_ledger(self):
        for ledger in (None, [], {1: '0/1'}, {'10': '0/1'}, {'1': '2/2'}, {'1': 0}):
            with self.subTest(ledger=ledger), self.assertRaises(ValueError):
                cash.validate_wallets(ledger)

    def test_missing_selected_or_any_other_wallet_fails_without_reconstruction(self):
        for missing in ('7', '1'):
            ledger = wallets(); del ledger[missing]
            original = dict(ledger)
            with self.assertRaisesRegex(ValueError, 'nine.*missing'):
                cash.calculate_payment(ledger, 7)
            self.assertEqual(ledger, original)


class CashTests(unittest.TestCase):
    def test_required_examples(self):
        for wallet, cents in ((1000, 1800), (0, 800), (-300, 500)):
            result = cash.calculate_payment(wallets(wallet), 1)
            self.assertEqual(result['final_eur_cents'], cents)
            self.assertEqual(cash.decode_fraction(result['pre_round_eur']), F(cents, 100))

    def test_all_nine_selected_blocks(self):
        ledger = {str(b): cash.encode_fraction(F(b, 6)) for b in range(1, 10)}
        for block in range(1, 10):
            result = cash.calculate_payment(ledger, block)
            self.assertEqual(cash.decode_fraction(result['selected_wallet']), F(block, 6))

    def test_fractional_and_repeating_policy_wallet(self):
        for wallet in (F(953125, 1000), F(5671, 18), F(-4499, 18)):
            record = cash.calculate_payment(wallets(wallet), 9)
            self.assertEqual(cash.decode_fraction(record['pre_round_eur']), F(8) + wallet / 100)
            self.assertEqual(cash.decode_fraction(record['selected_wallet']), wallet)
        # 250-point wallet plus the actual 1171/18 policy transfer.
        record = cash.calculate_payment(wallets(F(250) + F(1171, 18)), 9)
        self.assertEqual(record['pre_round_eur'], '20071/1800')
        self.assertEqual(record['final_eur_cents'], 1115)

    def test_exact_half_cent_below_equal_above(self):
        for wallet, expected in ((F(4999, 10000), 800), (F(1, 2), 801), (F(5001, 10000), 801)):
            self.assertEqual(cash.calculate_payment(wallets(wallet), 1)['final_eur_cents'], expected)

    def test_signed_half_up_is_total_rounding_not_variable_rounding(self):
        self.assertEqual(cash.euro_cents(F(-1, 200)), -1)
        # Positive total 7.995 rounds UP to 8.00, even though variable is -0.005.
        self.assertEqual(cash.calculate_payment(wallets(F(-1, 2)), 1)['final_eur_cents'], 800)
        self.assertEqual(cash.calculate_payment(wallets(F(-1601, 2)), 1)['final_eur_cents'], -1)

    def test_no_floor_cap_or_clipping(self):
        for wallet, cents in ((-500, 300), (2000, 2800), (-1000, -200)):
            self.assertEqual(cash.calculate_payment(wallets(wallet), 1)['final_eur_cents'], cents)

    def test_invalid_paid_block_and_payment_parameters(self):
        for block in (True, '9', 9.0, 0, 10):
            with self.assertRaises(ValueError): cash.calculate_payment(wallets(), block)
        for kwargs in ({'rate': F(1, 250)}, {'fee': 5}, {'rate': .01}):
            with self.assertRaises(ValueError): cash.calculate_payment(wallets(), 1, **kwargs)

    def test_cash_display_keeps_signed_cents(self):
        self.assertEqual(cash.cash_display(500), '€5.00')
        self.assertEqual(cash.cash_display(-1), '-€0.01')


if __name__ == '__main__': unittest.main()
