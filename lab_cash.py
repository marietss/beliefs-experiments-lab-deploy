"""Exact laboratory block-wallet ledger and one-time EUR-cent settlement.

The ledger and payment record use canonical n/d strings, never Currency or
floats. Final cash is rounded once, half away from zero (decimal HALF_UP).
oTree receives *cash-settlement equivalent points*: final cents minus 750.
Those integer points reproduce the rounded total through oTree's float-based
0.01 conversion without quantizing the selected experimental wallet first.
They are explicitly distinct from the exact selected wallet retained here.
"""
from collections.abc import Mapping
from decimal import Decimal
from fractions import Fraction

from lab_config import validate_lab_config
from lab_persistence import encode_fraction, decode_fraction

WALLETS_KEY = 'lab_block_wallets_v1'
CONFIG_KEY = 'lab_payment_config_v1'
PAYMENT_KEY = 'lab_final_payment_v1'
ROUNDING = 'EUR-cent-HALF_UP-v1'
RATE = Fraction(1, 100)
FEE = Fraction(15, 2)
BLOCK_KEYS = frozenset(str(b) for b in range(1, 10))


def _block(block):
    if type(block) is not int or not 1 <= block <= 9:
        raise ValueError('paid_block/block must be a strict integer from 1 through 9.')
    return str(block)


def validate_wallets(wallets, *, complete=False):
    if not isinstance(wallets, Mapping) or not set(wallets) <= BLOCK_KEYS:
        raise ValueError('Wallet ledger must contain only string block keys 1 through 9.')
    for value in wallets.values():
        decode_fraction(value)
    if complete and set(wallets) != BLOCK_KEYS:
        raise ValueError('Final payment requires all nine completed block wallets; a wallet is missing.')
    return dict(wallets)


def write_wallet(wallets, block, wallet):
    """Pure immutable write: identical replay succeeds; conflicting replay fails."""
    key = _block(block)
    result = validate_wallets(wallets)
    value = encode_fraction(wallet)
    if key in result and result[key] != value:
        raise ValueError(f'Conflicting final wallet replay for Block {block}.')
    return {**result, key: value}


def euro_cents(amount):
    """Exact HALF_UP, including negative totals; no Decimal context/float step."""
    encode_fraction(amount)  # reject floats/bools rather than silently rationalizing
    amount = Fraction(amount) * 100
    rounded = (2 * abs(amount.numerator) + amount.denominator) // (2 * amount.denominator)
    return -rounded if amount < 0 else rounded


def calculate_payment(wallets, paid_block, *, rate=RATE, fee=FEE):
    key = _block(paid_block)
    wallets = validate_wallets(wallets, complete=True)
    if encode_fraction(rate) != encode_fraction(RATE) or encode_fraction(fee) != encode_fraction(FEE):
        raise ValueError('Lab payment requires conversion 0.01 and fixed fee 7.50.')
    wallet = decode_fraction(wallets[key])
    variable = wallet * rate
    total = fee + variable
    cents = euro_cents(total)
    return dict(version=1, finalized=True, paid_block=paid_block,
                selected_wallet=encode_fraction(wallet), conversion=encode_fraction(rate),
                fixed_fee=encode_fraction(fee), variable_eur=encode_fraction(variable),
                pre_round_eur=encode_fraction(total), final_eur_cents=cents,
                admin_payoff_points=cents - 750, currency='EUR', rounding=ROUNDING)


