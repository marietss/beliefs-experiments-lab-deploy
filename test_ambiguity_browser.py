"""Offline A browser checks; real multiplayer/secrecy HTTP tests are separate."""

from pathlib import Path
import re
import unittest

import test_endogenous_browser as e_browser
from test_ambiguity import make_session, subsession, ready, reports, run_period
from test_ambiguity_ui import render_page
from otree.database import db
import ambiguity


@unittest.skipUnless(e_browser.CHROME, 'Headless Chrome unavailable.')
class AmbiguityBrowserTests(unittest.TestCase):
    def tearDown(self):
        db.rollback()

    def browser(self, fragment, assertions):
        fragment=fragment.replace('/static/ambiguity/',Path('_static/ambiguity').resolve().as_uri()+'/')
        e_browser.EndogenousBrowserTests.browser(self,fragment,assertions)

    def decision(self, *, zero=False, charts=True):
        session=make_session()
        ready(session)
        group=subsession(session).get_groups()[0]
        p=group.get_players()[0]
        if zero:
            run_period(group,[100]*6)
            p=p.in_round(2)
        else:
            reports(group)
        html=render_page(ambiguity.Decision,p)
        if not charts:
            html=re.sub(r'<script src="[^"]*chart\.umd-4\.4\.8\.js"></script>','',html)
        assertions='''
            const config=JSON.parse(document.getElementById('lab-chart-config').textContent);
            assert(config.thresholdLow===33 && config.thresholdHigh===42, 'support bounds');
            assert(config.thresholdRevealed===false && !('threshold' in config), 'realized value absent');
            assert(config.thresholdLow===33 && config.thresholdHigh===42, 'support drawn in chart');
            assert(!document.getElementById('revealed-threshold') && !document.getElementById('known-threshold'), 'no realized/E marker');
            const slider=document.getElementById('retirement-slider');
            const field=document.getElementById('retirement-value');
            const button=document.getElementById('confirm-retirement');
            assert(!document.getElementById('rules-dialog') && !document.getElementById('rules-open'), 'rules supplied on paper');
        '''
        if zero:
            assertions+="assert(!slider && field.value==='0' && !button.disabled && button.textContent==='Continua','zero Continua');"
        else:
            assertions+="""
                assert(button.disabled && field.value==='', 'explicit choice');
                slider.value='25'; slider.dispatchEvent(new Event('input'));
                assert(field.value==='25' && !button.disabled, 'slider wiring');
                assert(document.getElementById('selected-cost').textContent==='62.50 punti','cost preview');
            """
        if charts:
            assertions+='''
                assert(Chart.version==='4.4.8','local pinned Chart');
                const graph=Chart.getChart('equipment-chart');
                assert(graph.config.plugins.some(p=>p.id==='ambiguityThreshold'), 'range/band plugin');
                assert(!graph.config.plugins.some(p=>p.id==='knownMainThreshold'), 'no E threshold plugin');
                assert(document.getElementById('chart-unavailable').hidden, 'graph rendered');
            '''
        else:
            assertions+="assert(!document.getElementById('chart-unavailable').hidden,'graph fallback');"
        assertions+="""
            let submitted=false;
            document.getElementById('form').addEventListener('submit',e=>{submitted=true;e.preventDefault();});
            button.click(); assert(submitted,'Conferma/Continua normal form');
        """
        self.browser(html,assertions)

    def test_pre_main_range_slider_confirm_offline(self):
        self.decision()

    def test_zero_equipment_continue_remains_blind(self):
        self.decision(zero=True)

    def test_decision_without_chart_dependency(self):
        self.decision(charts=False)

    def test_main_reveal_and_post_main_indicator_offline(self):
        session=make_session()
        ready(session)
        for period in range(1,6):
            run_period(subsession(session,period).get_groups()[0],[58]*6 if period==5 else None)
        p=subsession(session,5).get_groups()[0].get_players()[0]
        self.browser(render_page(ambiguity.Result,p),"""
            const config=JSON.parse(document.getElementById('lab-chart-config').textContent);
            assert(config.thresholdRevealed && config.threshold===42,'current threshold reveal');
            assert(!('ambiguity_thresholds' in config),'full map absent');
            assert(document.getElementById('main-threshold').textContent==='42 unità','revealed label');
            assert(document.getElementById('group-mean').textContent==='42 unità','actual mean');
            assert(document.getElementById('target-satisfied').textContent==='No','equality not success');
            assert(document.getElementById('main-enforcement').textContent==='Sì','enforcement');
            assert(document.getElementById('main-fine').textContent==='196 punti','own fine');
            assert(Chart.getChart('equipment-chart').data.datasets[1].data.at(-1).y===42,'stored group graph');
        """)
        self.browser(render_page(ambiguity.Decision,p.in_round(6)),'''
            const config=JSON.parse(document.getElementById('lab-chart-config').textContent);
            assert(config.thresholdRevealed && config.threshold===42,'same-block post-Main threshold');
            assert(Chart.getChart('equipment-chart').config.plugins.some(p=>p.id==='ambiguityThreshold'),'revealed threshold chart');
        ''')
