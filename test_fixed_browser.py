"""Offline headless-Chrome checks of actual F fragments and local scripts.

No HTTP server or external resource is needed. Run from the disposable project
copy. Set LAB_CHROME_BINARY to override the local browser executable.
"""

import html as html_module
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_fixed_ui import render_page
from test_fixed import make_session, subsession, ready, reports, run_period
from otree.database import db
import fixed


CHROME = os.getenv('LAB_CHROME_BINARY') or shutil.which('chromium') or shutil.which('google-chrome')
if not CHROME:
    mac_chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    CHROME = mac_chrome if Path(mac_chrome).is_file() else None


@unittest.skipUnless(CHROME, 'Headless Chrome unavailable; template/HTTP checks still run separately.')
class FixedBrowserTests(unittest.TestCase):
    def tearDown(self):
        db.rollback()

    def check_browser(self, *, zero=False, charts=True):
        session = make_session()
        ready(session)
        if zero:
            group = subsession(session).get_groups()[0]
            run_period(group, [100] * 6)
            p = group.get_players()[0].in_round(2)
        else:
            p = subsession(session).get_players()[0]
        if not zero:
            reports(p.group)
        fragment = render_page(fixed.Decision, p)
        if not charts:
            fragment = re.sub(r'<script src="[^"]*chart\.umd-4\.4\.8\.js"></script>', '', fragment)
        fragment = fragment.replace('/static/fixed/', Path('_static/fixed').resolve().as_uri() + '/')
        assertions = '''
            const assert = (test, message) => {if (!test) throw new Error(message);};
            const button = document.getElementById('confirm-retirement');
            const field = document.getElementById('retirement-value');
            const slider = document.getElementById('retirement-slider');
            assert(document.querySelectorAll('input[type=number]').length === 0, 'numeric alternative');
            assert(!document.getElementById('rules-dialog') && !document.getElementById('rules-open'), 'rules supplied on paper');
        '''
        if zero:
            assertions += """
                assert(!slider && field.value === '0' && !button.disabled, 'zero Continua');
                assert(button.textContent === 'Continua', 'zero label');
            """
        else:
            assertions += """
                assert(button.disabled && field.value === '', 'explicit choice required');
                let premature = new Event('submit', {bubbles: true, cancelable: true});
                assert(!document.getElementById('form').dispatchEvent(premature), 'premature submit prevented');
                slider.value = '25'; slider.dispatchEvent(new Event('input', {bubbles: true}));
                assert(field.value === '25' && !button.disabled, 'slider wired');
                assert(document.getElementById('remaining-equipment').textContent === '75 unità', 'equipment preview');
                assert(document.getElementById('selected-cost').textContent === '62.50 punti', 'exact cost preview');
            """
            if charts:
                assertions += '''
                    assert(Chart.version === '4.4.8', 'pinned Chart version');
                    const chart = Chart.getChart('equipment-chart');
                    assert(chart.data.datasets[1].data.length === 1 && chart.data.datasets[1].data[0].x === 0 && chart.data.datasets[1].data[0].y === 100, 'common initial equipment anchor');
                    assert(chart.data.datasets[2].data[1].y === 75, 'equipment graph preview');
                    assert(Chart.getChart('cost-chart').data.datasets[1].data[0].y === 62.5, 'cost graph preview');
                '''
            else:
                assertions += "assert(!document.getElementById('chart-unavailable').hidden, 'chart failure fallback');"
            assertions += """
                slider.value = '1'; slider.dispatchEvent(new Event('input'));
                assert(document.getElementById('selected-cost').textContent === '0.10 punti', 'small exact cost');
                slider.value = '0'; slider.click();
                assert(field.value === '0' && !button.disabled, 'explicit zero selection');
            """
        assertions += """
            let submitted = false;
            document.getElementById('form').addEventListener('submit', event => {
                submitted = true; event.preventDefault();
                assert(!event.defaultPrevented || field.value !== '', 'valid form value');
            });
            button.click();
            assert(submitted, 'Conferma/Continua submits normal form');
        """
        harness = '''<script>
            window.addEventListener('load', () => setTimeout(() => {
                const result = document.createElement('pre'); result.id = 'browser-result';
                try { ASSERTIONS result.textContent = 'PASS'; }
                catch(error) { result.textContent = 'FAIL: ' + error.message; }
                document.body.appendChild(result);
            }, 100));
        </script>'''.replace('ASSERTIONS', assertions)
        with tempfile.TemporaryDirectory(prefix='fixed-browser-') as temp:
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
            self.assertIsNotNone(found, result.stdout[-1500:] + result.stderr[-1500:])
            self.assertEqual(html_module.unescape(found.group(1)), 'PASS')

    def test_slider_charts_cost_modal_and_confirm_offline(self):
        self.check_browser()

    def test_chart_unavailable_still_allows_decision(self):
        self.check_browser(charts=False)

    def test_zero_equipment_continue_offline(self):
        self.check_browser(zero=True)


if __name__ == '__main__':
    unittest.main()
