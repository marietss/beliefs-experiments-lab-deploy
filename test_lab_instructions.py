"""Active lab instruction content, real models/forms, privacy and quiz process measures.

Run in a disposable project with OTREE_LAB_PAYMENTS=1 OTREE_IN_MEMORY=1.
Legacy online instruction assets are intentionally excluded from content scans.
"""
import copy
from fractions import Fraction
import json
from pathlib import Path
import re
import unittest

import test_fixed  # initializes oTree models once
from test_lab_route import make_session
from otree.database import db
from otree.forms.forms import get_form
from otree.templating.template import Template
import fixed
import lab_instructions as instructions
import lab_route
from lab_policy import configured_rho


def render(page, player):
    context = dict(player=player, **page.vars_for_template(player))
    if hasattr(page, 'get_form_fields'):
        context['form'] = get_form(player, page.get_form_fields(player), page, None)
    elif getattr(page, 'form_fields', None):
        context['form'] = get_form(player, page.form_fields, page, None)
    template = page.template_name or f'{player.subsession.get_folder_name()}/{page.__name__}.html'
    path=Path(template)
    if not path.is_file():path=Path('_templates',template)
    return Template(path.read_text()).render(context)


def cases(branch='E'):
    session = make_session(branch)
    return session, [(lab_route._app(app), lab_route._app(app).Subsession.objects_get(session=session, round_number=1).get_players()[0])
                     for app in lab_route.full_sequence(branch)]


