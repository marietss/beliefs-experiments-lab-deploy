"""F template/context tests using actual oTree records in a disposable project.

Run alongside test_fixed in the isolated test copy; no working-tree DB needed.
"""

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import unittest

from test_fixed import make_session, subsession, ready, reports, run_period, finish_block
from otree.database import db
from otree.templating.template import Template
from otree.forms.forms import get_form
import fixed
from fixed import presentation


def render_page(page, player):
    context = dict(player=player)
    if hasattr(page, 'vars_for_template'):
        context.update(page.vars_for_template(player))
    if getattr(page, 'form_fields', None):
        context['form'] = get_form(player, page.form_fields, page, None)
    # Render the actual participant fragment with oTree's template engine.
    # Full base-page/HTTP rendering is also exercised by test_fixed and bots.
    template = page.template_name or f'fixed/{page.__name__}.html'
    path = Path(template) if Path(template).is_file() else Path('_templates', template)
    return Template(path.read_text()).render(context)


def chart_config(html):
    return json.loads(re.search(r'<script id="lab-chart-config" type="application/json">(.*?)</script>', html, re.S).group(1))


def finish_block_for_summary(player):
    """Complete the other groups too; the current summary requires its real barrier."""
    import importlib
    name = player.subsession.get_folder_name()
    app = importlib.import_module(name)
    helpers = importlib.import_module('test_' + name)
    start = player.round_number - player.period + 1
    for ss in player.subsession.in_rounds(start, start + 9):
        for group in ss.get_groups():
            if not group.settlement_complete:
                helpers.run_period(group)
    for peer in ss.get_players():
        app.Result.before_next_page(peer, False)
    app.BlockEndWait.after_all_players_arrive(ss)


