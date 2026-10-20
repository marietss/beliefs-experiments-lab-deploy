"""Production templates, explicit study parameter loading and launch validation.

No experimental arithmetic, random draws, credentials, database connection or
participant rendering. Six templates intentionally cannot launch until external
paid_block/matching_seed (and A thresholds) are supplied. oTree's API may also
supply these editable config values before creating_session.
"""
from collections.abc import Mapping
from fractions import Fraction
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from lab_config import validate_lab_config
from lab_policy import configured_rho
from lab_persistence import encode_fraction
import lab_rules as rules

DESIGN_VERSION = 'lab_design_v1'
RUNTIME_PYTHON = (3, 12, 6)
PRODUCTION_KEY = 'lab_production_config_v1'
BRANCH_APPS = {'E': 'endogenous', 'A': 'ambiguity', 'M': 'messages'}
PARAMETERS = frozenset(('paid_block', 'matching_seed', 'rho', 'rho_exact',
                        'ambiguity_thresholds', 'triplet_id', 'recruitment_batch'))


def templates():
    return [dict(name=f'lab_{branch}_{size}', display_name=f'LAB {branch} — {size} participants',
                 lab_production=True, lab_design_version=DESIGN_VERSION,
                 lab_session_size=size, num_demo_participants=size, branch=branch,
                 paid_block=None, matching_seed=None, rho=1/3, rho_exact='1/3',
                 ambiguity_thresholds={}, triplet_id='', recruitment_batch='',
                 T=5, real_world_currency_per_point=0.01, participation_fee=7.50,
                 exchange_rate_text='', completion_code='',
                 app_sequence=['fixed', BRANCH_APPS[branch], 'policy', 'lab_payment'])
            for branch in BRANCH_APPS for size in (18, 24)]


def is_production(config):
    # A changed/removed marker must not let a production name bypass validation.
    return bool(config.get('lab_production')) or str(config.get('name', '')).startswith('lab_')


def validate_config(config, *, currency='EUR', use_points=True):
    name = config.get('name')
    expected = {c['name']: c for c in templates()}.get(name)
    if expected is None or config.get('lab_production') is not True:
        raise ValueError('Use one of the six production lab templates with lab_production=True.')
    if config.get('paid_block') is None:
        raise ValueError('Production lab session requires explicit paid_block 1–9 before creation.')
    if config.get('matching_seed') is None:
        raise ValueError('Production lab session requires explicit matching_seed before creation.')
    if config.get('branch') == 'A' and not config.get('ambiguity_thresholds'):
        raise ValueError('A production session requires ambiguity thresholds for Blocks 4–9.')
    result = validate_lab_config(config)
    for key in ('branch', 'lab_session_size', 'num_demo_participants', 'app_sequence', 'lab_design_version'):
        if result.get(key) != expected[key] or (key.endswith('size') or key == 'num_demo_participants') and type(result[key]) is not int:
            raise ValueError(f'Production {name} requires its configured {key}: {expected[key]}.')
    if currency != 'EUR' or use_points is not True:
        raise ValueError('Lab production route requires EUR payment mode and points.')
    if 'rho_exact' not in result:
        raise ValueError('Production rho requires a consistent canonical rho_exact companion.')
    configured_rho(result)  # exact companion must agree; never approximate thirds
    from lab_cash import config_snapshot
    config_snapshot(result)  # unchanged fee/rate contract, including Currency types
    # Reject inconsistent obsolete aliases even though the lab engine ignores them.
    constants = dict(K0=100, initial_capital=100, initial_equipment=100,
                     W0=1000, starting_points=1000, starting_wallet=1000, T=5,
                     periods_per_block=10, blocks_per_section=3, total_blocks=9,
                     rounds_per_app=30, main_check_period=5, follow_up_period=10,
                     players_per_group=6, group_size=6, cost_factor=Fraction(3,40),
                     threshold=45, comparison_value=45, final_penalty_points=275,
                     main_fine_base=175, main_fine_per_unit=Fraction(1,2),
                     follow_up_fine=275, ambiguity_threshold_low=40, ambiguity_threshold_high=50,
                     section1_num_blocks=3, section2_num_blocks=3, section3_num_blocks=3)
    for key, expected_value in constants.items():
        if key in result:
            value=result[key]
            try: valid=not isinstance(value,bool) and Fraction(str(value))==expected_value
            except (ValueError,TypeError,ZeroDivisionError): valid=False
            if not valid: raise ValueError(f'Production fixed laboratory constant {key} must be {expected_value}.')
    # Assert the engine's fixed constants, rather than importing old defaults.
    if (rules.K0,rules.W0,rules.T,rules.PERIODS_PER_BLOCK,rules.BLOCKS_PER_SECTION,
        rules.TOTAL_BLOCKS,rules.GROUP_SIZE,rules.COST_FACTOR,rules.KNOWN_THRESHOLD,
        rules.AMBIGUITY_THRESHOLD_LOW,rules.AMBIGUITY_THRESHOLD_HIGH,rules.FOLLOW_UP_FINE,
        rules.MAIN_FINE_BASE,rules.MAIN_FINE_PER_UNIT,rules.ROUNDS_PER_APP,
        rules.MAIN_CHECK_PERIOD,rules.FOLLOW_UP_PERIOD) != (
            100,1000,5,10,3,9,6,Fraction(3,40),45,40,50,275,175,Fraction(1,2),30,5,10):
        raise ValueError('Executable laboratory constants differ from the production design version.')
    for key in ('triplet_id','recruitment_batch'):
        if not isinstance(result.get(key,''),str):
            raise ValueError(f'{key} must be optional server-only text.')
    return result


