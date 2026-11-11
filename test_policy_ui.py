"""Policy participant allowlists, privacy, active templates and genuine HTTP barriers."""
from fractions import Fraction
import json
from pathlib import Path
import re
import unittest

from test_policy import make_session,subsession,ready,reports,decide,run_period,main_group
from otree.database import db
from test_fixed_ui import finish_block_for_summary
from otree.bots.runner import make_bots
from otree.forms.forms import get_form
from otree.templating.template import Template
import policy


def render_page(page,player):
    context=dict(player=player)
    if hasattr(page,'vars_for_template'):context.update(page.vars_for_template(player))
    if getattr(page,'form_fields',None):context['form']=get_form(player,page.form_fields,page,None)
    template = page.template_name or f'policy/{page.__name__}.html'
    path = Path(template) if Path(template).is_file() else Path('_templates', template)
    return Template(path.read_text()).render(context)


def chart_config(html):
    return json.loads(re.search(r'<script id="lab-chart-config" type="application/json">(.*?)</script>',html,re.S).group(1))


def assert_blind(test,html):
    config=chart_config(html)
    test.assertEqual((config['thresholdLow'],config['thresholdHigh'],config['thresholdRevealed']),(33,42,False))
    test.assertNotIn('threshold',config)
    test.assertNotIn('id="revealed-threshold"',html)
    test.assertNotIn('id="main-threshold"',html)
    for name in ('ambiguity_thresholds','thresholds','fine_pool','recipient_count','redistributed_pool'):
        test.assertNotIn(name,config)
    return config


