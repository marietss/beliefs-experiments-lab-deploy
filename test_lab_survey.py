"""Focused survey routes, real HTTP validation, storage and standard export."""
import copy
import re
from pathlib import Path
import unittest
from unittest.mock import patch

import test_fixed
from starlette.testclient import TestClient
from starlette.datastructures import FormData
from otree.asgi import app
from otree.database import db
from otree.export import get_rows_for_wide_csv
from otree.forms.forms import get_form
from otree.lookup import _get_session_lookups
from otree.session import SESSION_CONFIGS_DICT
import lab_cash
import lab_payment
import lab_production
import lab_route
import survey
from test_lab_production import make_production_session
from test_fixed_browser import CHROME
import test_messages_browser as browser_harness


ANSWERS = dict(
    experiment_liking=0, experiment_clarity=10,
    experiment_perceived_purpose="Lo studio riguarda le decisioni di dismissione e il comportamento delle imprese in un gruppo.",
    strategy_description="Ho ripartito le dismissioni tra i periodi per ridurre il costo quadratico.",
    strategy_change="Ho mantenuto lo stesso approccio durante tutte le sezioni dello studio.",
    information_used="Ho utilizzato la media del gruppo e le informazioni disponibili sul grafico.",
    gender='Preferisco non rispondere', age=24, city_birth='Bologna', current_city='Bologna',
    university_affiliation='Economia', university_status='Laurea magistrale', university_status_other='',
    unibo_time='Preferisco non rispondere', previous_experiment_experience='Non ricordo / Preferisco non rispondere',
    falk_future=0, falk_risk=5, falk_giving=10,
    falk_favour=10, falk_revenge=0, falk_intentions=5,
)