def load_templates(filename=None):
    configs={c['name']:c for c in templates()}
    if filename:
        def unique_object(pairs):
            obj={}
            for key,value in pairs:
                if key in obj: raise ValueError('Duplicate key in production parameter file.')
                obj[key]=value
            return obj
        try:
            data=json.loads(Path(filename).read_text(),object_pairs_hook=unique_object)
        except (OSError,UnicodeError,json.JSONDecodeError):
            raise ValueError('Cannot read the production JSON parameter file; check its path and format.') from None
        if not isinstance(data,dict) or set(data)-set(configs):
            raise ValueError('Production parameter file must map known lab config names to parameter objects.')
        for name,values in data.items():
            if not isinstance(values,dict) or set(values)-PARAMETERS:
                raise ValueError(f'Unsupported production parameter fields for {name}.')
            configs[name].update(values)
            validate_config(configs[name])
    return list(configs.values())


def validate_runtime(env, *, python_version=None, otree_version=None, driver_available=None):
    """Fail before the production server can start; no credentials in errors."""
    if env.get('OTREE_LAB_PAYMENTS')!='1':
        raise ValueError('Lab production startup requires OTREE_LAB_PAYMENTS=1 (EUR).')
    if env.get('OTREE_IN_MEMORY'):
        raise ValueError('Production collection forbids OTREE_IN_MEMORY; use persistent PostgreSQL.')
    try:
        url=urlsplit(env.get('DATABASE_URL',''))
        valid_db=url.scheme in ('postgres','postgresql','postgresql+psycopg2') and bool(url.hostname and url.path.strip('/'))
    except ValueError: valid_db=False
    if not valid_db:
        raise ValueError('Production DATABASE_URL must identify a persistent PostgreSQL database.')
    if env.get('OTREE_PRODUCTION')!='1' or env.get('OTREE_AUTH_LEVEL')!='STUDY':
        raise ValueError('Production requires OTREE_PRODUCTION=1 and OTREE_AUTH_LEVEL=STUDY.')
    if not env.get('OTREE_ADMIN_PASSWORD','').strip():
        raise ValueError('Production requires an environment-provided OTREE_ADMIN_PASSWORD.')
    if len(env.get('OTREE_SECRET_KEY',''))<32:
        raise ValueError('Production requires OTREE_SECRET_KEY of at least 32 characters.')
    if tuple(python_version or sys.version_info[:3]) != RUNTIME_PYTHON:
        raise ValueError('Supported production Python is 3.12.6; use the tested runtime.')
    if (otree_version or importlib.metadata.version('otree')) != '6.0.15':
        raise ValueError('Production requires the tested otree==6.0.15.')
    if driver_available is None: driver_available=importlib.util.find_spec('psycopg2') is not None
    if not driver_available:
        raise ValueError('Production requires the psycopg2 PostgreSQL driver from requirements.txt.')


def validate_session(subsession):
    from otree import settings
    session=subsession.session
    config=validate_config(session.config,currency=settings.REAL_WORLD_CURRENCY_CODE,use_points=settings.USE_POINTS)
    expected=config['lab_session_size']
    if (session.num_participants!=expected or len(session.get_participants())!=expected
            or len(subsession.get_players())!=expected):
        raise ValueError(f'Configured session size {expected} does not match created participant count {session.num_participants}.')
    snapshot=dict(design_version=DESIGN_VERSION, config_name=config['name'],
                  branch=config['branch'], size=expected, paid_block=config['paid_block'],
                  matching_seed=config['matching_seed'], rho=encode_fraction(configured_rho(config)),
                  ambiguity_thresholds=dict(config['ambiguity_thresholds']),
                  triplet_id=config.get('triplet_id',''), recruitment_batch=config.get('recruitment_batch',''))
    prior=session.vars.get(PRODUCTION_KEY)
    if prior is not None and prior!=snapshot:
        raise ValueError('Production study parameters changed after initialization.')
    if prior is None: session.vars[PRODUCTION_KEY]=snapshot
