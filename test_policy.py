"Pure policy arithmetic e unctual six-human oTree callbacks; isolated copy only."

from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import ast
import unittest
from unittest.mock import patch

import test_fixed  # one shared oTree setup; never initialize a DB in the working repo
from otree.api import WaitPage
from otree.database import db
from otree.session import create_session
from lab_persistence import encode_fraction, decode_fraction
from lab_policy import redistribute, exact_rho, configured_rho
from lab_matching import select_matching
import lab_rules as rules
import lab_reports
import policy


def make_session(branch='E', size=18, *, rho=None, thresholds=None):
    custom = {}
    if rho is not None:
        custom['rho'] = rho
        custom['rho_exact'] = encode_fraction(exact_rho(rho))
    if thresholds is not None:
        custom['ambiguity_thresholds'] = thresholds
    return create_session(f'dev_lab_policy_{branch}_{size}', num_participants=size, modified_session_config_fields=custom)


def subsession(session, r=1):
    return policy.Subsession.objects_get(session=session, round_number=r)


def ready(session):
    policy.SessionReady.after_all_players_arrive(subsession(session))


def reports(group, own=None, private=None):
    for p, a, b in zip(group.get_players(), [50]*6 if own is None else own, [100]*6 if private is None else private):
        p.expected_own_equipment_main = a
        p.expected_group_average_main = b
        policy.Reports.before_next_page(p, False)
    policy.ReportsWait.after_all_players_arrive(group)


def decide(group, amounts=None):
    for p, amount in zip(group.get_players(), [0]*6 if amounts is None else amounts):
        p.retirement = amount
        policy.Decision.before_next_page(p, False)


def run_period(group, amounts=None):
    if group.period == 1:
        reports(group)
    decide(group, amounts)
    policy.PeriodWait.after_all_players_arrive(group)


def main_group(branch='E', *, rho=None, equipment=None, threshold=None, own=None):
    mapping = {'4':47,'5':33,'6':46,'7':47,'8':40,'9':33}
    if threshold is not None:
        mapping['7'] = threshold
    session = make_session(branch, rho=rho, thresholds=mapping if branch=='A' else None)
    ready(session)
    group = subsession(session).get_groups()[0]
    reports(group, own)
    decide(group); policy.settle_period(group)
    for r in (2,3,4):
        run_period(subsession(session,r).get_groups()[0])
    group = subsession(session,5).get_groups()[0]
    if equipment is not None:
        run_period(group,[100-k for k in equipment])
    return group


def finish_block(session, local):
    first = (local-1)*10+1
    for r in range(first,first+10):
        for group in subsession(session,r).get_groups():
            run_period(group)
    ss=subsession(session,first+9)
    for p in ss.get_players():
        policy.BlockEnd.before_next_page(p,False)
    policy.BlockEndWait.after_all_players_arrive(ss)