class PolicyUITests(unittest.TestCase):
    def tearDown(self):db.rollback()

    def test_branch_start_report_disclosure_exactly_two_questions(self):
        for branch in ('E','A','M'):
            session=make_session(branch);ready(session)
            p=subsession(session).get_players()[0]
            start=render_page(policy.BlockStart,p)
            html=render_page(policy.Reports,p)
            self.assertEqual(html.count('type="range"'),2)
            self.assertIn('il tuo gruppo avrà in media',html)
            self.assertIn('Prima della prima decisione di questo blocco',html)
            self.assertIn('Blocco 3.1',start)
            self.assertNotIn('Istruzioni del blocco',start)
            self.assertNotIn('public_report_mean',policy.Reports.vars_for_template(p))
            if branch=='M':
                self.assertLess(html.index('id="report-disclosure"'),html.index('name="expected_own_equipment_main"'))
                self.assertNotIn('report-disclosure',start)
                self.assertIn('quadratini grigi',html)
            else:
                self.assertNotIn('id="report-disclosure"',html)
                self.assertNotIn('Entrambe le risposte rimangono private',html)
            if branch=='A':
                self.assertNotIn('threshold',policy.BlockStart.vars_for_template(p))
                self.assertEqual(policy.BlockStart.vars_for_template(p)['support_high'],42)
                self.assertNotIn('id="revealed-threshold"',start)
            else:self.assertNotIn('soglia',start)

    def test_slider_only_local_assets_and_branch_specific_chart_payload(self):
        for branch in ('E','A','M'):
            session=make_session(branch);ready(session)
            group=subsession(session).get_groups()[0];reports(group,[0]*5+[1])
            p=group.get_players()[0];html=render_page(policy.Decision,p)
            self.assertRegex(html,r'type="range"[^>]*min="0" max="100" step="1"')
            self.assertEqual(html.count('type="range"'),1)
            self.assertNotIn('type="number"',html)
            self.assertNotIn('>+</button>',html);self.assertNotIn('>-</button>',html)
            self.assertNotIn('https://',html)
            self.assertIn('/static/fixed/vendor/chart.umd-4.4.8.js',html)
            self.assertIn('/static/policy/charts.js',html)
            config=chart_config(html)
            self.assertEqual(config['costMilliPoints'],100)
            self.assertEqual(config['groupHistory'],[])
            if branch=='A':assert_blind(self,html)
            else:self.assertEqual(config['threshold'],37)
            if branch=='M':
                self.assertNotIn('id="public-report-mean"',html)
                self.assertEqual(chart_config(html)['publicReportMean'],1/6)
                self.assertEqual(config['publicReportMean'],1/6)
            else:self.assertNotIn('publicReportMean',config)

    def test_every_A_pre_main_surface_is_blind_and_only_settled_current_reveals(self):
        session=make_session('A');ready(session)
        for r in range(1,6):
            group=subsession(session,r).get_groups()[0]
            if r==1:reports(group)
            for p in group.get_players():
                self.assertNotIn('threshold',policy.Decision.vars_for_template(p))
                assert_blind(self,render_page(policy.Decision,p))
            decide(group,[58]*6 if r==5 else None)
            if r==5:
                assert_blind(self,render_page(policy.Decision,group.get_players()[0]))
                self.assertFalse(group.settlement_complete)
            policy.settle_period(group)
            if r<5:assert_blind(self,render_page(policy.Result,group.get_players()[0]))
        p=group.get_players()[0]
        html=render_page(policy.Result,p)
        config=chart_config(html)
        self.assertEqual(config['threshold'],42)
        self.assertTrue(config['thresholdRevealed'])
        self.assertIn('id="main-threshold">42 unità',html)
        self.assertIn('id="target-satisfied">No',html)
        self.assertIn('strettamente maggiore di 42',html)
        self.assertNotIn('at least 42',html)
        self.assertEqual(set(k for k in config if 'threshold' in k.lower()),{'thresholdLow','thresholdHigh','thresholdRevealed','threshold'})
        self.assertNotIn('ambiguity_thresholds',html)
        self.assertNotIn('thresholds',policy.Result.vars_for_template(p))
        assert_blind(self,render_page(policy.Decision,p))  # stale period-5 decision stays blind
        self.assertEqual(chart_config(render_page(policy.Decision,p.in_round(6)))['threshold'],42)
        self.assertEqual(render_page(policy.Result,p),html)

    def test_main_feedback_recipient_nonrecipient_and_exact_wallet(self):
        group=main_group(equipment=[0,40,40,40,40,40])
        for p,transfer,wallet,fine in [(group.get_players()[0],'292.50','292.50','0'),(group.get_players()[1],'0','445','195')]:
            html=render_page(policy.Result,p)
            for key,text in [('fine-pool','975 punti'),('recipient-count','1'),('redistributed-pool','292.50 punti'),
                             ('own-transfer',f'{transfer} punti'),('settled-wallet',f'{wallet} punti'),('main-fine',f'{fine} punti'),
                             ('group-mean','33.33 unità')]:
                self.assertIn(f'id="{key}">{text}',html)
            self.assertIn('id="policy-rho">3/10',html)
            self.assertNotIn('id="no-recipients"',html)
        self.assertIn('id="policy-recipient">Sì',render_page(policy.Result,group.get_players()[0]))
        self.assertIn('id="policy-recipient">No',render_page(policy.Result,group.get_players()[1]))

    def test_no_recipient_feedback_zero_actual_distribution(self):
        group=main_group(equipment=[37]*6)
        html=render_page(policy.Result,group.get_players()[0])
        self.assertIn('id="fine-pool">1161 punti',html)
        self.assertIn('id="recipient-count">0',html)
        self.assertIn('id="redistributed-pool">0 punti',html)
        self.assertIn('Non è stato redistribuito nulla',html)
        self.assertIn('id="own-transfer">0 punti',html)

    def test_repeating_transfer_not_two_decimal_settlement(self):
        group=main_group(rho=Fraction(1,3),equipment=[0,0,0,40,40,41])
        html=render_page(policy.Result,group.get_players()[0])
        self.assertIn('id="own-transfer">65.06 punti',html)
        self.assertIn('id="settled-wallet">65.06 punti',html)
        self.assertEqual(group.get_players()[0].own_transfer,'1171/18')

    def test_post_main_wallet_contains_transfer_once_follow_up_and_block_end(self):
        group=main_group('M',equipment=[0,40,40,40,40,40],own=[0]*5+[1])
        p=group.get_players()[0]
        for r in range(6,11):
            row=p.in_round(r)
            html=render_page(policy.Decision,row)
            self.assertIn('id="current-wallet">292.50 punti',html)
            self.assertNotIn('id="public-report-mean"',html)
            self.assertEqual(chart_config(html)['publicReportMean'],1/6)
            self.assertIn('name="retirement" value="0"',html)
            run_period(row.group)
        html=render_page(policy.Result,row)
        for key,text in [('voluntary-equipment','0 unità'),('follow-up-fine','0 punti'),('forced-cost','0 punti')]:
            self.assertIn(f'id="{key}">{text}',html)
        self.assertNotIn('id="fine-pool"',html)
        finish_block_for_summary(row)
        end=render_page(policy.BlockEnd,row)
        self.assertIn('292.50 punti',end)
        self.assertNotIn('id="public-report-mean"',end)

    def test_negative_wallet_rendering(self):
        session=make_session();ready(session)
        for r in range(1,11):run_period(subsession(session,r).get_groups()[0])
        p=subsession(session,10).get_groups()[0].get_players()[0]
        self.assertIn('id="settled-wallet">-75 punti',render_page(policy.Result,p))
        finish_block_for_summary(p)
        self.assertIn('-75 punti',render_page(policy.BlockEnd,p))

    def test_all_branch_privacy_context_allowlist(self):
        for branch in ('E','A','M'):
            group=main_group(branch,equipment=[0,20,40,60,70,79],own=[3,17,29,53,71,97])
            for page,p in [(policy.Result,group.get_players()[0]),(policy.Decision,group.get_players()[0].in_round(6))]:
                html=render_page(page,p);context=page.vars_for_template(p);config=chart_config(html)
                allowed={'periods','period','mainPeriod','followUpPeriod','ownHistory','groupHistory','costMilliPoints','equipment','threshold','thresholdLow','thresholdHigh','thresholdRevealed','publicReportMean','publicReportPlans'}
                self.assertFalse(set(config)-allowed)
                self.assertTrue(all(set(point)=={'period','equipment'} for point in config['groupHistory']))
                for other in subsession(group.session).get_players():self.assertNotIn(other.participant.code,html)
                for key in ('public_report_record','locked_own_report','locked_group_report','report1','report2','reports',
                            'ambiguity_thresholds','matrices','settlement_record','matching_seed','paid_block'):
                    self.assertNotIn(key,context);self.assertNotIn(key,config)
                    if key != 'reports':self.assertNotIn(key,html)
                if branch!='M':self.assertNotIn('public_report_mean',context)

    def test_local_assets_resolve_and_no_legacy_live_cost(self):
        from starlette.testclient import TestClient
        from otree.asgi import app
        with TestClient(app) as client:
            for path in ('/static/policy/charts.js','/static/fixed/vendor/chart.umd-4.4.8.js'):
                self.assertEqual(client.get(path).status_code,200)
        for path in [*Path('policy').glob('*.html'),Path('_static/policy/charts.js')]:
            self.assertNotRegex(path.read_text(),r'\b0\.05\b')
            self.assertNotIn('cdn.jsdelivr.net',path.read_text())