class LabInstructionTests(unittest.TestCase):
    def tearDown(self):
        db.rollback()

    def test_general_structure_payment_rematching_and_exact_examples_both_sizes(self):
        for size in (18, 24):
            session = make_session('E', size)
            p = lab_route.block_subsession(session,1).get_players()[0]
            html = render(fixed.LabOverview, p)
            for expected in (f"{size} partecipanti alla sessione di oggi", '3 Sezioni', '3 Blocchi indipendenti',
                             'Blocco 1.1', 'Blocco 2.3', 'Blocco 3.3', '1000 punti', '€8.00', '€0.01',
                             'selezionato esternamente', 'Può essere negativo', 'riassegnati a nuovi gruppi', 'altre 5 imprese'):
                self.assertIn(expected, html)
            practice = render(fixed.SectionInstructions, p)
            for expected in ('dopo la tua decisione nel Periodo 5', 'dopo la tua decisione nel Periodo 10', '100 unità', '0.10 × d²'):
                self.assertIn(expected, practice)
            c = instructions.context(p)
            self.assertEqual([(e['retirement'],e['cost']) for e in c['cost_examples']],
                             [(10,'10'),(20,'40'),(25,'62.50'),(50,'250')])
            self.assertEqual(c['split_cost'], '20')
            self.assertNotIn('paid_block', json.dumps(c))

    def test_all_quizzes_correct_wrong_blank_and_per_question_counters(self):
        for branch in ('E', 'A', 'M'):
            _, players = cases(branch)
            for app, p in players:
                for general in ((True, False) if app is fixed else (False,)):
                    prefix = 'general' if general else 'comprehension'
                    qs = instructions.questions(p, general=general)
                    answers = instructions.correct_answers(p, general=general)
                    before = (p.wallet_after, p.start_equipment, copy.deepcopy(p.session.vars), copy.deepcopy(p.participant.vars))
                    self.assertIsNotNone(instructions.check_answers(p, {}, general=general))
                    self.assertEqual(getattr(p,prefix+'_errors'), len(qs))
                    self.assertFalse(getattr(p,prefix+'_passed'))
                    for q in qs:
                        bad = dict(answers, **{q['field']: 'b' if q['correct']=='a' else 'a'})
                        error = instructions.check_answers(p, bad, general=general)
                        self.assertIn(q['feedback'], error)
                        self.assertFalse(getattr(p,prefix+'_passed'))
                    self.assertIsNone(instructions.check_answers(p, answers, general=general))
                    self.assertTrue(getattr(p,prefix+'_passed'))
                    self.assertEqual(getattr(p,prefix+'_attempts'), len(qs)+2)
                    self.assertEqual(getattr(p,prefix+'_errors'), 2*len(qs))
                    self.assertEqual(json.loads(getattr(p,prefix+'_question_errors')), {q['id']:2 for q in qs})
                    self.assertEqual(before, (p.wallet_after,p.start_equipment,p.session.vars,p.participant.vars))
                    page=app.GeneralComprehension if general else app.SectionComprehension
                    self.assertEqual(page.get_form_fields(p),list(answers) if general else list(answers)[:2])
                    form=get_form(p,list(answers),page,None)
                    self.assertTrue(all(not getattr(form, name).flags.required for name in answers))  # blanks reach counted page validation
                    html=render(page,p)
                    self.assertEqual(html.count('<fieldset'),len(qs) if general else 2)
                    self.assertNotIn('Rivedi le istruzioni',html)
                    self.assertNotIn('instruction-review',html)
                    public=page.vars_for_template(p)
                    self.assertTrue(all('correct' not in q and 'feedback' not in q for q in public['questions']))

    def test_fixed_has_no_economic_threshold_and_follow_up_is_complete(self):
        _, ps = cases()
        app,p=ps[0]
        html=render(app.SectionInstructions,p)
        self.assertIn("Non determina la sanzione all'accertamento principale",html)
        self.assertIn("non c'è una soglia di gruppo",html)
        self.assertIn('Sanzione di 75 punti',html)
        self.assertIn('0.10 × attrezzatura rimanente²',html)
        self.assertIn('La tua attrezzatura rimanente sarà quindi 0 alla fine di ogni blocco',html)
        self.assertNotIn('la soglia nota è',html)

    def test_E_equality_and_own_inclusion(self):
        _,ps=cases();app,p=ps[1]
        html=render(app.SectionInstructions,p)
        self.assertIn('maggiore di 40 unità',html)
        self.assertIn('40 unità o meno',html)
        self.assertIn("L'attrezzatura della tua impresa è inclusa nella media del gruppo.",html)
        self.assertNotIn('Messaggi pubblici',html)
        self.assertNotIn('40 through 50',html)

    def test_A_support_secrecy_reveal_and_no_live_threshold_or_map_in_context(self):
        session,ps=cases('A')
        for app,p in ps[1:]:
            for page in (app.SectionInstructions,app.SectionComprehension):
                c=page.vars_for_template(p)
                self.assertNotIn('threshold',c)
                self.assertNotIn('known_threshold',c)
                self.assertNotIn('ambiguity_thresholds',json.dumps(c))
                self.assertNotIn('paid_block',json.dumps(c))
                html=render(page,p)
                if page is app.SectionInstructions:
                    self.assertIn('33 a 47 unità, estremi inclusi',html)
                    self.assertIn('fornite informazioni su quanto siano probabili',html)
                    self.assertIn('tutti e sei',html)
                else:
                    self.assertNotIn('instruction-review', html)
                self.assertNotIn('soglia è <strong>45',html)
                self.assertNotIn('soglia realizzata =',html)
                for pp in session.get_participants(): self.assertNotIn(pp.code,html)

    def test_M_two_reports_disclosure_private_second_and_informational_only(self):
        _,ps=cases('M')
        for app,p in ps[1:]:
            html=render(app.SectionInstructions,p)
            for phrase in ('La Risposta 2 rimane privata', '40', 'risposte'):
                self.assertIn(phrase,html)
            if app.__name__ == 'messages':
                self.assertIn('sei risposte individuali alla Risposta 1 sono mostrate come punti grigi anonimi',html)
                self.assertIn('non le risposte precedenti',html)
                self.assertIn("non determina l'applicazione delle sanzioni",html)
            else:
                self.assertIn('la media anonima della Risposta 1 e le sei risposte individuali',html)
                self.assertIn('Le identità non vengono mostrate',html)
            c=app.SectionComprehension.vars_for_template(p)
            self.assertFalse(any('report_values' in key or 'public_report_mean' in key for key in c))

    def test_policy_configured_share_and_feasible_numeric_example(self):
        _,ps=cases();app,p=ps[2]
        html=render(app.SectionInstructions,p)
        for phrase in ('780 punti','260 punti','130 punti','un terzo','alcun addebito aggiuntivo',
                       'la redistribuzione effettiva sarebbe zero',"Solo le sanzioni effettive all'accertamento principale",'decisione del Periodo 5'):
            self.assertIn(phrase,html)
        self.assertEqual(4*(175+Fraction(40,2)),780)
        self.assertLess(Fraction(160,6),40)  # example enforces under every allowed threshold
        for rho in (0,1):
            p.session.config['rho']=rho;p.session.config['rho_exact']=f'{rho}/1'
            c=instructions.context(p)
            self.assertEqual(c['policy_share'],f'{rho*100}%')
            self.assertEqual(c['example_transfer'],str(rho*390))

    def test_practice_is_slider_only_unpaid_and_read_only(self):
        _,ps=cases();_,p=ps[0]
        before=copy.deepcopy((p.session.vars,p.participant.vars,p.wallet_after,p.retirement if p.field_maybe_none('retirement') is not None else None))
        html=render(fixed.SectionInstructions,p)
        self.assertEqual(html.count('type="range"'),1)
        self.assertIn('min="0" max="100" step="1"',html)
        self.assertNotIn('name="retirement"',html)
        self.assertNotIn('type="number"',html)
        self.assertNotIn('http',html)
        self.assertIn('Non registra una decisione',html)
        self.assertEqual(before,(p.session.vars,p.participant.vars,p.wallet_after,None))

    def test_active_assets_have_no_obsolete_copy_or_baked_in_images(self):
        paths=[]
        for app in ('fixed','endogenous','ambiguity','messages','policy','lab_payment'):
            paths.extend(Path(app).glob('*.html'))
        paths.extend(Path('general_instructions').glob('Lab*.html'))
        paths.extend(Path('_static/fixed').glob('*.js'))
        for path in paths:
            text=path.read_text()
            for bad in ('£','Prolific','0.05','simulated firm','equally likely','selected at random','20 periods','expect or plan'):
                self.assertNotIn(bad,text,str(path))
            # Payment contains the accepted receipt QR; no instruction screenshots.
            for src in re.findall(r'<img[^>]+src="([^"]+)"', text):
                self.assertTrue(any(asset in src for asset in ('payment-receipt-qr.png', 'bless.png')), str(path))
            self.assertNotIn('cdn.jsdelivr',text,str(path))

    def test_paper_instruction_flow_leaves_gameplay_sequence_unchanged(self):
        for branch in ('E','A','M'):
            _,ps=cases(branch)
            for app,p in ps:
                names=[page.__name__ for page in app.page_sequence]
                self.assertLess(names.index('SectionComprehension'),names.index('BlockStart'))
                substantive=[n for n in names if n not in ('SectionInstructions','SectionComprehension','LabOverview','LabPractice','GeneralComprehension')]
                self.assertEqual(substantive,['ExperimentSplash' if app is fixed else 'SectionSplash','SessionReady','SectionComprehension2',*(['SectionComprehension3'] if app is fixed else []),'ComprehensionWait','FirstBlockSplash','BlockStart','BlockStartWait','Reports','ReportsWait','Decision','PeriodWait','MainCheckWait','Result','ResultWait','BlockEndWait','BlockEnd'])
                for page in (app.SectionInstructions,app.SectionComprehension):
                    self.assertTrue(page.is_displayed(p))
                    self.assertFalse(page.is_displayed(p.in_round(11)))

if __name__=='__main__': unittest.main()
