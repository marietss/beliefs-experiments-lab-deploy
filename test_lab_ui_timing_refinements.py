"""Native timing/barrier regressions; run in an isolated oTree development copy."""
import copy
import hashlib
from fractions import Fraction
import json
from pathlib import Path
import re
import time
import unittest

import test_fixed
from otree.asgi import app as asgi
from otree.constants import wait_page_http_header
from otree.database import db
from starlette.testclient import TestClient
from test_lab_reports_footer_timing import PilotRefinementTests
from test_lab_decision_ui import environments
from test_fixed_browser import CHROME
import lab_instructions
import lab_reports
import lab_rules
from lab_persistence import decode_fraction


class RefinementTests(unittest.TestCase):
    open_page = PilotRefinementTests.open_page
    browser = PilotRefinementTests.browser

    def setUp(self):
        self.client = TestClient(asgi)

    def tearDown(self):
        db.rollback()

    def post(self, response, data=None):
        result = self.client.post(str(response.url), data=data or {}, allow_redirects=True)
        self.assertEqual(result.status_code, 200)
        db.expire_all()
        return result

    def refresh(self, response):
        result = self.client.get(str(response.url), allow_redirects=True)
        self.assertEqual(result.status_code, 200)
        db.expire_all()
        return result

    def expire(self, player):
        pp = player.participant
        pp._timeout_expiration_time = time.time() - 1
        pp._timeout_page_index = pp._index_in_pages
        db.commit()

    def test_report_manual_timeout_idempotence_six_public_values_and_next_block(self):
        for app, helpers, branch in environments():
            with self.subTest(app=app.__name__, branch=branch):
                session = helpers.make_session(branch) if branch else helpers.make_session()
                helpers.ready(session)
                group = helpers.subsession(session).get_groups()[0]
                responses = []
                for i, player in enumerate(group.get_players()):
                    response = self.open_page(player, app.Reports)
                    self.assertIn('var remainingTimeoutSeconds = 120', response.text)
                    if i == 0:
                        # Even partially selected values must become explicit 0/0.
                        self.expire(player)
                        result = self.post(response, dict(timeout_happened=1,
                            expected_own_equipment_main=84, expected_group_average_main=''))
                        expected = (0, 0)
                    else:
                        result = self.post(response, dict(expected_own_equipment_main=10*i,
                                                          expected_group_average_main=91+i))
                        expected = (10*i, 91+i)
                    self.assertEqual((player.expected_own_equipment_main, player.expected_group_average_main), expected)
                    self.assertTrue(player.reports_submitted)
                    # A duplicated handler and stale native timeout POST cannot overwrite answers.
                    app.Reports.before_next_page(player, True)
                    db.commit()
                    self.post(response, dict(timeout_happened=1))
                    self.assertEqual((player.expected_own_equipment_main, player.expected_group_average_main), expected)
                    responses.append(result)
                for response in responses:
                    self.assertIn('id="confirm-retirement"', self.refresh(response).text)
                self.assertTrue(group.reports_complete)
                if app.__name__ == 'messages' or branch == 'M':
                    self.assertEqual(lab_reports.read_public_plans(group.get_players()[0]), [0,10,20,30,40,50])
                    self.assertEqual(lab_reports.read(group.get_players()[0]), 25)
                    record = json.loads(group.public_report_record)
                    self.assertEqual(len(record['report1']), 6)
                    self.assertNotIn('report2', record)
                    payload = json.loads(re.search(r'id="lab-chart-config" type="application/json">(.*?)</script>', self.refresh(responses[0]).text, re.S)[1])
                    self.assertEqual(payload['publicReportPlans'], [0,10,20,30,40,50])
                    self.assertEqual(payload['publicReportMean'], 25)
                    self.assertNotIn('expected_group_average_main', payload)
                # Finish current block without rewriting the already submitted reports.
                for r in range(1,11):
                    ss = helpers.subsession(session,r)
                    for g in ss.get_groups():
                        if r == 1 and not g.reports_complete:
                            helpers.reports(g)
                        helpers.decide(g)
                    if r == 5:
                        app.MainCheckWait.after_all_players_arrive(ss)
                    else:
                        for g in ss.get_groups(): app.PeriodWait.after_all_players_arrive(g)
                end = helpers.subsession(session,10)
                for p in end.get_players(): app.Result.before_next_page(p,False)
                app.BlockEndWait.after_all_players_arrive(end)
                next_player = group.get_players()[0].in_round(11)
                self.assertFalse(next_player.reports_submitted)
                for field in app.Reports.form_fields: self.assertIsNone(next_player.field_maybe_none(field))
                response = self.open_page(next_player,app.Reports)
                self.post(response, dict(expected_own_equipment_main=77,expected_group_average_main=88))
                self.assertEqual((next_player.expected_own_equipment_main,next_player.expected_group_average_main),(77,88))
                self.assertEqual(group.get_players()[0].expected_own_equipment_main,0)
                db.rollback()

    def check_barrier(self, size):
        for app, helpers, branch in environments():
            with self.subTest(app=app.__name__,branch=branch,size=size):
                session=helpers.make_session(branch,size) if branch else helpers.make_session(size)
                helpers.ready(session)
                for r in range(1,5):
                    for group in helpers.subsession(session,r).get_groups(): helpers.run_period(group)
                ss=helpers.subsession(session,5)
                matrix=ss.get_group_matrix(objects=True)
                identities=[[p.participant.code for p in row] for row in matrix]
                def member_matrix(round_number):
                    return [[p.participant.code for p in row] for row in helpers.subsession(session,round_number).get_group_matrix(objects=True)]
                responses={}
                for p in ss.get_players(): responses[p.id]=self.open_page(p,app.Decision)
                groups=ss.get_groups()
                # Distinct current-group outcomes: 40, 50, and mixed 0/40; fourth group100.
                amounts=[[60]*6,[50]*6,[100,100,100,60,60,60],[0]*6]
                flat=[(p,amounts[i][j]) for i,g in enumerate(groups) for j,p in enumerate(g.get_players())]
                for p,d in flat[:-1]:
                    responses[p.id]=self.post(responses[p.id],dict(retirement=d))
                    self.assertIn(wait_page_http_header,responses[p.id].headers)
                    self.assertNotIn('lab-chart-config',responses[p.id].text)
                    self.assertNotIn('main-threshold',responses[p.id].text)
                    self.assertFalse(any(g.settlement_complete for g in groups))
                with self.assertRaisesRegex(ValueError,'All session participants'):
                    app.MainCheckWait.after_all_players_arrive(ss)
                self.assertFalse(any(g.settlement_complete for g in groups))
                fast=flat[0][0]
                self.assertIn(wait_page_http_header,self.refresh(responses[fast.id]).headers)
                p,d=flat[-1]
                responses[p.id]=self.post(responses[p.id],dict(retirement=d))
                self.assertTrue(all(g.settlement_complete for g in groups))
                records=[g.settlement_record for g in groups]
                app.MainCheckWait.after_all_players_arrive(ss)
                self.assertEqual(records,[g.settlement_record for g in groups])
                for i,g in enumerate(groups):
                    total=sum(100-d for d in amounts[i])
                    for player,d in zip(g.get_players(),amounts[i]):
                        responses[player.id]=self.refresh(responses[player.id])
                        self.assertNotIn(wait_page_http_header,responses[player.id].headers)
                        self.assertIn('Accertamento principale — Periodo 5',responses[player.id].text)
                        k=100-d
                        threshold=session.config['ambiguity_thresholds'][str(player.global_block)] if app.__name__=='ambiguity' or branch=='A' else 37
                        enforced=app.__name__=='fixed' or total<=6*threshold
                        self.assertEqual(decode_fraction(player.main_fine),175+Fraction(k,2) if enforced and k else 0)
                        if app.__name__=='ambiguity' or branch=='A':
                            config=json.loads(re.search(r'id="lab-chart-config" type="application/json">(.*?)</script>',responses[player.id].text,re.S)[1])
                            self.assertEqual(config['threshold'],threshold)
                            self.assertTrue(config['thresholdRevealed'])
                        if app.__name__=='policy':
                            context=app.Result.vars_for_template(player)
                            self.assertEqual(context['fine_pool'], '585' if i==2 else '1170' if i==0 and branch=='A' else '0')
                            self.assertEqual(context['own_transfer'],'58.50' if i==2 and k==0 else '0')
                        if app.__name__=='messages' or branch=='M':
                            self.assertEqual(lab_reports.read_public_plans(player),[50]*6)
                for r in range(1,11): self.assertEqual(member_matrix(r),identities)
                # Fast group can reach P6 after its own Result wait, without other groups.
                for player in groups[0].get_players():
                    responses[player.id]=self.post(responses[player.id])
                for player in groups[0].get_players():
                    response=self.refresh(responses[player.id])
                    self.assertIn('Periodo 6 / 10',response.text)
                self.assertEqual(records,[g.settlement_record for g in groups])
                # Rest of block retains group barriers, then the original session-wide end wait.
                for r in range(6,11):
                    for g in helpers.subsession(session,r).get_groups(): helpers.run_period(g)
                    self.assertEqual(member_matrix(r),identities)
                end=helpers.subsession(session,10)
                end_responses=[(p,self.open_page(p,app.Result)) for p in end.get_players()]
                for p,response in end_responses[:-1]:
                    result=self.post(response)
                    self.assertIn(wait_page_http_header,result.headers)
                    self.assertFalse(end.block_barrier_complete)
                last=self.post(end_responses[-1][1])
                self.assertTrue(end.block_barrier_complete)
                self.assertTrue(helpers.subsession(session,11).grouping_installed)
                self.assertIn('Riepilogo del Blocco',last.text)
                self.assertEqual(end.get_players()[-1].participant._current_page_name, 'BlockEnd')
                self.assertEqual(member_matrix(5),identities)
                self.assertNotEqual(member_matrix(11),identities)
                db.rollback()

    def test_session_main_barrier_18_all_environments(self): self.check_barrier(18)
    def test_session_main_barrier_24_all_environments(self): self.check_barrier(24)

    def test_block_start_early_and_timeout_without_block_summary(self):
        for app, helpers, branch in environments():
            session=helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            helpers.finish_block(session,1)
            for page,round_number in [(app.BlockStart,11)]:
                self.assertEqual(page.timeout_seconds,60)
                for timeout,p in zip((False,True),helpers.subsession(session,round_number).get_players()[:2]):
                    response=self.open_page(p,page)
                    self.assertIn('var remainingTimeoutSeconds = 60',response.text)
                    self.assertIn('Continua',response.text)
                    before=copy.deepcopy(p.participant.vars)
                    if timeout:self.expire(p)
                    self.post(response,dict(timeout_happened=1) if timeout else {})
                    self.assertEqual(before,p.participant.vars)
                    self.assertNotEqual(p.participant._current_page_name,page.__name__)
            self.assertIsNone(getattr(app.FirstBlockSplash,'timeout_seconds',None))
            db.rollback()

    def test_reordering_preserves_every_question_option_feedback_and_correct_meaning(self):
        from lab_printed_questions import PRINTED_QUESTIONS
        # Frozen after the requested 37 / 33–42 threshold update, independent of option order/letters.
        expected = {'F': '6a09f33d41d8bd06aa93fbe8d00925957fb96dfa38c943fa6fb05d65b60ba4ce', 'E': '97e144756ae05d86344b573f5ff6c5a76884e30d5c5a3a86221433d53ba5eb89', 'A': '0953acbe145c53e878f3cd0221f8cca4c31d5163b8c9fbef94601f76c9e82f54', 'M': '62329bb51a2df0f6ff1e27683ca64bef675800a6c9c08c788679a900b9e3f9df', 'P': 'a40051e22d17691b0083dea625af18986e4d2b4c7edbcad4d2975108a9afbd7f'}
        for section, rows in PRINTED_QUESTIONS.items():
            semantic = [dict(id=q['id'], prompt=q['prompt'], feedback=q['feedback'],
                options=sorted(label for _, label in q['options']),
                correct=dict(q['options'])[q['correct']]) for q in rows]
            digest = hashlib.sha256(json.dumps(semantic,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            self.assertEqual(digest, expected[section])

    def test_answer_positions_and_nondefault_policy_share(self):
        expected={'fixed':'bacbac','endogenous':'cbac','ambiguity':'bcba','messages':'cabc','policy':'bcab'}
        for app, helpers, branch in environments():
            session=helpers.make_session(branch) if branch else helpers.make_session()
            p=helpers.subsession(session).get_players()[0]
            qs=lab_instructions.questions(p)
            self.assertEqual(''.join(q['correct'] for q in qs),expected[app.__name__])
            for q in qs:self.assertEqual([key for key,_ in q['options']],list('abc'[:len(q['options'])]))
            self.assertLessEqual(sum(q['correct']=='a' for q in qs),2)
            if app.__name__=='policy':
                session.config['rho']=0.5;session.config['rho_exact']='1/2'
                qs=lab_instructions.questions(p)
                self.assertIn('50%',dict(qs[1]['options'])[qs[1]['correct']])
                self.assertIn('180',dict(qs[2]['options'])[qs[2]['correct']])
            db.rollback()

    @unittest.skipUnless(CHROME,'Chrome unavailable')
    def test_browser_splash_reports_decision_and_result_rows(self):
        screenshots=Path('/tmp/lab-ui-timing-screenshots');screenshots.mkdir(exist_ok=True)
        for app,helpers,branch in environments():
            session=helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            p=helpers.subsession(session).get_players()[0]
            if app.__name__=='fixed':
                html=self.open_page(p,app.ExperimentSplash).text
                for width,height in [(1366,768),(1366,900),(650,900)]:
                    self.browser(html,"""
                        const box=document.querySelector('.bless-initial').getBoundingClientRect();
                        const content=document.querySelector('.bless-initial .otree-content').getBoundingClientRect();
                        assert(Math.abs(content.left+content.width/2-innerWidth/2)<3,'centered splash');
                        const title=document.querySelector('.bless-initial h3').getBoundingClientRect();
                        const last=[...document.querySelectorAll('.bless-initial h3')].at(-1).getBoundingClientRect();
                        assert(title.top>=60 && last.bottom<=innerHeight,'balanced vertical position '+title.top+'/'+last.bottom+'/'+innerHeight);
                        assert(parseFloat(getComputedStyle(document.querySelector('.bless-initial h3')).fontSize)>=25,'larger title');
                        assert(!document.querySelector('form,button'),'admin only');
                        assert(document.documentElement.scrollWidth<=innerWidth,'no overflow');
                    """,width,height,screenshots/f'splash-{width}-{height}.png')
            html=self.open_page(p,app.Reports).text
            for width,height in [(1366,768),(1366,900),(650,900)]:
                self.browser(html,"""
                    const qs=[...document.querySelectorAll('.report-question')];
                    assert(qs.length===2,'two reports');
                    const second=qs[1].getBoundingClientRect();
                    assert(second.top-qs[0].getBoundingClientRect().bottom>=32,'separated questions');
                    assert(parseFloat(getComputedStyle(qs[1]).borderTopWidth)>=1,'subtle divider');
                    assert(document.documentElement.scrollWidth<=innerWidth,'no overflow');
                    let submits=0;$('#form').on('submit',e=>{submits++;e.preventDefault();});
                    $('.otree-timer__time-left').trigger('finish.countdown');
                    assert(submits===1,'untouched reports timeout submits despite disabled Continue');
                """,width,height,screenshots/f'reports-{app.__name__}-{branch}-{width}-{height}.png')
            helpers.reports(p.group)
            html=self.open_page(p,app.Decision).text
            self.assertIn('Attrezzatura dismessa in questo periodo:',html)
            for r in range(1,11):
                g=helpers.subsession(session,r).get_groups()[0];helpers.run_period(g)
                if r not in (1,5,10):continue
                player=g.get_players()[0]
                html=self.open_page(player,app.Result).text
                if r==1:
                    self.assertEqual(player.voluntary_equipment_after,player.final_equipment)
                    self.assertNotIn('id="voluntary-equipment"',html)
                    self.assertIn('La tua attrezzatura al termine di questo periodo',html)
                    self.assertIn('id="group-mean"',html)
                for width,height in [(1366,768),(1366,900),(650,900)]:
                    self.browser(html,"""
                        assert(document.documentElement.scrollWidth<=innerWidth,'no overflow');
                        const dl=document.querySelector('.check-result-summary');
                        if(dl && innerWidth>800){
                            const rows=new Map();
                            [...dl.children].forEach(el=>{const b=el.getBoundingClientRect();const y=Math.round(b.top);if(!rows.has(y))rows.set(y,[]);rows.get(y).push(b);});
                            for(const row of rows.values()){
                                const left=Math.min(...row.map(b=>b.left)),right=Math.max(...row.map(b=>b.right));
                                const box=dl.getBoundingClientRect();
                                assert(Math.abs((left+right)/2-(box.left+box.right)/2)<2,'every partial check row centered');
                            }
                            const first=[...rows.values()][0];
                            assert(first.length===(document.querySelector('.policy-main-result')?4:3),'existing full row columns retained');
                        }
                        assert(!document.body.innerText.includes('Fornito da'),'footer stays hidden');
                    """,width,height,screenshots/f'result-{app.__name__}-{branch}-{r}-{width}-{height}.png')
            db.rollback()