class PolicyArithmeticTests(unittest.TestCase):
    def test_exact_rho_types_and_no_nearby_fraction_inference(self):
        for value, expected in [(0,Fraction(0)), (1,Fraction(1)), (Fraction(1,3),Fraction(1,3)),
                                (Decimal('0.125'),Fraction(1,8)), (0.1,Fraction(1,10))]:
            self.assertEqual(exact_rho(value),expected)
        self.assertEqual(exact_rho(1/3),Fraction('0.3333333333333333'))
        self.assertNotEqual(exact_rho(1/3),Fraction(1,3))
        for value in (True,-1,2,float('nan'),float('inf'),float('-inf'),'1/3'):
            with self.assertRaises(ValueError):exact_rho(value)

    def test_rho_zero_third_one_conservation_multiple_recipients(self):
        for zero_count in (1,2,3,4,6):
            equipment=[0]*zero_count+[43]*(6-zero_count)
            fines=[rules.main_fine(k) for k in equipment]
            for rho in (0,Fraction(1,3),1):
                result=redistribute(equipment,fines,rho)
                self.assertEqual(result.fine_pool,sum(fines))
                self.assertEqual(result.recipient_count,zero_count)
                self.assertEqual(result.redistributed_pool,rho*sum(fines))
                self.assertEqual(sum(result.transfers),result.redistributed_pool)
                self.assertTrue(all(t==result.redistributed_pool/zero_count for t in result.transfers[:zero_count]))
                self.assertTrue(all(t==0 for t in result.transfers[zero_count:]))

    def test_no_recipient_no_actual_redistribution(self):
        result=redistribute([45]*6,[Fraction('197.5')]*6,Fraction(1,3))
        self.assertEqual((result.fine_pool,result.recipient_count,result.redistributed_pool),(1185,0,0))
        self.assertEqual(result.transfers,(0,)*6)

    def test_no_fines_with_eligible_recipient_does_not_manufacture_money(self):
        result=redistribute([0,100,100,100,100,100],[0]*6,Fraction(1,3))
        self.assertEqual((result.recipient_count,result.fine_pool,result.redistributed_pool),(1,0,0))

    def test_roundtrips_halves_thirds_and_signed_results(self):
        for count in (2,3,4):
            equipment=[0]*count+[40]*(5-count)+[41]
            result=redistribute(equipment,[rules.main_fine(k) for k in equipment],Fraction(1,3))
            self.assertEqual(result.transfers[0],result.fine_pool/3/count)
            self.assertEqual(result.transfers[0].denominator % 3,0)
            for value in (Fraction(1,3),result.fine_pool,result.redistributed_pool,*result.transfers,
                          -100+result.transfers[0]):
                self.assertEqual(decode_fraction(encode_fraction(value)),value)
        self.assertEqual(redistribute([0]*4+[43]*2,[0]*4+[Fraction('196.5')]*2,Fraction(1,3)).transfers[0],Fraction(131,4))

    def test_exact_companion_is_explicit_checked_and_JSON_safe(self):
        self.assertEqual(configured_rho({'rho':1/3,'rho_exact':'1/3'}),Fraction(1,3))
        self.assertEqual(configured_rho({'rho':0.1}),Fraction(1,10))
        for config in ({'rho':0.5,'rho_exact':'1/3'}, {'rho':0.5,'rho_exact':'2/4'},
                       {'rho':1,'rho_exact':'2/1'}):
            with self.assertRaises(ValueError):configured_rho(config)
        from otree.common2 import json_dumps
        from otree.session import SESSION_CONFIGS_DICT
        self.assertIn('dev_lab_policy_E_18',json_dumps(list(SESSION_CONFIGS_DICT.values())))

    def test_invalid_primitives(self):
        for equipment,fines in [([0]*5,[0]*5),([True]*6,[0]*6),([0]*6,[175]*6),([1]*6,[-1]*6),([1]*6,[175.5]*6)]:
            with self.assertRaises(ValueError):redistribute(equipment,fines,Fraction(1,3))


