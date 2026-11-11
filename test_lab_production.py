"""Production contracts and real oTree creation; run in a disposable DEV/EUR test process.

Deployment guards are independently tested with explicit fake environments, never
bypassed in actual production startup. Full bots use these same templates with
explicit test study values through oTree's supported creation override API.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_fixed
from otree.database import db
from otree.session import create_session, get_session_configs_dict, SESSION_CONFIGS_DICT
from otree import settings
from otree.export import get_rows_for_wide_csv
import lab_production as production
import lab_route


TEST_THRESHOLDS = {'4':33,'5':41,'6':41,'7':38,'8':42,'9':40}


def parameters(branch, size, *, paid_block=9):
    value=dict(paid_block=paid_block, matching_seed=f'test-production-{branch}-{size}',
               rho=0.3,rho_exact='3/10', triplet_id='test-triplet',recruitment_batch='test-batch')
    if branch=='A': value['ambiguity_thresholds']=dict(TEST_THRESHOLDS)
    return value


def configured(branch='E', size=18):
    value=next(c for c in production.templates() if c['name']==f'lab_{branch}_{size}')
    value.update(parameters(branch,size))
    return value


def register_templates():
    # All app models are already registered by the explicit DEV test profile.
    SESSION_CONFIGS_DICT.update(get_session_configs_dict(production.templates(), {}))


def make_production_session(branch='E', size=18, **overrides):
    register_templates()
    return create_session(f'lab_{branch}_{size}',num_participants=size,
                          modified_session_config_fields={**parameters(branch,size),**overrides})


class ProductionConfigTests(unittest.TestCase):
    def tearDown(self): db.rollback()

    def test_six_templates_exact_routes_sizes_and_no_launch_placeholders(self):
        ts=production.templates()
        self.assertEqual({c['name'] for c in ts},{f'lab_{b}_{n}' for b in 'EAM' for n in (18,24)})
        for c in ts:
            self.assertEqual(c['lab_session_size'],c['num_demo_participants'])
            self.assertEqual(c['app_sequence'],lab_route.payment_sequence(c['branch']))
            self.assertIsNone(c['paid_block']);self.assertIsNone(c['matching_seed'])
            self.assertEqual(c['ambiguity_thresholds'],{})
            self.assertEqual((c['real_world_currency_per_point'],c['participation_fee']),(0.01,8.0))
            self.assertNotIn('dev',c['display_name'].lower())
            with self.assertRaisesRegex(ValueError,'explicit paid_block'):production.validate_config(c)
            c.update(parameters(c['branch'],c['lab_session_size']))
            self.assertEqual(production.validate_config(c)['lab_design_version'],production.DESIGN_VERSION)

    def test_paid_seed_rho_and_threshold_misconfiguration(self):
        for key in ('paid_block','matching_seed','rho','rho_exact'):
            c=configured();del c[key]
            with self.subTest(key=key),self.assertRaises(ValueError):production.validate_config(c)
        for b in (True,'1',1.0,0,10):
            c=configured();c['paid_block']=b
            with self.assertRaises(ValueError):production.validate_config(c)
        for rho,exact in [(0.5,'1/3'),(float('nan'),'1/3'),(float('inf'),'1/3'),(-1,'-1/1')]:
            c=configured();c.update(rho=rho,rho_exact=exact)
            with self.assertRaises(ValueError):production.validate_config(c)
        for change in ('missing','extra','bool','float','low','high'):
            c=configured('A');m=c['ambiguity_thresholds']
            if change=='missing':del m['7']
            if change=='extra':m['10']=37
            if change=='bool':m['7']=True
            if change=='float':m['7']=37.0
            if change=='low':m['7']=32
            if change=='high':m['7']=48
            with self.subTest(change=change),self.assertRaises(ValueError):production.validate_config(c)
        for branch in ('E','M'):
            c=configured(branch);c['ambiguity_thresholds']={'4':37}
            with self.assertRaisesRegex(ValueError,'empty or omitted'):production.validate_config(c)

    def test_production_share_defaults_to_thirty_percent_but_is_configurable(self):
        for branch in 'EAM':
            for size in (18, 24):
                self.assertEqual(production.validate_config(configured(branch, size))['rho_exact'], '3/10')
                for rho, exact in [(0, '0/1'), (0.5, '1/2'), (1, '1/1')]:
                    config = configured(branch, size)
                    config.update(rho=rho, rho_exact=exact)
                    with self.subTest(branch=branch, size=size, rho=exact):
                        self.assertEqual(production.validate_config(config)['rho_exact'], exact)

    def test_route_branch_size_version_fee_and_fixed_constants(self):
        for key,value in [('branch','A'),('lab_session_size',24),('num_demo_participants',24),
                          ('app_sequence',['fixed','ambiguity','policy','lab_payment']),
                          ('app_sequence',['fixed']),('lab_design_version','old'),
                          ('real_world_currency_per_point',0),('participation_fee',0),
                          ('T',10),('cost_factor',0.05),('starting_points',500),
                          ('threshold',45),('section1_num_blocks',2),('group_size',1),('lab_production',False)]:
            c=configured();c[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):production.validate_config(c)
        with self.assertRaisesRegex(ValueError,'EUR'):production.validate_config(configured(),currency='GBP')
        with patch.object(production.rules,'MAIN_CHECK_PERIOD',10):
            with self.assertRaisesRegex(ValueError,'Executable laboratory constants'):
                production.validate_config(configured())

    def test_external_JSON_and_rejection_of_unknown_duplicate_and_unsafe_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp,'study.json')
            original={'lab_A_18':parameters('A',18)};p.write_text(json.dumps(original))
            cs=production.load_templates(p)
            a=next(c for c in cs if c['name']=='lab_A_18')
            self.assertEqual(a['ambiguity_thresholds'],TEST_THRESHOLDS)
            self.assertIsNone(next(c for c in cs if c['name']=='lab_E_24')['paid_block'])
            for text in ('{"lab_E_18":{"paid_block":1,"paid_block":2}}','{"unknown":{}}',
                         '{"lab_E_18":{"branch":"A"}}','{"lab_A_18":{"paid_block":9,"matching_seed":"s"}}'):
                p.write_text(text)
                with self.assertRaises(ValueError):production.load_templates(p)
            self.assertEqual(original,{'lab_A_18':parameters('A',18)})

    def test_runtime_guards_no_memory_or_SQLite_and_no_credentials_in_errors(self):
        env=dict(OTREE_LAB_PAYMENTS='1',OTREE_PRODUCTION='1',OTREE_AUTH_LEVEL='STUDY',
                 DATABASE_URL='postgresql://test-user:never-print-me@db.example/lab',
                 OTREE_ADMIN_PASSWORD='test-only-password',OTREE_SECRET_KEY='test-only-secret-'*3)
        args=dict(python_version=(3,12,6),otree_version='6.0.15',driver_available=True)
        production.validate_runtime(env,**args)
        for field in env:
            c={**env};c.pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError) as exc:production.validate_runtime(c,**args)
            self.assertNotIn('never-print-me',str(exc.exception))
        for updates in ({'DATABASE_URL':'sqlite:///db.sqlite3'},{'OTREE_IN_MEMORY':'1'},
                        {'OTREE_IN_MEMORY':'0'},{'OTREE_SECRET_KEY':'short'}):
            with self.assertRaises(ValueError):production.validate_runtime({**env,**updates},**args)
        for changes in ({'python_version':(3,13,0)},{'otree_version':'6.1'},{'driver_available':False}):
            with self.assertRaises(ValueError):production.validate_runtime(env,**{**args,**changes})

    def test_settings_modes_are_separate_and_default_production_calls_runtime_guard(self):
        # settings itself does not initialize oTree or create a DB.
        for mode in ('development','legacy'):
            env={**os.environ,'OTREE_CONFIG_MODE':mode,'OTREE_LAB_PAYMENTS':'0'}
            output=subprocess.check_output([sys.executable,'-B','-c',
                'import json,settings; print(json.dumps([c["name"] for c in settings.SESSION_CONFIGS]))'],env=env,text=True)
            names=json.loads(output)
            self.assertTrue(all(n.startswith('dev_lab_')==(mode=='development') for n in names))
            self.assertEqual(len(names),20 if mode=='development' else 12)
        import runpy
        with patch.dict(os.environ,{'OTREE_CONFIG_MODE':'production'},clear=False),patch('lab_production.validate_runtime') as guard:
            data=runpy.run_path('settings.py')
            guard.assert_called_once()
            self.assertEqual({c['name'] for c in data['SESSION_CONFIGS']},{c['name'] for c in production.templates()})
            self.assertEqual(data['SESSION_CONFIG_DEFAULTS']['participation_fee'],8.0)

    def test_actual_creation_requires_parameters_exact_count_EUR_and_persists_metadata(self):
        register_templates()
        for size in (6,12,24,30):
            with self.assertRaisesRegex(ValueError,'Configured session size'):
                create_session('lab_E_18',num_participants=size,
                               modified_session_config_fields=parameters('E',18))
            db.rollback()
        with self.assertRaisesRegex(ValueError,'explicit paid_block'):
            create_session('lab_E_18',num_participants=18)
        db.rollback()
        with patch.object(settings,'REAL_WORLD_CURRENCY_CODE','GBP'):
            with self.assertRaisesRegex(ValueError,'EUR'):make_production_session()
        db.rollback()
        for branch in ('E','A','M'):
            for size in (18,24):
                session=make_production_session(branch,size)
                state=session.vars[production.PRODUCTION_KEY]
                self.assertEqual((state['branch'],state['size'],state['rho']),(branch,size,'3/10'))
                self.assertEqual(state['design_version'],production.DESIGN_VERSION)
                rows=get_rows_for_wide_csv(session.code)
                self.assertIn('session.config.lab_design_version',rows[0])
                self.assertEqual(rows[1][rows[0].index('session.config.lab_design_version')],production.DESIGN_VERSION)
                self.assertIn('session.config.triplet_id',rows[0])
                p=lab_route.block_subsession(session,1).get_players()[0]
                import lab_instructions
                context=lab_instructions.context(p)
                for field in ('paid_block','matching_seed','triplet_id','ambiguity_thresholds','lab_design_version'):
                    self.assertNotIn(field,context)

    def test_room_seats_process_and_local_assets(self):
        for n in (18,24):
            labels=Path(f'_rooms/lab_{n}.txt').read_text().splitlines()
            self.assertEqual(labels,[f'S{i:02d}' for i in range(1,n+1)])
            room=next(c for c in settings.ROOMS if c['name']==f'lab_{n}')
            self.assertFalse(room['use_secure_urls'])
        self.assertEqual(Path('Procfile').read_text().strip(),'web: otree prodserver')
        self.assertEqual(Path('.python-version').read_text().strip(),'3.12.6')
        for app in ('fixed','endogenous','ambiguity','messages','policy','lab_payment'):
            for p in Path(app).glob('*.html'):
                self.assertNotRegex(p.read_text(),r'(?:src|href)=["\']https?://')
        for p in Path('general_instructions').glob('Lab*.html'):
            self.assertNotIn('cdn.',p.read_text())

if __name__=='__main__':unittest.main()
