"""Bucket integration tests: run only in a disposable oTree project copy."""
import copy
import json
import re
import unittest
from fractions import Fraction
from unittest.mock import patch
import test_fixed
from otree.database import db
from otree.session import SESSION_CONFIGS_DICT
from otree.lookup import _get_session_lookups
from otree.export import get_rows_for_wide_csv
from otree.asgi import app
from starlette.testclient import TestClient
from test_lab_production import make_production_session
import bucket
import lab_cash
import lab_payment
import lab_route
import lab_export
import lab_production


class BucketTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.session = make_production_session()
        self.players = bucket.Player.objects_filter(session=self.session).all()

    def tearDown(self):
        db.rollback()

    def allocate(self, p, blue, yellow):
        bucket.start(p, now=1000)
        for i,color in enumerate(['blue']*blue+['yellow']*yellow,1):
            bucket.receive(p, dict(action='allocate',bucket=color,expected_index=i), now=1000+i)
        return bucket.state(p, now=1051)

    def position(self,p,page):
        pp=p.participant
        pp._index_in_pages=next(i for i,row in _get_session_lookups(self.session.code).items() if row.app_name==p.subsession.get_folder_name() and row.page_class is page)
        pp._current_app_name=p.subsession.get_folder_name();pp._current_page_name=page.__name__;pp._round_number=1;pp.visited=True
        pp._timeout_expiration_time=None;pp._timeout_page_index=None;db.commit()
        return self.client.get(pp._start_url(),allow_redirects=True)

    def test_exact_economics_and_history(self):
        for p,(blue,yellow,cents) in zip(self.players,[(50,0,250),(0,50,500),(25,25,375),(17,33,415)]):
            state=self.allocate(p,blue,yellow)
            self.assertEqual(p.bucket_payoff_cents,cents)
            self.assertEqual(p.balls_placed,50);self.assertTrue(state['done']);self.assertFalse(p.timed_out)
            self.assertEqual(len(json.loads(p.allocation_sequence)),50)
            self.assertEqual(json.loads(p.allocation_times),list(range(1,51)))
            self.assertEqual(p.payoff,0)
            self.assertEqual(bucket.payment_bonus(p.participant),cents)

    def test_duplicate_malformed_out_of_order_and_reload_are_inert(self):
        p=self.players[0];bucket.start(p,now=1000)
        msg=dict(action='allocate',bucket='blue',expected_index=1)
        bucket.receive(p,msg,now=1001)
        before=(p.balls_blue,p.balls_yellow,p.bucket_payoff_cents,p.allocation_sequence,p.allocation_times)
        for data in [msg,None,[],{},dict(msg,expected_index=True),dict(msg,expected_index=3),dict(msg,bucket='red',expected_index=2)]:
            bucket.receive(p,data,now=1002)
            self.assertEqual(before,(p.balls_blue,p.balls_yellow,p.bucket_payoff_cents,p.allocation_sequence,p.allocation_times))
        db.expire_all();p=bucket.Player.objects_get(id=p.id)
        bucket.start(p,now=1100)
        self.assertEqual(p.task_deadline,1300);self.assertEqual(p.task_started_at,1000)
        self.assertEqual(bucket.receive(p,dict(action='sync'),now=1100)['seconds_remaining'],200)
        bucket.receive(p,dict(action='allocate',bucket='yellow',expected_index=2),now=1101)
        self.assertEqual((p.balls_placed,p.bucket_payoff_cents),(2,15))

    def test_timeout_preserves_partial_bonus_and_blocks_late_drop(self):
        for p,n in zip(self.players,[0,3]):
            self.allocate(p,n,0)
            result=bucket.receive(p,dict(action='allocate',bucket='yellow',expected_index=n+1),now=1300)
            self.assertTrue(result['done']);self.assertTrue(p.timed_out)
            self.assertEqual((p.balls_placed,p.bucket_payoff_cents),(n,5*n))
            self.assertEqual(bucket.payment_bonus(p.participant),5*n)
            bucket.receive(p,dict(action='allocate',bucket='blue',expected_index=n+1),now=1400)
            self.assertEqual(p.balls_placed,n)

    def test_routes_and_no_waits(self):
        from otree.api import WaitPage
        self.assertEqual(bucket.C.NUM_ROUNDS,1);self.assertIsNone(bucket.C.PLAYERS_PER_GROUP)
        self.assertEqual([p.__name__ for p in bucket.page_sequence],['BucketInstructions','BucketTask','BucketComplete'])
        self.assertFalse(any(issubclass(p,WaitPage) for p in bucket.page_sequence))
        for branch in 'EAM':
            for size in (18,24):
                expected=['fixed',lab_route.BRANCH_APPS[branch],'policy','bucket','survey','lab_payment']
                self.assertEqual(next(c for c in lab_production.templates() if c['name']==f'lab_{branch}_{size}')['app_sequence'],expected)
                self.assertEqual(SESSION_CONFIGS_DICT[f'dev_lab_full_{branch}_{size}']['app_sequence'],expected)
                production=make_production_session(branch,size)
                self.assertEqual(bucket.Player.objects_filter(session=production).count(),size)
                from otree.session import create_session
                development=create_session(f'dev_lab_full_{branch}_{size}',num_participants=size)
                self.assertEqual(bucket.Player.objects_filter(session=development).count(),size)

    def test_native_websocket_replay_completion_and_survey_transition(self):
        p=self.players[0]
        self.assertIsNone(p.field_maybe_none('task_deadline'))
        response=self.position(p,bucket.BucketInstructions)
        self.assertIn('Ultimo task individuale',response.text)
        response=self.client.post(str(response.url),data={},allow_redirects=True);db.expire_all()
        self.assertIn('/BucketTask/',str(response.url));deadline=p.task_deadline
        match=re.search(r'id="otree-live" data-socket-url="([^"]+)"',response.text)
        self.assertIsNotNone(match)
        import html
        with self.client.websocket_connect(html.unescape(match[1])) as socket:
            for i in range(1,51):
                msg=dict(action='allocate',bucket='blue' if i%2 else 'yellow',expected_index=i)
                socket.send_json(msg);state=socket.receive_json()['live_method_payload'];self.assertEqual(state['balls_placed'],i)
                socket.send_json(msg);again=socket.receive_json()['live_method_payload'];self.assertEqual(again['balls_placed'],i)
        db.expire_all();self.assertEqual(p.bucket_payoff_cents,375);self.assertTrue(p.completed)
        self.assertEqual(p.task_deadline,deadline)
        response=self.client.post(str(response.url),data={},allow_redirects=True)
        self.assertIn('/BucketComplete/',str(response.url))
        response=self.client.post(str(response.url),data={},allow_redirects=True)
        self.assertIn('/survey/SurveyWelcome/',str(response.url))
        rows=get_rows_for_wide_csv(self.session.code)
        for name in ['balls_blue','balls_yellow','balls_placed','bucket_payoff_cents','timed_out','allocation_sequence','allocation_times']:
            self.assertIn('bucket.1.player.'+name,rows[0])

    def test_actual_payment_once_signed_wallet_and_export_decomposition(self):
        lab_route.block_subsession(self.session,9,last=True).block_barrier_complete=True
        for p,(wallet,blue,yellow,expected) in zip(self.players,[('500/1',50,0,1550),('500/1',0,50,1800),('500/1',25,25,1675),('-300/1',25,25,875),('500/1',0,0,1300)]):
            self.allocate(p,blue,yellow)
            if not p.completed:bucket.receive(p,dict(action='sync'),now=1300)
            p.participant.vars[lab_cash.WALLETS_KEY]={str(b):wallet for b in range(1,10)};db.commit()
            pay=lab_payment.Player.objects_get(participant=p.participant,round_number=1)
            context=lab_payment.Payment.vars_for_template(pay)
            self.assertEqual(pay.final_eur_cents,expected)
            self.assertEqual(pay.bucket_payoff_cents,p.bucket_payoff_cents)
            self.assertEqual(p.payoff,0)
            self.assertEqual(p.participant.payoff,expected-800)
            self.assertEqual(context,lab_payment.Payment.vars_for_template(pay))
            row=lab_export._payment_row(pay,{})
            self.assertEqual(row['bucket_payoff_cents'],p.bucket_payoff_cents)
            self.assertEqual(row['final_eur_cents'],expected)
            base=lab_cash.calculate_payment(p.participant.vars[lab_cash.WALLETS_KEY],self.session.config['paid_block'])
            self.assertEqual(expected,base['final_eur_cents']+p.bucket_payoff_cents)

    def test_early_post_blocked_and_deadline_refresh_unchanged(self):
        p=self.players[0];r=self.position(p,bucket.BucketInstructions)
        r=self.client.post(str(r.url),data={},allow_redirects=True);db.expire_all();deadline=p.task_deadline
        for data in ({}, {'timeout_happened':'1'}):
            r=self.client.post(str(r.url),data=data,allow_redirects=True)
            self.assertIn('/BucketTask/',str(r.url))
        self.client.get(str(r.url));db.expire_all();self.assertEqual(p.task_deadline,deadline)
        p.task_deadline=__import__('time').time()-1;db.commit()
        r=self.client.post(str(r.url),data={'timeout_happened':'1'},allow_redirects=True);db.expire_all()
        self.assertIn('/BucketComplete/',str(r.url));self.assertTrue(p.timed_out);self.assertEqual(p.bucket_payoff_cents,0)

    def test_unfinished_bonus_blocks_payment_and_bot_uses_native_callbacks(self):
        p=self.players[0]
        lab_route.block_subsession(self.session,9,last=True).block_barrier_complete=True
        p.participant.vars[lab_cash.WALLETS_KEY]={str(b):'500/1' for b in range(1,10)}
        db.commit()
        pay=lab_payment.Player.objects_get(participant=p.participant,round_number=1)
        with self.assertRaisesRegex(ValueError,'completed'):
            lab_payment.Payment.vars_for_template(pay)
        # The production snapshot deliberately omits app bot fixtures.
        # The unfinished-payment check above always executes.
        if not __import__('pathlib').Path('bucket/tests.py').is_file():
            self.skipTest('Historical bucket/tests.py bot fixture absent; live allocation/payment checks run independently.')
        from bucket.tests import PlayerBot
        bot=PlayerBot(case_number=0,app_name='bucket',player_pk=p.id,subsession_pk=p.subsession.id,session_pk=self.session.id,participant_code=p.participant.code)
        steps=bot.play_round()
        self.assertIs(next(steps),bucket.BucketInstructions)
        bucket.BucketInstructions.before_next_page(p,False)
        next(steps)  # fifty native live callbacks, then BucketTask submission
        self.assertEqual((p.balls_blue,p.balls_placed,p.bucket_payoff_cents),(50,50,250))
        self.assertIs(next(steps),bucket.BucketComplete)
        self.assertEqual(p.payoff,0)
