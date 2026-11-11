"""Real ORM, receipt, native HTTP and full-ledger tests in an isolated project."""
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

from test_lab_route import make_session, ready, finish_block, app_for, submit_reports, settle
from otree.database import db
from otree import settings
from otree.templating.template import Template
from otree.lookup import _get_session_lookups
from otree.common import participant_start_url
from otree.asgi import app as asgi_app
from starlette.testclient import TestClient
import lab_cash as cash
import lab_route as route
import lab_payment


def payment_player(session):
    return lab_payment.Player.objects_filter(session=session).first()


def finish_all(session, *, policy_fraction=False):
    ready(session)
    for block in range(1, 10):
        if block != 9 or not policy_fraction:
            finish_block(session, block)
            continue
        app = app_for(session, block)
        first = route.block_subsession(session, block)
        for group in first.get_groups(): submit_reports(app, group)
        for period in range(1, 11):
            ss = first.in_round(first.round_number + period - 1)
            for group in ss.get_groups():
                settle(app, group, [100, 100, 100, 60, 60, 59] if period == 1 else None)
        for p in ss.get_players(): app.BlockEnd.before_next_page(p, False)
        app.BlockEndWait.after_all_players_arrive(ss)

    import bucket
    for player in bucket.Player.objects_filter(session=session):
        bucket.start(player,now=1000)
        bucket.receive(player,dict(action='sync'),now=1300)


def render_payment(player):
    return Template(Path('lab_payment/Payment.html').read_text()).render(
        dict(player=player, **lab_payment.Payment.vars_for_template(player)))


class PaymentBackendTests(unittest.TestCase):
    def tearDown(self): db.rollback()

    def test_ledger_only_after_follow_up_and_conflicting_replay(self):
        session = make_session(paid_block=1); ready(session)
        first = route.block_subsession(session, 1)
        app = app_for(session, 1)
        for group in first.get_groups(): submit_reports(app, group)
        for period in range(1, 11):
            for group in first.in_round(period).get_groups():
                for p in group.get_players():
                    self.assertNotIn('1', p.participant.vars.get(cash.WALLETS_KEY, {}))
                settle(app, group)
        group = first.in_round(10).get_groups()[0]
        p = group.get_players()[0]
        self.assertEqual(p.participant.vars[cash.WALLETS_KEY], {'1': '-300/1'})
        before = dict(p.participant.vars[cash.WALLETS_KEY])
        app.PeriodWait.after_all_players_arrive(group)
        self.assertEqual(p.participant.vars[cash.WALLETS_KEY], before)
        p.participant.vars[cash.WALLETS_KEY] = {'1': '-249/1'}
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            app.PeriodWait.after_all_players_arrive(group)

    def test_all_six_routes_complete_exact_ledgers_and_policy_wallet_selection(self):
        for branch in ('E', 'A', 'M'):
            for size in (18, 24):
                session = make_session(branch, size)
                finish_all(session, policy_fraction=True)
                for p in lab_payment.Player.objects_filter(session=session):
                    ledger = cash.validate_wallets(p.participant.vars[cash.WALLETS_KEY], complete=True)
                    for block in range(1, 10):
                        app_name, start = route.block_location(session.config, block)
                        source = route._app(app_name).Player.objects_get(participant=p.participant, round_number=start+9)
                        self.assertEqual(ledger[str(block)], source.final_block_wallet)
                    result = cash.finalize(p)
                    self.assertEqual(result['selected_wallet'], ledger['9'])
                    self.assertEqual(Decimal(p.participant.payoff_plus_participation_fee()), Decimal(result['final_eur_cents'])/100)
                    self.assertEqual(cash.finalize(p), result)
                # Three recipients in every rematched policy group received 1171/20.
                group = route.block_subsession(session, 9).get_groups()[0]
                recipient = group.get_players()[0].participant
                p = lab_payment.Player.objects_get(participant=recipient)
                self.assertEqual(cash.decode_fraction(p.selected_wallet), Fraction(1171, 20))

    def test_negative_selected_wallet_receipt_and_admin_reload(self):
        session = make_session(paid_block=1); finish_all(session)
        p = payment_player(session)
        first = render_payment(p)
        self.assertIn('id="selected-block">1.1', first)
        self.assertIn('id="selected-wallet">-300 punti', first)
        self.assertIn('id="variable-payment">-€3', first)
        self.assertIn('id="total-payment">€5.00', first)
        self.assertEqual(first, render_payment(p))
        self.assertEqual(Decimal(p.payoff), -300)
        self.assertEqual(Decimal(p.participant.payoff_plus_participation_fee()), Decimal('5.00'))
        self.assertNotIn('Prolific', first); self.assertNotIn('GBP', first)

    def test_complete_barrier_and_complete_ledger_required(self):
        session = make_session(); p = payment_player(session)
        with self.assertRaisesRegex(ValueError, 'Block-9'): cash.finalize(p)
        finish_all(session)
        ledger = p.participant.vars[cash.WALLETS_KEY]
        p.participant.vars[cash.WALLETS_KEY] = {k:v for k,v in ledger.items() if k!='7'}
        with self.assertRaisesRegex(ValueError, 'missing'): cash.finalize(p)
        self.assertFalse(p.finalized)
        self.assertEqual(Decimal(p.participant.payoff), 0)

    def test_config_change_rejected_during_play_and_after_finalization(self):
        changes = ({'paid_block':8}, {'real_world_currency_per_point':.02}, {'participation_fee':7.5})
        for change in changes:
            session = make_session(); original = dict(session.config)
            session.config = {**original, **change}
            with self.assertRaisesRegex(ValueError, 'changed|requires'): cash.checked_config(session)
            session.config = original
        session = make_session(); finish_all(session); p = payment_player(session)
        cash.finalize(p)
        for change in changes:
            original = dict(session.config); session.config = {**original, **change}
            with self.assertRaisesRegex(ValueError, 'changed|requires'): cash.finalize(p)
            session.config = original
        ledger = p.participant.vars[cash.WALLETS_KEY]
        p.participant.vars[cash.WALLETS_KEY] = {**ledger, '9':'0/1'}
        with self.assertRaisesRegex(ValueError, 'changed'): cash.finalize(p)

    def test_oTree_admin_half_cent_rounding_reconciles_exact_total(self):
        session = make_session(); finish_all(session)
        examples = (Fraction(4999,10000),Fraction(1,2),Fraction(5001,10000),
                    Fraction(-1,2),Fraction(-1501,2),Fraction(5671,18))
        for p, wallet in zip(lab_payment.Player.objects_filter(session=session), examples):
            # Explicit backend payment fixture: replace selected primitive before
            # any finalization; ordinary ledger writes never permit this overwrite.
            p.participant.vars[cash.WALLETS_KEY] = {**p.participant.vars[cash.WALLETS_KEY], '9':cash.encode_fraction(wallet)}
            result = cash.finalize(p)
            self.assertEqual(Decimal(p.participant.payoff_plus_participation_fee()), Decimal(cash.euro_cents(Fraction(8)+wallet/100))/100)
            self.assertEqual(cash.decode_fraction(result['selected_wallet']), wallet)
            self.assertEqual(cash.finalize(p), result)

    def test_finalization_commits_marker_record_and_payoff_together(self):
        session = make_session(); finish_all(session); p = payment_player(session)
        from otree.models.player import BasePlayer
        original = BasePlayer.payoff.fset
        def observing_setter(player, value):
            self.assertTrue(player.finalized)
            self.assertEqual(player.participant.vars[cash.PAYMENT_KEY]['admin_payoff_points'], value)
            return original(player, value)
        with patch.object(BasePlayer, 'payoff', property(BasePlayer.payoff.fget, observing_setter)):
            cash.finalize(p)
        db.expire_all()
        self.assertTrue(p.finalized)
        self.assertEqual(cash.finalize(p)['final_eur_cents'], p.final_eur_cents)

    def test_EUR_mode_required_without_changing_legacy_default(self):
        with patch.object(settings,'REAL_WORLD_CURRENCY_CODE','GBP'):
            with self.assertRaisesRegex(ValueError, 'OTREE_LAB_PAYMENTS'):
                make_session()
        db.rollback()


