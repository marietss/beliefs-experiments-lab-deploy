"""Offline browser verification of restored comparable instruction presentation."""
import unittest
from otree.database import db
from test_fixed_browser import CHROME
from test_lab_instructions import cases,render
import test_messages_browser as harness
import fixed


@unittest.skipUnless(CHROME, 'Headless Chrome unavailable.')
class ComparableInstructionBrowserTests(unittest.TestCase):
    browser = harness.MessagesBrowserTests.browser

    def tearDown(self):
        db.rollback()

    def test_general_legacy_cards_navigation_and_review(self):
        _,ps=cases();_,p=ps[0]
        self.browser(render(fixed.LabOverview,p), """
            const deck=document.querySelector('[data-instruction-deck]');
            const panels=Array.from(deck.querySelectorAll('[data-instruction-panel]'));
            const next=deck.querySelector('[data-instruction-next]');
            const back=deck.querySelector('[data-instruction-back]');
            const finish=deck.querySelector('[data-instruction-finish]');
            assert(panels.length===3 && !panels[0].hidden && panels[1].hidden, 'legacy overview first');
            assert(back.hidden && finish.hidden, 'no early page submission');
            assert(deck.querySelectorAll('.study-part').length===3, 'section/block cards');
            next.click();assert(!panels[1].hidden && panels[1].textContent.includes('€8.00'),'payment second');
            back.click();assert(!panels[0].hidden,'previous page review');
            next.click();next.click();
            assert(!panels[2].hidden && panels[2].textContent.includes('domande di comprensione'),'structure third');
            assert(!finish.hidden && next.hidden,'normal final submit available');
        """)

    def test_fixed_task_cost_main_follow_up_order_and_rules_review(self):
        _,ps=cases();app,p=ps[0]
        self.browser(render(app.SectionInstructions,p), """
            const panels=Array.from(document.querySelectorAll('[data-instruction-panel]'));
            assert(panels.length===8,'canonical eight F pages');
            assert(panels[0].textContent.includes('Attrezzatura e portafoglio'),'equipment first');
            document.querySelector('[data-instruction-next]').click();
            assert(!panels[1].hidden && panels[1].textContent.includes('La tua decisione'),'decision second');
            assert(!document.querySelector('[data-comparable-review]'),'no redundant section-start review');
            assert(!document.getElementById('rules-dialog') && !document.getElementById('rules-open'), 'rules supplied on paper');
            document.querySelector('[data-instruction-next]').click();
            assert(!panels[2].hidden && panels[2].textContent.includes("Costo della dismissione dell'attrezzatura"),'costs third');
            document.querySelector('[data-instruction-next]').click();
            assert(!panels[3].hidden && panels[3].querySelector('.follow-up-check-box'),'Follow-up box');
        """)

    def test_practice_paired_graphs_and_existing_controls(self):
        _,ps=cases();_,p=ps[0]
        self.browser(render(fixed.SectionInstructions,p), """
            assert(document.querySelectorAll('.practice-decision .graph-row .chart-box').length===2,'paired pilot graph placement');
            const slider=document.getElementById('retirement-slider');
            slider.value=25;slider.dispatchEvent(new Event('input'));
            assert(document.getElementById('selected-cost').textContent==='62.50 punti','unchanged preview');
            assert(Chart.getChart('equipment-chart').data.datasets[2].data.at(-1).y===75,'equipment preview graph');
            assert(Chart.getChart('cost-chart').data.datasets[1].data[0].y===62.5,'cost preview graph');
            document.getElementById('confirm-retirement').click();
            assert(document.getElementById('practice-feedback').textContent.includes('confermata'),'existing unpaid Conferma');
            assert(!document.querySelector('input[name=retirement]'),'no experiment decision written');
        """)
