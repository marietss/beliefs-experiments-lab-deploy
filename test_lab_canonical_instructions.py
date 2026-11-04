"""User-canonical page order, route-specific information and unchanged primitives."""
import ast
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import unittest

from test_lab_instructions import cases, render
import fixed
import lab_instructions as instructions
from otree.database import db


def main_pages(html):
    html=html.split('</main>',1)[0]
    return re.findall(r'<section[^>]*data-instruction-panel>\s*<h2>(.*?)</h2>', html, re.S)


class CanonicalInstructionTests(unittest.TestCase):
    def tearDown(self): db.rollback()

    def test_canonical_flow_removes_general_extras_and_repeated_questions(self):
        names = [page.__name__ for page in fixed.page_sequence]
        self.assertEqual(names[:3], ['ExperimentSplash', 'SessionReady', 'SectionComprehension'])
        self.assertNotIn('LabOverview', names)
        self.assertNotIn('SectionInstructions', names)
        self.assertNotIn('GeneralComprehension', names)
        expected = {
            'fixed': ['reset', 'irreversible', 'period_cost', 'fixed_positive', 'fixed_average', 'follow_up'],
            'endogenous': ['known', 'equality', 'own_inclusion', 'zero'],
            'ambiguity': ['support', 'strict_unknown', 'own_inclusion', 'zero'],
            'messages': ['known', 'equality', 'two_reports', 'message_role'],
            'policy': ['pool', 'share', 'distribution_example', 'no_distribution'],
        }
        for branch in 'EAM':
            _, players = cases(branch)
            for app, player in players:
                rows = instructions.questions(player)
                self.assertEqual([q['id'] for q in rows], expected[app.__name__])
                pages = instructions.page_quiz_context(player)['quiz_pages']
                self.assertEqual([len(page['questions']) for page in pages], [2] * (len(rows) // 2))

    def test_visible_terminology_preserves_bindings_report_forms_and_payment(self):
        import html
        for app in ('fixed', 'endogenous', 'ambiguity', 'messages', 'policy'):
            for path in Path(app).glob('*.html'):
                source = path.read_text()
                # Exclude bindings, selectors and model names: only literal visible text.
                visible = re.sub(r'{{.*?}}|<[^>]*>', ' ', source, flags=re.S)
                visible = html.unescape(visible)
                self.assertNotRegex(visible, r'(?i)retir(?:e|ed|ing|ement)|penalt(?:y|ies)|wallet')
                self.assertNotIn('{{ next_button }}', source)
            decision = Path(app, 'Decision.html').read_text()
            self.assertIn('name="retirement"', decision)
            self.assertIn('id="retirement-slider"', decision)
            report = Path(app, 'Reports.html').read_text()
            self.assertIn('LabReportSliders.html', report)
            self.assertEqual(re.findall(r'name="([^"]+)"', Path('general_instructions/LabReportSliders.html').read_text()),
                             ['expected_own_equipment_main', 'expected_group_average_main'])
        self.assertIn('Portafoglio alla fine del blocco selezionato', Path('lab_payment/Payment.html').read_text())

    def test_general_verbatim_source_structure_both_sizes(self):
        from test_lab_route import make_session
        import lab_route
        for size in (18,24):
            s=make_session('E',size);p=lab_route.block_subsession(s,1).get_players()[0]
            html=render(fixed.LabOverview,p)
            self.assertEqual(main_pages(html),["ESPERIMENTO SULLA DISMISSIONE DELL'ATTREZZATURA",'Il tuo portafoglio e il pagamento','Struttura'])
            for sentence in (
                'Benvenuto! Questo è un esperimento sul processo decisionale. Leggi attentamente tutte le istruzioni.',
                f"Sei uno dei {size} partecipanti alla sessione di oggi.",
                "In questo esperimento sei il responsabile di un'impresa. Il tuo compito è gestire la dismissione di parte dell'attrezzatura esistente della tua impresa mantenendo i costi associati il più bassi possibile.",
                "L'esperimento comprende 3 Sezioni. Ogni Sezione è suddivisa in 3 Blocchi indipendenti.",
                'Le stesse istruzioni si applicano a tutti i blocchi di quella sezione.',
            ): self.assertIn(sentence,html)
            for section in (1,2,3):
                for block in (1,2,3): self.assertIn(f'Blocco {section}.{block}',html)
            self.assertIn('selezionato esternamente',html)
            self.assertIn('€8.00 + €0.01',html)
            self.assertNotIn('paid_block',json.dumps(fixed.LabOverview.vars_for_template(p)))

    def test_all_route_specific_page_sequences(self):
        expected={
            'fixed':['Attrezzatura e portafoglio','La tua decisione',"Costo della dismissione dell'attrezzatura",'Accertamenti','Schermata delle decisioni','Prova','Schermata dei risultati','Prima delle domande di comprensione'],
            'endogenous':['Introduzione','Cosa rimane uguale','La tua attrezzatura nella media del gruppo','Cosa cambia'],
            'ambiguity':['Introduzione','Cosa rimane uguale','Cosa cambia','Accertamento principale'],
            'messages':['Introduzione','Cosa rimane uguale',"Domande all'inizio di ogni blocco",'Informazioni mostrate al gruppo','Accertamento principale','Prima delle domande di comprensione'],
            'policy':['Introduzione','Cosa rimane uguale','Cosa cambia','Chi riceve la redistribuzione','Accertamento principale — Esempio'],
        }
        for branch in 'EAM':
            _,players=cases(branch)
            for app,p in players:
                before=copy.deepcopy((p.session.vars,p.participant.vars,p.wallet_after))
                html=render(app.SectionInstructions,p)
                self.assertEqual(main_pages(html),expected[app.__name__])
                self.assertEqual(before,(p.session.vars,p.participant.vars,p.wallet_after))
                section=1 if app is fixed else 3 if app.__name__=='policy' else 2
                self.assertIn(f'Sezione {section}',html)
                if section==2:
                    self.assertIn('stessa della Sezione 1',html)
                    self.assertNotIn('as in E',html)
                    self.assertNotIn('as in A',html)
                if section==3:
                    self.assertIn('stessa della Sezione 2',html)
                    self.assertIn('Blocchi 3.1, 3.2 e 3.3',html)
                if app.__name__=='ambiguity' or (app.__name__=='policy' and branch=='A'):
                    self.assertIn('33 a 47 unità, estremi inclusi',html)
                    self.assertNotIn('soglia nota di 40',html)
                    self.assertNotIn('Risposta 1:',html)
                elif app.__name__ in ('endogenous','messages','policy'):
                    self.assertIn('40',html)
                    self.assertNotIn('33 a 47 unità',html)

    def test_F_and_A_server_pair_counts_and_reserved_fields(self):
        import lab_comprehension
        for branch in ('E','A'):
            _,players=cases(branch)
            for app,p in players:
                if app.__name__ not in ('fixed','ambiguity'):continue
                pages=[page for page in app.page_sequence if issubclass(page,lab_comprehension.ComprehensionPair)]
                self.assertEqual(len(pages),3 if app is fixed else 2)
                fields=[]
                for page in pages:
                    c=page.vars_for_template(p)
                    self.assertEqual(len(c['questions']),2)
                    fields.extend(q['field'] for q in c['questions'])
                    for q in c['questions']:
                        self.assertTrue(hasattr(type(p),q['field']))
                        self.assertNotIn('correct',q)
                        self.assertNotIn('feedback',q)
                    self.assertNotIn('"correct"',json.dumps(c))
                    page.error_message(p,{})
                    self.assertEqual(p.comprehension_errors,0) # pure validation
                self.assertEqual(fields,[f'comprehension_{i}' for i in range(1,7 if app is fixed else 5)])

    def test_supplied_F_and_A_question_wording_and_correct_rules(self):
        _,players=cases('A')
        f=players[0][1];a=players[1][1]
        fq=instructions.questions(f);aq=instructions.questions(a)
        from lab_printed_questions import PRINTED_QUESTIONS
        for actual,section in ((fq,'F'),(aq,'A')):
            for question,printed in zip(actual,PRINTED_QUESTIONS[section]):
                self.assertEqual(question['prompt'],printed['prompt'])
                self.assertEqual(question['options'],printed['options'])
                self.assertEqual(question['correct'],printed['correct'])
                self.assertEqual(question['feedback'],printed['feedback'])

    def test_canonical_distractors_do_not_weaken_validation(self):
        _,players=cases('E');p=players[0][1]
        answers=instructions.correct_answers(p)
        before=copy.deepcopy((p.session.vars,p.participant.vars,p.wallet_after))
        for field in ('comprehension_1','comprehension_3'):
            self.assertIsNotNone(instructions.check_answers(p,dict(answers,**{field:'c'})))
            self.assertFalse(p.comprehension_passed)
        self.assertEqual(p.comprehension_attempts,2)
        self.assertEqual(p.comprehension_errors,2)
        self.assertIsNone(instructions.check_answers(p,answers))
        self.assertTrue(p.comprehension_passed)
        self.assertEqual(before,(p.session.vars,p.participant.vars,p.wallet_after))

    def test_secrecy_and_report_privacy_through_all_instruction_payloads(self):
        for branch in 'AM':
            s,players=cases(branch)
            for app,p in players[1:]:
                for page in (app.SectionInstructions,app.SectionComprehension):
                    c=page.vars_for_template(p);payload=json.dumps(c);html=render(page,p)
                    for forbidden in ('ambiguity_thresholds','matching_seed','lab_group_matrices','paid_block','report_values','peer_reports','peer_fines','peer_wallets'):
                        self.assertNotIn(forbidden,payload)
                        self.assertNotIn(forbidden,html)
                    if branch=='A':
                        self.assertNotIn('threshold',c)
                        self.assertNotIn('realized_threshold',payload)
                    for participant in s.get_participants():self.assertNotIn(participant.code,html)
                    if branch=='M':
                        if page is app.SectionInstructions:
                            self.assertIn('La Risposta 2 rimane privata',html)
                        else:
                            self.assertNotIn('instruction-review', html)
                        self.assertNotIn('public_report_mean',c)

    def test_examples_cost_policy_conservation_and_signed_budget_text(self):
        self.assertEqual(Fraction(1,10)*25**2,Fraction('62.5'))
        self.assertEqual(1000-Fraction(1,10)*25**2,Fraction('937.5'))
        self.assertEqual(800-75-Fraction(1,10)*25**2,Fraction('662.5'))
        self.assertEqual(4*(175+Fraction(40,2)),780)
        self.assertEqual(Fraction(1,3)*780,260)
        self.assertEqual(Fraction(1,3)*780/2,130)
        _,players=cases('A');app,p=players[2]
        html=render(app.SectionInstructions,p)
        for text in ('due imprese abbiano attrezzatura 0','quattro imprese abbiano ciascuna 40','780 punti','260 punti','130 punti','non vengono addebitate una seconda volta','non avviene alcuna redistribuzione'):
            self.assertIn(text,html)

    def test_gameplay_headings_and_only_authorized_copy_changes(self):
        # The M/Policy snapshots include authorized Decision UI changes;
        # non-Decision gameplay files remain frozen.
        for app,section in [('fixed',1),('endogenous',2),('ambiguity',2),('messages',2),('policy',3)]:
            for filename in ('BlockStart','Reports','Decision','Result','BlockEnd'):
                self.assertIn(f'Blocco {section}.{{{{ player.local_block }}}}',Path(app,filename+'.html').read_text())

        expected = {'fixed/BlockStart.html': 'dd1be398dcaa127ee60f198bcbeb3ff58714102bb9e505bc461c20f372be0246', 'fixed/Reports.html': '22e729b88c7581de9c0ecd294a25af618abcd424a8e0c6bb104a1690e8b8b937', 'fixed/Decision.html': '25a6968da5b5c24e349d57257be1dbce7708f850500e7fc9969f479c7510c5dd', 'fixed/Result.html': 'b86a399713172661612a32c4490fb4b7f367739bcd03bffb71f892fc7ffd12b5', 'fixed/BlockEnd.html': '0d08c2d1e68618c6db5395f258a42553220ee7586b6f1bf96317d5e351c71f8a', 'endogenous/BlockStart.html': 'db390c1acf9575c443fcc3f2360d150dd52a6e2287bd7214a4f9f985e5edaa57', 'endogenous/Reports.html': '705c2cbbdd94b45b9ca5ce49f00b4da06439247c041cae59ecec0fca4fa28470', 'endogenous/Decision.html': '66c6ce2a1b91f9c037e7e1aa679d3ed89ba20cec54b35475e423b440b1f80abc', 'endogenous/Result.html': 'f944dc43f1dd6c0535a52db7b6a06133349c2ade178e3cd2fa61fadd79e7cb12', 'endogenous/BlockEnd.html': 'b672678975afb5e03836631ef4415d626650ba0da0b6ed4faefc2ce3c2902d78', 'ambiguity/BlockStart.html': 'db390c1acf9575c443fcc3f2360d150dd52a6e2287bd7214a4f9f985e5edaa57', 'ambiguity/Reports.html': '705c2cbbdd94b45b9ca5ce49f00b4da06439247c041cae59ecec0fca4fa28470', 'ambiguity/Decision.html': '0e1e44fbd00bb2f42cfc702f67cbcee71b782e1c50296a15d5b08f7bd51972bf', 'ambiguity/Result.html': '53eb36747ebe66377c42d15b718f9c863f048589d3ff389aff64291a4f3d332a', 'ambiguity/BlockEnd.html': 'b672678975afb5e03836631ef4415d626650ba0da0b6ed4faefc2ce3c2902d78'}
        for path,digest in expected.items():
            source=Path(path).read_text()
            self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),digest,path)
