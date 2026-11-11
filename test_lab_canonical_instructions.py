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
        self.assertEqual(names[:5], ['ExperimentSplash', 'SessionReady', 'PracticeDecision', 'PracticeComplete', 'SectionComprehension'])
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

    @unittest.skipUnless(Path('general_instructions/LabOverview.html').is_file(), 'Historical instruction/summary wrapper absent from this deployment snapshot; active native pages tested separately.')
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

    @unittest.skipUnless(Path('general_instructions/LabSection.html').is_file(), 'Historical instruction/summary wrapper absent from this deployment snapshot; active native pages tested separately.')
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
                    self.assertIn('33 a 42 unità, estremi inclusi',html)
                    self.assertNotIn('soglia nota di 40',html)
                    self.assertNotIn('Risposta 1:',html)
                elif app.__name__ in ('endogenous','messages','policy'):
                    self.assertIn('37',html)
                    self.assertNotIn('33 a 42 unità',html)

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
                self.assertCountEqual(question['options'],printed['options'])
                self.assertEqual(question['correct'],printed['correct'])
                self.assertEqual(question['feedback'],printed['feedback'])

    def test_canonical_distractors_do_not_weaken_validation(self):
        _,players=cases('E');p=players[0][1]
        answers=instructions.correct_answers(p)
        before=copy.deepcopy((p.session.vars,p.participant.vars,p.wallet_after))
        for field in ('comprehension_1','comprehension_3'):
            self.assertIsNotNone(instructions.check_answers(p,dict(answers,**{field:next(key for key,_ in next(q for q in instructions.questions(p) if q['field']==field)['options'] if key!=answers[field])})))
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
                    c=page.vars_for_template(p);payload=json.dumps(c)
                    for forbidden in ('ambiguity_thresholds','matching_seed','lab_group_matrices','paid_block','report_values','peer_reports','peer_fines','peer_wallets'):
                        self.assertNotIn(forbidden,payload)
                    with self.subTest(branch=branch,app=app.__name__,page=page.__name__):
                        template=Path(page.template_name)
                        if not template.is_file() and not (Path('_templates')/template).is_file():
                            self.skipTest('Historical instruction wrapper absent: '+page.template_name)
                        html=render(page,p)
                        self.assertNotIn('paid_block',html)
                    if page is app.SectionInstructions and not Path(page.template_name).is_file():
                        continue

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
        self.assertEqual(Fraction(3,10)*780,234)
        self.assertEqual(Fraction(3,10)*780/2,117)
        _,players=cases('A');app,p=players[2]
        from otree.templating.template import Template
        body=Path('general_instructions/LabCanonicalPolicyBody.html').read_text()
        # Render its actual example section: historical wrapper/includes are absent.
        html=Template('<section'+body.rsplit('<section',1)[1]).render(dict(player=p,**instructions.context(p)))
        for text in ('due imprese abbiano attrezzatura 0','quattro imprese abbiano ciascuna 40','780 punti','234 punti','117 punti','non vengono addebitate una seconda volta'):
            self.assertIn(text,html)

    def test_gameplay_headings_and_only_authorized_copy_changes(self):
        import lab_route
        for app_name,section in [('fixed',1),('endogenous',2),('ambiguity',2),('messages',2),('policy',3)]:
            app=lab_route._app(app_name)
            for filename in ('BlockStart','Reports','Decision','Result'):
                self.assertIn(f'Blocco {section}.{{{{ player.local_block }}}}',Path(app_name,filename+'.html').read_text())
            self.assertEqual(app.BlockEnd.template_name,'lab/BlockSummary.html')
            self.assertEqual(app.page_sequence[-2:],[app.BlockEndWait,app.BlockEnd])
        summary=Path('_templates/lab/BlockSummary.html').read_text()
        self.assertIn('{{ summary_wallet }}',summary)
        self.assertIn('{{ summary_maximum }}',summary)
        self.assertNotIn('main_equipment',summary)
        for path,digest in GAMEPLAY_HASHES.items():
            self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(),digest,path)

GAMEPLAY_HASHES = {'fixed/BlockStart.html': 'dd1be398dcaa127ee60f198bcbeb3ff58714102bb9e505bc461c20f372be0246', 'fixed/Reports.html': '3a75c7e28ddb3f7c34dedc619918016bd3c8631720559bcaced17110403bbf40', 'fixed/Decision.html': '418342280b278b2f21187e5141aeee5a194a82af9aaf8402098af19f4476b051', 'fixed/Result.html': 'ff8981e4d6be9397b0fb29f104d7b45333b05495ab3dfbbd0b77bb9ea4323b50', 'endogenous/BlockStart.html': 'db390c1acf9575c443fcc3f2360d150dd52a6e2287bd7214a4f9f985e5edaa57', 'endogenous/Reports.html': '1942f30b0fe137f568b0006835c360504b67ee3db752bc26f0a7dee5d40efad0', 'endogenous/Decision.html': '4d31e0d0f1a0028d4fea58760935fad30949a576b86c884e5a7c8477d6a2bea8', 'endogenous/Result.html': '23020ad324bbf792871e57c6a9c404ab2d52e415d15417b33384ab4c9b8a0d00', 'ambiguity/BlockStart.html': 'db390c1acf9575c443fcc3f2360d150dd52a6e2287bd7214a4f9f985e5edaa57', 'ambiguity/Reports.html': '1942f30b0fe137f568b0006835c360504b67ee3db752bc26f0a7dee5d40efad0', 'ambiguity/Decision.html': 'db1db442dfec59c1e33006661f27c53dbf2813e0f3b5b8fc9825f4571d0ee407', 'ambiguity/Result.html': '598ed3e8e3feb6362b57827e7ad4d0f704e36123012512b6d78edbf4b8e44590', 'messages/BlockStart.html': 'db390c1acf9575c443fcc3f2360d150dd52a6e2287bd7214a4f9f985e5edaa57', 'messages/Reports.html': '7872630f40965a92982e161e2af96b14753936de761c30b46f2ac68cf7bf9d9e', 'messages/Decision.html': 'c1f51cb6832bb3311b6d411092312727125a73562db3c98d8146e1dcfd94bf9d', 'messages/Result.html': '47746a0d76ac28d5052028812bc4c282f983afb20a80e82636c7ba1f5c56e909', 'policy/BlockStart.html': '4d717d1d907d95fa3ba64db563fd8d1decfbe35d9cd21ea9006d78ca826364da', 'policy/Reports.html': '91a5f8a91d5de0489bcebfaf7bf70643be15228b33356710c4eb35980fbb995f', 'policy/Decision.html': '506f39ca1a42fb3e58ab294421b0e57eb601dabcf3123ebeb14add60077223c8', 'policy/Result.html': 'a12ec865adeb73872ade6b4690c887d8b18824d3d3a1851bfa428201f291ac82', '_templates/lab/BlockSummary.html': '62d00dbc4eb97123efcc53f5cb496ad48884856c289455ba95bd3213374ae9a3'}
