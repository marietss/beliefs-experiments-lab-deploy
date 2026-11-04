"""Independent arithmetic/coverage/CSV audit of the normalized lab datasets.

Run in a disposable copy with OTREE_LAB_PAYMENTS=1 OTREE_IN_MEMORY=1.
Fixtures execute actual reports/decisions/WaitPage callbacks, all 90 periods,
rematching barriers and payment finalization. Assertions use Fraction arithmetic
written here, not the gameplay economic/matching/payment calculation helpers.
"""
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction as F
from itertools import combinations
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_lab_route import make_session, ready, app_for, settle
from otree.database import db
from otree.export import custom_export_app, get_custom_export_functions
import lab_payment
import lab_cash
import lab_route
import lab_export as export


def completed_session(branch, size, paid_block):
    session=make_session(branch,size,paid_block=paid_block);ready(session)
    for block in range(1,10):
        first=lab_route.block_subsession(session,block);app=app_for(session,block)
        for group in first.get_groups():
            for p in group.get_players():
                app.BlockStart.before_next_page(p,False)
                p.expected_own_equipment_main=block*10+p.participant.id_in_session%6
                p.expected_group_average_main=100-p.expected_own_equipment_main
                app.Reports.before_next_page(p,False)
            app.ReportsWait.after_all_players_arrive(group)
        for r in range(first.round_number, first.round_number+10):
            for group in first.in_round(r).get_groups():
                amounts=[]
                for p in group.get_players():
                    if block==1: d=0  # negative -300 wallet
                    elif block==2:
                        # One zero wallet per group: C(100)=1000, no fines.
                        d=(100 if p.period==1 else 0) if p.id_in_group==1 else (10 if p.period in (1,2) else 1 if p.period==3 else 0)
                    elif block==3:d=100 if p.period==1 else 0
                    else:
                        threshold=session.config['ambiguity_thresholds'][str(block)] if branch=='A' else 40
                        local=(block-1)%3+1
                        target=(threshold+1 if block<7 else 0 if p.id_in_group==1 else 100) if local==1 else threshold if local==2 else (0 if p.id_in_group<=3 else 41 if p.id_in_group==6 else 40)
                        d=100-target if p.period==1 else 0
                    amounts.append(d)
                settle(app,group,amounts)
        end=first.in_round(first.round_number+9)
        for p in end.get_players():app.BlockEnd.before_next_page(p,False)
        app.BlockEndWait.after_all_players_arrive(end)
    import bucket
    for p in bucket.Player.objects_filter(session=session):
        bucket.start(p,now=1000);bucket.receive(p,dict(action='sync'),now=1300)
    for p in lab_payment.Player.objects_filter(session=session):lab_cash.finalize(p)
    return session


def database_snapshot(session):
    """Persisted columns only; exclude SQLAlchemy relationship/cache bookkeeping."""
    objects=[session,*session.get_participants()]
    for name in session.config['app_sequence']:
        app=lab_route._app(name)
        for model in (app.Subsession,app.Group,app.Player):objects.extend(model.objects_filter(session=session))
    return [(type(obj).__module__,obj.id,tuple((col.key,repr(obj.field_maybe_none(col.key)
            if hasattr(obj,'field_maybe_none') else getattr(obj,col.key)))
            for col in obj.__table__.columns)) for obj in objects]


class ExportReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sessions={};cls.bundles={}
        for branch in 'EAM':
            for size in (18,24):
                paid=1 if (branch,size)==('E',18) else 2 if (branch,size)==('E',24) else 3 if (branch,size)==('A',18) else 9
                session=completed_session(branch,size,paid)
                cls.sessions[(branch,size)]=session
                cls.bundles[(branch,size)]=export.export_session(session,require_complete=True)
                print(f'Export fixture complete: {branch}/{size}, nine blocks, 90 periods, finalized payments.',flush=True)
        db.commit()

    def tearDown(self):db.rollback()

    def test_full_coverage_and_unambiguous_treatment_keys_both_sizes(self):
        for (branch,n),tables in self.bundles.items():
            self.assertTrue(tables['session'][0]['complete'])
            expected={'session':1,'membership':9*n,'period':90*n,'group_period':90*n//6,
                'reports':9*n,'messages':6*n//6 if branch=='M' else 0,'main_group':9*n//6,
                'main':9*n,'completion':9*n,'ledger':9*n,'payment':n}
            self.assertEqual({k:len(v) for k,v in tables.items()},expected)
            self.assertEqual(len(tables['period']),1620 if n==18 else 2160)
            for table,rows in tables.items():
                self.assertEqual(len(rows),len({tuple(r[k] for k in export.KEYS[table]) for r in rows}))
                list(export.csv_rows(tables,table))  # every field/header checked
            for row in tables['period']:
                b,p=row['global_block'],row['period']
                self.assertEqual(row['global_period'],(b-1)*10+p)
                self.assertEqual(row['app_round'],((b-1)%3)*10+p)
                self.assertEqual(row['treatment'],'F' if b<4 else branch if b<7 else f'P({branch})')
                self.assertEqual(row['section'],('F','Z','P(Z)')[(b-1)//3])

    def test_independent_cost_equipment_group_totals_and_wallet_audit(self):
        for tables in self.bundles.values():
            groups={(r['group_id'],r['period']):r for r in tables['group_period']}
            grouped=defaultdict(list);paths=defaultdict(list)
            completions={(r['participant_code'],r['global_block']):r for r in tables['completion']}
            ledger={(r['participant_code'],r['global_block']):F(r['final_block_wallet']) for r in tables['ledger']}
            for r in tables['period']:
                self.assertEqual(F(r['voluntary_cost']),F(1,10)*r['voluntary_retirement']**2)
                self.assertEqual(r['equipment_after_voluntary'],r['equipment_before']-r['voluntary_retirement'])
                grouped[(r['group_id'],r['period'])].append(r)
                paths[(r['participant_code'],r['global_block'])].append(r)
                transfer=F(r['own_transfer']) if r['own_transfer'] is not None else 0
                self.assertEqual(F(r['wallet_after']),F(r['wallet_before'])-F(r['voluntary_cost'])-F(r['main_fine'])-F(r['follow_up_fine'])-F(r['forced_retirement_cost'])+transfer)
            for key,rows in grouped.items():
                self.assertEqual(len(rows),6)
                total=sum(r['equipment_after_voluntary'] for r in rows)
                self.assertEqual(total,groups[key]['equipment_total'])
                self.assertEqual(F(groups[key]['group_mean']),F(total,6))
                self.assertEqual(sum(r['final_equipment'] for r in rows),groups[key]['final_equipment_total'])
            for key,rows in paths.items():
                rows.sort(key=lambda r:r['period']);equipment=100;wallet=F(1000)
                for r in rows:
                    self.assertEqual(r['equipment_before'],equipment)
                    self.assertEqual(F(r['wallet_before']),wallet)
                    equipment=r['final_equipment'];wallet=F(r['wallet_after'])
                self.assertEqual(wallet,ledger[key]);self.assertEqual(wallet,F(completions[key]['final_block_wallet']))

    def test_independent_Main_and_policy_reconstruction(self):
        for tables in self.bundles.values():
            groups={r['group_id']:r for r in tables['main_group']}
            grouped=defaultdict(list)
            for r in tables['main']:grouped[r['group_id']].append(r)
            for gid,rows in grouped.items():
                g=groups[gid];ks=[r['equipment_after_voluntary'] for r in rows]
                active=g['treatment']=='F' or sum(ks)<=6*g['threshold']
                if g['treatment']=='F':
                    self.assertIsNone(g['threshold']);self.assertIsNone(g['group_main_enforcement_applied'])
                else:self.assertEqual(g['group_main_enforcement_applied'],active)
                fines=[F(175)+F(k,2) if active and k>0 else F(0) for k in ks]
                self.assertEqual([F(r['main_fine']) for r in rows],fines)
                if g['is_policy']:
                    count=ks.count(0);pool=sum(fines);distributed=F(g['rho'])*pool if count else F(0)
                    self.assertEqual(F(g['fine_pool']),pool)
                    self.assertEqual(g['recipient_count'],count)
                    self.assertEqual(F(g['actual_redistributed_pool']),distributed)
                    expected=[distributed/count if k==0 else F(0) for k in ks]
                    self.assertEqual([F(r['own_transfer']) for r in rows],expected)
                    self.assertEqual(sum(F(r['own_transfer']) for r in rows),distributed)
                    for r,k in zip(rows,ks):
                        self.assertEqual(r['is_policy_recipient'],k==0)
                        self.assertEqual(F(r['wallet_after_main_fine']),F(r['wallet_before_main_fine'])-F(r['main_fine']))
                        self.assertEqual(F(r['wallet_after_policy']),F(r['wallet_after_main_fine'])+F(r['own_transfer']))
                        self.assertEqual(r['wallet_after_policy'],r['wallet_after_main_settlement'])
                else:
                    self.assertTrue(all(g[k] is None for k in ('fine_pool','rho','recipient_count','actual_redistributed_pool')))
                    self.assertTrue(all(r['wallet_before_main_fine'] is None and r['own_transfer'] is None for r in rows))
                    self.assertTrue(all(r['wallet_after_main_fine']==r['wallet_after_main_settlement'] for r in rows))
            self.assertTrue(any(r['is_policy'] and r['recipient_count']==0 and F(r['fine_pool'])>0 and F(r['actual_redistributed_pool'])==0 for r in tables['main_group']))

    def test_independent_Follow_up_and_ledger_consistency(self):
        for key,tables in self.bundles.items():
            session=self.sessions[key]
            people={p.code:p for p in session.get_participants()}
            for row in tables['completion']:
                k=row['pre_forced_equipment']
                self.assertEqual(F(row['follow_up_fine']),75 if k else 0)
                self.assertEqual(row['forced_retirement'],k)
                self.assertEqual(F(row['forced_retirement_cost']),F(1,10)*k*k)
                self.assertEqual(row['final_equipment'],0)
                self.assertEqual(row['final_block_wallet'],people[row['participant_code']].vars[lab_cash.WALLETS_KEY][str(row['global_block'])])
            self.assertTrue(any(r['pre_forced_equipment']>0 and r['final_equipment']==0 for r in tables['completion']))
            self.assertTrue(any(F(r['final_block_wallet'])<0 for r in tables['completion']))

    def test_independent_payment_reconstruction_positive_zero_negative_fractional(self):
        observed=set()
        for tables in self.bundles.values():
            ledger={(r['participant_code'],r['global_block']):F(r['final_block_wallet']) for r in tables['ledger']}
            for row in tables['payment']:
                wallet=ledger[(row['participant_code'],row['paid_block'])]
                self.assertEqual(F(row['selected_wallet']),wallet)
                exact=F(row['fixed_fee'])+F(row['conversion'])*wallet
                # Independent rational rounding: divmod and explicit tie branch.
                quotient,remainder=divmod(abs(exact)*100,1)
                cents=int(quotient)+(1 if remainder>=F(1,2) else 0)
                if exact<0:cents=-cents
                self.assertEqual(F(row['pre_round_eur']),exact)
                self.assertEqual(F(row['variable_eur']),wallet/100)
                self.assertEqual(row['final_eur_cents'],cents)
                self.assertEqual(F(row['final_eur']),F(cents,100))
                self.assertEqual(F(row['admin_cash_eur']),F(cents,100))
                self.assertEqual(F(row['admin_payoff_stored']),cents-800)
                self.assertTrue(row['finalized'])
                observed.add('negative' if wallet<0 else 'zero' if wallet==0 else 'positive')
                if wallet.denominator%3==0:observed.add('policy_fraction')
        self.assertEqual(observed,{'negative','zero','positive','policy_fraction'})

    def test_A_actual_thresholds_match_all_six_external_keys(self):
        for size in (18,24):
            tables=self.bundles[('A',size)]
            thresholds=json.loads(tables['session'][0]['ambiguity_thresholds_json'])
            for row in tables['main_group']:
                if row['global_block']>=4:
                    self.assertEqual(row['threshold'],thresholds[str(row['global_block'])])
                    self.assertTrue(row['threshold_hidden_before_main'])
                else:self.assertIsNone(row['threshold'])
        for branch in ('E','M'):
            self.assertEqual(json.loads(self.bundles[(branch,18)]['session'][0]['ambiguity_thresholds_json']),{})

    def test_M_reports_public_mean_report2_exclusion_and_fresh_blocks(self):
        for size in (18,24):
            tables=self.bundles[('M',size)];grouped=defaultdict(list)
            for r in tables['reports']:grouped[r['group_id']].append(r)
            per_person=defaultdict(list)
            for row in tables['messages']:
                reports=grouped[row['group_id']]
                mean=F(sum(r['report_1'] for r in reports),6)
                self.assertEqual(F(row['public_report_mean']),mean)
                self.assertNotEqual(mean,F(sum(r['report_2'] for r in reports),6))
                for report in reports:per_person[report['participant_code']].append((row['global_block'],mean))
            for values in per_person.values():
                self.assertEqual({b for b,_ in values},set(range(4,10)))
                self.assertEqual(len({m for _,m in values}),6)
            self.assertEqual({r['global_block'] for r in tables['messages']},set(range(4,10)))
        self.assertEqual(self.bundles[('E',18)]['messages'],[])
        self.assertEqual(self.bundles[('A',18)]['messages'],[])

    def test_membership_reconstructs_all_matrices_and_section_pair_counts(self):
        for key,tables in self.bundles.items():
            stored=self.sessions[key].vars[lab_route.MATRICES_KEY]['matrices'];by_block=defaultdict(lambda:defaultdict(list))
            for row in tables['membership']:by_block[row['global_block']][row['group_id']].append(row['participant_code'])
            counts={section:Counter() for section in ('F','Z','P(Z)')}
            reference={section:Counter() for section in counts}
            for block,groups in by_block.items():
                matrix=tuple(sorted(tuple(sorted(g)) for g in groups.values()))
                self.assertEqual(matrix,tuple(tuple(g) for g in stored[str(block)]))
                section=('F','Z','P(Z)')[(block-1)//3]
                for group in matrix:counts[section].update(combinations(group,2))
                for group in stored[str(block)]:reference[section].update(combinations(sorted(group),2))
            self.assertEqual(counts,reference)
            self.assertTrue(all(sum(c.values())==size//6*3*15 for c in counts.values() for size in [key[1]]))

    def test_exports_are_read_only_idempotent_and_do_not_call_economic_helpers(self):
        session=self.sessions[('M',18)]
        before=database_snapshot(session)
        with patch('lab_cash.finalize',side_effect=AssertionError('export finalized payment')), \
             patch('lab_route.select_matching',side_effect=AssertionError('export rematched')), \
             patch('lab_cash.calculate_payment',side_effect=AssertionError('export recalculated cash')), \
             patch('fixed.settle_period',side_effect=AssertionError('export settled F')), \
             patch('lab_threshold.ThresholdSection.settle_period',side_effect=AssertionError('export settled threshold branch')), \
             patch('lab_reports.complete',side_effect=AssertionError('export recomputed a message')):
            first=export.export_session(session,require_complete=True)
            second=export.export_session(session,require_complete=True)
        self.assertEqual(first,second)
        self.assertEqual(first,self.bundles[('M',18)])
        self.assertEqual(before,database_snapshot(session))

    def test_all_native_oTree_export_functions_and_CSV_roundtrips(self):
        session=self.sessions[('A',24)];tables=self.bundles[('A',24)]
        before=database_snapshot(session)
        functions=get_custom_export_functions('lab_payment')
        self.assertEqual(set(functions),{f'custom_export_{table}' for table in export.HEADERS})
        for table in export.HEADERS:
            fp=io.StringIO();custom_export_app('lab_payment',fp,session_code=session.code,function_name=f'custom_export_{table}')
            rows=list(csv.DictReader(io.StringIO(fp.getvalue())))
            self.assertEqual(len(rows),len(tables[table]))
            for source,dest in zip(tables[table],rows):
                for field,value in source.items():
                    self.assertEqual(dest[field],'' if value is None else str(int(value)) if type(value)is bool else str(value))
        with tempfile.TemporaryDirectory(prefix='lab-export-csv-') as temp:
            export.write_csvs(tables,temp)
            self.assertEqual(len(list(Path(temp).glob('*.csv'))),11)
            for table in export.HEADERS:
                with (Path(temp)/f'{export.SCHEMA}_{table}.csv').open(newline='') as fp:rows=list(csv.DictReader(fp))
                self.assertEqual(len(rows),len(tables[table]))
            row=tables['period'][0]
            fp=io.StringIO();csv.writer(fp).writerows(export.csv_rows(tables,'period'))
            imported=list(csv.DictReader(io.StringIO(fp.getvalue())))
            self.assertEqual(imported[0]['voluntary_cost'],row['voluntary_cost'])
        self.assertEqual(before,database_snapshot(session))

    def test_export_refuses_ledger_and_payment_corruption_without_repair(self):
        session=self.sessions[('E',18)];p=lab_payment.Player.objects_filter(session=session).first()
        before=copy.deepcopy(p.participant.vars[lab_cash.WALLETS_KEY])
        p.participant.vars[lab_cash.WALLETS_KEY]={**before,'1':'0/1'}
        with self.assertRaisesRegex(ValueError,'ledger'):export.export_session(session)
        self.assertEqual(p.participant.vars[lab_cash.WALLETS_KEY]['1'],'0/1')
        db.rollback()
        record=copy.deepcopy(p.participant.vars[lab_cash.PAYMENT_KEY])
        p.participant.vars[lab_cash.PAYMENT_KEY]={**record,'final_eur_cents':999}
        with self.assertRaisesRegex(ValueError,'disagrees'):export.export_session(session)


class IncompleteExportTests(unittest.TestCase):
    def tearDown(self):db.rollback()

    def test_initial_partial_and_unfinalized_sessions_are_flagged_without_fabrication(self):
        session=make_session();before=database_snapshot(session)
        tables=export.export_session(session)
        self.assertFalse(tables['session'][0]['complete'])
        self.assertEqual(len(tables['membership']),18)
        self.assertEqual(tables['period'],[]);self.assertEqual(tables['reports'],[])
        self.assertEqual(tables['ledger'],[])
        self.assertTrue(all(not r['finalized'] and r['selected_wallet'] is None for r in tables['payment']))
        self.assertEqual(before,database_snapshot(session))
        with self.assertRaisesRegex(ValueError,'Incomplete'):export.export_session(session,require_complete=True)
        ready(session);app=app_for(session,1);group=lab_route.block_subsession(session,1).get_groups()[0]
        for p in group.get_players()[:5]:
            p.expected_own_equipment_main=10;p.expected_group_average_main=20
            app.Reports.before_next_page(p,False)
        tables=export.export_session(session)
        self.assertEqual(len(tables['reports']),5);self.assertFalse(any(r['group_reports_complete'] for r in tables['reports']))
        self.assertEqual(tables['period'],[])
        p=group.get_players()[5];p.expected_own_equipment_main=10;p.expected_group_average_main=20
        app.Reports.before_next_page(p,False);app.ReportsWait.after_all_players_arrive(group)
        settle(app,group)
        tables=export.export_session(session)
        self.assertEqual(len(tables['period']),6);self.assertEqual(len(tables['group_period']),1)
        self.assertEqual(tables['completion'],[])

    def test_custom_header_empty_input_and_dedup_session_inputs(self):
        self.assertEqual(list(export.custom_rows([], 'period')),[list(export.HEADERS['period'])])
        session=make_session();players=list(lab_payment.Player.objects_filter(session=session))
        rows=list(export.custom_rows(players+players,'session'))
        self.assertEqual(len(rows),2)

    def test_legacy_source_is_not_an_export_dependency(self):
        source=Path('lab_export.py').read_text()
        for term in ('research_export','simulated_environment','lab_presentation','from payment import'):
            self.assertNotIn(term,source)


if __name__=='__main__':unittest.main()