class SurveyTests(unittest.TestCase):
    def test_all_four_open_answers_require_twenty_non_whitespace_characters(self):
        player = self.start(make_production_session())
        self.post()
        for field in ('experiment_perceived_purpose', 'strategy_description', 'strategy_change', 'information_used'):
            for bad in ('', ' \t\n'*30, 'a '*19):
                self.post({**self.answer(survey.ExperimentFeedback), field:bad})
                self.assertIn('ExperimentFeedback/', str(self.response.url))
                self.assertIn('Per favore, descrivi la tua risposta con qualche parola in più.', self.response.text)
        self.post({**self.answer(survey.ExperimentFeedback), 'experiment_clarity':0})
        self.assertIn('Demographics/', str(self.response.url))

    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        db.rollback()

    def start(self, session):
        player = survey.Player.objects_filter(session=session).first()
        participant = player.participant
        index = next(i for i, row in _get_session_lookups(session.code).items()
                     if row.app_name == 'survey' and row.page_class is survey.SurveyWelcome)
        participant._index_in_pages = index
        participant._current_app_name = 'survey'
        participant._current_page_name = 'SurveyWelcome'
        participant._round_number = 1
        participant.visited = True
        db.commit()
        self.response = self.client.get(participant._start_url(), allow_redirects=True)
        self.assertEqual(self.response.status_code, 200)
        return player

    def post(self, values=None):
        self.response = self.client.post(str(self.response.url), data=values or {}, allow_redirects=True)
        db.expire_all()
        self.assertEqual(self.response.status_code, 200)
        return self.response

    def answer(self, page):
        return {name: ANSWERS[name] for name in page.form_fields}

    def test_all_six_production_and_dev_routes_and_single_round(self):
        self.assertEqual(survey.C.NUM_ROUNDS, 1)
        from otree.api import WaitPage
        self.assertFalse(any(issubclass(page, WaitPage) for page in survey.page_sequence))
        self.assertEqual([p.__name__ for p in survey.page_sequence], [
            'SurveyWelcome', 'ExperimentFeedback', 'Demographics', 'UniversityBackground', 'Preferences1', 'Preferences2'])
        for branch in 'EAM':
            for size in (18, 24):
                with self.subTest(branch=branch, size=size):
                    config = next(c for c in lab_production.templates() if c['name'] == f'lab_{branch}_{size}')
                    expected = ['fixed', lab_route.BRANCH_APPS[branch], 'policy', 'bucket', 'survey', 'lab_payment']
                    self.assertEqual(config['app_sequence'], expected)
                    self.assertEqual(SESSION_CONFIGS_DICT[f'dev_lab_full_{branch}_{size}']['app_sequence'], expected)
                    session = make_production_session(branch, size)
                    self.assertEqual(survey.Player.objects_filter(session=session).count(), size)
                    self.assertTrue(lab_route.validate_route(session.config, 'survey'))
                    db.rollback()

    def test_http_required_inputs_bounds_minimum_lengths_and_preserved_choices(self):
        player = self.start(make_production_session())
        self.assertIn('Questionario finale', self.response.text)
        self.assertIn('Nelle domande a risposta aperta, scrivi una breve risposta con parole tue.', self.response.text)
        payment_index = next(i for i,row in _get_session_lookups(player.session.code).items()
                             if row.app_name == 'lab_payment' and row.page_class is lab_payment.Payment)
        future = str(self.response.url).replace('/survey/SurveyWelcome/', '/lab_payment/Payment/')
        future = future.rsplit('/',1)[0]+'/'+str(payment_index)
        with patch.object(lab_payment.Payment, 'vars_for_template', side_effect=AssertionError('Premature payment')):
            response = self.client.get(future, allow_redirects=True)
        self.assertIn('SurveyWelcome/',str(response.url))
        self.post()
        self.assertIn('ExperimentFeedback/', str(self.response.url))
        self.assertIn("Secondo te, qual era l'oggetto principale delle prime tre sezioni di questo studio? Descrivilo brevemente con parole tue.", self.response.text)
        self.assertEqual(self.response.text.count('data-untouched'), 2)
        self.assertIn('id="id_experiment_liking" name="experiment_liking" value=""', self.response.text)
        self.post({})
        self.assertIn('ExperimentFeedback/', str(self.response.url))
        self.assertIn("Per favore, descrivi la tua risposta con qualche parola in più.", self.response.text)
        self.assertIn("Per favore, descrivi la tua risposta con qualche parola in più.", self.response.text)
        self.assertNotIn('almeno 20 caratteri', self.response.text)
        for bad in (' \t\n'*60, 'x '*19):
            response = self.post({**self.answer(survey.ExperimentFeedback), 'experiment_perceived_purpose':bad})
            self.assertIn('ExperimentFeedback/', str(response.url))
            self.assertIn("Per favore, descrivi la tua risposta con qualche parola in più.", response.text)
            self.assertIn('name="experiment_liking" value="0"', response.text)
            self.assertIn('name="experiment_clarity" value="10"', response.text)
            self.assertNotIn('data-untouched', response.text)
        for bad in (' \t\n'*60, 'a '*19):
            self.post({**self.answer(survey.ExperimentFeedback), 'strategy_description':bad})
            self.assertIn("Per favore, descrivi la tua risposta con qualche parola in più.", self.response.text)
        self.post({**self.answer(survey.ExperimentFeedback), 'experiment_liking':11})
        self.assertIn('ExperimentFeedback/', str(self.response.url))
        self.post({**self.answer(survey.ExperimentFeedback), 'experiment_liking':-1})
        self.assertIn('ExperimentFeedback/', str(self.response.url))
        # Boundary lengths count only non-whitespace characters.
        feedback = {**self.answer(survey.ExperimentFeedback),
                    'experiment_perceived_purpose':'a '*20, 'strategy_description':'b '*20}
        self.post(feedback)
        self.assertIn('Demographics/', str(self.response.url))
        self.assertEqual(player.experiment_liking, 0)
        self.assertEqual(player.experiment_clarity, 10)
        for bad in ({}, {**self.answer(survey.Demographics), 'age':17},
                    {**self.answer(survey.Demographics), 'age':101},
                    {**self.answer(survey.Demographics), 'city_birth':'   '},
                    {**self.answer(survey.Demographics), 'current_city':'   '}):
            self.post(bad)
            self.assertIn('Demographics/', str(self.response.url))
        for option in ('Uomo', 'Donna', 'Altro', 'Preferisco non rispondere'):
            self.assertIn(option, self.response.text)
        self.post(self.answer(survey.Demographics))
        self.assertIn('UniversityBackground/', str(self.response.url))
        self.assertIn('Prima di oggi, quante volte avevi già partecipato ad uno studio nel laboratorio BLESS o online?', self.response.text)
        self.post({**self.answer(survey.UniversityBackground), 'university_affiliation':'   '})
        self.assertIn('UniversityBackground/', str(self.response.url))
        self.post(self.answer(survey.UniversityBackground))
        for page in (survey.Preferences1, survey.Preferences2):
            self.assertIn(page.__name__+'/', str(self.response.url))
            self.assertEqual(self.response.text.count('data-untouched'), 3)
            self.assertEqual(self.response.text.count('class="survey-ticks"'), 3)
            self.assertNotIn('WP134', self.response.text)
            data = self.answer(page)
            self.post({name:value for name,value in data.items() if name != page.form_fields[-1]})
            self.assertIn(page.__name__+'/', str(self.response.url))
            if page is survey.Preferences1:
                self.post(data)
        # A successful final submission reaches the terminal receipt directly;
        # this flow-only case has no fabricated experimental ledger.
        with patch.object(lab_payment.Payment, 'vars_for_template', staticmethod(lambda p: dict(
                selected_block=1, selected_wallet='0', fixed_fee='€8.00', variable_eur='0', total_eur='€8.00',bucket_eur='€0.00'))):
            self.post(self.answer(survey.Preferences2))
        self.assertIn('/lab_payment/Payment/', str(self.response.url))
        self.assertEqual(player.falk_future, 0)
        self.assertEqual(player.falk_giving, 10)

    def test_survey_answers_export_and_real_payment_are_independent(self):
        from test_lab_payment import make_session, finish_all, payment_player
        session = make_session('M', paid_block=7)
        finish_all(session)
        player = self.start(session)
        ledger = copy.deepcopy(player.participant.vars)
        self.post()
        for page in survey.page_sequence[1:]:
            self.post(self.answer(page))
        self.assertIn('/lab_payment/Payment/', str(self.response.url))
        receipt_player = payment_player(session)
        record = lab_cash.calculate_payment(ledger[lab_cash.WALLETS_KEY], session.config['paid_block'])
        self.assertIn('id="total-payment">'+lab_cash.cash_display(record['final_eur_cents']), self.response.text)
        self.assertEqual(player.participant.vars[lab_cash.WALLETS_KEY], ledger[lab_cash.WALLETS_KEY])
        self.assertTrue(receipt_player.finalized)
        for name,value in ANSWERS.items():
            self.assertEqual(getattr(player,name),value,name)
        rows = get_rows_for_wide_csv(session.code)
        record_row = next(row for row in rows[1:] if row[rows[0].index('participant.code')] == player.participant.code)
        for name,value in ANSWERS.items():
            column = rows[0].index('survey.1.player.'+name)
            self.assertEqual(record_row[column],value,name)
        # Existing normalized datasets keep their schema; only their route
        # acceptance guard learns about the intervening survey app.
        import lab_export
        bundle = lab_export.export_session(session)
        self.assertEqual(set(bundle),set(lab_export.HEADERS))
        for table, records in bundle.items():
            for row in records:
                self.assertEqual(set(row),set(lab_export.HEADERS[table]))

    def test_city_fields_and_optional_other_status_persist_and_export(self):
        for status, explanation, expected in (('Altro', 'Professionista', 'Professionista'),
                                               ('Laurea magistrale', 'Testo non pertinente', '')):
            player = self.start(make_production_session())
            self.post()
            self.post(self.answer(survey.ExperimentFeedback))
            self.post(self.answer(survey.Demographics))
            self.assertIn('university-status-other', self.response.text)
            self.post({**self.answer(survey.UniversityBackground),
                       'university_status': status, 'university_status_other': explanation})
            self.assertIn('/Preferences1/', str(self.response.url))
            self.assertEqual(player.university_status_other, expected)
            self.assertEqual(player.city_birth, 'Bologna')
            self.assertEqual(player.current_city, 'Bologna')
            rows = get_rows_for_wide_csv(player.session.code)
            row = next(row for row in rows[1:] if row[rows[0].index('participant.code')] == player.participant.code)
            for name, value in (('city_birth', 'Bologna'), ('current_city', 'Bologna'),
                                ('university_status_other', expected)):
                self.assertEqual(row[rows[0].index('survey.1.player.' + name)], value)
            self.assertNotIn('survey.1.player.country_birth', rows[0])
            self.assertNotIn('survey.1.player.country_residence', rows[0])
            db.rollback()

    def test_server_forms_enforce_all_gps_fields_and_options(self):
        session = make_production_session()
        player = survey.Player.objects_filter(session=session).first()
        self.assertEqual([name for page in survey.page_sequence for name in page.form_fields],list(ANSWERS))
        for page in (survey.Preferences1, survey.Preferences2):
            for value in (0,10):
                form = get_form(player,page.form_fields,page,FormData({name:str(value) for name in page.form_fields}))
                self.assertTrue(form.validate(), form.errors)
            for missing in page.form_fields:
                values = {name:5 for name in page.form_fields if name != missing}
                form = get_form(player,page.form_fields,page,FormData({name:str(value) for name,value in values.items()}))
                self.assertFalse(form.validate())
                self.assertIn(missing,form.errors)
        for name in survey.Demographics.form_fields + survey.UniversityBackground.form_fields:
            self.assertTrue(getattr(survey.Player,name).form_props['label'])
        choices = {
            'gender':['Uomo','Donna','Altro','Preferisco non rispondere'],
            'university_status':['Laurea triennale','Laurea magistrale','Laurea magistrale a ciclo unico',
                                 'Master','Dottorato di ricerca','Personale docente o ricercatore',
                                 'Personale tecnico-amministrativo','Altro','Preferisco non rispondere'],
            'unibo_time':['Questo è il mio primo anno','Questo è il mio secondo anno','Questo è il mio terzo anno',
                          'Questo è il mio quarto anno','Da più di quattro anni','Preferisco non rispondere'],
            'previous_experiment_experience':['Mai','1 volta','2–5 volte','Più di 5 volte','Non ricordo / Preferisco non rispondere'],
        }
        for page in (survey.Demographics,survey.UniversityBackground):
            form = get_form(player,page.form_fields,page,None)
            for name in page.form_fields:
                if name in choices:
                    self.assertEqual([label for value,label in form[name].choices],choices[name])


