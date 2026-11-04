"""Offline receipt DOM check; native reloads are covered by PaymentHTTPTests."""
import copy
from pathlib import Path
import unittest
from otree.database import db
from test_fixed_browser import CHROME
import test_messages_browser as harness
from test_lab_payment import make_session, finish_all, payment_player, render_payment
from otree.templating.template import Template


@unittest.skipUnless(CHROME, 'Headless Chrome unavailable.')
class PaymentBrowserTests(unittest.TestCase):
    def tearDown(self): db.rollback()

    def test_selected_block_uses_section_and_local_block_labels(self):
        source = Path('lab_payment/Payment.html').read_text()
        for number, label in enumerate(('1.1', '1.2', '1.3', '2.1', '2.2', '2.3', '3.1', '3.2', '3.3'), 1):
            rendered = Template(source).render(dict(selected_block=number, selected_wallet='250',
                                                     fixed_fee='€8.00', variable_eur='2.50',
                                                     total_eur='€10.50', bucket_eur='€0.00'))
            self.assertIn(f'id="selected-block">{label}</dd>', rendered)

    def test_payment_equation_renders_positive_zero_and_negative_components(self):
        source = Path('lab_payment/Payment.html').read_text()
        for variable, operator, magnitude, total in (
            ('2.50', '+', '2.50', '€10.50'),
            ('0', '+', '0', '€8.00'),
            ('-2.50', '-', '2.50', '€5.50'),
        ):
            rendered = Template(source).render(dict(selected_block=1, selected_wallet='250',
                                                     fixed_fee='€8.00', variable_eur=variable,
                                                     total_eur=total, bucket_eur='€0.00'))
            self.assertIn(f'<span class="payment-calculation">€8.00 {operator} €{magnitude} + €0.00 = </span>', rendered)
            self.assertIn(f'id="total-payment">{total}</strong>', rendered)
            self.assertIn('id="payment-heading">Pagamento</h2>', rendered)
            self.assertNotIn('Il blocco selezionato esternamente viene ora rivelato', rendered)
            self.assertNotIn('Gli importi esattamente a metà centesimo', rendered)

    def test_negative_wallet_final_receipt_offline(self):
        session = make_session(paid_block=1); finish_all(session)
        p = payment_player(session)
        fragment = render_payment(p)
        self.assertEqual(fragment, render_payment(p))
        before = copy.deepcopy(p.participant.vars)
        fields = {name: getattr(p, name) for name in p.RECORD_FIELDS}
        payoff = p.participant.payoff
        # Match oTree's surrounding title element in this offline fragment.
        fragment = fragment.replace("Il tuo pagamento per lo studio di oggi",
                                    '<h2 class="otree-title" id="_otree-title">Il tuo pagamento per lo studio di oggi</h2>', 1)
        fragment = fragment.replace('/static/', Path('_static').resolve().as_uri() + '/')
        harness.MessagesBrowserTests.browser(self, fragment, """
            assert(document.getElementById('selected-block').textContent==='1.1','final block reveal in section notation');
            assert(document.getElementById('selected-wallet').textContent==='-300 punti','signed exact wallet');
            assert(document.getElementById('fixed-fee').textContent==='€8.00','fixed fee');
            assert(document.getElementById('variable-payment').textContent==='-€3','negative variable component');
            assert(document.getElementById('total-payment').textContent==='€5.00','formula total');
            assert(document.getElementById('payment-equation').textContent==='€8.00 - €3 + €0.00 = €5.00','negative component shown as subtraction');
            assert(getComputedStyle(document.getElementById('_otree-title')).textAlign==='center','centered earnings title');
            assert(getComputedStyle(document.querySelector('.payment-total')).textAlign==='center','prominent centered payment');
            assert(document.querySelector('.payment-thanks').textContent==="Grazie per aver partecipato allo studio di oggi!",'earnings thank-you message');
            assert(!document.getElementById('form').textContent.includes('Prolific'),'no online payment dependency');
            const summary=document.getElementById('earnings-summary');
            const splash=document.getElementById('bless-closing-splash');
            const title=document.getElementById('_otree-title');
            const button=document.getElementById('toggle-earnings-summary');
            const original=summary.innerHTML, url=location.href;
            assert(!summary.hidden && !title.hidden && splash.hidden,'summary and title initially visible');
            assert(getComputedStyle(summary).display!=='none' && getComputedStyle(splash).display==='none','actual initial visibility');
            assert(button.type==='button' && button.textContent==='Nascondi riepilogo pagamento','non-submit initial toggle');
            assert(document.querySelectorAll('button').length===1 && !document.querySelector('button[type=submit],.otree-btn-next'),'no Continue or submit button');
            assert(splash.querySelector('h2').textContent==="Grazie per aver partecipato allo studio di oggi!",'closing heading');
            assert(!document.body.innerText.includes('Attendi le indicazioni del ricercatore'),'old waiting instruction removed');
            const receipt=document.getElementById('payment-receipt');
            assert(receipt.querySelectorAll('ol li').length===4,'four receipt steps');
            const qr=receipt.querySelector('img');
            assert(qr.complete && qr.naturalWidth>0,'supplied QR loads');
            assert(!splash.querySelector('dl,[id=selected-block],[id=total-payment]'),'no economic summary in splash');
            let submissions=0;
            document.getElementById('form').addEventListener('submit',event=>{submissions++;event.preventDefault();});
            for(let i=0;i<3;i++) {
                button.click();
                assert(summary.hidden && title.hidden && !splash.hidden,'summary/title hidden and splash visible');
                assert(getComputedStyle(summary).display==='none' && getComputedStyle(splash).display!=='none','actual closing visibility');
                assert(button.textContent==='Mostra riepilogo pagamento' && button.getAttribute('aria-expanded')==='false','show-summary toggle');
                assert(summary.innerHTML===original,'hidden payment content unchanged');
                assert(getComputedStyle(receipt).display!=='none' && receipt.querySelectorAll('ol li').length===4,'receipt remains visible');
                button.click();
                assert(!summary.hidden && !title.hidden && splash.hidden,'summary/title restored');
                assert(button.textContent==='Nascondi riepilogo pagamento' && button.getAttribute('aria-expanded')==='true','hide-summary toggle restored');
                assert(summary.innerHTML===original,'exact original summary restored');
            }
            assert(submissions===0 && location.href===url,'no submission or navigation');
        """)
        self.assertEqual(p.participant.vars, before)
        self.assertEqual({name: getattr(p, name) for name in p.RECORD_FIELDS}, fields)
        self.assertEqual(p.participant.payoff, payoff)

    def test_native_payment_receipt_layout_and_privacy_at_three_viewports(self):
        import html as html_module
        import re
        import subprocess
        import tempfile
        import otree
        from starlette.testclient import TestClient
        from otree.asgi import app
        from otree.lookup import _get_session_lookups
        import lab_cash, lab_route, lab_payment
        session=make_session(paid_block=1)
        import bucket
        for row in bucket.Player.objects_filter(session=session):
            bucket.start(row,now=1000);bucket.receive(row,dict(action='sync'),now=1300)
        p=payment_player(session);pp=p.participant
        # A synthetic completed ledger isolates UI checks from a 90-period replay.
        pp.vars[lab_cash.WALLETS_KEY]={str(b):'330/1' for b in range(1,10)}
        lab_route.block_subsession(session,9,last=True).block_barrier_complete=True
        pp._index_in_pages=next(i for i,row in _get_session_lookups(session.code).items() if row.page_class is lab_payment.Payment)
        pp._current_app_name='lab_payment';pp._current_page_name='Payment';pp._round_number=1;pp.visited=True;db.commit()
        client=TestClient(app);response=client.get(pp._start_url(),allow_redirects=True);db.expire_all()
        self.assertEqual(response.status_code,200)
        before=copy.deepcopy(pp.vars);payoff=pp.payoff;record={n:getattr(p,n) for n in p.RECORD_FIELDS}
        self.assertEqual(client.get('/static/global/payment-receipt-qr.png').content,Path('_static/global/payment-receipt-qr.png').read_bytes())
        source=re.sub(r'<script id="websocket-redirect".*?</script>','',response.text,flags=re.S)
        def asset(m):
            target=Path('_static',m[2].split('?')[0])
            if not target.is_file():target=Path(otree.__file__).parent/'static'/m[2].split('?')[0]
            self.assertTrue(target.is_file(),str(target))
            return m[1]+target.resolve().as_uri()
        source=re.sub(r'([\"\'])/static/([^\"\']+)',asset,source)
        artifact=Path(tempfile.mkdtemp(prefix='payment-receipt-ui-'))
        for width,height in ((1366,768),(1366,900),(650,900)):
            for hidden in (False,True):
                assertions="""
                    document.querySelectorAll('.debug-info').forEach(el=>el.parentElement.remove());
                    document.querySelectorAll('body > br').forEach(el=>el.remove());
                    const summary=document.getElementById('earnings-summary'),receipt=document.getElementById('payment-receipt'),button=document.getElementById('toggle-earnings-summary');
                    assert(document.getElementById('receipt-heading').textContent==='Per ricevere il pagamento','shared receipt heading');
                    const original=summary.innerHTML,url=location.href;
                    assert(!summary.hidden,'initial earnings visible');
                    assert(document.getElementById('payment-heading').textContent==='Pagamento','exact payment heading');
                    assert(document.getElementById('total-payment').textContent==='€11.30','unchanged exact payment');
                    assert(document.getElementById('variable-payment').textContent==='€3.30','unchanged variable');
                    const paymentLabels=[...document.querySelectorAll('.payment-components > div:last-child dt')];
                    assert(paymentLabels.map(el=>el.textContent.trim().split(':')[0]).join('|')==='Componente fissa|Componente variabile|Task individuale','requested component order');
                    const formulaNote=paymentLabels[1].querySelector('span');
                    assert(formulaNote?.textContent==='(punti nel portafoglio × 0.01)' && Number(getComputedStyle(formulaNote).fontWeight)<=400,'variable explanation has normal weight');
                    assert(receipt.querySelectorAll('li').length===4 && document.querySelectorAll('#payment-receipt').length===1,'one shared four-step receipt');
                    const expected=['Scansiona il QR code.','Inserisci il codice alfanumerico che ti è stato consegnato.','Compila la ricevuta.',"Dopo aver compilato la ricevuta puoi lasciare il laboratorio. Non è necessario attendere l'e-mail di conferma."];
                    assert([...receipt.querySelectorAll('li')].every((li,i)=>li.textContent===expected[i]),'literal receipt instructions');
                    const qr=receipt.querySelector('img'),rect=qr.getBoundingClientRect();
                    assert(qr.complete && qr.naturalWidth>0 && rect.width>=160 && rect.width<=190,'exact supplied QR at compact size');
                    assert(Math.abs(rect.width-rect.height)<1,'QR aspect ratio');
                    const columns=[...document.querySelectorAll('.payment-components > div')].map(el=>el.getBoundingClientRect());
                    if(innerWidth>=768){
                        assert(Math.abs(columns[0].top-columns[1].top)<1 && columns[1].left>columns[0].left,'desktop two columns');
                        const labels=[...document.querySelectorAll('.payment-components dt')];
                        assert(Math.abs(labels[0].getBoundingClientRect().top-labels[2].getBoundingClientRect().top)<1,'first row aligned');
                        assert(Math.abs(labels[1].getBoundingClientRect().top-labels[3].getBoundingClientRect().top)<1,'second row aligned');
                    }else assert(columns[1].top>columns[0].top,'narrow summary stacks');
                    let submits=0;document.getElementById('form').addEventListener('submit',e=>{submits++;e.preventDefault();});
                    for(let i=0;i<3;i++){
                        button.click();
                        assert(summary.hidden && !document.getElementById('bless-closing-splash').hidden,'hidden earnings state');
                        assert(!document.body.innerText.includes('€') && !document.body.innerText.includes('330') && !document.body.innerText.includes('1.1'),'all sensitive values invisible');
                        assert(receipt.getBoundingClientRect().height>0 && qr.getBoundingClientRect().width===180,'receipt still visible');
                        assert(button.textContent==='Mostra riepilogo pagamento','show label');
                        button.click();assert(!summary.hidden && summary.innerHTML===original,'exact original summary restored');
                    }
                    assert(submits===0 && location.href===url,'no submission or navigation');
                    assert(!document.body.innerText.includes('Attendi le indicazioni del ricercatore'),'waiting message removed');
                    assert(!document.body.innerText.includes('Fornito da'),'existing hidden footer preserved');
                    if(HIDDEN)button.click();
                    assert(document.documentElement.scrollWidth<=innerWidth,'no horizontal overflow');
                """.replace('HIDDEN',str(hidden).lower())
                script="<script>window.addEventListener('load',()=>setTimeout(()=>{const assert=(x,m)=>{if(!x)throw Error(m)};const out=document.createElement('pre');out.id='receipt-result';out.hidden=true;try{"+assertions+"out.textContent='PASS';}catch(e){out.textContent='FAIL '+e.message;}document.body.append(out);},100));</script>"
                fixture=artifact/f'{width}x{height}-{hidden}.html';fixture.write_text(source.replace('</body>',script+'</body>'))
                result=subprocess.run([CHROME,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--allow-file-access-from-files',f'--user-data-dir={artifact}/profile-{width}-{height}-{hidden}',f'--window-size={width},{height}','--dump-dom','--virtual-time-budget=1200',f'--screenshot={artifact}/{width}x{height}-{hidden}.png',fixture.as_uri()],capture_output=True,text=True,timeout=40)
                self.assertEqual(result.returncode,0,result.stderr[-500:])
                found=re.search(r'<pre id="receipt-result"[^>]*>(.*?)</pre>',result.stdout,re.S)
                self.assertIsNotNone(found,result.stdout[-1000:]);self.assertEqual(html_module.unescape(found[1]),'PASS')
        db.expire_all();self.assertEqual(pp.vars,before);self.assertEqual(pp.payoff,payoff)
        self.assertEqual({n:getattr(p,n) for n in p.RECORD_FIELDS},record)
        print('Payment UI screenshots:',artifact)