class FixedUITests(unittest.TestCase):
    def setUp(self):
        self.session = make_session()
        ready(self.session)

    def tearDown(self):
        db.rollback()

    def group(self, period=1):
        return subsession(self.session, period).get_groups()[0]

    def advance_to(self, period, first_amounts=None):
        for r in range(1, period):
            run_period(self.group(r), first_amounts if r == 1 else None)
        return self.group(period)

    def test_slider_only_explicit_confirmation_and_preview_contract(self):
        p = self.group().get_players()[0]
        reports(p.group)
        html = render_page(fixed.Decision, p)
        self.assertRegex(html, r'type="range"[^>]+min="0" max="100" step="1"')
        self.assertEqual(html.count('type="range"'), 1)
        self.assertNotIn('type="number"', html)
        self.assertNotIn('type="text"', html)
        self.assertNotIn('>+</button>', html)
        self.assertNotIn('>-</button>', html)
        self.assertRegex(html, r'id="confirm-retirement"[^>]+disabled')
        config = chart_config(html)
        self.assertEqual(config['costMilliPoints'], 100)
        self.assertEqual(config['groupHistory'], [])
        self.assertEqual(config['ownHistory'], [dict(period=0, equipment=100)])
        self.assertEqual(config['periods'], 10)

    def test_reduced_equipment_controls_and_exact_current_wallet(self):
        self.advance_to(2, [25] * 6)
        p = self.group(2).get_players()[0]
        html = render_page(fixed.Decision, p)
        self.assertIn('max="75"', html)
        self.assertIn('937.50 punti', html)
        self.assertEqual(chart_config(html)['equipment'], 75)

    def test_zero_equipment_hidden_zero_and_continue_still_normal_form(self):
        self.advance_to(2, [100] * 6)
        html = render_page(fixed.Decision, self.group(2).get_players()[0])
        self.assertNotIn('type="range"', html)
        self.assertIn('name="retirement" value="0"', html)
        self.assertRegex(html, r'id="confirm-retirement"[^>]*>Continua</button>')
        self.assertNotRegex(html, r'id="confirm-retirement"[^>]*disabled')
        self.assertEqual(fixed.Decision.form_fields, ['retirement'])

    def test_main_zero_and_positive_actual_mean_without_threshold(self):
        group = self.advance_to(5)
        run_period(group, [100, 50, 1, 0, 0, 0])
        expected = ['0', '200', '224.50', '225', '225', '225']
        record = group.settlement_record
        for p, fine in zip(group.get_players(), expected):
            html = render_page(fixed.Result, p)
            self.assertEqual(html, render_page(fixed.Result, p))
            self.assertIn(f'id="main-fine">{fine} punti', html)
            self.assertIn('id="group-mean">74.83 unità', html)
            self.assertIn(f'id="main-applied">{"No" if fine == "0" else 'Sì'}', html)
            self.assertNotIn('threshold', chart_config(html))
            self.assertAlmostEqual(chart_config(html)['groupHistory'][-1]['equipment'], 449 / 6)
            self.assertIn(presentation.points(Fraction(p.wallet_after)) + ' punti', html)
        self.assertEqual(group.settlement_record, record)

    def test_follow_up_positive_separates_voluntary_and_forced_state(self):
        group = self.advance_to(10)
        run_period(group)
        p = group.get_players()[0]
        html = render_page(fixed.Result, p)
        for key, value in [('voluntary-equipment', '100 unità'), ('follow-up-fine', '75 punti'),
                           ('forced-retirement', '100 unità'), ('forced-cost', '1000 punti'),
                           ('final-equipment', '0 unità'), ('settled-wallet', '-300 punti')]:
            self.assertIn(f'id="{key}">{value}', html)
        self.assertIn("Attrezzatura prima dell'accertamento finale", html)
        self.assertEqual(chart_config(html)['ownHistory'][-1]['equipment'], 100)
        self.assertEqual(chart_config(html)['groupHistory'][-1]['equipment'], 100)
        finish_block_for_summary(p)
        end = render_page(fixed.BlockEnd, p)
        self.assertIn('-300 punti', end)
        record, wallet = group.settlement_record, p.wallet_after
        db.commit()
        db.expire_all()
        self.assertEqual(html, render_page(fixed.Result, p))
        self.assertEqual(end, render_page(fixed.BlockEnd, p))
        self.assertEqual((record, wallet), (group.settlement_record, p.wallet_after))

    def test_follow_up_voluntarily_zero_has_no_forced_cost(self):
        group = self.advance_to(10)
        run_period(group, [100] * 6)
        html = render_page(fixed.Result, group.get_players()[0])
        for key, unit in [('voluntary-equipment', 'unità'), ('follow-up-fine', 'punti'),
                          ('forced-retirement', 'unità'), ('forced-cost', 'punti'), ('final-equipment', 'unità')]:
            self.assertIn(f'id="{key}">0 {unit}', html)

    def test_exact_fractional_cost_and_read_only_reload(self):
        group = self.group()
        run_period(group, [1] * 6)
        p = group.get_players()[0]
        before = (group.settlement_record, p.wallet_after, p.voluntary_cost)
        first = render_page(fixed.Result, p)
        self.assertIn('id="voluntary-cost">0.10 punti', first)
        self.assertIn('id="settled-wallet">999.90 punti', first)
        self.assertEqual(first, render_page(fixed.Result, p))
        self.assertEqual(before, (group.settlement_record, p.wallet_after, p.voluntary_cost))

    def test_exact_point_formatting_and_mean_display(self):
        for value, text in [(0, '0'), (Fraction(3, 40), '0.08'), (Fraction('46.875'), '46.88'),
                            (Fraction('175.5'), '175.50'), (-250, '-250'), (Fraction(1, 3), '0.33')]:
            self.assertEqual(presentation.points(value), text)
        self.assertEqual(presentation.mean_display(Fraction(449, 6)), '74.83')
        self.assertEqual(presentation.mean_display(Fraction('0.125')), '0.13')

    def test_privacy_allowlist_and_actual_stored_mean_history(self):
        group = self.group()
        run_period(group, [1, 2, 3, 4, 5, 6])
        p = group.get_players()[0]
        result = render_page(fixed.Result, p)
        decision = render_page(fixed.Decision, p.in_round(2))
        config = chart_config(decision)
        self.assertEqual(set(config), {'periods', 'period', 'mainPeriod', 'followUpPeriod',
                                      'ownHistory', 'groupHistory', 'costMilliPoints', 'equipment'})
        self.assertEqual(config['groupHistory'], [dict(period=1, equipment=96.5)])
        for html in (result, decision):
            for peer in subsession(self.session).get_players():
                self.assertNotIn(peer.participant.code, html)
            for forbidden in ('Other firm', 'simulated', 'matching_seed', 'lab_group_matrices',
                              'settlement_record', 'paid_block', 'id_in_group'):
                self.assertNotIn(forbidden, html)

    def test_reports_exactly_two_integer_questions_and_own_inclusion(self):
        html = render_page(fixed.Reports, self.group().get_players()[0])
        self.assertEqual(html.count('type="range"'), 2)
        self.assertIn('il tuo gruppo avrà in media', html)
        self.assertIn('Prima della prima decisione di questo blocco', html)
        self.assertNotIn('public', html)
        self.assertEqual(len(fixed.Reports.form_fields), 2)
        self.assertIn('Blocco 1.1', render_page(fixed.BlockStart, self.group().get_players()[0]))

    def test_new_block_graph_and_wallet_reset(self):
        finish_block(self.session, 1)
        p = subsession(self.session, 11).get_players()[0]
        html = render_page(fixed.Decision, p)
        self.assertIn('Blocco 1.2', html)
        self.assertIn('1000 punti', html)
        config = chart_config(html)
        self.assertEqual(config['ownHistory'], [dict(period=0, equipment=100)])
        self.assertEqual(config['groupHistory'], [])

    def test_local_assets_served_by_otree_http(self):
        from otree.asgi import app
        from starlette.testclient import TestClient
        with TestClient(app) as client:
            for name in ('vendor/chart.umd-4.4.8.js', 'comparable-charts.js', 'decision.js', 'interface.css'):
                response = client.get('/static/fixed/' + name)
                self.assertEqual(response.status_code, 200, name)
                self.assertEqual(response.content, Path('_static/fixed', name).read_bytes())

    def test_local_pinned_chart_and_no_legacy_live_cost_assets(self):
        p = self.group().get_players()[0]
        reports(p.group)
        html = render_page(fixed.Decision, p)
        self.assertIn('/static/fixed/vendor/chart.umd-4.4.8.js', html)
        self.assertNotIn('https://', html)
        self.assertNotIn('stage_game_section1', html)
        vendor = Path('_static/fixed/vendor/chart.umd-4.4.8.js').read_bytes()
        self.assertEqual(hashlib.sha256(vendor).hexdigest(), 'e4cf4d144b222634f2e64ff707cd57b953f8de4b65b231cd5ac6bde114648e4d')
        for path in [*Path('fixed').glob('*.html'), *Path('_static/fixed').glob('*.js')]:
            self.assertNotRegex(path.read_text(), r'\b0\.05\b')
        for script in re.findall(r'<script src="([^"]+)"', html):
            self.assertTrue(Path('_static', script.split('?',1)[0].removeprefix('/static/')).is_file())


if __name__ == '__main__':
    unittest.main()
