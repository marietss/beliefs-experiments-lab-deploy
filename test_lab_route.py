"""Integrated ORM coverage and safe handoff/recovery; disposable project only."""
from fractions import Fraction
from pathlib import Path
import ast
import unittest
from unittest.mock import patch

import test_fixed  # initialize oTree exactly once, in the isolated test copy
from otree.database import db
from otree.session import create_session, SESSION_CONFIGS_DICT
from lab_matching import select_matching
from lab_persistence import decode_fraction
import lab_route as route
import lab_reports
import fixed


def make_session(branch='E',size=18,**overrides):
    return create_session(f'dev_lab_full_{branch}_{size}',num_participants=size,
                          modified_session_config_fields=overrides)


def app_for(session,block):
    return route._app(route.block_location(session.config,block)[0])


def ready(session):
    fixed.SessionReady.after_all_players_arrive(route.block_subsession(session,1))


def submit_reports(app,group,*,offset=0):
    for p in group.get_players():
        app.BlockStart.before_next_page(p,False)
        p.expected_own_equipment_main=offset+p.participant.id_in_session
        p.expected_group_average_main=100
        app.Reports.before_next_page(p,False)
    app.ReportsWait.after_all_players_arrive(group)


def settle(app,group,amounts=None):
    for p,d in zip(group.get_players(),[0]*6 if amounts is None else amounts):
        p.retirement=d
        app.Decision.before_next_page(p,False)
    app.PeriodWait.after_all_players_arrive(group)


def prepare_block(session,block,*,last_period=10,feedback=True):
    app=app_for(session,block);first=route.block_subsession(session,block)
    for r in range(first.round_number,first.round_number+last_period):
        ss=first.in_round(r)
        for group in ss.get_groups():
            if r==first.round_number:submit_reports(app,group,offset=block*5)
            settle(app,group)
    if last_period==10 and feedback:
        for p in ss.get_players():app.BlockEnd.before_next_page(p,False)
    return ss


def finish_block(session,block):
    end=prepare_block(session,block)
    app_for(session,block).BlockEndWait.after_all_players_arrive(end)


def finish_through(session,block):
    for b in range(1,block+1):finish_block(session,b)


