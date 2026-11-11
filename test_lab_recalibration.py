"""Authoritative calibration benchmarks; run with the isolated oTree test harness."""
from fractions import Fraction as F
import json
import unittest

import test_fixed
from otree.database import db
import lab_cash as cash
import lab_rules as rules
from lab_config import validate_lab_config
from lab_policy import redistribute
from lab_persistence import decode_fraction
from test_lab_cash import wallets
from test_lab_config import configuration


class CalibrationBenchmarks(unittest.TestCase):
    def test_constants_and_cost_examples(self):
        self.assertEqual((rules.K0, rules.W0, rules.T, rules.PERIODS_PER_BLOCK), (100, 1000, 5, 10))
        self.assertEqual((rules.COST_FACTOR, rules.KNOWN_THRESHOLD, rules.FOLLOW_UP_FINE), (F(1,10), 37, 75))
        for d, cost in [(0,0),(1,F(1,10)),(10,10),(20,40),(25,F(125,2)),(50,250),(100,1000)]:
            self.assertEqual(rules.retirement_cost(d), cost)
        self.assertEqual(2 * rules.retirement_cost(10), 20)
        self.assertEqual(rules.main_fine(50),200)
        self.assertEqual(rules.main_fine(100),225)

    def test_active_comprehension_calibration_and_keys(self):
        from lab_printed_questions import PRINTED_QUESTIONS
        by_id = {section: {q['id']: q for q in rows}
                 for section, rows in PRINTED_QUESTIONS.items()}
        self.assertEqual({k: len(v) for k, v in by_id.items()},
                         {'F': 6, 'E': 4, 'A': 4, 'M': 4, 'P': 4})
        cost = by_id['F']['period_cost']
        self.assertIn('0,10', cost['feedback'])
        self.assertIn('20 punti in totale', cost['feedback'])
        self.assertIn('40 punti', cost['feedback'])
        final = by_id['F']['follow_up']
        self.assertIn('75 punti', dict(final['options'])[final['correct']])
        self.assertIn('0,10 × unità rimanenti²', final['feedback'])
        for branch in ('E', 'M'):
            for item in ('known', 'equality'):
                self.assertIn('37 unità', by_id[branch][item]['prompt'])
            self.assertIn('con 0 unità non', dict(by_id[branch]['equality']['options'])[by_id[branch]['equality']['correct']])
        support = by_id['A']['support']
        self.assertIn('33 e 42', dict(support['options'])[support['correct']])
        self.assertIn('né la probabilità', dict(support['options'])[support['correct']])

    def test_threshold_benchmarks_all_supported_thresholds(self):
        # Six late, then five, four, three late firms (others at zero).
        for late, em_enforced, safe_a in [(6,False,range(33,43)),(5,False,range(33,42)),
                                         (4,True,[33]),(3,True,[])]:
            total=late*50
            for branch in 'EM':
                self.assertEqual(rules.main_enforcement_applies(branch,group_total=total),em_enforced)
            for threshold in range(33,43):
                self.assertEqual(rules.main_enforcement_applies('A',group_total=total,
                                  ambiguity_threshold=threshold), threshold not in safe_a)
        for branch in 'EM':
            for total, enforced in [(221,True),(222,True),(223,False)]:
                self.assertEqual(rules.main_enforcement_applies(branch,group_total=total),enforced)
        for threshold in range(33,43):
            self.assertTrue(rules.main_enforcement_applies('A',group_total=6*threshold,ambiguity_threshold=threshold))

    def test_external_support_and_missing_blocks_fail_closed(self):
        for threshold in (33,42):
            c=configuration('A',ambiguity_thresholds={str(i):threshold for i in range(4,10)})
            self.assertEqual(validate_lab_config(c)['ambiguity_thresholds'],c['ambiguity_thresholds'])
        for missing in range(4,10):
            c=configuration('A');del c['ambiguity_thresholds'][str(missing)]
            with self.assertRaisesRegex(ValueError,'ambiguity_thresholds'):validate_lab_config(c)
        for invalid in (32,43,33.0,42.0,True,'40',None):
            c=configuration('A');c['ambiguity_thresholds']['4']=invalid
            with self.assertRaisesRegex(ValueError,'ambiguity_thresholds'):validate_lab_config(c)

    def test_worst_wallet_over_all_feasible_integer_paths_without_floor(self):
        # Dynamic programming retains the smallest wallet for every equipment
        # state. F enforces irrespective of peers; other branches cannot charge
        # more and Policy only adds nonnegative transfers.
        states={100:F(1000)}
        for period in range(1,11):
            next_states={}
            for equipment,wallet in states.items():
                for d in range(equipment+1):
                    remaining=rules.equipment_after_retirement(equipment,d)
                    value=wallet-rules.retirement_cost(d)
                    if period==5:value-=rules.main_fine(remaining)
                    if period==10:
                        follow=rules.follow_up_enforcement(remaining)
                        value-=follow.follow_up_fine+follow.forced_retirement_cost
                        remaining=follow.final_equipment
                    next_states[remaining]=min(value,next_states.get(remaining,value))
            states=next_states
        self.assertEqual(states,{0:F(-300)})
        self.assertEqual(cash.calculate_payment(wallets(-300),1)['final_eur_cents'],500)
        # Below-feasible and above-feasible inputs prove no hidden floor/cap;
        # every integer experimental point has the same one-cent slope.
        for wallet in range(-400,2001):
            self.assertEqual(cash.calculate_payment(wallets(wallet),1)['final_eur_cents'],800+wallet)

    def test_policy_main_only_and_configured_share(self):
        for rho in (F(0),F(3,10),F(1,3),F(1,2),F(1)):
            result=redistribute([0,0,50,50,50,50],[0,0,200,200,200,200],rho)
            self.assertEqual(result.fine_pool,800)
            self.assertEqual(result.transfers,(400*rho,400*rho,0,0,0,0))
        self.assertEqual(redistribute([0,100,100,100,100,100],[0]*6,F(1,3)).redistributed_pool,0)
        self.assertEqual(redistribute([50]*6,[200]*6,F(1,3)).redistributed_pool,0)
        # 275 here deliberately mixes 200 Main + 75 Follow-up: reject it.
        with self.assertRaises(ValueError):redistribute([0,0,50,50,50,50],[0,0,275,275,275,275],F(1,3))


