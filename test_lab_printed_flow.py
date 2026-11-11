"""Printed-document contract and non-economic lab flow/timer regression checks."""
import ast
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import unittest
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import test_fixed
from test_fixed import make_session, subsession, ready, reports
from test_lab_production import make_production_session
from otree.api import WaitPage
from otree.database import db
import fixed
import lab_instructions as instructions
import lab_route
from lab_printed_questions import PRINTED_QUESTIONS, SOURCE_SHA256

DOCX = Path('/Users/andrea/Downloads/Istruzioni_lab_261026_chiarezza_impaginazione.docx')


class PrintedFlowTests(unittest.TestCase):
    def tearDown(self): db.rollback()

    def test_literal_question_snapshots_and_correct_option_positions(self):
        keys={'F':'bacbac','E':'cbac','A':'bcba','M':'cabc','P':'bcab'}
        for section,rows in PRINTED_QUESTIONS.items():
            self.assertEqual(''.join(q['correct'] for q in rows),keys[section])
            self.assertEqual(hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),QUESTION_HASHES[section])
            self.assertTrue(all(q['prompt'].startswith(f'Domanda {i} — ') for i,q in enumerate(rows,1)))

    @unittest.skipUnless(DOCX.is_file(),'External printed DOCX unavailable; frozen literal snapshots still apply.')
    def test_uncalibrated_items_retain_original_docx_wording(self):
        self.assertEqual(hashlib.sha256(DOCX.read_bytes()).hexdigest(),SOURCE_SHA256)
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        with ZipFile(DOCX) as archive:root=ET.fromstring(archive.read('word/document.xml'))
        headings={'Domande di comprensione — Sezione 1':'F','Domande di comprensione — Sezione 2 (E)':'E','Domande di comprensione — Sezione 2 (A)':'A','Domande di comprensione — Sezione 2 (M)':'M','Domande di comprensione — Sezione 3':'P'}
        found={};section=None;row=None
        for paragraph in root.findall('.//w:body/w:p',ns):
            text=''.join(t.text or '' for t in paragraph.findall('.//w:t',ns))
            if text in headings:section=headings[text];found[section]=[];row=None
            elif section and text.startswith('Domanda '):row=dict(prompt=text,options=[],feedback='');found[section].append(row)
            elif section and row and text.startswith('•  '):row['options'].append(text[3:])
            elif section and row and text.startswith('Feedback in caso di risposta errata: '):row['feedback']=text.split(': ',1)[1]
            elif text.startswith('Sezione '):section=None;row=None
        for section,rows in found.items():
            changed = {'F': {'period_cost', 'fixed_positive', 'follow_up'},
                       'E': {'known', 'equality'}, 'A': {'support'},
                       'M': {'known', 'equality'}, 'P': {'share', 'distribution_example'}}
            for original, q in zip(rows, PRINTED_QUESTIONS[section]):
                if q['id'] not in changed[section]:
                    self.assertCountEqual(original['options'], [label for _, label in q['options']])
                    self.assertEqual(original, dict(prompt=q['prompt'], options=original['options'], feedback=q['feedback']))

    def test_six_production_sequences_and_counts(self):
        for branch in 'EAM':
            for size in (18,24):
                s=make_production_session(branch,size)
                self.assertEqual(s.config['app_sequence'],lab_route.payment_sequence(branch))
                for name in s.config['app_sequence'][:3]:
                    app=lab_route._app(name);p=app.Subsession.objects_get(session=s,round_number=1).get_players()[0]
                    names=[page.__name__ for page in app.page_sequence]
                    self.assertEqual(names,[('ExperimentSplash' if name=='fixed' else 'SectionSplash'),'SessionReady',*(['PracticeDecision','PracticeComplete'] if name=='fixed' else []),'SectionComprehension','SectionComprehension2',*(['SectionComprehension3'] if name=='fixed' else []),'ComprehensionWait','FirstBlockSplash','BlockStart','BlockStartWait','Reports','ReportsWait','Decision','PeriodWait','MainCheckWait','Result','ResultWait','BlockEndWait','BlockEnd'])
                    self.assertEqual(len(instructions.questions(p)),6 if name=='fixed' else 4)
                    self.assertEqual(app.SectionComprehension.get_form_fields(p),['comprehension_1','comprehension_2'])
                    self.assertEqual(app.Decision.get_timeout_seconds(p),40)
                    for period, seconds in ((1,20),(5,60),(10,60)):
                        self.assertEqual(app.Result.get_timeout_seconds(p.in_round(period)),seconds)
                    for page in [app.ComprehensionWait,app.BlockStartWait,app.MainCheckWait,app.BlockEndWait]:self.assertTrue(page.wait_for_all_groups)
                    for page in [app.ReportsWait,app.PeriodWait,app.ResultWait]:self.assertFalse(page.wait_for_all_groups)
                    for page in [app.SessionReady,app.ComprehensionWait,app.BlockStartWait,app.ReportsWait,app.PeriodWait,app.ResultWait,app.BlockEndWait]:self.assertTrue(issubclass(page,WaitPage))
                    self.assertTrue(app.FirstBlockSplash.is_displayed(p))
                    self.assertFalse(app.BlockStart.is_displayed(p))
                    for r in [11,21]:self.assertTrue(app.BlockStart.is_displayed(p.in_round(r)));self.assertFalse(app.FirstBlockSplash.is_displayed(p.in_round(r)))
                    self.assertFalse(app.ResultWait.is_displayed(p.in_round(10)))

    def test_pair_validation_is_pure_and_section_passes_only_after_final_pair(self):
        for branch in 'EAM':
            s=make_production_session(branch,18)
            for name in s.config['app_sequence'][:3]:
                app=lab_route._app(name);p=app.Subsession.objects_get(session=s,round_number=1).get_players()[0]
                for page in [page for page in app.page_sequence if page.__name__.startswith('SectionComprehension')]:
                    qs=[q for q in instructions.questions(p) if q['field'] in page.get_form_fields(p)]
                    self.assertTrue(page.error_message(p,{}))
                    wrong={q['field']:next(v for v,_ in q['options'] if v!=q['correct']) for q in qs}
                    feedback=page.error_message(p,wrong)
                    for q in qs:self.assertIn(q['feedback'],feedback)
                    self.assertEqual((p.comprehension_attempts,p.comprehension_errors),(0,0))
                    self.assertIsNone(page.error_message(p,instructions.correct_answers(p)))
                    self.assertFalse(p.comprehension_passed)
                    for q in qs:setattr(p,q['field'],q['correct'])
                    page.before_next_page(p,False)
                    payload=json.dumps(page.vars_for_template(p))
                    self.assertNotIn('"correct"',payload)
                self.assertTrue(p.comprehension_passed)

    def test_admin_template_has_no_form_input_button_or_automatic_timer(self):
        html=Path('_templates/lab/AdminSplash.html').read_text()
        for forbidden in ['<form','<input','<button','next_button','timeout_seconds','setTimeout']:self.assertNotIn(forbidden,html)
        self.assertIn("static 'global/bless.png'",html)
        for name in ['fixed','endogenous','ambiguity','messages','policy']:
            app=lab_route._app(name)
            for page in [app.FirstBlockSplash,getattr(app,'ExperimentSplash',None) or app.SectionSplash]:
                self.assertIsNone(getattr(page,'timeout_seconds',None))
                self.assertIsNone(getattr(page,'form_model',None))
                self.assertFalse(getattr(page,'form_fields',[]))
        self.assertNotIn('instruction-review',Path('_templates/lab/ComprehensionPair.html').read_text())

    def test_timeout_zero_and_result_invariance_in_all_apps_and_policy_branches(self):
        import importlib
        fixtures=[('test_fixed',None),('test_endogenous',None),('test_ambiguity',None),('test_messages',None)]
        fixtures += [('test_policy',branch) for branch in 'EAM']
        for module, branch in fixtures:
            fixture=importlib.import_module(module)
            session=fixture.make_session() if branch is None else fixture.make_session(branch)
            fixture.ready(session)
            group=fixture.subsession(session).get_groups()[0]
            fixture.reports(group)
            app=lab_route._app(group.subsession.get_folder_name())
            participant_vars=copy.deepcopy([p.participant.vars for p in group.get_players()])
            for player in group.get_players():
                player.retirement=75
                app.Decision.before_next_page(player,True)
                self.assertEqual((player.retirement,player.locked_retirement),(0,0))
            app.PeriodWait.after_all_players_arrive(group)
            balances=[(p.wallet_after,p.voluntary_cost,p.main_fine) for p in group.get_players()]
            for player in group.get_players():app.Result.before_next_page(player,True)
            self.assertEqual(balances,[(p.wallet_after,p.voluntary_cost,p.main_fine) for p in group.get_players()])
            self.assertEqual(participant_vars,[p.participant.vars for p in group.get_players()])
            db.rollback()

    def test_decision_timeout_locks_exactly_zero_and_result_timeout_no_money_change(self):
        s=make_session();ready(s);g=subsession(s).get_groups()[0];reports(g)
        before=copy.deepcopy(g.get_players()[0].participant.vars)
        for i,p in enumerate(g.get_players()):
            p.retirement=37 if i%2 else 0
            fixed.Decision.before_next_page(p,True)
            self.assertEqual((p.retirement,p.locked_retirement),(0,0))
        self.assertFalse(g.settlement_complete)
        fixed.PeriodWait.after_all_players_arrive(g)
        for p in g.get_players():
            self.assertEqual((p.final_equipment,p.wallet_after),(100,'1000/1'))
            state=(p.wallet_after,p.voluntary_cost,p.main_fine,p.follow_up_fine,p.forced_retirement_cost)
            fixed.Result.before_next_page(p,True)
            self.assertEqual(state,(p.wallet_after,p.voluntary_cost,p.main_fine,p.follow_up_fine,p.forced_retirement_cost))
        self.assertEqual(before,g.get_players()[0].participant.vars)

    def test_protected_economics_reports_M_graphs_payment_and_exports_are_unchanged(self):
        for name,digest in PROTECTED_HASHES.items():self.assertEqual(hashlib.sha256(Path(name).read_bytes()).hexdigest(),digest,name)


