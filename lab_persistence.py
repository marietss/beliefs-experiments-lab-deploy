"""Lossless rational boundary for oTree text fields and JSON session values.

Canonical `numerator/denominator` text uses reduced arbitrary-size integers,
positive denominators, and `0/1` for zero. It supports signed wallets and future
thirds without floats, display rounding, or database integer-size assumptions.
"""

from fractions import Fraction
import re


def encode_fraction(value: Fraction | int) -> str:
    if type(value) is not int and not isinstance(value, Fraction):
        raise ValueError('Exact persistence requires an int or Fraction.')
    value = Fraction(value)
    return f'{value.numerator}/{value.denominator}'


def decode_fraction(value: str) -> Fraction:
    if type(value) is not str or not re.fullmatch(r'-?(0|[1-9][0-9]*)/[1-9][0-9]*', value):
        raise ValueError('Invalid canonical rational text.')
    numerator, denominator = value.split('/')
    result = Fraction(int(numerator), int(denominator))
    if encode_fraction(result) != value:
        raise ValueError('Rational text must be reduced and canonical.')
    return result