class ActualSettlementBenchmarks(unittest.TestCase):
    def tearDown(self):db.rollback()

    def path(self, module, helpers, decisions):
        session=helpers.make_session();helpers.ready(session)
        for period,d in enumerate(decisions,1):
            group=helpers.subsession(session,period).get_groups()[0]
            helpers.run_period(group,[d]*6)
        p=group.get_players()[0]
        return p

    def test_early_late_and_worst_through_real_group_settlement(self):
        import fixed, endogenous, test_endogenous
        cases=[(fixed,test_fixed,[20]*5+[0]*5,200,0,800,1600),
               (endogenous,test_endogenous,[10]*10,100,0,900,1700),
               (fixed,test_fixed,[10]*10,100,200,700,1500),
               (fixed,test_fixed,[0]*10,0,225,-300,500)]
        for app,helpers,decisions,cost,fine,wallet,cents in cases:
            with self.subTest(app=app.__name__,decisions=decisions):
                p=self.path(app,helpers,decisions)
                self.assertEqual(sum(decode_fraction(q.voluntary_cost) for q in p.in_all_rounds()[:10]),cost)
                self.assertEqual(decode_fraction(p.in_round(5).main_fine),fine)
                self.assertEqual(decode_fraction(p.final_block_wallet),wallet)
                self.assertEqual(cash.calculate_payment(wallets(wallet),1)['final_eur_cents'],cents)
                self.assertEqual(p.final_equipment,0)

    def test_every_app_preview_uses_same_coefficient(self):
        import fixed, endogenous, ambiguity, messages, policy
        import test_endogenous, test_ambiguity, test_messages, test_policy
        for app,helpers in [(fixed,test_fixed),(endogenous,test_endogenous),(ambiguity,test_ambiguity),
                            (messages,test_messages),(policy,test_policy)]:
            session=helpers.make_session();helpers.ready(session)
            group=helpers.subsession(session).get_groups()[0];helpers.reports(group)
            config=json.loads(app.Decision.vars_for_template(group.get_players()[0])['chart_config_json'])
            self.assertEqual(config['costMilliPoints'],100)
            for d in range(101):
                self.assertEqual(F(config['costMilliPoints']*d*d,1000),rules.retirement_cost(d))

    def test_policy_questions_follow_configured_rho(self):
        import test_policy, lab_instructions
        for rho in (F(3,10),F(1,3),F(1,2),F(0),F(1)):
            session=test_policy.make_session(rho=rho)
            p=test_policy.subsession(session).get_players()[0]
            questions=lab_instructions.questions(p)
            self.assertEqual(len(questions),4)
            self.assertIn(questions[2]['correct'], dict(questions[2]['options']))
            expected=720*rho/2
            self.assertIn(str(int(expected)),dict(questions[2]['options'])[questions[2]['correct']])


class NativeRouteSmoke(unittest.TestCase):
    def tearDown(self):
        db.rollback()

    @unittest.skipUnless(__import__('pathlib').Path('policy/tests.py').is_file(), 'Deployment snapshot omits policy bots; native HTTP full route is tested separately.')
    def test_complete_E18_native_route_including_bucket_survey_payment(self):
        from test_lab_production import make_production_session
        from otree.bots.runner import run_bots
        session = make_production_session('E', 18)
        db.commit()
        run_bots(session.id)
        db.expire_all()
        for participant in session.get_participants():
            self.assertEqual(participant._current_app_name, 'lab_payment')
            self.assertEqual(len(participant.vars[cash.WALLETS_KEY]), 9)
            record = participant.vars[cash.PAYMENT_KEY]
            self.assertEqual(record['fixed_fee'], '8/1')
            self.assertEqual(record['bucket_payoff_cents'], 250)
            self.assertEqual(record['final_eur_cents'], cash.euro_cents(
                F(8) + decode_fraction(record['selected_wallet']) / 100 + F(5, 2)))
