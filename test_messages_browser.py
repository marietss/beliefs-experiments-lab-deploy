"""Offline headless-Chrome checks of M controls, threshold and Main feedback.

Rendered-page fixtures exercise local assets; actual multiplayer HTTP flow is
covered separately by test_messages and the 18/24-person bot sessions.
"""

import html as html_module
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from test_fixed_browser import CHROME
from test_messages import make_session, subsession, ready, reports, run_period
from test_messages_ui import render_page
from otree.database import db
import messages


@unittest.skipUnless(CHROME, 'Headless Chrome unavailable.')
class MessagesBrowserTests(unittest.TestCase):
    def tearDown(self):
        db.rollback()

    def browser(self, fragment, assertions):
        for app in ('fixed', 'messages'):
            fragment = fragment.replace(f'/static/{app}/', Path('_static', app).resolve().as_uri() + '/')
        harness = '''<script>
        window.addEventListener('load', () => setTimeout(() => {
            const result = document.createElement('pre'); result.id = 'browser-result';
            const assert = (condition, text) => {if (!condition) throw new Error(text);};
            try { ASSERTIONS result.textContent = 'PASS'; }
            catch(error) { result.textContent = 'FAIL: ' + error.message; }
            document.body.appendChild(result);
        }, 100));
        </script>'''.replace('ASSERTIONS', assertions)
        with tempfile.TemporaryDirectory(prefix='messages-browser-') as temp:
            fixture = Path(temp, 'fixture.html')
            fixture.write_text('<!doctype html><html><body><form id="form">' + fragment + '</form>' + harness + '</body></html>')
            result = subprocess.run([
                CHROME, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
                '--disable-background-networking', '--disable-component-update',
                '--host-resolver-rules=MAP * ~NOTFOUND', '--allow-file-access-from-files',
                '--user-data-dir=' + str(Path(temp, 'profile')), '--dump-dom',
                '--virtual-time-budget=2000', fixture.as_uri(),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            found = re.search(r'<pre id="browser-result">(.*?)</pre>', result.stdout, re.S)
            self.assertIsNotNone(found, result.stdout[-2000:] + result.stderr[-1000:])
            self.assertEqual(html_module.unescape(found.group(1)), 'PASS')

    def decision(self, *, zero=False, charts=True):
        session = make_session()
        ready(session)
        group = subsession(session).get_groups()[0]
        p = group.get_players()[0]
        if zero:
            run_period(group, [100] * 6)
            p = p.in_round(2)
        else:
            reports(group)
        fragment = render_page(messages.Decision, p)
        if not charts:
            fragment = re.sub(r'<script src="[^"]*chart\.umd-4\.4\.8\.js"></script>', '', fragment)
        assertions = """
            const config = JSON.parse(document.getElementById('lab-chart-config').textContent);
            assert(config.threshold === 37, 'known threshold source');
            assert(config.publicReportMean === 50, 'public aggregate');
            assert(!document.getElementById('public-report-mean') && config.publicReportMean === 50, 'public mean in chart rather than repeated box');
            assert(!document.getElementById('known-threshold'), 'threshold prose removed; configured graph reference retained');
            const button = document.getElementById('confirm-retirement');
            const field = document.getElementById('retirement-value');
            const slider = document.getElementById('retirement-slider');
            assert(!document.getElementById('rules-dialog') && !document.getElementById('rules-open'), 'rules supplied on paper');
        """
        if zero:
            assertions += "assert(!slider && field.value === '0' && !button.disabled && button.textContent === 'Continua', 'zero Continua');"
        else:
            assertions += """
                assert(button.disabled && field.value === '', 'explicit decision');
                assert(slider.min === '0' && slider.max === '100', 'slider limits');
                slider.value = '25'; slider.dispatchEvent(new Event('input'));
                assert(!button.disabled && field.value === '25', 'slider wiring');
                assert(document.getElementById('selected-cost').textContent === '62.50 punti', 'cost');
                assert(document.getElementById('remaining-equipment').textContent === '75 unità', 'equipment');
            """
        if charts:
            assertions += '''
                assert(Chart.version === '4.4.8', 'local pinned Chart');
                const graph = Chart.getChart('equipment-chart');
                assert(graph.config.plugins.some(plugin => plugin.id === 'knownMainThreshold'), 'threshold graph indicator');
                const message = graph.data.datasets[3];
                assert(message.data.length === 1 && message.data[0].y === 50 && message.pointStyle === 'rect', 'distinct planned aggregate marker');
                assert(message.label === 'Attrezzatura media prevista', 'planned label');
            '''
        else:
            assertions += "assert(!document.getElementById('chart-unavailable').hidden, 'graph-independent controls');"
        assertions += '''
            let submitted = false;
            document.getElementById('form').addEventListener('submit', e => {submitted = true; e.preventDefault();});
            button.click(); assert(submitted, 'normal form submission');
        '''
        self.browser(fragment, assertions)

    def test_slider_threshold_graph_and_confirm(self):
        self.decision()

    def test_zero_equipment_continue(self):
        self.decision(zero=True)

    def test_controls_without_chart_dependency(self):
        self.decision(charts=False)

    def test_main_equality_and_above_threshold_feedback(self):
        for equipment, success, enforced, fine in [(37, 'No', 'Sì', '193.50'), (38, 'Sì', 'No', '0')]:
            session = make_session()
            ready(session)
            for r in range(1, 5):
                run_period(subsession(session, r).get_groups()[0])
            group = subsession(session, 5).get_groups()[0]
            run_period(group, [100 - equipment] * 6)
            fragment = render_page(messages.Result, group.get_players()[0])
            self.browser(fragment, f'''
                assert(Chart.getChart('equipment-chart').data.datasets[3].data[0].y === 50, 'fixed block-start report');
                assert(document.getElementById('main-threshold').textContent === '37 unità', 'threshold');
                assert(document.getElementById('group-mean').textContent === '{equipment} unità', 'actual mean');
                assert(document.getElementById('target-satisfied').textContent === '{success}', 'strict comparison');
                assert(document.getElementById('main-enforcement').textContent === '{enforced}', 'common enforcement');
                assert(document.getElementById('main-fine').textContent === '{fine} punti', 'own fine');
                assert(Chart.getChart('equipment-chart').data.datasets[1].data.at(-1).y === {equipment}, 'stored mean graph');
            ''')
