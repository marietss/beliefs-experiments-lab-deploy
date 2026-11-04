"""E participant rendering from actual settled records; isolated project only."""

from fractions import Fraction
import json
from pathlib import Path
import re
import unittest

from test_endogenous import make_session, subsession, ready, reports, run_period
from otree.database import db
from test_fixed_ui import finish_block_for_summary
from otree.forms.forms import get_form
from otree.templating.template import Template
import endogenous
import lab_presentation


def render_page(page, player):
    context = dict(player=player)
    if hasattr(page, 'vars_for_template'):
        context.update(page.vars_for_template(player))
    if getattr(page, 'form_fields', None):
        context['form'] = get_form(player, page.form_fields, page, None)
    template = page.template_name or f'endogenous/{page.__name__}.html'
    path = Path(template) if Path(template).is_file() else Path('_templates', template)
    return Template(path.read_text()).render(context)


def chart_config(html):
    return json.loads(re.search(r'<script id="lab-chart-config" type="application/json">(.*?)</script>', html, re.S).group(1))


class EndogenousUITests(unittest.TestCase):
    def setUp(self):
        self.session = make_session()
        ready(self.session)

    def tearDown(self):
        db.rollback()

    def group(self, period=1):
        return subsession(self.session, period).get_groups()[0]

    def main(self, equipment):
        for r in range(1, 5):
            run_period(self.group(r))
        group = self.group(5)
        run_period(group, [100 - k for k in equipment])
        return group

    def test_decision_known_threshold_sole_slider_and_local_assets(self):
        p = self.group().get_players()[0]
        reports(p.group)
        html = render_page(endogenous.Decision, p)
        self.assertRegex(html, r'type="range"[^>]*min="0" max="100" step="1"')
        self.assertEqual(html.count('type="range"'), 1)
        self.assertNotIn('type="number"', html)
        self.assertNotIn('>+</button>', html)
        self.assertNotIn('>-</button>', html)
        self.assertEqual(chart_config(html)['threshold'], 40)
        self.assertEqual(chart_config(html)['threshold'], 40)
        config = chart_config(html)
        self.assertEqual(config['threshold'], 40)
        self.assertEqual(config['groupHistory'], [])
        self.assertEqual(config['costMilliPoints'], 100)
        self.assertIn('/static/fixed/vendor/chart.umd-4.4.8.js', html)
        self.assertIn('/static/endogenous/charts.js', html)
        self.assertNotIn('https://', html)

    def test_main_equality_feedback_is_not_success(self):
        group = self.main([40] * 6)
        p = group.get_players()[0]
        html = render_page(endogenous.Result, p)
        for key, text in [('group-mean', '40 unità'), ('main-threshold', '40 unità'),
                          ('target-satisfied', 'No'), ('main-enforcement', 'Sì'),
                          ('main-fine', '195 punti'), ('settled-wallet', '445 punti')]:
            self.assertIn(f'id="{key}">{text}', html)
        self.assertIn('uguale o inferiore a 40 unità', html)
        self.assertNotIn('at least 40', html)
        before = group.settlement_record
        self.assertEqual(html, render_page(endogenous.Result, p))
        self.assertEqual(before, group.settlement_record)

    def test_main_above_no_enforcement_and_actual_mean(self):
        group = self.main([0, 20, 40, 50, 60, 71])
        for p in group.get_players():
            html = render_page(endogenous.Result, p)
            self.assertIn('id="group-mean">40.17 unità', html)
            self.assertIn('id="target-satisfied">Sì', html)
            self.assertIn('id="main-enforcement">No', html)
            self.assertIn('id="main-fine">0 punti', html)
            self.assertEqual(chart_config(html)['groupHistory'][-1]['equipment'], float(Fraction(241, 6)))

    def test_main_mixed_zero_exemption_under_common_enforcement(self):
        group = self.main([0, 20, 40, 50, 60, 69])
        for p, fine in zip(group.get_players(), ['0', '185', '195', '200', '205', '209.50']):
            html = render_page(endogenous.Result, p)
            self.assertIn('id="main-enforcement">Sì', html)
            self.assertIn(f'id="main-fine">{fine} punti', html)
            self.assertIn('id="group-mean">39.83 unità', html)

    def test_zero_continue_preserves_normal_submission(self):
        group = self.group()
        run_period(group, [100] * 6)
        p = group.get_players()[0].in_round(2)
        html = render_page(endogenous.Decision, p)
        self.assertNotIn('type="range"', html)
        self.assertIn('name="retirement" value="0"', html)
        self.assertIn('>Continua</button>', html)
        self.assertEqual(chart_config(html)['threshold'], 40)

    def test_follow_up_and_own_negative_block_wallet(self):
        for r in range(1, 11):
            run_period(self.group(r))
        p = self.group(10).get_players()[0]
        html = render_page(endogenous.Result, p)
        for key, text in [('voluntary-equipment', '100 unità'), ('follow-up-fine', '75 punti'),
                          ('forced-retirement', '100 unità'), ('forced-cost', '1000 punti'),
                          ('final-equipment', '0 unità'), ('settled-wallet', '-75 punti')]:
            self.assertIn(f'id="{key}">{text}', html)
        finish_block_for_summary(p)
        end = render_page(endogenous.BlockEnd, p)
        self.assertIn('-75 punti', end)
        self.assertNotIn('id="main-enforcement"', html)

    def test_two_private_reports_and_start_rules(self):
        p = self.group().get_players()[0]
        html = render_page(endogenous.Reports, p)
        self.assertEqual(html.count('type="range"'), 2)
        self.assertIn('il tuo gruppo avrà in media', html)
        self.assertIn('Prima della prima decisione di questo blocco', html)
        start = render_page(endogenous.BlockStart, p)
        self.assertIn('Blocco 2.1', start)
        self.assertNotIn('Istruzioni del blocco', start)
        self.assertNotIn('informational', start)

    def test_privacy_and_no_A_M_policy_payloads(self):
        group = self.main([0, 20, 40, 50, 60, 69])
        p = group.get_players()[0]
        for page, row in [(endogenous.Result, p), (endogenous.Decision, p.in_round(6))]:
            html = render_page(page, row)
            for other in subsession(self.session).get_players():
                self.assertNotIn(other.participant.code, html)
            for term in ('simulated', 'other firm', 'ambiguity', 'reveal', 'public average',
                         'redistribut', 'transfer', 'matching_seed', 'paid_block', 'settlement_record'):
                self.assertNotIn(term, re.sub(r'<(?:style|script)\b[^>]*>.*?</(?:style|script)>', '', html, flags=re.S).lower())
            config = chart_config(html)
            allowed = {'threshold','periods','period','mainPeriod','followUpPeriod','ownHistory','groupHistory','costMilliPoints','equipment'}
            self.assertFalse(set(config) - allowed)
            self.assertTrue(all(set(point) == {'period','equipment'} for point in config['groupHistory']))

    def test_presentation_extraction_preserves_F_function_identity(self):
        from fixed import presentation
        for name in ('points','mean_display','chart_context','outcome_context','block_summary'):
            self.assertIs(getattr(presentation, name), getattr(lab_presentation, name))
