"""Pure validation of externally supplied lab session configuration.

This module has no oTree dependencies and is not wired into session creation.
"""

from collections.abc import Mapping
from decimal import Decimal
from fractions import Fraction
from math import isfinite
from numbers import Real


DEFAULT_RHO = Fraction(1, 3)
AMBIGUITY_BLOCK_KEYS = frozenset(str(block) for block in range(4, 10))


def validate_lab_config(config: Mapping) -> dict:
    """Return a validated copy, or raise ValueError naming the invalid field.

    All fields except ambiguity_thresholds are required, including rho: use
    DEFAULT_RHO explicitly for the current design. Seeds must be integers
    (excluding bool) or nonblank strings; no seed or thresholds are generated.
    Rho accepts real numbers and Decimal, excluding bool and nonfinite values;
    its original precision/type is preserved. E/M may omit thresholds or supply
    an empty mapping. Other session-config keys are preserved, not validated.
    Neither the input mapping nor its threshold mapping is mutated or returned
    by reference (other extra values are only shallow-copied).
    """
    if not isinstance(config, Mapping):
        raise ValueError('lab config must be a mapping.')

    size = config.get('lab_session_size')
    if type(size) is not int or size not in (18, 24):
        raise ValueError('lab_session_size must be an integer equal to 18 or 24.')

    branch = config.get('branch')
    if not isinstance(branch, str) or branch not in ('E', 'A', 'M'):
        raise ValueError('branch must be E, A, or M.')

    paid_block = config.get('paid_block')
    if type(paid_block) is not int or not 1 <= paid_block <= 9:
        raise ValueError('paid_block must be an integer from 1 through 9.')

    rho = config.get('rho')
    # Check Decimal finiteness before comparisons, which can raise for NaN.
    # For Real, range-check first to reject huge integers without float overflow.
    if isinstance(rho, Decimal):
        valid_rho = rho.is_finite() and 0 <= rho <= 1
    else:
        valid_rho = (
            isinstance(rho, Real)
            and not isinstance(rho, bool)
            and 0 <= rho <= 1
            and isfinite(rho)
        )
    if not valid_rho:
        raise ValueError('rho must be a finite real numeric value from 0 through 1.')

    seed = config.get('matching_seed')
    if not (
        type(seed) is int
        or isinstance(seed, str) and bool(seed.strip())
    ):
        raise ValueError('matching_seed must be an explicit integer or nonblank string.')

    thresholds = config.get('ambiguity_thresholds', {})
    if not isinstance(thresholds, Mapping):
        raise ValueError('ambiguity_thresholds must be a mapping.')
    if branch == 'A':
        if set(thresholds) != AMBIGUITY_BLOCK_KEYS:
            raise ValueError(
                'ambiguity_thresholds for A must have exactly string keys 4 through 9.'
            )
        if any(type(value) is not int or not 40 <= value <= 50
               for value in thresholds.values()):
            raise ValueError(
                'ambiguity_thresholds values must be integers from 40 through 50.'
            )
    elif thresholds:
        raise ValueError('ambiguity_thresholds must be empty or omitted for E/M.')

    validated = dict(config)
    validated['ambiguity_thresholds'] = dict(thresholds)
    return validated