class PolicyBackendTests(unittest.TestCase):
    def tearDown(self):db.rollback()

    def test_exact_size_mapping_resolved_branch_rho_pickle_roundtrip(self):
        for branch in ('E','A','M'):
            for size in (18,24):
                session=make_session(branch,size)
                self.assertEqual(configured_rho(session.config),Fraction(1,3))
                for r in (1,5,10,11,20,21,30):
                    ss=subsession(session,r)
                    self.assertEqual(ss.underlying_branch,branch)
                    for p in ss.get_players():
                        self.assertEqual((p.global_block,p.local_block,p.period),
                                         (rules.global_block_for_round(r,'P(Z)'),rules.local_block_for_round(r),rules.period_for_round(r)))
                        self.assertEqual(p.underlying_branch,branch)
                        self.assertEqual(p.group.rho,'1/3')
                db.commit();db.expire_all()
                self.assertEqual(session.config['rho_exact'],'1/3')
                self.assertEqual(policy.resolved_config(subsession(session))['rho'],'1/3')

    def test_wrong_exact_size_rejected(self):
        for count in (6,12,24,30):
            with self.assertRaisesRegex(ValueError,'lab_session_size'):
                create_session('dev_lab_policy_E_18',num_participants=count)
            db.rollback()

    def test_branch_rho_threshold_snapshot_and_standalone_guard(self):
        for change in ({'branch':'M'}, {'rho':1}, {'ambiguity_thresholds':{'4':41,'5':43,'6':45,'7':46,'8':40,'9':33}}):
            session=make_session('A' if 'ambiguity_thresholds' in change else 'E')
            session.config={**session.config,**change}
            with self.assertRaisesRegex(ValueError,'configuration changed|agree'):
                policy.resolved_config(subsession(session))
        session=make_session()
        session.config={**session.config,'app_sequence':['fixed','policy']}
        with self.assertRaisesRegex(ValueError,'standalone'):policy.validated_session(subsession(session))

    def test_A_complete_map_required_and_no_fallback(self):
        for mapping in ({}, {'7':47,'8':40,'9':50}):
            with self.assertRaisesRegex(ValueError,'exactly string keys'):
                make_session('A',thresholds=mapping)
            db.rollback()

    def test_six_locked_decisions_before_fines_or_transfers(self):
        group=main_group()
        for p in group.get_players()[:5]:
            p.retirement=60;policy.Decision.before_next_page(p,False)
        with self.assertRaisesRegex(ValueError,'six decisions'):policy.settle_period(group)
        self.assertFalse(group.settlement_complete)
        self.assertEqual((group.fine_pool,group.redistributed_pool),('',''))
        self.assertTrue(all(not p.main_fine and not p.own_transfer for p in group.get_players()))
        p=group.get_players()[-1];p.retirement=60;policy.Decision.before_next_page(p,False)
        policy.settle_period(group)
        self.assertEqual(group.equipment_total,240)
        self.assertTrue(group.main_enforcement_applied)

    def test_E_M_and_A_strict_equality_above_below(self):
        for branch in ('E','M','A'):
            for threshold in ((33,40,47) if branch=='A' else (40,)):
                for delta in (-1,0,1):
                    equipment=[threshold]*5+[threshold+delta]
                    group=main_group(branch,equipment=equipment,threshold=threshold)
                    self.assertEqual(group.equipment_total,6*threshold+delta)
                    self.assertEqual(decode_fraction(group.group_mean),Fraction(6*threshold+delta,6))
                    self.assertEqual(group.main_enforcement_applied,delta<=0)
                    self.assertEqual(group.recipient_count,0)
                    self.assertEqual(decode_fraction(group.redistributed_pool),0)
                    for p,k in zip(group.get_players(),equipment):
                        self.assertEqual(decode_fraction(p.main_fine),rules.main_fine(k) if delta<=0 else 0)

    def test_one_recipient_no_second_payer_charge(self):
        group=main_group(equipment=[0,40,40,40,40,40])
        self.assertEqual((decode_fraction(group.fine_pool),group.recipient_count,decode_fraction(group.redistributed_pool)),(975,1,325))
        for p in group.get_players():
            fine=decode_fraction(p.main_fine);transfer=decode_fraction(p.own_transfer)
            before=decode_fraction(p.wallet_before);cost=decode_fraction(p.voluntary_cost)
            self.assertEqual(decode_fraction(p.wallet_after_main_fine),before-cost-fine)
            self.assertEqual(decode_fraction(p.wallet_after),before-cost-fine+transfer)
            self.assertEqual(transfer,325 if p.voluntary_equipment_after==0 else 0)
        self.assertEqual(sum(decode_fraction(p.own_transfer) for p in group.get_players()),325)

    def test_multiple_recipients_repeating_fraction_and_rho_boundaries(self):
        for rho in (0,Fraction(1,3),1):
            group=main_group(rho=rho,equipment=[0,0,0,43,43,43])
            pool=Fraction('589.5')
            self.assertEqual(decode_fraction(group.fine_pool),pool)
            self.assertEqual(decode_fraction(group.redistributed_pool),rho*pool)
            self.assertEqual(sum(decode_fraction(p.own_transfer) for p in group.get_players()),rho*pool)
            for p in group.get_players()[:3]:
                self.assertEqual(decode_fraction(p.own_transfer),rho*pool/3)
        group=main_group(equipment=[0,0,0,40,40,41])
        self.assertEqual(group.get_players()[0].own_transfer,'1171/18')

    def test_no_enforcement_no_pool_despite_recipient(self):
        group=main_group(equipment=[0,100,100,100,100,100])
        self.assertFalse(group.main_enforcement_applied)
        self.assertEqual(group.recipient_count,1)
        self.assertEqual((group.fine_pool,group.redistributed_pool),('0/1','0/1'))
        self.assertTrue(all(p.own_transfer=='0/1' for p in group.get_players()))

    def test_fines_but_no_recipients(self):
        group=main_group(equipment=[40]*6)
        self.assertEqual(group.fine_pool,'1170/1')
        self.assertEqual((group.recipient_count,group.redistributed_pool),(0,'0/1'))
        self.assertTrue(all(p.own_transfer=='0/1' for p in group.get_players()))

    def test_all_six_zero(self):
        group=main_group(equipment=[0]*6)
        self.assertTrue(group.main_enforcement_applied)
        self.assertEqual((group.fine_pool,group.recipient_count,group.redistributed_pool),('0/1',6,'0/1'))
        self.assertTrue(all(p.is_policy_recipient and p.main_fine=='0/1' and p.own_transfer=='0/1' for p in group.get_players()))

    def test_follow_up_excluded_transfer_carried_once_zero_stays_in_group(self):
        main=main_group(equipment=[0,40,40,40,40,40])
        session=main.session
        initial=main.get_players()[0]
        for r in range(6,11):
            row=subsession(session,r).get_groups()[0]
            run_period(row)
            recipient=initial.in_round(r)
            self.assertTrue(recipient.decision_submitted and recipient.period_settled)
            self.assertEqual(decode_fraction(recipient.wallet_before),325)
            self.assertEqual(decode_fraction(recipient.wallet_after),325)
            self.assertEqual(row.fine_pool,'0/1')
            self.assertEqual(row.redistributed_pool,'0/1')
            self.assertTrue(all(p.own_transfer=='0/1' for p in row.get_players()))
        self.assertEqual(decode_fraction(recipient.follow_up_fine),0)
        for p in row.get_players()[1:]:
            self.assertEqual(decode_fraction(p.follow_up_fine),75)
            self.assertEqual(decode_fraction(p.forced_retirement_cost),160)
        self.assertEqual(main.fine_pool,'975/1')
        self.assertEqual(main.redistributed_pool,'325/1')

    def test_actual_game_can_end_with_negative_fine_payer_wallet(self):
        session=make_session();ready(session)
        for r in range(1,11):run_period(subsession(session,r).get_groups()[0])
        p=subsession(session,10).get_groups()[0].get_players()[0]
        self.assertEqual(decode_fraction(p.final_block_wallet),-75)

    def test_signed_starting_primitives_transfer_can_raise_wallet(self):
        # Accounting stress fixture, not a claim this negative Main start is
        # reachable from W0=1000 under the fixed irreversible-retirement rules.
        group=main_group()
        for p in group.get_players():p.in_round(4).wallet_after='-100/1'
        run_period(group,[100,60,60,60,60,60])
        recipient=group.get_players()[0]
        self.assertEqual(decode_fraction(recipient.wallet_after_main_fine),-1100)
        self.assertEqual(decode_fraction(recipient.wallet_after),-775)
        self.assertEqual(decode_fraction(recipient.own_transfer),325)
        self.assertLess(decode_fraction(group.get_players()[1].wallet_after),0)

    def test_main_idempotence_reload_and_tamper_detection(self):
        for branch in ('E','A','M'):
            group=main_group(branch,equipment=[0,0,0,40,40,41])
            before=(group.settlement_record,[(p.main_fine,p.own_transfer,p.wallet_after) for p in group.get_players()])
            policy.settle_period(group)
            db.commit();db.expire_all()
            policy.settle_period(group)
            self.assertEqual(before,(group.settlement_record,[(p.main_fine,p.own_transfer,p.wallet_after) for p in group.get_players()]))
            group.redistributed_pool='1/1'
            with self.assertRaisesRegex(ValueError,'Inconsistent replay'):policy.settle_period(group)

    def test_equivalence_to_actual_E_A_M_before_transfer(self):
        import endogenous,ambiguity,messages
        for branch,app in [('E',endogenous),('A',ambiguity),('M',messages)]:
            equipment=[0,20,40,60,70,79]
            pg=main_group(branch,equipment=equipment,threshold=47)
            session=create_session(f'dev_lab_{app.__name__}_18',num_participants=18)
            first=app.Subsession.objects_get(session=session,round_number=1)
            app.SessionReady.after_all_players_arrive(first)
            for r in range(1,6):
                group=first.in_round(r).get_groups()[0]
                if r==1:
                    for p in group.get_players():
                        p.expected_own_equipment_main=50;p.expected_group_average_main=100
                        app.Reports.before_next_page(p,False)
                    app.ReportsWait.after_all_players_arrive(group)
                for p,k in zip(group.get_players(),equipment):
                    p.retirement=100-k if r==5 else 0
                    app.Decision.before_next_page(p,False)
                app.PeriodWait.after_all_players_arrive(group)
            self.assertEqual((group.equipment_total,group.main_enforcement_applied),(pg.equipment_total,pg.main_enforcement_applied))
            self.assertEqual([p.main_fine for p in group.get_players()],[p.main_fine for p in pg.get_players()])
            self.assertEqual([p.wallet_after for p in group.get_players()],[p.wallet_after_main_fine for p in pg.get_players()])
            if branch=='M':self.assertEqual(group.in_round(1).public_report_mean,pg.in_round(1).public_report_mean)

    def test_M_six_report_barrier_exact_mean_report2_exclusion(self):
        session=make_session('M');ready(session)
        group=subsession(session).get_groups()[0]
        for index,p in enumerate(group.get_players()):
            p.expected_own_equipment_main=int(index==5);p.expected_group_average_main=100
            policy.Reports.before_next_page(p,False)
            if index<5:
                with self.assertRaisesRegex(ValueError,'six'):policy.complete_reports(group)
                self.assertFalse(group.public_report_complete)
        self.assertFalse(group.public_report_complete)
        policy.complete_reports(group)
        self.assertEqual(group.public_report_mean,'1/6')
        self.assertEqual(lab_reports.read(group.get_players()[0]),Fraction(1,6))
        record=group.public_report_record
        policy.complete_reports(group)
        self.assertEqual(group.public_report_record,record)

    def test_M_message_has_no_mechanical_payoff_effect(self):
        outcomes=[]
        for report in (0,100):
            group=main_group('M',equipment=[0,20,40,60,70,79],own=[report]*6)
            outcomes.append((group.main_enforcement_applied,group.fine_pool,
                             [(p.main_fine,p.own_transfer,p.wallet_after) for p in group.get_players()]))
        self.assertEqual(*outcomes)

    def test_E_A_reports_do_not_publish(self):
        for branch in ('E','A'):
            session=make_session(branch);ready(session)
            group=subsession(session).get_groups()[0];reports(group)
            self.assertTrue(group.reports_complete)
            self.assertFalse(group.public_report_complete)
            self.assertEqual(group.public_report_mean,'')

    def test_fresh_history_7_8_9_both_sizes_all_rounds_and_A_block_thresholds(self):
        for size in (18,24):
            with patch('policy.select_matching',wraps=select_matching) as select:
                session=make_session('A',size);ready(session)
                self.assertEqual(select.call_args.args[2:],(7,{}))
                session.vars['lab_messages_matching_v1']={'unrelated':'bad Z history'}
                old_ids=[g.id for g in subsession(session).get_groups()]
                for local,global_block in ((1,7),(2,8),(3,9)):
                    first=(local-1)*10+1
                    matrix=policy.stored_matrix(subsession(session),global_block)
                    for r in range(first,first+10):
                        self.assertEqual(policy._actual_matrix(subsession(session,r)),matrix)
                        self.assertEqual(policy.threshold_for_round(subsession(session,r)),{7:47,8:40,9:33}[global_block])
                    finish_block(session,local)
                    if local<3:
                        self.assertEqual(select.call_args.args[2],global_block+1)
                        self.assertEqual(set(select.call_args.args[3]),set(range(7,global_block+1)))
                        calls=select.call_count
                        policy.complete_block(subsession(session,local*10))
                        self.assertEqual(select.call_count,calls)
                self.assertEqual(select.call_count,3)
                self.assertEqual(set(session.vars[policy.MATCHING_KEY]['matrices']),{'7','8','9'})
                self.assertEqual(old_ids,[g.id for g in subsession(session).get_groups()])
                self.assertTrue(subsession(session,30).block_barrier_complete)

    def test_waitpages_and_unfinished_session_cannot_rematch(self):
        self.assertEqual([p.__name__ for p in policy.page_sequence],['SectionSplash','SessionReady','SectionComprehension','SectionComprehension2','ComprehensionWait','FirstBlockSplash','BlockStart','BlockStartWait','Reports','ReportsWait','Decision','PeriodWait','MainCheckWait','Result','ResultWait','BlockEndWait'])
        for page in (policy.SessionReady,policy.ComprehensionWait,policy.BlockStartWait,policy.ReportsWait,policy.PeriodWait,policy.MainCheckWait,policy.ResultWait,policy.BlockEndWait):
            self.assertTrue(issubclass(page,WaitPage))
        self.assertTrue(policy.SessionReady.wait_for_all_groups and policy.BlockEndWait.wait_for_all_groups)
        self.assertFalse(policy.PeriodWait.wait_for_all_groups or policy.ResultWait.wait_for_all_groups)
        self.assertTrue(policy.ComprehensionWait.wait_for_all_groups and policy.BlockStartWait.wait_for_all_groups and policy.MainCheckWait.wait_for_all_groups)
        session=make_session();ready(session)
        with self.assertRaisesRegex(ValueError,'All session'):policy.complete_block(subsession(session,10))
        self.assertFalse(subsession(session,11).grouping_installed)
        self.assertEqual(set(session.vars[policy.MATCHING_KEY]['matrices']),{'7'})
        source=Path(policy.__file__).read_text()
        self.assertFalse(any(token in source for token in ('simulated_environment','generate_simulated_paths','DecisionWait','random.randint')))
        self.assertIs(policy.engines['E'].settle_period.__func__,policy.engines['A'].settle_period.__func__)

