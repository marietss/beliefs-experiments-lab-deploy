"""Pure exact redistribution; no oTree models, settlement writes or payment.

Integers, Fractions and Decimals retain their exact value. A supplied float is
interpreted as its explicit shortest decimal spelling. For JSON-safe oTree
configs an optional canonical rho_exact (e.g. '1/3') disambiguates a repeating
share and must agree with numeric rho. No denominator approximation is used.
"""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from math import isfinite

import lab_rules as rules
from lab_persistence import decode_fraction


def exact_rho(value):
    if isinstance(value, bool):
        raise ValueError('rho must be finite and between zero and one.')
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError('rho must be finite.')
        value = Fraction(str(value))
    elif type(value) is int or isinstance(value, (Fraction, Decimal)):
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError('rho must be finite.')
        value = Fraction(value)
    else:
        raise ValueError('rho must be numeric.')
    if not 0 <= value <= 1:
        raise ValueError('rho must be between zero and one.')
    return value


def configured_rho(config):
    """Resolve explicit exact configuration, never guess a nearby fraction.

    rho_exact is optional and checked against the validated numeric rho. Float
    conversion here checks their agreement only; it never enters accounting.
    This keeps the Task-1 numeric rho contract and oTree's config REST API.
    """
    numeric = exact_rho(config['rho'])
    if 'rho_exact' not in config:
        return numeric
    exact = decode_fraction(config['rho_exact'])
    if not 0 <= exact <= 1:
        raise ValueError('rho_exact must be between zero and one.')
    agrees = float(exact) == config['rho'] if isinstance(config['rho'], float) else exact == numeric
    if not agrees:
        raise ValueError('rho_exact must agree with numeric rho.')
    return exact


@dataclass(frozen=True)
class Redistribution:
    fine_pool: Fraction
    recipient_count: int
    redistributed_pool: Fraction
    recipients: tuple[bool, ...]
    transfers: tuple[Fraction, ...]


def redistribute(equipment, actual_fines, rho):
    """Allocate ONLY actual Main fines supplied after branch enforcement.

    Equipment and fines are six aligned primitive values. No second payer
    deduction is returned. With no recipients, actual redistribution is zero.
    """
    equipment, actual_fines = tuple(equipment), tuple(actual_fines)
    if len(equipment) != rules.GROUP_SIZE or len(actual_fines) != rules.GROUP_SIZE:
        raise ValueError('Policy requires exactly six equipment values and actual Main fines.')
    for k, fine in zip(equipment, actual_fines):
        rules.equipment_after_retirement(k, 0)
        if (type(fine) is not int and not isinstance(fine, Fraction)) or fine < 0:
            raise ValueError('Actual Main fines must be nonnegative exact amounts.')
        if fine not in (0, rules.main_fine(k)):
            raise ValueError('Actual Main fines must respect own-equipment fine/exemption.')
    rho = exact_rho(rho)
    pool = sum(actual_fines, Fraction(0))
    recipients = tuple(k == 0 for k in equipment)
    count = sum(recipients)
    redistributed = rho * pool if count else Fraction(0)
    transfers = tuple(redistributed / count if eligible else Fraction(0) for eligible in recipients)
    if sum(transfers, Fraction(0)) != redistributed:
        raise ValueError('Policy transfers must conserve actual redistribution exactly.')
    return Redistribution(pool, count, redistributed, recipients, transfers)