class PolicyHTTPTests(unittest.TestCase):
    @unittest.skipUnless(Path('policy/tests.py').is_file(), 'Policy bot fixture policy/tests.py absent from deployment; native session barriers are tested without bots.')
    def test_actual_waitpages_slow_groups_branch_privacy_and_block_barrier(self):
        for branch in ('E','A','M'):
            session=make_session(branch)
            bots=make_bots(session_pk=session.id,case_number=0,use_browser_bots=False)
            db.commit()
            for bot in bots:bot.open_start_url();self.assertFalse(bot.on_wait_page())
            for bot in bots[:-1]:
                bot.submit(bot.get_next_submit());self.assertTrue(bot.on_wait_page())
            self.assertFalse(subsession(session).readiness_complete)
            bots[-1].submit(bots[-1].get_next_submit());db.expire_all()
            by_code={b.participant_code:b for b in bots}
            groups=[[by_code[p.participant.code] for p in g.get_players()] for g in subsession(session).get_groups()]
            first=subsession(session).get_groups()[0]
            def submit(bot):
                self.assertFalse(bot.on_wait_page())
                db.expire_all();bot.submit(bot.get_next_submit());db.expire_all()
            for bot in bots:
                for _ in range(4):submit(bot) # rejected/correct section pairs
            for bot in bots:submit(bot) # authenticated admin first-block release
            def start_report(bot):
                for _ in range(2):submit(bot) # rejected/valid reports
            for bot in groups[0][:-1]:start_report(bot)
            self.assertFalse(first.reports_complete)
            self.assertFalse(first.public_report_complete)
            self.assertEqual(first.public_report_mean,'')
            start_report(groups[0][-1])
            self.assertTrue(first.reports_complete)
            self.assertEqual(first.public_report_complete,branch=='M')
            for r in range(1,11):
                active=subsession(session,r).get_groups()[0]
                for index,bot in enumerate(groups[0]):
                    self.assertFalse(bot.on_wait_page())
                    if branch=='A' and r<=5:assert_blind(self,bot.html)
                    if branch=='M':self.assertEqual(chart_config(bot.html)['publicReportMean'],1/6)
                    for peer in bots:
                        if peer.participant_code!=bot.participant_code:self.assertNotIn(peer.participant_code,bot.html)
                    submit(bot)
                    if index<5:self.assertFalse(active.settlement_complete)
                for bot in groups[0]:
                    self.assertFalse(bot.on_wait_page())
                    if r==5:
                        self.assertIn('id="fine-pool">0 punti',bot.html)
                        if branch=='A':self.assertEqual(chart_config(bot.html)['threshold'],42)
                    submit(bot)
            self.assertTrue(groups[0][0].on_wait_page())
            self.assertFalse(subsession(session,10).block_barrier_complete)
            self.assertFalse(subsession(session,11).grouping_installed)
            for group_bots in groups[1:]:
                for bot in group_bots:start_report(bot)
                for _ in range(10):
                    for bot in group_bots:submit(bot)
                    for bot in group_bots:submit(bot)
            self.assertTrue(subsession(session,10).block_barrier_complete)
            self.assertTrue(subsession(session,11).grouping_installed)
            self.assertFalse(groups[0][0].on_wait_page())
            # New rematched block's message is unavailable until its own reports.
            p=next(p for p in subsession(session,11).get_players() if p.participant.code==groups[0][0].participant_code)
            self.assertNotIn('public_report_mean',policy.BlockStart.vars_for_template(p))
            self.assertFalse(p.group.public_report_complete)
