"""Offline canonical panels and three-page F/A quiz interaction."""
import unittest
from otree.database import db
from test_fixed_browser import CHROME
from test_lab_instructions import cases,render
import test_messages_browser as harness


@unittest.skipUnless(CHROME,'Headless Chrome unavailable.')
class CanonicalInstructionBrowserTests(unittest.TestCase):
    browser=harness.MessagesBrowserTests.browser
    def tearDown(self):db.rollback()

    def test_F_practice_is_sixth_page_and_still_unpaid(self):
        _,players=cases();app,p=players[0]
        self.browser(render(app.SectionInstructions,p),"""
            const deck=document.querySelector('[data-instruction-deck]');
            const panels=Array.from(deck.querySelectorAll('[data-instruction-panel]'));
            assert(panels.length===8,'eight canonical F pages');
            for(let i=0;i<5;i++)deck.querySelector('[data-instruction-next]').click();
            assert(!panels[5].hidden && panels[5].querySelector('h2').textContent==='Prova','practice sixth');
            const slider=document.getElementById('retirement-slider');
            slider.value=25;slider.dispatchEvent(new Event('input'));
            assert(document.getElementById('selected-cost').textContent==='62.50 punti','exact practice cost');
            assert(document.querySelector('.current-points-badge strong').textContent==='1000 punti','initial practice wallet');
            document.getElementById('confirm-retirement').click();
            assert(document.getElementById('practice-feedback').textContent.includes('confermata'),'practice confirmation');
            assert(!document.querySelector('input[name=retirement]'),'no paid decision field');
            assert(document.querySelectorAll('#retirement-slider').length===1,'no duplicate review controls');
            deck.querySelector('[data-instruction-next]').click();
            assert(!panels[6].hidden && panels[6].textContent.includes('937.5'),'results example next');
        """)

    def test_F_three_real_quiz_pages_have_only_their_two_questions(self):
        _,players=cases('A');app,p=players[0]
        from lab_comprehension import ComprehensionPair
        pages=[page for page in app.page_sequence if issubclass(page,ComprehensionPair)]
        self.assertEqual(len(pages),3)
        for page in pages:
            self.browser(render(page,p),'''
                const fields=document.querySelectorAll('fieldset');
                assert(fields.length===2,'only the current pair');
                assert(!document.querySelector('[data-instruction-next]'),'no client-only advance');
                assert(!document.querySelector('[data-quiz-deck]'),'real server pages');
                assert(!document.getElementById('instruction-review'),'printed rules');
                assert(document.querySelector('button[type=submit]').textContent==='Verifica le risposte','server submission');
            ''')

    def test_M_policy_share_the_same_instruction_navigation_without_live_values(self):
        for branch in ('A','M'):
            session,players=cases(branch)
            for app,p in players[1:]:
                self.browser(render(app.SectionInstructions,p),"""
                    const deck=document.querySelector('main[data-instruction-deck]');
                    const panels=Array.from(deck.querySelectorAll('[data-instruction-panel]'));
                    assert(panels[0].querySelector('h2').textContent==='Introduzione','intro first');
                    deck.querySelector('[data-instruction-next]').click();
                    assert(!panels[1].hidden && panels[1].querySelector('h2').textContent==='Cosa rimane uguale','same before changes');
                    assert(document.querySelector('.instruction-card'),'shared legacy cards');
                    assert(!document.querySelector('script[src^="http"]'),'offline scripts');
                    assert(!deck.innerHTML.includes('ambiguity_thresholds'),'no threshold map');
                    assert(!deck.innerHTML.includes('report_values'),'no report arrays');
                """)

    def test_branch_and_policy_have_two_real_question_pages(self):
        from lab_comprehension import ComprehensionPair
        for branch in 'EAM':
            _,players=cases(branch)
            for app,player in players[1:]:
                pages=[page for page in app.page_sequence if issubclass(page,ComprehensionPair)]
                self.assertEqual(len(pages),2)
                for page in pages:
                    self.browser(render(page,player),'''
                        assert(document.querySelectorAll('fieldset').length===2,'two printed questions');
                        assert(!document.querySelector('[data-instruction-next]'),'no client-only advance');
                        assert(document.querySelector('button[type=submit]').textContent==='Verifica le risposte','server check');
                    ''')
