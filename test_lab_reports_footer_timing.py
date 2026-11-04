"""Focused monitor readability, participant footer and native timeout regressions.

Run in a disposable project copy with the normal DEV/EUR in-memory test profile.
"""
import copy
import asyncio
import base64
import json
from urllib.request import urlopen, Request
import websockets
import html as html_module
from pathlib import Path
import re
import subprocess
import tempfile
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

import test_fixed
from otree.asgi import app as asgi
from otree.constants import wait_page_http_header
from otree.database import db
from otree.lookup import _get_session_lookups
from starlette.testclient import TestClient
from test_fixed_browser import CHROME
from test_lab_decision_ui import environments
from test_lab_production import make_production_session
import lab_payment
import survey


class PilotRefinementTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(asgi)

    def tearDown(self):
        db.rollback()

    def open_page(self, player, page):
        pp = player.participant
        pp._index_in_pages = next(i for i, row in _get_session_lookups(player.session.code).items()
                                  if row.app_name == player.subsession.get_folder_name()
                                  and row.round_number == player.round_number and row.page_class is page)
        pp._current_app_name = player.subsession.get_folder_name()
        pp._current_page_name = page.__name__
        pp._round_number = player.round_number
        pp.visited = True
        pp._timeout_expiration_time = None
        pp._timeout_page_index = None
        db.commit()
        response = self.client.get(pp._start_url(), allow_redirects=True)
        db.expire_all()
        self.assertEqual(response.status_code, 200)
        return response

    def browser(self, source, assertions, width=1366, height=900, screenshot=None):
        import otree
        def asset(match):
            relative = match[2].split('?')[0]
            target = Path('_static', relative)
            if not target.is_file():
                target = Path(otree.__file__).parent / 'static' / relative
            self.assertTrue(target.is_file(), str(target))
            return match[1] + target.resolve().as_uri()
        source = re.sub(r'([\"\'])/static/([^\"\']+)', asset, source)
        # An offline fixture has no oTree websocket server; keep the native timer.
        source = re.sub(r'<script id="websocket-redirect".*?</script>', '', source, flags=re.S)
        harness = '''<script>window.addEventListener('load',()=>setTimeout(()=>{
          const result=document.createElement('pre');result.id='pilot-check';
          const assert=(condition,message)=>{if(!condition)throw Error(message);};
          try { ASSERTIONS result.textContent='PASS'; }
          catch(error){result.textContent='FAIL '+error.message;}
          document.body.appendChild(result);
        },100));</script>'''.replace('ASSERTIONS', assertions)
        source = source.replace('</body>', harness + '</body>')
        with tempfile.TemporaryDirectory(prefix='pilot-readability-') as temp:
            page = Path(temp, 'page.html');page.write_text(source)
            if screenshot:
                # CDP sets the actual content viewport, unlike Chrome's outer window size.
                chrome = subprocess.Popen([CHROME, '--headless', '--disable-gpu', '--no-first-run',
                    '--no-default-browser-check', '--allow-file-access-from-files',
                    '--disable-background-networking', '--remote-debugging-port=0',
                    '--user-data-dir='+str(Path(temp,'profile')), 'about:blank'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    active=Path(temp,'profile/DevToolsActivePort')
                    for _ in range(100):
                        if active.exists():break
                        time.sleep(.05)
                    port=active.read_text().splitlines()[0]
                    with urlopen(Request(f'http://127.0.0.1:{port}/json/new?about:blank',method='PUT')) as response:
                        target=json.load(response)
                    async def check():
                        async with websockets.connect(target['webSocketDebuggerUrl'],max_size=20_000_000) as ws:
                            sequence=0
                            async def command(method,params=None):
                                nonlocal sequence
                                sequence+=1
                                await ws.send(json.dumps(dict(id=sequence,method=method,params=params or {})))
                                while True:
                                    reply=json.loads(await ws.recv())
                                    if reply.get('id')==sequence:break
                                self.assertNotIn('error',reply)
                                return reply.get('result',{})
                            await command('Page.enable')
                            await command('Page.bringToFront')
                            await command('Emulation.setDeviceMetricsOverride',dict(width=width,height=height,deviceScaleFactor=1,mobile=False))
                            await command('Page.navigate',dict(url=page.as_uri()))
                            await command('Emulation.setVirtualTimePolicy',dict(policy='pauseIfNetworkFetchesPending',budget=2000))
                            for _ in range(150):
                                result=await command('Runtime.evaluate',dict(expression="document.getElementById('pilot-check')?.textContent",returnByValue=True))
                                value=result.get('result',{}).get('value')
                                if value:break
                                await asyncio.sleep(.05)
                            if value != 'PASS':
                                diagnostic=await command('Runtime.evaluate',dict(expression='document.documentElement.outerHTML',returnByValue=True))
                                Path(str(screenshot)+'.html').write_text(str(diagnostic))
                            self.assertEqual(value,'PASS')
                            await command('Page.bringToFront')
                            await command('Emulation.setVirtualTimePolicy',dict(policy='advance',budget=500))
                            await asyncio.sleep(.2)
                            capture=await command('Page.captureScreenshot',dict(format='png',captureBeyondViewport=False))
                            Path(screenshot).write_bytes(base64.b64decode(capture['data']))
                            self.assertEqual(value,'PASS')
                    asyncio.run(check())
                finally:
                    chrome.terminate();chrome.wait(timeout=10)
                return
            result = subprocess.run([
                CHROME, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
                '--disable-background-networking', '--host-resolver-rules=MAP * ~NOTFOUND',
                '--allow-file-access-from-files', '--window-size='+str(width)+','+str(height),
                *(['--screenshot='+str(screenshot)] if screenshot else []),
                '--user-data-dir='+str(Path(temp,'profile')), '--dump-dom', '--virtual-time-budget=2000',
                page.as_uri()], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr[-1200:])
            found = re.search(r'<pre id="pilot-check">(.*?)</pre>', result.stdout, re.S)
            self.assertIsNotNone(found, result.stdout[-1500:])
            self.assertEqual(html_module.unescape(found[1]), 'PASS')

    @unittest.skipUnless(CHROME, 'Headless Chrome unavailable.')
    def test_reports_readable_desktop_responsive_narrow_and_deliberate_choices(self):
        for app, helpers, branch in environments():
            if app.__name__ not in ('fixed','ambiguity','messages','policy') or app.__name__=='policy' and branch!='M':
                continue
            session = helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            player = helpers.subsession(session).get_players()[0]
            response = self.open_page(player, app.Reports)
            for width in (1366, 600):
                with self.subTest(app=app.__name__, width=width):
                    self.browser(response.text, '''
                        assert(innerWidth===WIDTH,'tested viewport');
                        assert(document.documentElement.scrollWidth<=innerWidth,'no horizontal overflow');
                        const labels=[...document.querySelectorAll('.report-question-label')];
                        assert(labels.length===2,'both original questions');
                        assert(document.body.innerText.includes('Prima della prima decisione'),'introduction retained');
                        labels.forEach(label=>{
                            const style=getComputedStyle(label);
                            assert(parseFloat(style.fontSize)>=19,'larger question font');
                            if(WIDTH>=1000){const range=document.createRange();range.selectNodeContents(label);
                                assert(range.getBoundingClientRect().height<=parseFloat(style.lineHeight)*1.1,'one-line question');}
                        });
                        const sliders=[...document.querySelectorAll('.report-slider')];
                        const button=document.getElementById('reports-continue');
                        assert(button.disabled,'initial Continue disabled');
                        sliders.forEach(slider=>{
                            const rect=slider.getBoundingClientRect();
                            assert(rect.width<=840.1 && (WIDTH<1000 || rect.width>=700),'wide responsive slider');
                            assert(slider.hasAttribute('data-untouched'),'initial thumb unselected');
                            assert(slider.min==='0' && slider.max==='100' && slider.step==='1','unchanged integer range');
                            const ends=slider.nextElementSibling;
                            assert(ends.children[0].textContent==='0' && ends.children[1].textContent==='100','endpoint labels');
                            assert(Math.abs(ends.getBoundingClientRect().left-rect.left)<1,'left endpoint alignment');
                            assert(Math.abs(ends.getBoundingClientRect().right-rect.right)<1,'right endpoint alignment');
                        });
                        assert(parseFloat(getComputedStyle(document.querySelector('.report-selected-value')).fontSize)>=17,'larger selected value');
                        sliders[0].click();assert(document.getElementById('report-own-value').value==='0' && button.disabled,'deliberate zero alone');
                        sliders[1].value='100';sliders[1].dispatchEvent(new Event('input'));
                        assert(document.getElementById('report-group-selected').textContent==='100' && !button.disabled,'both reports answered');
                        let submitted=false;document.getElementById('form').addEventListener('submit',e=>{submitted=true;e.preventDefault();});
                        button.click();assert(submitted,'Continue works');
                    '''.replace('WIDTH', str(width)), width)
            db.rollback()

    @unittest.skipUnless(CHROME, 'Headless Chrome unavailable.')
    def test_footer_hidden_on_all_representative_participant_pages_not_admin(self):
        import fixed
        session = test_fixed.make_session();test_fixed.ready(session)
        player = test_fixed.subsession(session).get_players()[0]
        test_fixed.reports(player.group)
        pages = [(player, fixed.ExperimentSplash),(player, fixed.SectionComprehension),
                 (player, fixed.Reports),(player, fixed.Decision)]
        for p, page in pages:
            response = self.open_page(p,page)
            self.browser(response.text, "assert(!document.body.innerText.includes('Fornito da'),'no visible branding');document.querySelectorAll('.powered-by-otree').forEach(el=>assert(getComputedStyle(el).display==='none','footer only hidden'));")
        test_fixed.run_period(player.group)
        self.browser(self.open_page(player,fixed.Result).text, "assert(getComputedStyle(document.querySelector('.powered-by-otree')).display==='none','Result footer hidden');")
        complete = make_production_session()
        sp = survey.Player.objects_filter(session=complete).first()
        self.browser(self.open_page(sp,survey.SurveyWelcome).text, "assert(getComputedStyle(document.querySelector('.powered-by-otree')).display==='none','survey footer hidden');")
        pp = lab_payment.Player.objects_filter(session=complete).first()
        with patch.object(lab_payment.Payment,'vars_for_template',staticmethod(lambda p: dict(selected_block=1,selected_wallet='0',fixed_fee='€8.00',variable_eur='0',total_eur='€8.00',bucket_eur='€0.00'))):
            response = self.open_page(pp,lab_payment.Payment)
        self.browser(response.text, "assert(getComputedStyle(document.querySelector('.powered-by-otree')).display==='none','payment footer hidden');assert(!document.getElementById('earnings-summary').hidden && document.getElementById('bless-closing-splash').hidden,'earnings default unchanged');")
        admin = self.client.get('/sessions')
        self.assertEqual(admin.status_code,200)
        self.assertNotIn('.powered-by-otree { display: none !important; }',admin.text)

    def test_native_timeouts_early_continue_and_economic_invariance(self):
        for app, helpers, branch in environments():
            self.assertEqual(app.Decision.get_timeout_seconds(SimpleNamespace(period=1)),40)
            self.assertEqual(app.Decision.get_timeout_seconds(SimpleNamespace(period=2)),30)
            for period in range(1,11):
                self.assertEqual(app.Result.get_timeout_seconds(SimpleNamespace(period=period)),60 if period in (5,10) else 20)
            if app.__name__ not in ('fixed','ambiguity','messages','policy') or app.__name__=='policy' and branch!='M':
                continue
            session = helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            group = helpers.subsession(session).get_groups()[0]
            helpers.reports(group)
            player = group.get_players()[0]
            response = self.open_page(player,app.Decision)
            self.assertIn('var remainingTimeoutSeconds = 40',response.text)
            pp = player.participant;pp._timeout_expiration_time=time.time()-1;pp._timeout_page_index=pp._index_in_pages;db.commit()
            result = self.client.post(str(response.url),data={'retirement':'','timeout_happened':'1'},allow_redirects=True)
            db.expire_all();self.assertEqual(result.status_code,200)
            self.assertEqual((player.retirement,player.locked_retirement),(0,0))
            self.assertFalse(group.settlement_complete)
            for period in range(1,11):
                group = helpers.subsession(session,period).get_groups()[0]
                helpers.run_period(group)
                if period not in (1,5,10):continue
                duration=60 if period in (5,10) else 20
                for timeout,p in zip((False,True),group.get_players()[:2]):
                    response=self.open_page(p,app.Result)
                    self.assertIn('var remainingTimeoutSeconds = '+str(duration),response.text)
                    self.assertIn('>Continua</button>',response.text)
                    before=tuple(getattr(p,f) for f in ['wallet_after','voluntary_cost','main_fine','follow_up_fine','forced_retirement_cost'])
                    variables=copy.deepcopy(p.participant.vars)
                    if timeout:
                        pp=p.participant;pp._timeout_expiration_time=time.time()-1;pp._timeout_page_index=pp._index_in_pages;db.commit()
                    result=self.client.post(str(response.url),data={'timeout_happened':'1'} if timeout else {},allow_redirects=True)
                    db.expire_all();self.assertEqual(result.status_code,200)
                    self.assertIn(wait_page_http_header,result.headers)
                    self.assertEqual(before,tuple(getattr(p,f) for f in ['wallet_after','voluntary_cost','main_fine','follow_up_fine','forced_retirement_cost']))
                    self.assertEqual(variables,p.participant.vars)
            db.rollback()

    @unittest.skipUnless(CHROME, 'Headless Chrome unavailable.')
    def test_result_countdown_finish_submits_native_timeout_flag(self):
        import fixed
        session=test_fixed.make_session();test_fixed.ready(session)
        for period in range(1,6):
            group=test_fixed.subsession(session,period).get_groups()[0];test_fixed.run_period(group)
        response=self.open_page(group.get_players()[0],fixed.Result)
        self.browser(response.text, '''
            assert(document.querySelector('button[type=submit]').textContent==='Continua','early Continue retained');
            let submissions=0;$('#form').on('submit',event=>{submissions++;event.preventDefault();});
            $('.otree-timer__time-left').trigger('finish.countdown');
            assert(submissions===1,'native countdown automatically submits');
            assert(document.querySelector('input[name=timeout_happened]').value==='1','native timeout flag');
        ''')
