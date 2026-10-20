"""Pure laboratory timing and economic primitives; no oTree integration.

Equipment, rounds, periods and block numbers are strict integers. Monetary
results are exact Fractions: no display rounding or Decimal-context dependence.
Wallet inputs may be int, Fraction, or finite Decimal; floats, strings and bools
are rejected rather than silently converted. No payment conversion lives here.
"""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction


K0 = 100
W0 = Fraction(1000)
T = 5
GROUP_SIZE = 6
BLOCKS_PER_SECTION = 3
PERIODS_PER_BLOCK = 10
ROUNDS_PER_APP = 30
TOTAL_BLOCKS = 9
MAIN_CHECK_PERIOD = T
FOLLOW_UP_PERIOD = PERIODS_PER_BLOCK
COST_FACTOR = Fraction(75, 1000)
KNOWN_THRESHOLD = 45
AMBIGUITY_THRESHOLD_LOW = 40
AMBIGUITY_THRESHOLD_HIGH = 50
MAIN_FINE_BASE = Fraction(175)
MAIN_FINE_PER_UNIT = Fraction(1, 2)
FOLLOW_UP_FINE = Fraction(275)


def _integer_in_range(value, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer from {minimum} through {maximum}.')
    return value


def local_block_for_round(round_number: int) -> int:
    """Map app rounds 1–30 to local blocks 1–3, without padding rounds."""
    _integer_in_range(round_number, 'round_number', 1, ROUNDS_PER_APP)
    return (round_number - 1) // PERIODS_PER_BLOCK + 1


def period_for_round(round_number: int) -> int:
    """Map app rounds 1–30 to within-block decision periods 1–10."""
    _integer_in_range(round_number, 'round_number', 1, ROUNDS_PER_APP)
    return (round_number - 1) % PERIODS_PER_BLOCK + 1


def section_offset(section: str) -> int:
    """Explicit section identifiers: F → 0, Z → 3, P(Z) → 6.

    Z means any configured substantive branch E/A/M. App names, numeric section
    numbers and implicit/default sections are deliberately not accepted.
    """
    sections = ('F', 'Z', 'P(Z)')
    if not isinstance(section, str) or section not in sections:
        raise ValueError('section must be F, Z, or P(Z).')
    return sections.index(section) * BLOCKS_PER_SECTION


def global_block(local_block: int, section: str) -> int:
    """Map local block 1–3 plus an explicit section to global block 1–9."""
    _integer_in_range(local_block, 'local_block', 1, BLOCKS_PER_SECTION)
    return section_offset(section) + local_block


def global_block_for_round(round_number: int, section: str) -> int:
    return global_block(local_block_for_round(round_number), section)


def is_main_period(period: int) -> bool:
    """Accept a within-block period (not an app round)."""
    _integer_in_range(period, 'period', 1, PERIODS_PER_BLOCK)
    return period == MAIN_CHECK_PERIOD


def is_follow_up_period(period: int) -> bool:
    """Accept a within-block period (not an app round)."""
    _integer_in_range(period, 'period', 1, PERIODS_PER_BLOCK)
    return period == FOLLOW_UP_PERIOD


def equipment_after_retirement(current_equipment: int, retirement: int) -> int:
    """Irreversible voluntary retirement, bounded only by equipment, not wallet."""
    _integer_in_range(current_equipment, 'current_equipment', 0, K0)
    _integer_in_range(retirement, 'retirement', 0, current_equipment)
    return current_equipment - retirement


def retirement_cost(retirement: int) -> Fraction:
    """Cost for ONE period's retirement; also used for forced retirement."""
    _integer_in_range(retirement, 'retirement', 0, K0)
    return COST_FACTOR * retirement ** 2


def main_fine(equipment: int) -> Fraction:
    """Own fine amount conditional on enforcement; zero equipment is exempt."""
    _integer_in_range(equipment, 'equipment', 0, K0)
    return MAIN_FINE_BASE + MAIN_FINE_PER_UNIT * equipment if equipment else Fraction(0)


def main_enforcement_applies(
    branch: str, *, group_total: int | None = None,
    ambiguity_threshold: int | None = None,
) -> bool:
    """Whether Main enforcement is active, separately from own zero exemption.

    F always enforces and needs no group total/threshold. E/M use fixed 45.
    A requires an externally supplied integer threshold in 40–50. For E/M/A,
    pass the sum of all SIX post-voluntary Main equipment levels, not a mean
    or a rounded display value. Equality triggers enforcement. A supplied total
    is validated even for F, but does not affect its enforcement condition.
    Policy transfers and threshold generation are outside this primitive.
    """
    if not isinstance(branch, str) or branch not in ('F', 'E', 'A', 'M'):
        raise ValueError('branch must be F, E, A, or M.')
    if group_total is not None or branch != 'F':
        _integer_in_range(group_total, 'group_total', 0, GROUP_SIZE * K0)
    if branch != 'A' and ambiguity_threshold is not None:
        raise ValueError('ambiguity_threshold is only applicable to A.')
    if branch == 'F':
        return True
    if branch == 'A':
        threshold = _integer_in_range(
            ambiguity_threshold, 'ambiguity_threshold',
            AMBIGUITY_THRESHOLD_LOW, AMBIGUITY_THRESHOLD_HIGH,
        )
    else:
        threshold = KNOWN_THRESHOLD
    return group_total <= GROUP_SIZE * threshold


@dataclass(frozen=True)
class FollowUpOutcome:
    pre_forced_equipment: int
    follow_up_fine: Fraction
    forced_retirement: int
    forced_retirement_cost: Fraction
    final_equipment: int


def follow_up_enforcement(equipment: int) -> FollowUpOutcome:
    """Apply Follow-up to equipment AFTER period-10 voluntary retirement.

    Components are returned separately; this function does not change a wallet
    or re-charge the period's voluntary retirement cost.
    """
    _integer_in_range(equipment, 'equipment', 0, K0)
    return FollowUpOutcome(
        pre_forced_equipment=equipment,
        follow_up_fine=FOLLOW_UP_FINE if equipment else Fraction(0),
        forced_retirement=equipment,
        forced_retirement_cost=retirement_cost(equipment),
        final_equipment=0,
    )


def _money(value, name: str) -> Fraction:
    if type(value) is int or isinstance(value, Fraction):
        return Fraction(value)
    if isinstance(value, Decimal) and value.is_finite():
        return Fraction(value)
    raise ValueError(f'{name} must be an integer, Fraction, or finite Decimal.')


def wallet_after_deductions(wallet, *deductions) -> Fraction:
    """Subtract nonnegative costs/fines exactly, accepting signed balances.

    There is no liquidity check, zero clipping, floor or cap. Callers pass
    individual voluntary/forced costs and fines; no settlement is implicit.
    """
    balance = _money(wallet, 'wallet')
    for deduction in deductions:
        amount = _money(deduction, 'deduction')
        if amount < 0:
            raise ValueError('deduction must be nonnegative.')
        balance -= amount
    return balance