# Updated only after reviewed recalibration; original DOCX provenance retained above.
QUESTION_HASHES = {'F': '62ad63a8d144be8422f9edc905fa2e94b7cba8cfe9fe320a05ea887533c0b403', 'E': 'dc039ada482728958d3a7633fb0ed54766474f996a3cd72d915b94b77d64cae4', 'A': 'e38d50683a700ee5d920985c557afd5d98c24b4ce2f7c4bdf338d5b9ff83d3b0', 'M': 'b0c0a70e714ce3c7158055d59ea134de93e9311f249af0c5804bcec4355929ed', 'P': '5a7d8f069bc7fc6821091b1bc476b76d432327f8f3d8dc41bcb29d01d7cdbe72'}
PROTECTED_HASHES = {'lab_rules.py': '70a12353f00855eb58b76b90808d1d2dc5b2a90e69b3062be8fbd50528d7327d', 'lab_policy.py': 'a266d5b2ce72759f3f5c448b9913ea92e2b8c5bd800fb42858acf74bc3c42c5a', 'lab_cash.py': 'b762184e1f545e3a3c7236a20b24d9abf7a97f19d1729cd240b0216543d383a7', 'lab_export.py': 'b21fc51a8ee6fef2b1b4d691ba34aefa302fa775731cf7d1da371ad80fce3df0', 'lab_matching.py': '9af26dcb74b59f58ef36a787d2b7914283f3f8dcf92bdc35b7e00bd0d03923dd', 'lab_route.py': '7cc9cfeaadf2e762453e586756d506bd5194195840e1c3bd72d9e64d0e6c67e2', 'lab_threshold.py': '86967019ce3e338e2ca3bcd4935fc9cf7e8f8d9ec2b129a9dd92c57b5ba17a5b', 'lab_reports.py': 'beb8510a26b28c75ef895f358ef2c9ec0741258a15e5e765f2f4fab4fde6bf75', 'lab_config.py': '027ea39e855f79d2afbf939948423580586a66a14410a01e6a4c80007c9ef6a1', 'lab_production.py': 'ed7eaa5a69f0e2494dd64aba6d64e211900102a6bd8443c07cc34d47a57210ba', 'lab_presentation.py': 'c97b9760076a21baf56d102dc9cd917f304b5b3c116e6271a4476b358369f185', 'messages/presentation.py': 'f7a7d8c31812eb8d0c08b89388bad8a8ebe36d0baa7c5180f40f26fa05730fc9', 'messages/public_reports.py': '1de88ccc009d8f061291a44c4cce567eaa902c069caffaa0fd8b9fb86b032629', 'policy/presentation.py': 'e85f5e3d12ce3e3906324f3505b580ac541bf678f300d65163c92d650ab67d54', 'policy/settlement.py': '8fea9f8e71f45210f66676c93aab844920821e22c746834f661f45041576d03f', '_static/messages/charts.js': 'a54b981e21cb7917a7467f6a1d9353995d163caaec346bc0eaccaff67a5ed236', '_static/policy/charts.js': '14430b89dfcc5dedfa57d03714a3d52782f13c24babe32c8fb4f82acd605866f', '_static/fixed/equipment-presentation.js': 'aba306b3ebbb34e0534959603887f30940360ad520732c026809dc1be6b415b2', 'lab_payment/__init__.py': '0ce1d9cc2ab1f76cc6980bb808000385dfd9739d70bc1e3925230b58fca2ed24', 'lab_payment/Payment.html': 'd3a779fe71babc0d8fa78055da2f7b6ac4e607306345e7cc2f1e086964b3cf01', 'lab_payment/tests.py': '31780847469ba23c5ef50b856f44aeace70178e44a49be55da4c5a3e51212ee9', 'test_lab_payment.py': '212095a88dfb1d0a72bb1ec20e593a3fb5d9c547fbb62df077de43e3fb1a9b0d'}