@unittest.skipUnless(CHROME, 'Headless Chrome unavailable.')
class SurveyBrowserTests(unittest.TestCase):
    setUp = SurveyTests.setUp
    tearDown = SurveyTests.tearDown
    start = SurveyTests.start
    post = SurveyTests.post
    answer = SurveyTests.answer
    browser = browser_harness.MessagesBrowserTests.browser

    def fragment(self):
        import otree
        html = self.response.text
        main = re.search(r'<main class="survey-page"[^>]*>.*?</main>', html, re.S).group(0)
        styles = ''.join(re.findall(r'<link rel="stylesheet"[^>]*>', html))
        fragment = styles + main + '<script src="/static/survey/survey.js?v=2"></script>'
        def asset(match):
            relative = match[2].split('?')[0]
            path = Path('_static', relative)
            if not path.is_file():
                path = Path(otree.__file__).parent / 'static' / relative
            self.assertTrue(path.is_file(),str(path))
            return match[1]+path.resolve().as_uri()
        return re.sub(r'([\"\'])/static/([^\"\']+)', asset, fragment)

    def test_feedback_and_both_gps_pages_have_deliberate_integer_sliders(self):
        player = self.start(make_production_session())
        lookups = _get_session_lookups(player.session.code)
        for page in (survey.ExperimentFeedback, survey.Preferences1, survey.Preferences2):
            pp = player.participant
            pp._index_in_pages = next(i for i,row in lookups.items() if row.page_class is page)
            pp._current_page_name = page.__name__
            db.commit()
            self.response = self.client.get(pp._start_url(),allow_redirects=True)
            self.assertEqual(self.response.status_code,200)
            self.browser(self.fragment(), """
                const scales=Array.from(document.querySelectorAll('[data-survey-scale]'));
                const button=document.getElementById('survey-continue');
                assert(scales.length===COUNT,'exact requested slider count');
                assert(button.disabled,'Continue initially disabled');
                const followup=document.getElementById('clarity-improvement');
                if(followup) assert(followup.hidden,'clarity follow-up hidden before selection');
                scales.forEach(scale=>{
                    const slider=scale.querySelector('input[type=range]');
                    assert(slider.min==='0' && slider.max==='10' && slider.step==='1','integer 0–10 range');
                    assert(slider.hasAttribute('data-untouched'),'initial thumb hidden');
                    assert(scale.querySelector('input[type=hidden]').value==='','no implicit response');
                    assert(scale.querySelector('.survey-selected strong').textContent==='—','no visible default number');
                    const ticks=[...scale.querySelectorAll('.survey-ticks span')].map(s=>s.textContent);
                    assert(JSON.stringify(ticks)===JSON.stringify(Array.from({length:11},(_,i)=>String(i))),'all ticks 0 through 10');
                });
                const form=document.getElementById('form');
                const missing=new Event('submit',{bubbles:true,cancelable:true});
                form.dispatchEvent(missing);assert(missing.defaultPrevented,'untouched submission prevented');
                scales.forEach((scale,index)=>{
                    const slider=scale.querySelector('input[type=range]');
                    const value=index===0?'0':'10';
                    slider.value=value;
                    slider.dispatchEvent(new Event(index===0?'click':'input'));
                    assert(!slider.hasAttribute('data-untouched'),'selected thumb visible');
                    assert(scale.querySelector('input[type=hidden]').value===value,'deliberate zero/ten retained');
                    assert(scale.querySelector('.survey-selected strong').textContent===value,'selected number updates');
                    assert(button.disabled===(index<scales.length-1),'all sliders required');
                });
                const complete=new Event('submit',{bubbles:true,cancelable:true});
                form.dispatchEvent(complete);assert(!complete.defaultPrevented,'fully answered page can submit');
                if(followup) {
                    const clarity=document.getElementById('slider-experiment_clarity');
                    const response=followup.querySelector('textarea');
                    for(const value of [4,5,0,10]) {
                        clarity.value=String(value);clarity.dispatchEvent(new Event('input'));
                        assert(followup.hidden===(value>=5),'follow-up shown only below five');
                        assert(response.required===(value<5),'only low clarity requires response');
                    }
                }
            """.replace('COUNT',str(2 if page is survey.ExperimentFeedback else 3)))
        db.rollback();db.expire_all()
        pp = player.participant
        pp._index_in_pages = next(i for i,row in lookups.items() if row.page_class is survey.ExperimentFeedback)
        pp._current_page_name = 'ExperimentFeedback'
        db.commit()
        self.response = self.client.get(pp._start_url(),allow_redirects=True)
        self.post({**self.answer(survey.ExperimentFeedback),'experiment_perceived_purpose':'troppo breve'})
        self.browser(self.fragment(), """
            const scales=Array.from(document.querySelectorAll('[data-survey-scale]'));
            assert(document.body.innerText.includes("Secondo te, qual era l'oggetto principale delle prime tre sezioni di questo studio?"),'revised purpose question visible');
            assert(document.body.innerText.includes("Per favore, descrivi la tua risposta con qualche parola in più."),'short-answer feedback visible');
            assert(document.body.innerText.includes("Per favore, descrivi la tua risposta con qualche parola in più."),'exact purpose feedback visible');
            assert(!document.getElementById('survey-continue').disabled,'valid responses preserved on text error');
            assert(scales[0].querySelector('input[type=hidden]').value==='0','zero preserved');
            assert(scales[1].querySelector('input[type=hidden]').value==='10','ten preserved');
            assert(scales.every(s=>!s.querySelector('input[type=range]').hasAttribute('data-untouched')),'answered state restored');
        """)
        self.post({**self.answer(survey.ExperimentFeedback), 'strategy_description':'troppo breve'})
        self.browser(self.fragment(), """
            assert(document.body.innerText.includes("Per favore, descrivi la tua risposta con qualche parola in più."),'exact changes feedback visible');
        """)
        db.rollback();db.expire_all()
        pp = player.participant
        pp._index_in_pages = next(i for i,row in lookups.items() if row.page_class is survey.UniversityBackground)
        pp._current_page_name = 'UniversityBackground'
        db.commit()
        self.response = self.client.get(pp._start_url(),allow_redirects=True)
        self.browser(self.fragment(), """
            assert(document.body.innerText.includes('Prima di oggi, quante volte avevi già partecipato ad uno studio nel laboratorio BLESS o online?'),'exact previous-study label visible');
        """)