class PolicyAdditionalBoundaryTests(unittest.TestCase):
    def tearDown(self):db.rollback()

    def test_each_rematched_M_block_uses_only_its_new_six_reports(self):
        session=make_session('M');ready(session)
        for local in (1,2,3):
            first=(local-1)*10+1
            ss=subsession(session,first)
            for group in ss.get_groups():
                for p in group.get_players():
                    with self.assertRaisesRegex(ValueError,'unavailable'):lab_reports.read(p)
                values=[local*10+p.participant.id_in_session for p in group.get_players()]
                reports(group,values,[100]*6)
                expected=Fraction(sum(values),6)
                for p in group.get_players():
                    for r in (first,first+4,first+9):
                        self.assertEqual(lab_reports.read(p.in_round(r)),expected)
            for r in range(first,first+10):
                for group in subsession(session,r).get_groups():
                    decide(group);policy.settle_period(group)
            end=subsession(session,first+9)
            for p in end.get_players():policy.BlockEnd.before_next_page(p,False)
            policy.complete_block(end)

    def test_policy_installer_refuses_used_or_early_future_rounds(self):
        session=make_session();ready(session)
        source=subsession(session,10)
        with self.assertRaisesRegex(ValueError,'barrier'):policy._install_block(source,8)
        source.block_barrier_complete=True
        subsession(session,20).get_players()[0].retirement=0
        with self.assertRaisesRegex(ValueError,'used destination'):policy._install_block(source,8)
        self.assertFalse(subsession(session,11).grouping_installed)
        self.assertEqual(set(session.vars[policy.MATCHING_KEY]['matrices']),{'7'})