class RouteValidationTests(unittest.TestCase):
    def tearDown(self):db.rollback()

    def test_all_six_routes_exact_sizes_initialization_and_single_store(self):
        for branch in ('E','A','M'):
            for size in (18,24):
                session=make_session(branch,size)
                ss=route.block_subsession(session,1)
                state,people=route.matching_state(ss)
                self.assertEqual(len(people),size)
                self.assertEqual(state['branch'],branch)
                self.assertEqual(set(state['matrices']),{'1'})
                for b in (1,4,7):
                    first=route.block_subsession(session,b)
                    for target in first.in_rounds(1,10):
                        self.assertEqual(target.grouping_installed,b==1)
                        self.assertEqual(len(target.get_groups()),size//6)
                    if b!=1:
                        app=app_for(session,b)
                        self.assertFalse(app.SessionReady.is_displayed(first.get_players()[0]))
                        with self.assertRaisesRegex(ValueError,'matching'):app.current_state(first.get_players()[0])
                        # Retry creating_session must not preselect/install a downstream matrix.
                        app.creating_session(first)
                        self.assertFalse(first.grouping_installed)
                self.assertEqual(set(state['matrices']),{'1'})
                for key in ('lab_fixed_matching_v1','lab_endogenous_matching_v1','lab_ambiguity_matching_v1',
                            'lab_messages_matching_v1','lab_policy_matching_v1'):
                    self.assertNotIn(key,session.vars)

    def test_inexact_size_and_route_mismatches_fail_before_gameplay(self):
        for size in (6,12,24,30):
            with self.assertRaisesRegex(ValueError,'lab_session_size'):
                create_session('dev_lab_full_E_18',num_participants=size)
            db.rollback()
        for branch,wrong in [('E','ambiguity'),('M','endogenous'),('A','messages')]:
            name=f'dev_lab_full_{branch}_18'
            invalid={**SESSION_CONFIGS_DICT[name], 'app_sequence':['fixed',wrong,'policy']}
            # oTree deliberately forbids app_sequence as a runtime API override.
            # Patch the static config fixture to exercise creation-time rejection.
            with patch.dict(SESSION_CONFIGS_DICT,{name:invalid}):
                with self.assertRaisesRegex(ValueError,'configured branch'):
                    create_session(name,num_participants=18)
            db.rollback()

    def test_root_snapshot_rejects_changed_branch_seed_thresholds_or_rho(self):
        for overrides in ({'branch':'M'},{'matching_seed':'changed'},{'rho':0,'rho_exact':'0/1'},
                          {'ambiguity_thresholds':{'4':33,'5':41,'6':46,'7':44,'8':47,'9':40}}):
            session=make_session('A' if 'ambiguity_thresholds' in overrides else 'E')
            session.config={**session.config,**overrides}
            with self.assertRaises(ValueError):route.matching_state(route.block_subsession(session,1))

    def test_no_economic_functions_changed_and_no_persistence_switch(self):
        # Direct source evidence: integration adds delegation around matching
        # and readiness, not settlement/primitives. Runtime equivalence below
        # and the existing regressions are the substantive checks.
        self.assertNotIn('wallet_after',Path('lab_route.py').read_text().split('def _assert_unused')[0])
        self.assertNotIn('set_group_matrix',Path('lab_bot_checks.py').read_text())
        self.assertEqual(Fraction(3,40),decode_fraction('3/40'))


class IntegratedCoverageTests(unittest.TestCase):
    def tearDown(self):db.rollback()

    def test_nine_blocks_both_group_counts_determinism_resets_economics_and_exact_coverage(self):
        from lab_bot_checks import assert_participant_finished
        for branch,size in [('E',18),('A',24),('M',18)]:
            with patch('lab_route.select_matching',wraps=select_matching) as select:
                session=make_session(branch,size);ready(session)
                for block in range(1,10):
                    app=app_for(session,block);first=route.block_subsession(session,block)
                    matrix=route.stored_matrix(first,block)
                    self.assertEqual(len(matrix),size//6)
                    for target in first.in_rounds(first.round_number,first.round_number+9):
                        self.assertEqual(route.actual_matrix(target),matrix)
                    if block in (4,7):
                        self.assertTrue(first.readiness_complete)
                    for group in first.get_groups():
                        for p in group.get_players():
                            self.assertEqual(app.current_state(p),(100,1000))
                            if branch=='M' and block>=4:
                                with self.assertRaisesRegex(ValueError,'unavailable'):lab_reports.read(p)
                        submit_reports(app,group,offset=block*8)
                        if branch=='M' and block>=4:
                            expected=Fraction(sum(p.expected_own_equipment_main for p in group.get_players()),6)
                            self.assertEqual(lab_reports.read(group.get_players()[0]),expected)
                    for r in range(first.round_number,first.round_number+10):
                        ss=first.in_round(r)
                        for group in ss.get_groups():
                            at_main=group.period==5
                            threshold=(session.config['ambiguity_thresholds'][str(block)] if branch=='A' and block>=4 else 40)
                            local=(block-1)%3+1
                            equipment=([threshold+1]*6 if block in (4,) else [threshold]*6 if block in (5,8)
                                       else [0,100,100,100,100,100] if block==9
                                       else [0,0,0,40,40,41] if block in (3,6,7)
                                       else [100]*6)
                            settle(app,group,[100-k for k in equipment] if at_main else None)
                            self.assertEqual(decode_fraction(group.group_mean),Fraction(group.equipment_total,6))
                            if at_main:
                                enforced=block<=3 or sum(equipment)<=6*threshold
                                fines=[Fraction(175)+Fraction(k,2) if enforced and k>0 else Fraction(0) for k in equipment]
                                count=equipment.count(0)
                                allocation=Fraction(sum(fines),3) if block>=7 and count else Fraction(0)
                                for p,k,fine in zip(group.get_players(),equipment,fines):
                                    transfer=allocation/count if block>=7 and k==0 else Fraction(0)
                                    self.assertEqual(decode_fraction(p.main_fine),fine)
                                    expected=decode_fraction(p.wallet_before)-Fraction(1,10)*(100-k)**2-fine+transfer
                                    self.assertEqual(decode_fraction(p.wallet_after),expected)
                                    if block>=7:
                                        self.assertEqual(decode_fraction(p.own_transfer),transfer)
                                        self.assertEqual(p.underlying_branch,branch)
                                    if branch=='A' and block>=4:self.assertEqual(p.applied_main_threshold,threshold)
                                if block>=7:
                                    self.assertEqual(decode_fraction(group.fine_pool),sum(fines))
                                    self.assertEqual(sum(decode_fraction(p.own_transfer) for p in group.get_players()),allocation)
                                record=group.settlement_record
                                app.PeriodWait.after_all_players_arrive(group)
                                self.assertEqual(group.settlement_record,record)
                    end=first.in_round(first.round_number+9)
                    for p in end.get_players():
                        self.assertEqual(p.final_equipment,0)
                        app.BlockEnd.before_next_page(p,False)
                    ids=[g.id for g in end.get_groups()]
                    app.BlockEndWait.after_all_players_arrive(end)
                    if block<9:
                        destination=route.block_subsession(session,block+1)
                        prepared_ids=[g.id for g in destination.get_groups()]
                        app.BlockEndWait.after_all_players_arrive(end)
                        self.assertEqual(prepared_ids,[g.id for g in destination.get_groups()])
                    self.assertEqual(ids,[g.id for g in end.get_groups()])
                self.assertEqual(select.call_count,9)
                for call in select.call_args_list:
                    block=call.args[2];start=((block-1)//3)*3+1
                    self.assertEqual(set(call.args[3]),set(range(start,block)))
            for p in route.block_subsession(session,9,last=True).get_players():assert_participant_finished(p)


class HandoffSafetyTests(unittest.TestCase):
    def tearDown(self):db.rollback()

    def source(self):
        session=make_session();ready(session);finish_block(session,1);finish_block(session,2)
        source=prepare_block(session,3)
        return session,source

    def test_destination_preflight_checks_last_round_data_and_waitpage_without_early_selection(self):
        session,source=self.source()
        app=app_for(session,4);last=route.block_subsession(session,4).in_round(10)
        p=last.get_players()[0]
        with patch('lab_route.select_matching',wraps=select_matching) as select:
            for attr,value in [('retirement',0),('expected_own_equipment_main',50),('wallet_after','0/1')]:
                old=p.field_maybe_none(attr);setattr(p,attr,value)
                with self.assertRaisesRegex(ValueError,'used destination'):fixed.complete_block(source)
                self.assertFalse(source.block_barrier_complete)
                self.assertFalse(route.block_subsession(session,4).grouping_installed)
                self.assertNotIn('4',session.vars[route.MATRICES_KEY]['matrices'])
                setattr(p,attr,old)
            pp=p.participant
            pp._current_app_name='endogenous';pp._round_number=1;pp._current_page_name='SessionReady'
            with self.assertRaisesRegex(ValueError,'WaitPage'):fixed.complete_block(source)
            self.assertEqual(select.call_count,0)
            pp._current_app_name='fixed';pp._round_number=30
            fixed.complete_block(source)
            self.assertEqual(select.call_count,1)
        self.assertTrue(source.block_barrier_complete)

    def test_partially_committed_install_retries_same_matrix_without_releasing_source_or_deleting_prepared_groups(self):
        session,source=self.source();app=app_for(session,4)
        original=app.Subsession.set_group_matrix
        def fail_on_third(target,matrix):
            if target.round_number==3:raise RuntimeError('test interrupted handoff')
            return original(target,matrix)
        with patch('lab_route.select_matching',wraps=select_matching) as select:
            with patch.object(app.Subsession,'set_group_matrix',fail_on_third):
                with self.assertRaisesRegex(RuntimeError,'interrupted'):fixed.complete_block(source)
            db.commit();db.expire_all() # emulate persisted intermediate state/internal oTree commits
            first=route.block_subsession(session,4)
            ids={r:[g.id for g in first.in_round(r).get_groups()] for r in (1,2)}
            self.assertFalse(source.block_barrier_complete)
            self.assertFalse(first.readiness_complete)
            with self.assertRaisesRegex(ValueError,'barrier'):app.current_state(first.get_players()[0])
            matrix=route.stored_matrix(source,4)
            fixed.complete_block(source)
            self.assertEqual(select.call_count,1)
            self.assertEqual(route.stored_matrix(source,4),matrix)
            self.assertTrue(source.block_barrier_complete and first.readiness_complete)
            for r,expected in ids.items():self.assertEqual(expected,[g.id for g in first.in_round(r).get_groups()])
            for target in first.in_rounds(1,10):self.assertEqual(route.actual_matrix(target),matrix)

    def test_duplicate_handoff_after_destination_data_preserves_rows_and_corrupt_store_fails_closed(self):
        session,source=self.source();fixed.complete_block(source)
        destination=route.block_subsession(session,4);app=app_for(session,4)
        for group in destination.get_groups():submit_reports(app,group);settle(app,group)
        records=[g.settlement_record for g in destination.get_groups()]
        ids=[g.id for g in destination.get_groups()]
        fixed.complete_block(source)
        app.creating_session(destination)
        self.assertEqual(ids,[g.id for g in destination.get_groups()])
        self.assertEqual(records,[g.settlement_record for g in destination.get_groups()])
        state=session.vars[route.MATRICES_KEY]
        wrong=[list(g) for g in route.stored_matrix(source,4)]
        wrong[0][0],wrong[1][0]=wrong[1][0],wrong[0][0]
        session.vars[route.MATRICES_KEY]={**state,'matrices':{**state['matrices'],'4':[list(g) for g in wrong]}}
        with self.assertRaisesRegex(ValueError,'disagrees'):fixed.complete_block(source)
        self.assertEqual(ids,[g.id for g in destination.get_groups()])
        self.assertEqual(records,[g.settlement_record for g in destination.get_groups()])