def _configured_number(value):
    # oTree config rates are floats and fees are Decimal currency values. Parse
    # their decimal spelling; these fixed settings must equal their exact contract.
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, Fraction)):
        raise ValueError('Invalid laboratory payment conversion/fixed fee.')
    try:
        # Currency subclasses Decimal but str(Currency) is formatted money.
        return Fraction(str(value)) if isinstance(value, float) else Fraction(value)
    except (ValueError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Invalid laboratory payment conversion/fixed fee.') from exc


def config_snapshot(config):
    config = validate_lab_config(config)
    rate = _configured_number(config.get('real_world_currency_per_point'))
    fee = _configured_number(config.get('participation_fee'))
    if rate != RATE or fee != FEE:
        raise ValueError('Lab payment requires conversion 0.01 and fixed fee 7.50.')
    return dict(version=1, paid_block=config['paid_block'], conversion=encode_fraction(rate),
                fixed_fee=encode_fraction(fee), currency='EUR', rounding=ROUNDING)


def initialize(session):
    from otree import settings
    if settings.REAL_WORLD_CURRENCY_CODE != 'EUR' or not settings.USE_POINTS:
        raise ValueError('Start the lab payment server with OTREE_LAB_PAYMENTS=1 (EUR, points).')
    if settings.REAL_WORLD_CURRENCY_DECIMAL_PLACES != 2:
        raise ValueError('Lab cash accounting requires two euro-cent decimal places.')
    expected = config_snapshot(session.config)
    previous = session.vars.get(CONFIG_KEY)
    if previous is not None and previous != expected:
        raise ValueError('Laboratory payment configuration changed after initialization.')
    if previous is None:
        session.vars[CONFIG_KEY] = expected
    return expected


def checked_config(session):
    expected = config_snapshot(session.config)
    if session.vars.get(CONFIG_KEY) != expected:
        raise ValueError('Laboratory payment configuration changed or was not initialized.')
    # Recheck the global currency as well, without writing anything on a read.
    from otree import settings
    if settings.REAL_WORLD_CURRENCY_CODE != 'EUR' or not settings.USE_POINTS or settings.REAL_WORLD_CURRENCY_DECIMAL_PLACES != 2:
        raise ValueError('Laboratory EUR currency settings changed.')
    return expected


def record_group(group):
    """Called only from period settlement, after period-10 outcomes are complete.

    Preflight all six ledger writes before assigning any participant vars.
    The existing oTree callback transaction owns persistence/rollback.
    Standalone substantive routes also retain their completed block entries.
    """
    if group.period != 10:
        return
    if 'lab_payment' in group.session.config['app_sequence']:
        checked_config(group.session)
    players = group.get_players()
    if not group.settlement_complete or len(players) != 6:
        raise ValueError('A completed six-person Follow-up settlement is required for ledger storage.')
    updates = []
    for p in players:
        if (not p.period_settled or p.period != 10 or p.final_equipment != 0
                or p.final_block_wallet != p.wallet_after):
            raise ValueError('Ledger requires the exact post-Follow-up final block wallet.')
        updates.append(write_wallet(p.participant.vars.get(WALLETS_KEY, {}), p.global_block,
                                    decode_fraction(p.final_block_wallet)))
    for p, ledger in zip(players, updates):
        if p.participant.vars.get(WALLETS_KEY) != ledger:
            p.participant.vars[WALLETS_KEY] = ledger


def finalize(player):
    """Finalize at the terminal payment stage, after the Block-9 session barrier."""
    import lab_route
    session, participant = player.session, player.participant
    if session.config['app_sequence'] != lab_route.full_sequence(session.config['branch']) + ['lab_payment']:
        raise ValueError('Final lab payment requires the complete laboratory payment route.')
    checked_config(session)
    if not lab_route.block_subsession(session, 9, last=True).block_barrier_complete:
        raise ValueError('Final payment is unavailable before the Block-9 session barrier.')
    record = calculate_payment(participant.vars.get(WALLETS_KEY, {}), session.config['paid_block'])
    expected_cash = Decimal(record['final_eur_cents']) / 100
    from otree.api import cu
    if Decimal(session._get_payoff_plus_participation_fee(cu(record['admin_payoff_points']))) != expected_cash:
        raise ValueError('oTree/admin cash total disagrees with exact laboratory payment.')
    previous = participant.vars.get(PAYMENT_KEY)
    if previous is not None:
        if previous != record:
            raise ValueError('Finalized laboratory payment changed.')
        if not player.finalized or any(player.field_maybe_none(k) != record[k] for k in player.RECORD_FIELDS):
            raise ValueError('Finalized payment primitives disagree with canonical payment.')
        if Decimal(player.payoff) != record['admin_payoff_points'] or Decimal(participant.payoff) != record['admin_payoff_points']:
            raise ValueError('Finalized oTree payoff changed.')
    else:
        if player.finalized or Decimal(player.payoff) != 0 or Decimal(participant.payoff) != 0:
            raise ValueError('Unexpected existing oTree payoff before laboratory finalization.')
        for key in player.RECORD_FIELDS:
            setattr(player, key, record[key])
        player.finalized = True
        participant.vars[PAYMENT_KEY] = record
        # BasePlayer's setter commits internally. Prepare ALL primitives first,
        # then assign once so record, marker and both payoffs commit together.
        player.payoff = record['admin_payoff_points']
    if Decimal(participant.payoff_plus_participation_fee()) != expected_cash:
        raise ValueError('oTree/admin cash total disagrees with exact laboratory payment.')
    return dict(record)


def cash_display(cents):
    if type(cents) is not int:
        raise ValueError('Cash display requires integer cents.')
    whole, tail = divmod(abs(cents), 100)
    return f'{"-" if cents < 0 else ""}€{whole}.{tail:02d}'
