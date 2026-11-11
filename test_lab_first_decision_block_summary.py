"""Focused local-period timing, restored block-summary and native flow regressions.

Use an isolated development/in-memory project copy, never a production database.
"""
from collections import Counter
from fractions import Fraction
import re
import unittest

import test_fixed
from otree.database import db
from otree.lookup import _get_session_lookups
from otree.common import CSRF_TOKEN_NAME
from otree.export import get_rows_for_wide_csv
from test_lab_ui_timing_refinements import RefinementTests
from test_lab_decision_ui import environments
from test_lab_production import make_production_session
from test_fixed_browser import CHROME
import lab_cash
import lab_route
from lab_persistence import decode_fraction


class FirstDecisionTests(unittest.TestCase):
    setUp=RefinementTests.setUp
    tearDown=RefinementTests.tearDown
    open_page=RefinementTests.open_page
    post=RefinementTests.post
    refresh=RefinementTests.refresh
    expire=RefinementTests.expire
    browser=RefinementTests.browser

    def test_local_period_timing_all_blocks_all_production_and_dev_routes(self):
        from otree.session import create_session
        for production in (True,False):
            for branch in 'EAM':
                for size in (18,24):
                    session=make_production_session(branch,size) if production else create_session(f'dev_lab_full_{branch}_{size}',num_participants=size)
                    for block in range(1,10):
                        ss=lab_route.block_subsession(session,block)
                        app=lab_route._app(ss.get_folder_name())
                        for r in range(ss.round_number,ss.round_number+10):
                            p=ss.in_round(r).get_players()[0]
                            self.assertEqual(p.global_block,block)
                            self.assertEqual(p.period,r-ss.round_number+1)
                            self.assertEqual(app.Decision.get_timeout_seconds(p),40 if p.period==1 else 30)
                            self.assertEqual(app.Result.get_timeout_seconds(p),60 if p.period in (5,10) else 20)
                        self.assertEqual(app.Reports.timeout_seconds,120)
                        self.assertEqual(app.BlockStart.timeout_seconds,60)
                        self.assertEqual(app.BlockEnd.timeout_seconds,30)
                        self.assertIn(app.BlockEnd,app.page_sequence)
                        self.assertEqual(app.page_sequence[-2:], [app.BlockEndWait, app.BlockEnd])
                        self.assertTrue(app.MainCheckWait.wait_for_all_groups)
                        self.assertTrue(app.BlockEndWait.wait_for_all_groups)
                    self.assertEqual(session.config['app_sequence'][-3:],['bucket','survey','lab_payment'])
                    import fixed
                    self.assertEqual(fixed.PracticeDecision.timeout_seconds,60)
                    db.rollback()

    def test_native_decision_timeout_zero_early_submission_and_period_results(self):
        for app,helpers,branch in environments():
            session=helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            group=helpers.subsession(session).get_groups()[0]
            helpers.reports(group)
            for r in (1,2):
                group=helpers.subsession(session,r).get_groups()[0]
                for i,p in enumerate(group.get_players()):
                    response=self.open_page(p,app.Decision)
                    self.assertIn(f'var remainingTimeoutSeconds = {40 if r==1 else 30}',response.text)
                    if i==0:
                        self.expire(p)
                        self.post(response,dict(retirement=17,timeout_happened=1))
                        expected=0
                    else:
                        self.post(response,dict(retirement=10))
                        expected=10
                    self.assertEqual((p.retirement,p.locked_retirement),(expected,expected))
                self.assertTrue(group.settlement_complete)
                for p in group.get_players():
                    html=self.open_page(p,app.Result).text
                    self.assertIn('I tuoi risultati',html)
                    self.assertNotIn('Riepilogo del Blocco',html)
                    self.assertEqual(decode_fraction(p.voluntary_cost),0 if p.id_in_group==1 else 10)
            db.rollback()

    @unittest.skipUnless(CHROME,'Chrome unavailable')
    def test_browser_countdown_and_preserved_main_followup_feedback(self):
        import fixed
        session=test_fixed.make_session();test_fixed.ready(session)
        g=test_fixed.subsession(session).get_groups()[0];test_fixed.reports(g)
        for r in range(1,11):
            p=test_fixed.subsession(session,r).get_groups()[0].get_players()[0]
            if r in (1,2,10):
                html=self.open_page(p,fixed.Decision).text
                for width in (1366,650):
                    self.browser(html,"""
                        const script=[...document.scripts].map(s=>s.textContent).join('');
                        assert(script.includes('var remainingTimeoutSeconds = SECONDS'),'native Decision duration');
                        const button=document.querySelector('#confirm-retirement');
                        assert(button && button.disabled,'existing deliberate choice unchanged');
                        let count=0;$('#form').on('submit',e=>{count++;e.preventDefault();});
                        $('.otree-timer__time-left').trigger('finish.countdown');
                        assert(count===1,'native timeout submits');
                        assert(document.querySelector('[name=timeout_happened]').value==='1','native timeout flag');
                        assert(document.documentElement.scrollWidth<=innerWidth,'no overflow');
                    """.replace('SECONDS',str(40 if r==1 else 30)),width)
            test_fixed.run_period(p.group)
            if r in (5,10):
                html=self.open_page(p,fixed.Result).text
                for width in (1366,650):
                    self.browser(html,"""
                        assert(document.querySelector('#settled-wallet'),'period wallet retained');
                        assert(document.querySelector('button[type=submit]').textContent==='Continua','early Continue retained');
                        assert(!document.querySelector('.block-group-summary'),'no extra block summary');
                        assert(document.body.innerText.includes('HEADING'),'check feedback retained');
                    """.replace('HEADING','Accertamento principale — Periodo 5' if r==5 else "Esito dell\\'accertamento finale"),width)

    def test_full_native_E18_nine_blocks_bucket_survey_payment_and_export(self):
        import bucket,survey
        import lab_comprehension
        from test_lab_survey import ANSWERS
        session=make_production_session('E',18)
        people=session.get_participants();db.commit()
        lookups=_get_session_lookups(session.code)
        counts=Counter();main=Counter();follow=Counter();summaries=Counter();visited=set()
        for step in range(400):
            gate=False;done=0
            for pp in people:
                response=self.client.get(pp._start_url(),allow_redirects=True)
                self.assertEqual(response.status_code,200)
                db.expire_all()
                name=pp._current_page_name;app_name=pp._current_app_name
                if app_name=='lab_payment':
                    done+=1
                    self.assertIn('id="earnings-summary"',response.text)
                    continue
                self.assertNotIn('id="earnings-summary"',response.text)
                self.assertNotIn('paid_block',response.text)
                row=lookups[pp._index_in_pages];page=row.page_class
                if name in ('ExperimentSplash','SectionSplash','FirstBlockSplash','PracticeComplete'):
                    gate=True;continue
                from otree.api import WaitPage
                if issubclass(page,WaitPage):continue
                app=lab_route._app(app_name)
                p=app.Player.objects_get(participant=pp,round_number=row.round_number)
                data={}
                if name.startswith('SectionComprehension'):
                    data={q['field']:q['correct'] for q in lab_comprehension.pair_questions(p,page.pair_number)}
                elif name=='PracticeDecision':
                    self.assertEqual(app.PracticeDecision.timeout_seconds,60)
                    remaining=float(re.search(r'var remainingTimeoutSeconds = ([0-9.]+)',response.text)[1])
                    self.assertTrue(0<remaining<=60)
                    self.expire(p);data=dict(timeout_happened=1)
                elif name=='Reports':
                    data=dict(expected_own_equipment_main=50,expected_group_average_main=50)
                elif name=='Decision':
                    duration=40 if p.period==1 else 30
                    self.assertEqual(app.Decision.get_timeout_seconds(p),duration)
                    remaining=float(re.search(r'var remainingTimeoutSeconds = ([0-9.]+)',response.text)[1])
                    self.assertTrue(0<remaining<=duration)
                    data=dict(retirement=10);counts[pp.code]+=1
                elif name=='Result':
                    duration=60 if p.period in (5,10) else 20
                    remaining=float(re.search(r'var remainingTimeoutSeconds = ([0-9.]+)',response.text)[1])
                    self.assertTrue(0<remaining<=duration)
                    if p.period in (5,10) and pp.id_in_session==1:
                        self.expire(p);data=dict(timeout_happened=1)
                    if p.period==5:
                        main[pp.code]+=1
                        self.assertIn('Accertamento principale — Periodo 5',response.text)
                    if p.period==10:
                        follow[pp.code]+=1
                        self.assertIn("Esito dell'accertamento finale",response.text)
                        self.assertTrue(p.final_block_wallet)
                elif name=='BlockEnd':
                    self.assertEqual(app.BlockEnd.timeout_seconds,30)
                    remaining=float(re.search(r'var remainingTimeoutSeconds = ([0-9.]+)',response.text)[1])
                    self.assertTrue(0<remaining<=30)
                    if pp.id_in_session==1:
                        self.expire(p);data=dict(timeout_happened=1)
                    summaries[pp.code]+=1
                    self.assertIn('Il tuo portafoglio alla fine del blocco è di',response.text)
                    self.assertNotIn("Attrezzatura all'accertamento principale",response.text)
                elif name=='BucketTask':
                    for i in range(1,51):bucket.receive(p,dict(action='allocate',bucket='blue',expected_index=i))
                    db.commit()
                elif app_name=='survey':
                    fields=page.get_form_fields(p) if hasattr(page,'get_form_fields') else getattr(page,'form_fields',[])
                    data={f:ANSWERS[f] for f in fields}
                visited.add((app_name,name))
                self.post(response,data)
            if done==18:break
            if gate:
                admin=self.client.get('/sessions')
                token=re.search(r'name="'+CSRF_TOKEN_NAME+r'" value="([^"]+)"',admin.text)[1]
                self.assertEqual(self.client.post('/AdvanceSession/'+session.code,data={'advancemode':'visited_only',CSRF_TOKEN_NAME:token}).status_code,200)
                db.expire_all()
        else:self.fail('Native complete route did not finish')
        for pp in people:
            self.assertEqual(counts[pp.code],90)
            self.assertEqual(summaries[pp.code],9)
            self.assertEqual(main[pp.code],9);self.assertEqual(follow[pp.code],9)
            self.assertEqual(len(pp.vars[lab_cash.WALLETS_KEY]),9)
            record=pp.vars[lab_cash.PAYMENT_KEY]
            self.assertEqual(record['paid_block'],session.config['paid_block'])
            self.assertEqual(decode_fraction(record['selected_wallet']),900)
            self.assertEqual(record['bucket_payoff_cents'],250)
            self.assertEqual(record['final_eur_cents'],1950)
        for page in ('BucketInstructions','BucketTask','BucketComplete'):self.assertIn(('bucket',page),visited)
        self.assertIn(('survey','Preferences2'),visited)
        rows=list(get_rows_for_wide_csv(session.code));header=rows[0]
        for app_name in ('fixed','endogenous','policy'):
            for r in (10,20,30):
                field=f'{app_name}.{r}.player.final_block_wallet'
                index=header.index(field)
                self.assertTrue(all(str(row[index]) not in ('','None') for row in rows[1:]))
        for block in range(1,10):
            ss=lab_route.block_subsession(session,block)
            end=ss.in_round(ss.round_number+9)
            self.assertTrue(end.block_barrier_complete)
        print('Native E18: 18 participants × 90 decisions, all Main/Follow-up Results, bucket, survey, payment, wide export verified.',flush=True)
