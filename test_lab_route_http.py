"""Native oTree HTTP tests at both app boundaries, with deliberately slow groups.

Prior periods are genuinely settled through app callbacks as fixture setup.
Only then are test participants positioned at the final-period Decision page.
The final decision, PeriodWait, Result, BlockEndWait and downstream
pages use real HTTP requests. Full 90-period HTTP traversal is separately
covered by tutti e sei unshortened integrated bot sessions.
"""
from fractions import Fraction
import json
import re
import unittest
from unittest.mock import patch
from test_lab_route import make_session,ready,finish_block,prepare_block,app_for
from starlette.testclient import TestClient
from otree.database import db
from otree.common import participant_start_url
from otree.lookup import _get_session_lookups
from otree.constants import wait_page_http_header
from otree.asgi import app as asgi_app
from lab_matching import select_matching
from lab_persistence import decode_fraction
import lab_route as route
import lab_reports


def chart_config(html):
    return json.loads(re.search(r'<script id="lab-chart-config" type="application/json">(.*?)</script>',html,re.S).group(1))


class CrossAppHTTPTests(unittest.TestCase):
    def tearDown(self):db.rollback()

    def test_E_A_M_both_cross_app_barriers_slow_sixth_reload_privacy_and_fresh_messages(self):
        for branch in ('E','A','M'):
            session=make_session(branch);ready(session)
            responses={}
            participants={p.participant.code:p.participant for p in route.block_subsession(session,1).get_players()}
            client=TestClient(asgi_app)  # match oTree bot clients: no lifespan/shutdown backup
            def refresh(code):
                responses[code]=client.get(str(responses[code].url),allow_redirects=True)
                self.assertEqual(responses[code].status_code,200)
                db.expire_all()
                return responses[code]
            def post(code,data=None):
                responses[code]=client.post(str(responses[code].url),data=data or {},allow_redirects=True)
                self.assertEqual(responses[code].status_code,200)
                db.expire_all()
                return responses[code]
            def private_payload(code,html):
                for other in participants:
                    if other!=code:self.assertNotIn(other,html)
                for term in ('paid_block','matching_seed','lab_group_matrices','ambiguity_thresholds',
                             'public_report_record','settlement_record','locked_own_report','locked_group_report'):
                    self.assertNotIn(term,html)
            for boundary in (3,6):
                # Genuine completed prefix; never fabricate settlement markers.
                for b in ((1,2) if boundary==3 else (4,5)):finish_block(session,b)
                source=prepare_block(session,boundary,last_period=9)
                source=source.in_round(30)
                source_app=app_for(session,boundary)
                destination=route.block_subsession(session,boundary+1)
                destination_app=app_for(session,boundary+1)
                self.assertFalse(destination.grouping_installed)
                ids_before=[g.id for g in source.get_groups()]
                source_matrix=route.actual_matrix(source)
                index=next(idx for idx,lookup in _get_session_lookups(session.code).items()
                           if lookup.app_name==source.get_folder_name() and lookup.round_number==30
                           and lookup.page_class is source_app.Decision)
                for pp in participants.values():
                    pp._index_in_pages=index;pp.visited=True
                    pp._current_app_name=source.get_folder_name();pp._round_number=30
                    pp._current_page_name='Decision'
                db.commit()
                for code in participants:
                    responses[code]=client.get(participant_start_url(code),allow_redirects=True)
                    self.assertEqual(responses[code].status_code,200)
                    self.assertIn('id="confirm-retirement"',responses[code].text)
                    private_payload(code,responses[code].text)
                groups=[[p.participant.code for p in g.get_players()] for g in source.get_groups()]
                with patch('lab_route.select_matching',wraps=select_matching) as select:
                    # Two fast groups reach the OLD grouping's all-session wait.
                    for codes in groups[:-1]:
                        for code in codes:post(code,{'retirement':0})
                        for code in codes:
                            refresh(code);self.assertIn("Esito dell'accertamento finale",responses[code].text)
                            wallet=source_app.Player.objects_get(participant=participants[code],round_number=30).wallet_after
                            refresh(code)
                            self.assertEqual(wallet,source_app.Player.objects_get(participant=participants[code],round_number=30).wallet_after)
                            post(code) # Result -> whole-session block barrier
                            self.assertIn(wait_page_http_header,responses[code].headers)
                    self.assertFalse(source.block_barrier_complete)
                    self.assertFalse(destination.grouping_installed)
                    self.assertNotIn(str(boundary+1),session.vars[route.MATRICES_KEY]['matrices'])
                    # Five choices in the last group cannot settle that period.
                    slow_codes=groups[-1];slow_group=source.get_groups()[-1]
                    for code in slow_codes[:-1]:
                        post(code,{'retirement':0})
                        self.assertIn(wait_page_http_header,responses[code].headers)
                    self.assertFalse(slow_group.settlement_complete)
                    self.assertFalse(any(p.block_feedback_submitted for p in slow_group.get_players()))
                    for code in groups[0]:
                        refresh(code)
                        self.assertIn(wait_page_http_header,responses[code].headers)
                        self.assertEqual(participants[code]._current_app_name,source.get_folder_name())
                    post(slow_codes[-1],{'retirement':0})
                    self.assertTrue(slow_group.settlement_complete)
                    record=slow_group.settlement_record
                    for code in slow_codes:
                        refresh(code);post(code)
                    self.assertEqual(record,slow_group.settlement_record)
                    self.assertTrue(source.block_barrier_complete and destination.grouping_installed)
                    self.assertEqual(select.call_count,1)
                    self.assertEqual(select.call_args.args[2:],(boundary+1,{}))
                    matrix=route.stored_matrix(source,boundary+1)
                    for target in destination.in_rounds(1,10):self.assertEqual(route.actual_matrix(target),matrix)
                    dest_ids={r:[g.id for g in destination.in_round(r).get_groups()] for r in range(1,11)}
                    for code in participants:
                        refresh(code)
                        self.assertIn('Altra azienda',responses[code].text)
                        post(code)  # Existing individual BlockEnd summary after the session barrier.
                        self.assertNotIn(wait_page_http_header,responses[code].headers)
                        self.assertEqual(participants[code]._current_app_name,destination.get_folder_name())
                        self.assertEqual(participants[code]._round_number,1)
                        self.assertIn(f'Sezione {2 if boundary==3 else 3} — Attendi le nuove istruzioni.',responses[code].text)
                        self.assertNotIn('<form',responses[code].text)
                        private_payload(code,responses[code].text)
                    def admin_release():
                        from otree.common import CSRF_TOKEN_NAME
                        admin=client.get('/sessions')
                        token=re.search(r'name="'+CSRF_TOKEN_NAME+r'" value="([^"]+)"',admin.text).group(1)
                        response=client.post('/AdvanceSession/'+session.code,data={'advancemode':'visited_only',CSRF_TOKEN_NAME:token})
                        self.assertEqual(response.status_code,200)
                        db.expire_all()
                    admin_release()
                    for code in participants:
                        refresh(code)
                        self.assertIn('Domande di comprensione',responses[code].text)
                        self.assertNotIn('instruction-review',responses[code].text)
                        self.assertNotIn('Rivedi le istruzioni',responses[code].text)
                        private_payload(code,responses[code].text)
                    import lab_instructions
                    for code in participants:
                        p=destination_app.Player.objects_get(participant=participants[code],round_number=1)
                        for number in (1,2):
                            import lab_comprehension
                            post(code,{q['field']:q['correct'] for q in lab_comprehension.pair_questions(p,number)})
                    for code in participants:
                        refresh(code)
                        self.assertIn('Blocco 2.1' if boundary==3 else 'Blocco 3.1',responses[code].text)
                        self.assertNotIn('<form',responses[code].text)
                        private_payload(code,responses[code].text)
                        p=destination_app.Player.objects_get(participant=participants[code],round_number=1)
                        self.assertEqual(destination_app.current_state(p),(100,1000))
                        self.assertFalse(p.group.reports_complete)
                        context=destination_app.BlockStart.vars_for_template(p)
                        if branch=='A':
                            self.assertNotIn('threshold',context)
                            self.assertEqual((context['support_low'],context['support_high']),(33,47))
                        elif branch=='E':self.assertEqual(context['threshold'],40)
                        else:self.assertNotIn('report-disclosure',responses[code].text)
                    admin_release()
                    for code in participants:
                        refresh(code)
                        self.assertIn('report-own-slider',responses[code].text)
                    source_app.complete_block(source) # duplicate callback after participants entered next app
                    self.assertEqual(select.call_count,1)
                    for r,ids in dest_ids.items():self.assertEqual(ids,[g.id for g in destination.in_round(r).get_groups()])
                self.assertEqual(ids_before,[g.id for g in source.get_groups()])
                self.assertEqual(source_matrix,route.actual_matrix(source))
                if boundary==6:
                    # Native report flow in rematched policy Block 7. No old M message.
                    for group in destination.get_groups():
                        codes=[p.participant.code for p in group.get_players()]
                        for index,code in enumerate(codes):
                            self.assertNotIn('id="public-report-mean"',responses[code].text)
                            post(code,{'expected_own_equipment_main':60+participants[code].id_in_session,
                                       'expected_group_average_main':100})
                            if index<5:
                                self.assertFalse(group.reports_complete)
                                self.assertFalse(group.public_report_complete)
                        for code in codes:
                            refresh(code);private_payload(code,responses[code].text)
                            config=chart_config(responses[code].text)
                            if branch=='M':
                                p=destination_app.Player.objects_get(participant=participants[code],round_number=1)
                                expected=Fraction(sum(60+participants[c].id_in_session for c in codes),6)
                                self.assertEqual(lab_reports.read(p),expected)
                                self.assertEqual(config['publicReportMean'],float(expected))
                                old=source_app.Player.objects_get(participant=participants[code],round_number=21)
                                self.assertNotEqual(lab_reports.read(old),lab_reports.read(p))
                            elif branch=='A':
                                self.assertNotIn('threshold',config)
                                self.assertFalse(config['thresholdRevealed'])
                                self.assertNotIn('thresholds',config)
                    # Fast groups cannot reveal Main feedback while another group is still deciding.
                    all_codes=[]
                    for group in destination.get_groups():
                        codes=[p.participant.code for p in group.get_players()]
                        all_codes.extend(codes)
                        for period in range(1,6):
                            for pos,code in enumerate(codes):
                                amount=(100 if pos<3 else 59 if pos==5 else 60) if period==1 else 0
                                if branch=='A':self.assertNotIn('threshold',chart_config(responses[code].text))
                                post(code,{'retirement':amount})
                            for code in codes:
                                refresh(code)
                                if period<5:post(code)
                            if period<5:
                                for code in codes:refresh(code)
                        if group!=destination.get_groups()[-1]:
                            for code in all_codes:
                                refresh(code)
                                self.assertIn(wait_page_http_header,responses[code].headers)
                                self.assertNotIn('lab-chart-config',responses[code].text)
                            self.assertFalse(any(g.settlement_complete for g in destination.in_round(5).get_groups()))
                    for code in all_codes:
                        refresh(code)
                        config=chart_config(responses[code].text)
                        self.assertEqual(config['threshold'],session.config['ambiguity_thresholds']['7'] if branch=='A' else 40)
                        self.assertIn('id="fine-pool">585.50 punti',responses[code].text)
                        self.assertIn('id="redistributed-pool">195.17 punti',responses[code].text)
                        private_payload(code,responses[code].text)
                    self.assertTrue(all(g.settlement_complete for g in destination.in_round(5).get_groups()))
                    # Source retries preserve already-collected destination reports/settlements.
                    before=[g.settlement_record for g in destination.get_groups()]
                    source_app.complete_block(source)
                    self.assertEqual(before,[g.settlement_record for g in destination.get_groups()])
            db.commit()
