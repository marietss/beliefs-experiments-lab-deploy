"""A secrecy/privacy and reveal tests against actual templates and HTTP pages."""

import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from test_ambiguity import make_session, subsession, ready, reports, run_period, decide
from otree.bots.runner import make_bots
from otree.database import db
from test_fixed_ui import finish_block_for_summary
from otree.forms.forms import get_form
from otree.templating.template import Template
import ambiguity


def render_page(page, player):
    context = dict(player=player)
    if hasattr(page, 'vars_for_template'):
        context.update(page.vars_for_template(player))
    if getattr(page, 'form_fields', None):
        context['form'] = get_form(player, page.form_fields, page, None)
    template = page.template_name or f'ambiguity/{page.__name__}.html'
    path = Path(template) if Path(template).is_file() else Path('_templates', template)
    return Template(path.read_text()).render(context)


def chart_config(html):
    return json.loads(re.search(r'<script id="lab-chart-config" type="application/json">(.*?)</script>',html,re.S).group(1))


def assert_blind(test, html):
    config = chart_config(html)
    test.assertEqual(config['thresholdLow'], 33)
    test.assertEqual(config['thresholdHigh'], 47)
    test.assertFalse(config['thresholdRevealed'])
    test.assertNotIn('threshold', config)
    test.assertNotIn('ambiguity_thresholds', html)
    test.assertNotIn('lab_ambiguity_thresholds', html)
    test.assertNotIn('id="main-threshold"', html)
    test.assertNotIn('id="revealed-threshold"', html)
    test.assertNotIn('known-threshold', html)
    allowed={'periods','period','mainPeriod','followUpPeriod','ownHistory','groupHistory','costMilliPoints','equipment','thresholdLow','thresholdHigh','thresholdRevealed'}
    test.assertFalse(set(config) - allowed)
    return config


class AmbiguityUITests(unittest.TestCase):
    def setUp(self):
        self.session=make_session()
        ready(self.session)

    def tearDown(self):
        db.rollback()

    def group(self, period=1):
        return subsession(self.session,period).get_groups()[0]

    def test_start_reports_and_decisions_context_allowlist(self):
        p=self.group().get_players()[0]
        context=ambiguity.BlockStart.vars_for_template(p)
        self.assertEqual(context, dict(support_low=33,support_high=47,threshold_revealed=False))
        self.assertNotIn('threshold',context)  # Public support may include realized value 47.
        reports(p.group)
        context=ambiguity.Decision.vars_for_template(p)
        self.assertNotIn('threshold',context)
        self.assertNotIn('ambiguity_thresholds',json.dumps(context))
        self.assertNotIn('threshold',context)  # Public support may include realized value 47.
        html=render_page(ambiguity.Decision,p)
        config=assert_blind(self,html)
        self.assertEqual(config['groupHistory'],[])
        self.assertEqual(config['costMilliPoints'],100)
        self.assertRegex(html,r'type="range"[^>]*min="0" max="100" step="1"')
        self.assertEqual(html.count('type="range"'),1)
        self.assertNotIn('type="number"',html)
        self.assertNotIn('>+</button>',html)
        self.assertNotIn('>-</button>',html)
        self.assertNotIn('https://',html)
        self.assertIn('/static/fixed/vendor/chart.umd-4.4.8.js',html)
        report=render_page(ambiguity.Reports,p)
        self.assertEqual(report.count('type="range"'),2)
        self.assertIn('il tuo gruppo avrà in media',report)
        for page_html in (report,render_page(ambiguity.BlockStart,p),html):
            for wrong in ('equally likely','uniform','random draw','public average','redistribution'):
                self.assertNotIn(wrong,page_html)
            self.assertNotIn('ambiguity_thresholds',page_html)

    def test_every_pre_main_decision_and_result_is_blind(self):
        for period in range(1,6):
            group=self.group(period)
            if period==1:
                reports(group)
            for p in group.get_players():
                context=ambiguity.Decision.vars_for_template(p)
                self.assertNotIn('threshold',context)
                assert_blind(self,render_page(ambiguity.Decision,p))
                error=ambiguity.Decision.error_message(p,dict(retirement=101))
                self.assertNotIn('47',error)
            decide(group)
            if period==5:
                # Six locks are still insufficient until the WaitPage settles.
                self.assertFalse(group.settlement_complete)
                assert_blind(self,render_page(ambiguity.Decision,group.get_players()[0]))
            ambiguity.settle_period(group)
            if period<5:
                assert_blind(self,render_page(ambiguity.Result,group.get_players()[0]))

    def test_reveal_current_only_reload_and_post_main_visibility(self):
        for period in range(1,6):
            run_period(self.group(period),[53]*6 if period==5 else None)
        p=self.group(5).get_players()[0]
        html=render_page(ambiguity.Result,p)
        context=ambiguity.Result.vars_for_template(p)
        self.assertEqual(context['threshold'],47)
        config=chart_config(html)
        self.assertTrue(config['thresholdRevealed'])
        self.assertEqual(config['threshold'],47)
        self.assertIn('id="main-threshold">47 unità',html)
        self.assertIn('id="group-mean">47 unità',html)
        self.assertIn('id="target-satisfied">No',html)
        self.assertIn('id="main-enforcement">Sì',html)
        self.assertIn('id="main-fine">198.50 punti',html)
        self.assertIn('strettamente maggiore di 47',html)
        self.assertNotIn('at least 47',html)
        self.assertNotIn('ambiguity_thresholds',html)
        self.assertNotIn('49',json.dumps({k:v for k,v in config.items() if 'threshold' in k.lower()}))
        self.assertEqual(set(k for k in config if 'threshold' in k.lower()),
                         {'thresholdLow','thresholdHigh','thresholdRevealed','threshold'})
        before=(p.wallet_after,p.group.settlement_record)
        db.commit();db.expire_all()
        self.assertEqual(html,render_page(ambiguity.Result,p))
        self.assertEqual(before,(p.wallet_after,p.group.settlement_record))
        later=render_page(ambiguity.Decision,p.in_round(6))
        self.assertEqual(chart_config(later)['threshold'],47)
        # Even a stale period-5 Decision request remains blind.
        assert_blind(self,render_page(ambiguity.Decision,p))

    def test_post_main_period_number_without_settlement_cannot_reveal(self):
        p=self.group().get_players()[0].in_round(6)
        with self.assertRaisesRegex(ValueError,'before synchronized settlement'):
            ambiguity.presentation.revealed_main(p)

    def test_other_group_main_cannot_reveal_for_a_slow_group(self):
        for period in range(1,6):
            run_period(self.group(period))
        slow=subsession(self.session,5).get_groups()[1].get_players()[0]
        self.assertIsNone(ambiguity.presentation.revealed_main(slow))
        with self.assertRaisesRegex(ValueError,'before synchronized settlement'):
            ambiguity.presentation.revealed_main(slow,result=True)

    def test_zero_equipment_still_submits_zero_without_reveal(self):
        run_period(self.group(),[100]*6)
        p=self.group().get_players()[0].in_round(2)
        html=render_page(ambiguity.Decision,p)
        assert_blind(self,html)
        self.assertNotIn('type="range"',html)
        self.assertIn('name="retirement" value="0"',html)
        self.assertIn('>Continua</button>',html)

    def test_privacy_no_peer_arrays_codes_or_future_thresholds(self):
        for period in range(1,6):
            run_period(self.group(period))
        p=self.group(5).get_players()[0]
        for page,row in ((ambiguity.Result,p),(ambiguity.Decision,p.in_round(6))):
            html=render_page(page,row)
            for other in subsession(self.session).get_players():
                self.assertNotIn(other.participant.code,html)
            for term in ('ambiguity_thresholds','matching_seed','paid_block','settlement_record',
                         'lab_group_matrices','simulated','Other firm'):
                self.assertNotIn(term,html)
            for point in chart_config(html)['groupHistory']:
                self.assertEqual(set(point),{'period','equipment'})

    def test_local_assets_served_and_no_old_cost_fallback(self):
        from starlette.testclient import TestClient
        from otree.asgi import app
        with TestClient(app) as client:
            response=client.get('/static/ambiguity/charts.js')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.content,Path('_static/ambiguity/charts.js').read_bytes())
        for path in [*Path('ambiguity').glob('*.html'),Path('_static/ambiguity/charts.js')]:
            self.assertNotRegex(path.read_text(),r'\b0\.05\b')


