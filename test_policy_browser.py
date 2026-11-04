"""Offline Chrome fixtures; genuine multiplayer flow is covered by policy HTTP/bots."""
from pathlib import Path
import re
import unittest
from otree.database import db
import test_messages_browser as harness
from test_fixed_browser import CHROME
from test_policy import make_session,subsession,ready,reports,run_period,main_group
from test_policy_ui import render_page
import policy


@unittest.skipUnless(CHROME,'Headless Chrome unavailable.')
class PolicyBrowserTests(unittest.TestCase):
    def tearDown(self):db.rollback()

    def browser(self,fragment,assertions):
        fragment=fragment.replace('/static/policy/',Path('_static/policy').resolve().as_uri()+'/')
        harness.MessagesBrowserTests.browser(self,fragment,assertions)

    def test_all_branch_slider_confirmation_threshold_and_message_offline(self):
        for branch in ('E','A','M'):
            session=make_session(branch);ready(session)
            group=subsession(session).get_groups()[0];reports(group,[0]*5+[1])
            html=render_page(policy.Decision,group.get_players()[0])
            self.browser(html,"""const config=JSON.parse(document.getElementById('lab-chart-config').textContent);
                assert(Chart.version==='4.4.8','local pinned chart');
                const slider=document.getElementById('retirement-slider');
                const button=document.getElementById('confirm-retirement');
                assert(button.disabled && slider.min==='0' && slider.max==='100','explicit slider');
                slider.value='25';slider.dispatchEvent(new Event('input'));
                assert(document.getElementById('retirement-value').value==='25','slider submission value');
                assert(document.getElementById('selected-cost').textContent==='62.50 punti','0.10 preview');
            assert(!document.getElementById('rules-dialog') && !document.getElementById('rules-open'), 'rules supplied on paper');
                let submitted=false;document.getElementById('form').addEventListener('submit',e=>{submitted=true;e.preventDefault();});
                button.click();assert(submitted,'Conferma');
            """+('''assert(!Object.hasOwn(config,'threshold') && !config.thresholdRevealed,'A secret');
                assert(config.thresholdLow===33 && config.thresholdHigh===47,'A range');''' if branch=='A' else "assert(config.threshold===40,'known threshold');")+
            ("""assert(config.publicReportMean===1/6,'public report only');
                assert(!document.getElementById('public-report-mean'),'public mean box removed');
                const planned=Chart.getChart('equipment-chart').data.datasets[3];
                assert(planned.pointStyle==='rect' && planned.data.length===1,'aggregate planned marker');""" if branch=='M' else "assert(!Object.hasOwn(config,'publicReportMean'),'no public message');"))

    def test_all_branch_main_recipient_and_nonrecipient_feedback(self):
        for branch in ('E','A','M'):
            group=main_group(branch,equipment=[0,40,40,40,40,40],own=[0]*5+[1])
            for p,transfer,wallet in ((group.get_players()[0],325,325),(group.get_players()[1],0,445)):
                self.browser(render_page(policy.Result,p),f'''
                    assert(document.getElementById('fine-pool').textContent==='975 punti','actual fine pool');
                    assert(document.getElementById('recipient-count').textContent==='1','recipients');
                    assert(document.getElementById('redistributed-pool').textContent==='325 punti','actual allocation');
                    assert(document.getElementById('own-transfer').textContent==='{transfer} punti','own transfer');
                    assert(document.getElementById('settled-wallet').textContent==='{wallet} punti','wallet');
                    assert(document.getElementById('group-mean').textContent==='33.33 unità','actual mean');
                    assert(document.getElementById('main-threshold').textContent==='{'47' if branch=='A' else '40'} unità','current threshold');
                '''+("assert(Chart.getChart('equipment-chart').data.datasets[3].data[0].y===1/6,'M graphical reference persists');" if branch=='M' else ''))

    def test_no_recipient_is_not_claimed_redistributed(self):
        group=main_group(equipment=[40]*6)
        self.browser(render_page(policy.Result,group.get_players()[0]),"""
            assert(document.getElementById('fine-pool').textContent==='1170 punti','positive pool');
            assert(document.getElementById('redistributed-pool').textContent==='0 punti','zero actual redistribution');
            assert(document.getElementById('own-transfer').textContent==='0 punti','zero transfer');
            assert(document.getElementById('no-recipients').textContent.includes('Non è stato redistribuito nulla'),'honest feedback');
        """)

    def test_negative_wallet_follow_up(self):
        session=make_session();ready(session)
        for r in range(1,11):run_period(subsession(session,r).get_groups()[0])
        p=subsession(session,10).get_groups()[0].get_players()[0]
        self.browser(render_page(policy.Result,p),"""
            assert(document.getElementById('settled-wallet').textContent==='-75 punti','signed wallet');
            assert(document.getElementById('follow-up-fine').textContent==='75 punti','ordinary follow-up');
            assert(!document.getElementById('fine-pool'),'no new pooling');
        """)

    def test_A_main_reveal_and_post_main_reference(self):
        group=main_group('A',equipment=[47]*6)
        p=group.get_players()[0]
        for page,row in ((policy.Result,p),(policy.Decision,p.in_round(6))):
            self.browser(render_page(page,row),'''
                const config=JSON.parse(document.getElementById('lab-chart-config').textContent);
                assert(config.threshold===47 && config.thresholdRevealed,'own-block reveal');
                assert(Chart.getChart('equipment-chart').config.plugins.some(p=>p.id==='ambiguityThreshold'),'visible revealed chart reference');
                assert(!Object.hasOwn(config,'thresholds'),'no future map');
            ''')

    def test_zero_continue_and_message_without_Chart(self):
        session=make_session('M');ready(session)
        group=subsession(session).get_groups()[0];run_period(group,[100]*6)
        p=group.get_players()[0].in_round(2)
        html=re.sub(r'<script src="[^"]*chart\.umd-4\.4\.8\.js"></script>','',render_page(policy.Decision,p))
        self.browser(html,"""
            assert(!document.getElementById('retirement-slider'),'zero state');
            assert(document.getElementById('retirement-value').value==='0','normal zero submission');
            assert(JSON.parse(document.getElementById('lab-chart-config').textContent).publicReportMean===50,'M reference unchanged without graph');
            const button=document.getElementById('confirm-retirement');
            assert(!button.disabled && button.textContent==='Continua','Continua');
            let submitted=false;document.getElementById('form').addEventListener('submit',e=>{submitted=true;e.preventDefault();});
            button.click();assert(submitted,'zero still submits through group barrier');
        """)
