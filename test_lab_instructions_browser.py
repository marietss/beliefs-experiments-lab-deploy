"""Offline rendering and interaction of actual lab instruction templates."""
from pathlib import Path
import unittest
import test_messages_browser as harness
from test_fixed_browser import CHROME
from test_lab_instructions import cases, render
from otree.database import db
import fixed


@unittest.skipUnless(CHROME, 'Headless Chrome unavailable.')
class LabInstructionBrowserTests(unittest.TestCase):
    browser = harness.MessagesBrowserTests.browser
    def tearDown(self): db.rollback()

    def test_general_costs_and_slider_practice_offline(self):
        _,ps=cases();_,p=ps[0]
        self.browser(render(fixed.LabOverview,p), """
            const text=document.getElementById('form').textContent;
            assert(text.includes('€8.00') && text.includes('Blocco 3.3'), 'canonical general rules');
        """)
        self.browser(render(fixed.LabPractice,p), """
            const slider=document.getElementById('retirement-slider');
            assert(slider.min==='0' && slider.max==='100' && slider.step==='1', 'slider only bounds');
            assert(document.querySelectorAll('input[type=range]').length===1, 'sole retirement control');
            assert(!document.querySelector('input[name=retirement]'), 'no experimental submission');
            const confirm=document.getElementById('confirm-retirement');
            assert(confirm.disabled, 'explicit choice');
            slider.value=25;slider.dispatchEvent(new Event('input'));
            assert(document.getElementById('selected-cost').textContent==='62.50 punti','0.10 preview');
            assert(document.getElementById('remaining-equipment').textContent==='75 unità','preview equipment');
            assert(document.querySelector('.current-points-badge strong').textContent==='1000 punti','unchanged initial practice wallet');
            confirm.click();assert(document.getElementById('practice-feedback').textContent.includes('confermata'),'practice confirm');
            slider.value=0;slider.dispatchEvent(new Event('input'));
            assert(document.getElementById('selected-cost').textContent==='0 punti','zero preview');
        """)

    def test_E_A_M_and_policy_review_and_quiz_offline(self):
        for branch in ('E','A','M'):
            _,ps=cases(branch)
            for app,p in ps[1:]:
                checks="""
                    const form=document.getElementById('form');
                    const text=form.textContent;
                    assert(!document.getElementById('instruction-review'),'no on-screen rule review');
                    assert(form.querySelectorAll('fieldset').length===2,'quiz questions');
                    assert(!text.includes('Prolific') && !text.includes('£'),'lab wording');
                """
                self.browser(render(app.SectionComprehension,p),checks)

if __name__=='__main__':unittest.main()
