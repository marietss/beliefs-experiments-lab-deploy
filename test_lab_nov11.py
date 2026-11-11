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
        self.assertIn('var remainingTimeoutSeconds = 90',response.text)
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
        response=self.post(response)
        self.assertIn('SectionComprehension/',str(response.url))
        lookups=_get_session_lookups(session.code)
        practice=[row for row in lookups.values() if row.page_class is fixed.PracticeDecision]
        self.assertEqual(sum(fixed.PracticeDecision.is_displayed(p.in_round(row.round_number)) for row in practice),1)
        self.assertEqual(fixed.PracticeDecision.timeout_seconds,90)

    @unittest.skipUnless(CHROME,'Chrome unavailable')
    def test_practice_browser_same_controls_and_timer_at_lab_and_narrow_sizes(self):
        p=test_fixed.subsession(test_fixed.make_session()).get_players()[0]
        response=self.open_page(p,fixed.PracticeDecision)
        for width,height in ((1366,768),(1366,900),(650,900)):
            screenshot=f'/tmp/nov11-practice-{width}x{height}.png'
            self.browser(response.text,"""
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
                assert(submissions===1,'native 90-second timer advances');
            """,width,height,screenshot=screenshot)

    @unittest.skipUnless(CHROME,'Chrome unavailable')
    def test_summary_browser_shows_only_wallets_and_no_main_equipment(self):
        session=test_fixed.make_session();test_fixed.ready(session);test_fixed.finish_block(session,1)
        p=test_fixed.subsession(session,10).get_players()[0]
        response=self.open_page(p,fixed.BlockEnd)
        for width,height in ((1366,768),(1366,900),(650,900)):
            self.browser(response.text,"""
                const text=document.body.innerText;
                assert(text.includes('Il massimo portafoglio in questa sezione era 800.'),'fixed benchmark');
                assert(!text.includes('Attrezzatura all'), 'no Main equipment column');
                const table=document.querySelector('.block-feedback-table');
                assert(table.querySelectorAll('thead th').length===2,'two columns');
                assert(table.querySelectorAll('tbody tr').length===5,'five actual other managers');
                assert(table.querySelector('thead').innerText.includes('Altri manager'),'anonymous peer label');
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
            self.assertEqual([r['manager'] for r in context['summary_rows']],list(range(5)))
            from lab_presentation import points
            from lab_persistence import decode_fraction
            peers=[q for q in p.group.get_players() if q.id!=p.id]
            self.assertEqual([r['points'] for r in context['summary_rows']],
                             [points(decode_fraction(q.final_block_wallet)) for q in peers])
            self.assertEqual(context['summary_wallet'],points(decode_fraction(p.final_block_wallet)))
            response=self.open_page(p,app.BlockEnd)
            self.assertIn('Il tuo portafoglio è di '+context['summary_wallet']+' punti.',response.text)
            self.assertIn('Altri manager',response.text)
            self.assertNotIn("Attrezzatura all'accertamento principale",response.text)
            self.assertNotIn('main_equipment',response.text)
            self.assertEqual(app.page_sequence[-2:],[app.BlockEndWait,app.BlockEnd])
            self.assertTrue(app.BlockEndWait.wait_for_all_groups)
            self.assertEqual(app.Decision.get_timeout_seconds(p.in_round(1)),40)
            self.assertEqual(app.Decision.get_timeout_seconds(p),30)
            db.rollback()