class AmbiguityHTTPSecrecyTests(unittest.TestCase):
    def test_real_HTTP_pages_wait_for_six_and_reveal_only_current_block(self):
        session=make_session()
        bots=make_bots(session_pk=session.id,case_number=0,use_browser_bots=False)
        db.commit()
        by_code={b.participant_code:b for b in bots}
        for bot in bots:
            bot.open_start_url()
        for bot in bots:
            bot.submit(bot.get_next_submit())  # authenticated section-splash release
        db.expire_all()
        self.assertTrue(subsession(session).readiness_complete)
        group=subsession(session).get_groups()[0]
        selected=[by_code[p.participant.code] for p in group.get_players()]
        def submit(bot):
            self.assertFalse(bot.on_wait_page())
            db.expire_all();bot.submit(bot.get_next_submit());db.expire_all()
        for bot in bots:
            for _ in range(4):submit(bot)  # rejected/correct section pairs
        for bot in bots:submit(bot)  # admin first-block release, then all-session wait
        for bot in selected:
            for _ in range(2):submit(bot)  # rejected/valid reports
        for period in range(1,6):
            active=group.in_round(period)
            for index,bot in enumerate(selected):
                self.assertFalse(bot.on_wait_page())
                assert_blind(self,bot.html)
                for peer in bots:
                    if peer.participant_code != bot.participant_code:
                        self.assertNotIn(peer.participant_code,bot.html)
                submit(bot)
                if period==5 and index<5:
                    self.assertFalse(active.settlement_complete)
                    self.assertNotIn('ambiguity_thresholds',bot.html)
            for bot in selected:
                self.assertFalse(bot.on_wait_page())
                if period==5:
                    self.assertTrue(active.settlement_complete)
                    self.assertEqual(chart_config(bot.html)['threshold'],47)
                    self.assertNotIn('ambiguity_thresholds',bot.html)
                else:
                    assert_blind(self,bot.html)
                submit(bot)  # stored Result -> next Decision
        for bot in selected:
            self.assertFalse(bot.on_wait_page())
            self.assertEqual(chart_config(bot.html)['threshold'],47)
        self.assertFalse(subsession(session,5).get_groups()[1].settlement_complete)
