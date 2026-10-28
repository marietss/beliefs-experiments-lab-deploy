"""Minimal laboratory payment receipt, separate from the legacy online end app."""
from otree.api import BaseConstants, BaseSubsession, BaseGroup, BasePlayer, Page, models

# The pure helper has a distinct module name to avoid app/module shadowing.
import lab_cash as cash
import lab_route
from lab_persistence import decode_fraction
from lab_presentation import points


class C(BaseConstants):
    NAME_IN_URL = 'lab_payment'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    RECORD_FIELDS = ('paid_block', 'selected_wallet', 'conversion', 'fixed_fee',
                     'variable_eur', 'pre_round_eur', 'final_eur_cents',
                     'admin_payoff_points', 'rounding')
    finalized = models.BooleanField(initial=False)
    paid_block = models.IntegerField(blank=True)
    selected_wallet = models.LongStringField(initial='', blank=True)
    conversion = models.LongStringField(initial='', blank=True)
    fixed_fee = models.LongStringField(initial='', blank=True)
    variable_eur = models.LongStringField(initial='', blank=True)
    pre_round_eur = models.LongStringField(initial='', blank=True)
    final_eur_cents = models.IntegerField(blank=True)
    admin_payoff_points = models.IntegerField(blank=True)
    rounding = models.StringField(initial='', blank=True)


def creating_session(subsession):
    if subsession.session.config['app_sequence'] != lab_route.payment_sequence(subsession.session.config['branch']):
        raise ValueError('The laboratory payment app requires the complete payment route.')
    lab_route.validate_route(subsession.session.config, 'lab_payment')
    cash.initialize(subsession.session)


class Payment(Page):
    @staticmethod
    def vars_for_template(player):
        record = cash.finalize(player)
        return dict(
            selected_block=record['paid_block'],
            selected_wallet=points(decode_fraction(record['selected_wallet'])),
            fixed_fee=cash.cash_display(750),
            variable_eur=points(decode_fraction(record['variable_eur'])),
            total_eur=cash.cash_display(record['final_eur_cents']),
        )


page_sequence = [Payment]


# Installed oTree 6.0.15 discovers each custom_export_* function as a separate
# admin dataset. These adapters read all substantive apps through stored keys.
def custom_export_session(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'session')


def custom_export_membership(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'membership')


def custom_export_group_period(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'group_period')


def custom_export_period(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'period')


def custom_export_reports(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'reports')


def custom_export_messages(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'messages')


def custom_export_main_group(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'main_group')


def custom_export_main(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'main')


def custom_export_completion(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'completion')


def custom_export_ledger(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'ledger')


def custom_export_payment(players):
    from lab_export import custom_rows
    yield from custom_rows(players, 'payment')