class PaymentHTTPTests(unittest.TestCase):
    def tearDown(self): db.rollback()

    def test_terminal_receipt_native_http_reload_negative_wallet_and_secrecy(self):
        session = make_session('A', paid_block=1); finish_all(session)
        p = payment_player(session); pp = p.participant
        lookups = _get_session_lookups(session.code)
        index = next(i for i,row in lookups.items() if row.page_class is lab_payment.Payment)
        pp._index_in_pages=index; pp.visited=True
        pp._current_app_name='lab_payment'; pp._round_number=1; pp._current_page_name='Payment'
        db.commit()
        client=TestClient(asgi_app)
        response=client.get(participant_start_url(pp.code),allow_redirects=True)
        db.expire_all()  # HTTP callback commits in the ASGI thread; reload ORM snapshots.
        self.assertEqual(response.status_code,200)
        self.assertIn('id="selected-wallet">-300 punti',response.text)
        self.assertIn('id="total-payment">€5.00',response.text)
        before=dict(pp.vars[cash.PAYMENT_KEY]); payoff=Decimal(pp.payoff)
        for _ in range(3):
            response=client.get(str(response.url),allow_redirects=True)
            db.expire_all()
            self.assertEqual(response.status_code,200)
            self.assertIn('id="total-payment">€5.00',response.text)
        db.expire_all()
        self.assertEqual(pp.vars[cash.PAYMENT_KEY],before)
        self.assertEqual(Decimal(pp.payoff),payoff)
        self.assertNotIn('ambiguity_thresholds',response.text)
        for other in session.get_participants():
            if other.code!=pp.code:self.assertNotIn(other.code,response.text)

    def test_pre_end_context_and_HTML_hide_selection_across_all_five_apps(self):
        for branch in ('E','A','M'):
            session=make_session(branch,paid_block=7); ready(session)
            for block in range(1,10):
                app=app_for(session,block); first=route.block_subsession(session,block)
                for group in first.get_groups():
                    p=group.get_players()[0]
                    for page in (app.BlockStart,app.Reports):
                        context=page.vars_for_template(p) if hasattr(page,'vars_for_template') else {}
                        self.assertFalse({'paid_block','selected_block','selected_wallet'} & set(context))
                    submit_reports(app,group)
                    context=app.Decision.vars_for_template(p)
                    self.assertFalse({'paid_block','selected_block','selected_wallet'} & set(context))
                    from otree.forms.forms import get_form
                    context.update(player=p,form=get_form(p,['retirement'],app.Decision,None))
                    html=Template(Path(f'{app.__name__}/Decision.html').read_text()).render(context)
                    for phrase in ('paid_block','selected block','selected_wallet','lab_final_payment','lab_payment_config'):
                        self.assertNotIn(phrase,html.lower())
                # Complete this block without recollecting locked reports.
                for r in range(first.round_number,first.round_number+10):
                    ss=first.in_round(r)
                    for group in ss.get_groups():settle(app,group)
                for p in ss.get_players():app.BlockEnd.before_next_page(p,False)
                app.BlockEndWait.after_all_players_arrive(ss)


if __name__=='__main__':unittest.main()
