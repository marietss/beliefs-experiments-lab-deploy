"""Native regressions for thresholds, isolated practice and restored wallet feedback."""
import copy
import json
from pathlib import Path
import re
import unittest
from fractions import Fraction

import test_fixed
from otree.database import db
from otree.forms.forms import get_form
from otree.export import get_rows_for_wide_csv
from otree.lookup import _get_session_lookups
import test_lab_ui_timing_refinements as refinement_harness
from test_lab_decision_ui import environments
from test_fixed_browser import CHROME
import fixed
import lab_flow
import lab_rules as rules
import survey


class NovemberTests(unittest.TestCase):
    setUp=refinement_harness.RefinementTests.setUp
    tearDown=refinement_harness.RefinementTests.tearDown
    open_page=refinement_harness.RefinementTests.open_page
    post=refinement_harness.RefinementTests.post
    refresh=refinement_harness.RefinementTests.refresh
    expire=refinement_harness.RefinementTests.expire
    browser=refinement_harness.RefinementTests.browser

    def advance(self, session):
        from otree.common import CSRF_TOKEN_NAME
        admin = self.client.get('/sessions')
        token = re.search(r'name="'+CSRF_TOKEN_NAME+r'" value="([^"]+)"', admin.text)[1]
        response = self.client.post('/AdvanceSession/'+session.code,
            data={'advancemode':'visited_only', CSRF_TOKEN_NAME:token})
        self.assertEqual(response.status_code, 200)
        db.expire_all()

    def test_known_thresholds_strict_and_external_ambiguity_bounds(self):
        from lab_config import validate_lab_config
        from test_lab_config import configuration
        self.assertEqual(rules.KNOWN_THRESHOLD,37)
        for branch in ('E','M'):
            for total, expected in ((221,True),(222,True),(223,False)):
                self.assertEqual(rules.main_enforcement_applies(branch,group_total=total),expected)
        for threshold in (33,42):
            c=configuration('A',ambiguity_thresholds={str(i):threshold for i in range(4,10)})
            self.assertEqual(validate_lab_config(c)['ambiguity_thresholds'],c['ambiguity_thresholds'])
            self.assertTrue(rules.main_enforcement_applies('A',group_total=6*threshold,ambiguity_threshold=threshold))
        for threshold in (32,43,42.0,True,None):
            with self.assertRaises(ValueError):
                validate_lab_config(configuration('A',ambiguity_thresholds={str(i):threshold for i in range(4,10)}))

    def test_practice_native_isolation_deadline_and_completion_then_comprehension(self):
        session=test_fixed.make_session();p=test_fixed.subsession(session).get_players()[0]
        # SessionReady is the existing cohort barrier following admin splash release.
        test_fixed.ready(session)
        fields=['retirement','locked_retirement','decision_submitted','period_settled',
                'start_equipment','final_equipment','wallet_before','wallet_after','final_block_wallet','reports_submitted']
        before={f:p.field_maybe_none(f) for f in fields}
        variables=copy.deepcopy(p.participant.vars);session_vars=copy.deepcopy(session.vars)
        response=self.open_page(p,fixed.PracticeDecision)
        self.assertIn('var remainingTimeoutSeconds = 60',response.text)
        self.assertIn('Periodo di prova',response.text)
        deadline=p.participant._timeout_expiration_time
        response=self.refresh(response)
        self.assertEqual(p.participant._timeout_expiration_time,deadline)
        response=self.post(response,dict(retirement=99))
        self.assertIn('PracticeDecision/',str(response.url))
        self.assertEqual(before,{f:p.field_maybe_none(f) for f in fields})
        self.expire(p)
        response=self.post(response,dict(timeout_happened=1,retirement=100))
        self.assertIn('PracticeComplete/',str(response.url))
        self.assertIn('Il periodo di prova è concluso',response.text)
        for text in ('settled-wallet','main-fine','follow-up-fine','lab-chart-config'):
            self.assertNotIn(text,response.text)
        self.assertEqual(before,{f:p.field_maybe_none(f) for f in fields})
        self.assertEqual(variables,p.participant.vars);self.assertEqual(session_vars,session.vars)
        self.assertFalse(p.group.settlement_complete)
        self.assertIsNone(getattr(fixed.PracticeComplete, 'timeout_seconds', None))
        self.assertNotIn('<button', response.text)
        for data in ({}, dict(timeout_happened=1)):
            response = self.post(response, data)
            self.assertIn('PracticeComplete/', str(response.url))
        self.advance(session)
        response = self.refresh(response)
        self.assertIn('SectionComprehension/',str(response.url))
        lookups=_get_session_lookups(session.code)
        practice=[row for row in lookups.values() if row.page_class is fixed.PracticeDecision]
        self.assertEqual(sum(fixed.PracticeDecision.is_displayed(p.in_round(row.round_number)) for row in practice),1)
        self.assertEqual(fixed.PracticeDecision.timeout_seconds,60)

    @unittest.skipUnless(CHROME,'Chrome unavailable')
    def test_practice_browser_same_controls_and_timer_at_lab_and_narrow_sizes(self):
        p=test_fixed.subsession(test_fixed.make_session()).get_players()[0]
        response=self.open_page(p,fixed.PracticeDecision)
        for width,height in ((1366,768),(1366,900),(650,900)):
            screenshot=f'/tmp/nov11-practice-{width}x{height}.png'
            self.browser(response.text,"""
                assert([...document.scripts].filter(s=>!s.textContent.includes('pilot-check')).some(s=>s.textContent.includes('var remainingTimeoutSeconds = 60')),'practice duration');
                const slider=document.getElementById('retirement-slider');
                const confirm=document.getElementById('confirm-retirement');
                assert(confirm.type==='button','preview confirmation never submits');
                let submissions=0;$('#form').on('submit',e=>{submissions++;e.preventDefault();});
                slider.value='20';slider.dispatchEvent(new Event('input'));confirm.click();
                assert(document.getElementById('selected-cost').textContent==='40 punti','same quadratic preview');
                assert(document.getElementById('remaining-equipment').textContent==='80 unità','same equipment preview');
                assert(submissions===0,'practice interaction never advances');
                assert(document.querySelector('#cost-chart'),'same cost graph');
                assert(!document.querySelector('.powered-by-otree') || getComputedStyle(document.querySelector('.powered-by-otree')).display==='none','footer hidden');
                assert(document.documentElement.scrollWidth<=innerWidth,'no horizontal overflow');
                $('.otree-timer__time-left').trigger('finish.countdown');
                assert(submissions===1,'native 60-second timer advances');
            """,width,height,screenshot=screenshot)

    @unittest.skipUnless(CHROME,'Chrome unavailable')
    def test_summary_browser_shows_only_wallets_and_no_main_equipment(self):
        session=test_fixed.make_session();test_fixed.ready(session);test_fixed.finish_block(session,1)
        p=test_fixed.subsession(session,10).get_players()[0]
        response=self.open_page(p,fixed.BlockEnd)
        for width,height in ((1366,768),(1366,900),(650,900)):
            self.browser(response.text,"""
                assert([...document.scripts].filter(s=>!s.textContent.includes('pilot-check')).some(s=>s.textContent.includes('var remainingTimeoutSeconds = 30')),'summary duration');
                let submissions=0;$('#form').on('submit',e=>{submissions++;e.preventDefault();});
                $('.otree-timer__time-left').trigger('finish.countdown');
                assert(submissions===1,'native summary timeout advances');
                const text=document.body.innerText;
                assert(text.includes('Il portafoglio massimo ottenibile è di 800 punti.'),'fixed benchmark');
                const summary=document.querySelector('.block-wallet-summary');
                assert(parseFloat(getComputedStyle(summary).fontSize)>=19,'larger summary text');
                assert(summary.querySelector('strong').textContent.endsWith(' punti'),'own wallet is bold');
                assert(!text.includes('Attrezzatura all'), 'no Main equipment column');
                const table=document.querySelector('.block-feedback-table');
                assert(table.querySelectorAll('thead th').length===2,'two columns');
                assert(table.querySelectorAll('tbody tr').length===5,'five actual other managers');
                assert([...table.querySelectorAll('thead th')].map(e=>e.textContent).join('|')==='Manager|Portafoglio alla fine del blocco','exact headings');
                assert([...table.querySelectorAll('tbody th')].map(e=>e.textContent).join('|')===Array(5).fill('Altro manager').join('|'),'anonymous peer labels');
                assert(document.documentElement.scrollWidth<=innerWidth,'no horizontal overflow');
            """,width,height,screenshot=f'/tmp/nov11-summary-{width}x{height}.png')

    def test_all_seven_block_benchmarks_and_actual_anonymous_peer_wallets(self):
        for app,helpers,branch in environments():
            session=helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session);helpers.finish_block(session,1)
            p=helpers.subsession(session,10).get_players()[0]
            context=app.BlockEnd.vars_for_template(p)
            maximum=1100 if branch=='A' else 1095 if app is __import__('policy') else 800 if app is fixed else 900
            self.assertEqual(context['summary_maximum'],maximum)
            self.assertEqual(len(context['summary_rows']),5)
            self.assertEqual([r['manager'] for r in context['summary_rows']],list(range(1,6)))
            from lab_presentation import points
            from lab_persistence import decode_fraction
            peers=[q for q in p.group.get_players() if q.id!=p.id]
            self.assertEqual([r['points'] for r in context['summary_rows']],
                             [points(decode_fraction(q.final_block_wallet)) for q in peers])
            self.assertEqual(context['summary_wallet'],points(decode_fraction(p.final_block_wallet)))
            response=self.open_page(p,app.BlockEnd)
            self.assertIn('Il tuo portafoglio alla fine del blocco è di <strong>'+context['summary_wallet']+' punti</strong>.',response.text)
            self.assertEqual(response.text.count('>Altro manager</th>'),5)
            self.assertNotIn("Attrezzatura all'accertamento principale",response.text)
            self.assertNotIn('main_equipment',response.text)
            self.assertEqual(app.page_sequence[-2:],[app.BlockEndWait,app.BlockEnd])
            self.assertTrue(app.BlockEndWait.wait_for_all_groups)
            self.assertEqual(app.Decision.get_timeout_seconds(p.in_round(1)),40)
            self.assertEqual(app.Decision.get_timeout_seconds(p),30)
            # Both native early Continue and timeout leave the same stored result intact.
            for finished, timeout in zip(p.group.get_players()[:2], (False, True)):
                finished.block_feedback_submitted = False
                saved_wallet = finished.final_block_wallet
                response = self.open_page(finished, app.BlockEnd)
                self.assertIn('var remainingTimeoutSeconds = 30', response.text)
                if timeout:
                    self.expire(finished)
                advanced = self.post(response, dict(timeout_happened=1) if timeout else {})
                self.assertNotIn('/BlockEnd/', str(advanced.url))
                self.assertTrue(finished.block_feedback_submitted)
                self.assertEqual(finished.final_block_wallet, saved_wallet)
            # A fresh native Decision deadline is created at period 1 of block 2.
            next_player = p.in_round(11)
            helpers.reports(next_player.group)
            response = self.open_page(next_player, app.Decision)
            self.assertIn('var remainingTimeoutSeconds = 40', response.text)
            deadline = next_player.participant._timeout_expiration_time
            self.refresh(response)
            self.assertEqual(next_player.participant._timeout_expiration_time, deadline)
            db.rollback()

    @unittest.skipUnless(CHROME, 'Chrome unavailable')
    def test_bucket_readable_width_alignment_and_no_overflow_at_lab_viewports(self):
        import bucket
        from test_lab_production import make_production_session
        session = make_production_session()
        player = bucket.Player.objects_filter(session=session).first()
        screens = [('instructions', self.open_page(player, bucket.BucketInstructions).text)]
        response = self.post(self.open_page(player, bucket.BucketInstructions))
        self.assertIn('/BucketTask/', str(response.url))
        screens.append(('task', response.text))
        for index, color in enumerate(('blue', 'yellow', 'blue', 'yellow', 'blue'), 1):
            bucket.receive(player, dict(action='allocate', bucket=color, expected_index=index))
        screens.append(('mixed', self.open_page(player, bucket.BucketTask).text))
        for index in range(6, 51):
            bucket.receive(player, dict(action='allocate', bucket='blue', expected_index=index))
        screens.append(('complete', self.open_page(player, bucket.BucketComplete).text))
        for width, height in ((1366, 768), (1366, 900), (650, 900)):
            for screen, source in screens:
                with self.subTest(screen=screen, width=width, height=height):
                    self.browser(source, """
                        assert(innerWidth===WIDTH && innerHeight===HEIGHT,'exact content viewport');
                        assert(document.documentElement.scrollWidth<=innerWidth,'no horizontal overflow');
                        const content=document.querySelector('main');
                        const box=content.getBoundingClientRect();
                        const title=document.getElementById('_otree-title');
                        assert(parseFloat(getComputedStyle(title).fontSize)>=28,'readable heading');
                        assert(Math.abs(box.left+box.width/2-innerWidth/2)<2,'centered content');
                        if(content.classList.contains('bucket-instructions')) {
                            assert(box.width<=920.1 && (WIDTH<1000 || box.width>=800),'comfortable reading width');
                            assert(parseFloat(getComputedStyle(content).fontSize)>=17,'readable instruction text');
                            assert(parseFloat(getComputedStyle(content).lineHeight)>=25,'comfortable line spacing');
                            const paragraphs=[...content.querySelectorAll('p')];
                            assert(paragraphs.length===7,'unchanged instructions');
                            assert(paragraphs.every(p=>parseFloat(getComputedStyle(p).marginBottom)>=18),'paragraph spacing');
                        }
                        if(content.classList.contains('bucket-task')) {
                            const targets=[...document.querySelectorAll('[data-bucket]')];
                            const rectangles=targets.map(t=>t.getBoundingClientRect());
                            assert(rectangles.length===2 && rectangles[0].right<rectangles[1].left,'separate aligned buckets');
                            assert(Math.abs(rectangles[0].width-rectangles[1].width)<1,'balanced bucket widths');
                            assert(Math.abs(rectangles[0].top-rectangles[1].top)<1,'aligned bucket tops');
                            assert(box.bottom<=innerHeight,'active task fits vertically');
                            assert(document.getElementById('active-ball'),'same active ball');
                            assert(parseFloat(getComputedStyle(document.querySelector('.bucket-rule')).fontSize)>=20,'readable task rule');
                            if('SCREEN'==='mixed') {
                                assert(document.getElementById('balls-remaining').textContent==='45','authoritative remaining count');
                                assert(document.getElementById('bucket-earnings').textContent==='€0,35','unchanged mixed payoff');
                            }
                        }
                        const action=document.querySelector('.bucket-actions button');
                        if(action) {const b=action.getBoundingClientRect();assert(Math.abs(b.left+b.width/2-innerWidth/2)<2,'centered Continue');}
                    """.replace('WIDTH', str(width)).replace('HEIGHT', str(height)).replace('SCREEN', screen),
                    width, height, screenshot=f'/tmp/final-timing-bucket-{screen}-{width}x{height}.png')

    def test_participant_option_orders_stable_scoring_and_per_question_export(self):
        import random
        import lab_comprehension
        import lab_instructions
        from lab_printed_questions import PRINTED_QUESTIONS
        bank = copy.deepcopy(PRINTED_QUESTIONS)
        for app, helpers, branch in environments():
            with self.subTest(app=app.__name__, branch=branch):
                session=helpers.make_session(branch) if branch else helpers.make_session()
                players=helpers.subsession(session).get_players()
                rng = random.getstate()
                rows=[lab_instructions.questions(p) for p in players]
                self.assertEqual(random.getstate(),rng)
                for index, question in enumerate(rows[0]):
                    orders={tuple(key for key,_ in qs[index]['options']) for qs in rows}
                    positions=[next(i for i,(key,_) in enumerate(qs[index]['options']) if key==qs[index]['correct']) for qs in rows]
                    self.assertGreater(len(orders),1)
                    self.assertGreater(len(set(positions)),1)
                    self.assertLess(sum(pos==0 for pos in positions),len(players))
                for p, qs in zip(players, rows):
                    self.assertEqual(lab_instructions.questions(p),qs)
                    for q, original in zip(qs, bank['P' if app.__name__=='policy' else {'fixed':'F','endogenous':'E','ambiguity':'A','messages':'M'}[app.__name__]]):
                        self.assertEqual(q['correct'],original['correct'])
                        self.assertEqual(dict(q['options'])[q['correct']],dict(original['options'])[original['correct']])
                expected={q['id']:0 for q in rows[0]}
                for pair, page in enumerate([p for p in app.page_sequence if p.__name__.startswith('SectionComprehension')],1):
                    p=players[0]
                    q1,q2=lab_comprehension.pair_questions(p,pair)
                    correct={q['field']:q['correct'] for q in (q1,q2)}
                    response=self.open_page(p,page)
                    for wrong in (q1,q2,q1):
                        data=dict(correct)
                        data[wrong['field']]=next(key for key,_ in wrong['options'] if key!=wrong['correct'])
                        response=self.post(response,data)
                        expected[wrong['id']]+=1
                        self.assertEqual(json.loads(p.comprehension_question_errors),expected)
                        self.assertEqual(p.comprehension_errors,sum(expected.values()))
                        self.refresh(response)
                        self.assertEqual(json.loads(p.comprehension_question_errors),expected)
                        self.assertEqual(lab_instructions.questions(p),rows[0])
                    self.post(response,correct)
                    self.assertEqual(json.loads(p.comprehension_question_errors),expected)
                    clean=players[1]
                    self.post(self.open_page(clean,page),lab_instructions.correct_answers(clean))
                    self.assertEqual(json.loads(clean.comprehension_question_errors),{q['id']:0 for q in lab_instructions.questions(clean)})
                    self.assertEqual(clean.comprehension_errors,0)
                self.assertTrue(players[0].comprehension_passed)
                exported=list(get_rows_for_wide_csv(session.code))
                header=exported[0]
                record=next(row for row in exported[1:] if row[header.index('participant.code')]==players[0].participant.code)
                prefix=app.__name__+'.1.player.'
                self.assertEqual(json.loads(record[header.index(prefix+'comprehension_question_errors')]),expected)
                self.assertEqual(int(record[header.index(prefix+'comprehension_errors')]),sum(expected.values()))
                db.rollback()
        self.assertEqual(PRINTED_QUESTIONS,bank)

    @unittest.skipUnless(CHROME, 'Chrome unavailable')
    def test_practice_complete_and_shuffled_comprehension_at_lab_viewports(self):
        import lab_comprehension
        session=test_fixed.make_session()
        players=test_fixed.subsession(session).get_players()
        complete=self.open_page(players[0],fixed.PracticeComplete).text
        samples=[self.open_page(p,fixed.SectionComprehension).text for p in players[:2]]
        for width,height in ((1366,768),(1366,900),(650,900)):
            self.browser(complete,"""
                assert(document.body.innerText.includes('Il periodo di prova è concluso'),'completion title');
                assert(!document.querySelector('button,input[type=submit],.otree-btn-next'),'no participant advancement');
                assert(!document.querySelector('.otree-timer'),'untimed gate');
                assert(document.documentElement.scrollWidth<=innerWidth,'no overflow');
            """,width,height,screenshot=f'/tmp/participant-final-practice-gate-{width}x{height}.png')
            for index,source in enumerate(samples):
                expected=[key for q in lab_comprehension.pair_questions(players[index],1) for key,_ in q['options']]
                self.browser(source,"""
                    const fields=[...document.querySelectorAll('fieldset')];
                    assert(fields.length===2,'same paired structure');
                    assert(JSON.stringify([...document.querySelectorAll('input[type=radio]')].map(e=>e.value))===JSON.stringify(EXPECTED),'stable shuffled display');
                    assert(!document.body.innerText.includes('correct'),'no answer key');
                    assert(document.documentElement.scrollWidth<=innerWidth,'no overflow');
                """.replace('EXPECTED',json.dumps(expected)),width,height,
                screenshot=f'/tmp/participant-final-comprehension-{index}-{width}x{height}.png')
