from os import environ

RETAINED_CONFIGS = [
    # Integrated DEV ONLY regression routes; production templates are selected below.
    dict(
        name='dev_lab_full_E_18', display_name='DEV ONLY: full lab E (18)',
        num_demo_participants=18, lab_session_size=18, branch='E',
        paid_block=9, rho=0.3, rho_exact='3/10', matching_seed='dev-full-E-18-v1',
        T=5, real_world_currency_per_point=0.01, participation_fee=8.00,
        exchange_rate_text='', app_sequence=['fixed', 'endogenous', 'policy', 'bucket', 'survey', 'lab_payment'],
    ),
    dict(
        name='dev_lab_full_E_24', display_name='DEV ONLY: full lab E (24)',
        num_demo_participants=24, lab_session_size=24, branch='E',
        paid_block=9, rho=0.3, rho_exact='3/10', matching_seed='dev-full-E-24-v1',
        T=5, real_world_currency_per_point=0.01, participation_fee=8.00,
        exchange_rate_text='', app_sequence=['fixed', 'endogenous', 'policy', 'bucket', 'survey', 'lab_payment'],
    ),
    dict(
        name='dev_lab_full_A_18', display_name='DEV ONLY: full lab A (18)',
        num_demo_participants=18, lab_session_size=18, branch='A',
        paid_block=9, rho=0.3, rho_exact='3/10', matching_seed='dev-full-A-18-v1',
        ambiguity_thresholds={'4': 42, '5': 33, '6': 41, '7': 42, '8': 40, '9': 33},
        T=5, real_world_currency_per_point=0.01, participation_fee=8.00,
        exchange_rate_text='', app_sequence=['fixed', 'ambiguity', 'policy', 'bucket', 'survey', 'lab_payment'],
    ),
    dict(
        name='dev_lab_full_A_24', display_name='DEV ONLY: full lab A (24)',
        num_demo_participants=24, lab_session_size=24, branch='A',
        paid_block=9, rho=0.3, rho_exact='3/10', matching_seed='dev-full-A-24-v1',
        ambiguity_thresholds={'4': 42, '5': 33, '6': 41, '7': 42, '8': 40, '9': 33},
        T=5, real_world_currency_per_point=0.01, participation_fee=8.00,
        exchange_rate_text='', app_sequence=['fixed', 'ambiguity', 'policy', 'bucket', 'survey', 'lab_payment'],
    ),
    dict(
        name='dev_lab_full_M_18', display_name='DEV ONLY: full lab M (18)',
        num_demo_participants=18, lab_session_size=18, branch='M',
        paid_block=9, rho=0.3, rho_exact='3/10', matching_seed='dev-full-M-18-v1',
        T=5, real_world_currency_per_point=0.01, participation_fee=8.00,
        exchange_rate_text='', app_sequence=['fixed', 'messages', 'policy', 'bucket', 'survey', 'lab_payment'],
    ),
    dict(
        name='dev_lab_full_M_24', display_name='DEV ONLY: full lab M (24)',
        num_demo_participants=24, lab_session_size=24, branch='M',
        paid_block=9, rho=0.3, rho_exact='3/10', matching_seed='dev-full-M-24-v1',
        T=5, real_world_currency_per_point=0.01, participation_fee=8.00,
        exchange_rate_text='', app_sequence=['fixed', 'messages', 'policy', 'bucket', 'survey', 'lab_payment'],
    ),
    # Standalone policy development only; exact rho, no payment/handoff.
    dict(
        name='dev_lab_policy_E_18', display_name='DEV ONLY: lab P(E) (18)',
        num_demo_participants=18, lab_session_size=18, branch='E',
        paid_block=7, rho=0.3, rho_exact='3/10', matching_seed='dev-policy-E-18-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['policy'],
    ),
    dict(
        name='dev_lab_policy_E_24', display_name='DEV ONLY: lab P(E) (24)',
        num_demo_participants=24, lab_session_size=24, branch='E',
        paid_block=7, rho=0.3, rho_exact='3/10', matching_seed='dev-policy-E-24-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['policy'],
    ),
    dict(
        name='dev_lab_policy_A_18', display_name='DEV ONLY: lab P(A) (18)',
        num_demo_participants=18, lab_session_size=18, branch='A',
        paid_block=7, rho=0.3, rho_exact='3/10', matching_seed='dev-policy-A-18-v1',
        ambiguity_thresholds={'4': 42, '5': 33, '6': 41, '7': 42, '8': 40, '9': 33},
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['policy'],
    ),
    dict(
        name='dev_lab_policy_A_24', display_name='DEV ONLY: lab P(A) (24)',
        num_demo_participants=24, lab_session_size=24, branch='A',
        paid_block=7, rho=0.3, rho_exact='3/10', matching_seed='dev-policy-A-24-v1',
        ambiguity_thresholds={'4': 42, '5': 33, '6': 41, '7': 42, '8': 40, '9': 33},
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['policy'],
    ),
    dict(
        name='dev_lab_policy_M_18', display_name='DEV ONLY: lab P(M) (18)',
        num_demo_participants=18, lab_session_size=18, branch='M',
        paid_block=7, rho=0.3, rho_exact='3/10', matching_seed='dev-policy-M-18-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['policy'],
    ),
    dict(
        name='dev_lab_policy_M_24', display_name='DEV ONLY: lab P(M) (24)',
        num_demo_participants=24, lab_session_size=24, branch='M',
        paid_block=7, rho=0.3, rho_exact='3/10', matching_seed='dev-policy-M-24-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['policy'],
    ),
    # Standalone M development only: no cash payment or cross-app handoff.
    dict(
        name='dev_lab_messages_18', display_name='DEV ONLY: lab M (18)',
        num_demo_participants=18, lab_session_size=18,
        branch='M', paid_block=4, rho=0.3, rho_exact='3/10', matching_seed='dev-messages-18-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['messages'],
    ),
    dict(
        name='dev_lab_messages_24', display_name='DEV ONLY: lab M (24)',
        num_demo_participants=24, lab_session_size=24,
        branch='M', paid_block=4, rho=0.3, rho_exact='3/10', matching_seed='dev-messages-24-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['messages'],
    ),
    # Standalone A development only: externally specified values, no cash payment.
    dict(
        name='dev_lab_ambiguity_18', display_name='DEV ONLY: lab A (18)',
        num_demo_participants=18, lab_session_size=18,
        branch='A', paid_block=4, rho=0.3, rho_exact='3/10', matching_seed='dev-ambiguity-18-v1',
        ambiguity_thresholds={'4': 42, '5': 33, '6': 41, '7': 42, '8': 40, '9': 33},
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['ambiguity'],
    ),
    dict(
        name='dev_lab_ambiguity_24', display_name='DEV ONLY: lab A (24)',
        num_demo_participants=24, lab_session_size=24,
        branch='A', paid_block=4, rho=0.3, rho_exact='3/10', matching_seed='dev-ambiguity-24-v1',
        ambiguity_thresholds={'4': 42, '5': 33, '6': 41, '7': 42, '8': 40, '9': 33},
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['ambiguity'],
    ),
    # Standalone E development routes only; no cross-app handoff or cash payment.
    dict(
        name='dev_lab_endogenous_18', display_name='DEV ONLY: lab E (18)',
        num_demo_participants=18, lab_session_size=18,
        branch='E', paid_block=4, rho=0.3, rho_exact='3/10', matching_seed='dev-endogenous-18-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['endogenous'],
    ),
    dict(
        name='dev_lab_endogenous_24', display_name='DEV ONLY: lab E (24)',
        num_demo_participants=24, lab_session_size=24,
        branch='E', paid_block=4, rho=0.3, rho_exact='3/10', matching_seed='dev-endogenous-24-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['endogenous'],
    ),
    # Development-only F backend routes: no cash payment or other sections.
    dict(
        name='dev_lab_fixed_18', display_name='DEV ONLY: lab F backend (18)',
        num_demo_participants=18, lab_session_size=18,
        branch='E', paid_block=1, rho=0.3, rho_exact='3/10', matching_seed='dev-fixed-18-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['fixed'],
    ),
    dict(
        name='dev_lab_fixed_24', display_name='DEV ONLY: lab F backend (24)',
        num_demo_participants=24, lab_session_size=24,
        branch='E', paid_block=1, rho=0.3, rho_exact='3/10', matching_seed='dev-fixed-24-v1',
        T=5, real_world_currency_per_point=0, participation_fee=0,
        exchange_rate_text='', app_sequence=['fixed'],
    ),
    dict(
        name='general_instructions_only',
        display_name='General Instructions only',
        num_demo_participants=1,
        section1_num_blocks=3,
        section2_num_blocks=3,
        section3_num_blocks=3,
        app_sequence=['general_instructions'],
    ),

    dict(
        name='section1_instructions_only',
        display_name='Section 1 instructions only',
        num_demo_participants=1,
        section1_num_blocks=3,
        section2_num_blocks=3,
        section3_num_blocks=3,
        app_sequence=['instructions_section1'],
    ),

    dict(
        name='fixed_target_only',
        display_name='Section 1 gameplay only (Blocks 1-3)',
        num_demo_participants=1,
        section1_num_blocks=3,
        section2_num_blocks=3,
        section3_num_blocks=3,
        app_sequence=[
            'stage_game_section1'
        ],
    ),

    dict(
        name='section2_instructions_only',
        display_name='Section 2 instructions only',
        num_demo_participants=1,
        section1_num_blocks=3,
        section2_num_blocks=3,
        section3_num_blocks=3,
        app_sequence=['instructions_section2'],
    ),

    dict(
        name='endogenous_target_only',
        display_name='Section 2 gameplay only (Blocks 4-6)',
        num_demo_participants=1,
        section1_num_blocks=3,
        section2_num_blocks=3,
        section3_num_blocks=3,
        app_sequence=[
            'stage_game_section2'
        ],
    ),

    dict(
        name='section3_ambiguity_only',
        display_name='Section 3 gameplay only (Ambiguity information)',
        num_demo_participants=1,
        section1_num_blocks=3,
        section2_num_blocks=3,
        section3_num_blocks=3,
        section3_environment='ambiguity',
        app_sequence=['instructions_section3', 'stage_game_section3'],
    ),

    dict(
        name='section3_risk_only',
        display_name='Section 3 gameplay only (Risk information)',
        num_demo_participants=1,
        section1_num_blocks=3,
        section2_num_blocks=3,
        section3_num_blocks=3,
        section3_environment='risk',
        app_sequence=['instructions_section3', 'stage_game_section3'],
    ),

    dict(
        name='prolific_ambiguity_t5',
        display_name='Prolific: Ambiguity T=5',
        exchange_rate_text="100 points = 0.40 £",
        estimated_duration_minutes=25,
        num_demo_participants=1,
        section1_num_blocks=2,
        section2_num_blocks=2,
        section3_num_blocks=2,
        section3_environment='ambiguity',
        T=5,
        paid_block=1,
        app_sequence=[
            'general_instructions', 'instructions_section1', 'stage_game_section1',
            'instructions_section2', 'stage_game_section2',
            'instructions_section3', 'stage_game_section3', 'experiment_end',
        ],
    ),

    dict(
        name='prolific_ambiguity_t5_1block',
        display_name='Prolific: Ambiguity T=5',
        exchange_rate_text="100 points = 0.40 £",
        estimated_duration_minutes=25,
        num_demo_participants=1,
        section1_num_blocks=1,
        section2_num_blocks=1,
        section3_num_blocks=1,
        section3_environment='ambiguity',
        T=5,
        paid_block=1,
        app_sequence=[
            'general_instructions', 'instructions_section1', 'stage_game_section1',
            'instructions_section2', 'stage_game_section2',
            'instructions_section3', 'stage_game_section3', 'experiment_end',
        ],
    ),

    dict(
        name='prolific_risk_t5',
        display_name='Prolific: Risk T=5',
        exchange_rate_text="100 points = 0.40 £",
        estimated_duration_minutes=25,
        num_demo_participants=1,
        section1_num_blocks=2,
        section2_num_blocks=2,
        section3_num_blocks=2,
        section3_environment='risk',
        T=5,
        paid_block=1,
        app_sequence=[
            'general_instructions', 'instructions_section1', 'stage_game_section1',
            'instructions_section2', 'stage_game_section2',
            'instructions_section3', 'stage_game_section3', 'experiment_end',
        ],
    ),

    dict(
        name='prolific_ambiguity_t10',
        display_name='Prolific: Ambiguity T=10',
        exchange_rate_text="100 points = 0.40 £",
        estimated_duration_minutes=35,
        num_demo_participants=1,
        section1_num_blocks=2,
        section2_num_blocks=2,
        section3_num_blocks=2,
        section3_environment='ambiguity',
        T=10,
        paid_block=1,
        app_sequence=[
            'general_instructions', 'instructions_section1', 'stage_game_section1',
            'instructions_section2', 'stage_game_section2',
            'instructions_section3', 'stage_game_section3', 'experiment_end',
        ],
    ),

    dict(
        name='prolific_risk_t10',
        display_name='Prolific: Risk T=10',
        exchange_rate_text="100 points = 0.40 £",
        estimated_duration_minutes=35,
        num_demo_participants=1,
        section1_num_blocks=2,
        section2_num_blocks=2,
        section3_num_blocks=2,
        section3_environment='risk',
        T=10,
        paid_block=1,
        app_sequence=[
            'general_instructions', 'instructions_section1', 'stage_game_section1',
            'instructions_section2', 'stage_game_section2',
            'instructions_section3', 'stage_game_section3', 'experiment_end',
        ],
    ),
]

# Production is the normal launch menu. Test/development and online retention
# require separate explicit processes; never mix EUR and GBP collection.
from lab_production import load_templates, validate_runtime
CONFIG_MODE = environ.get('OTREE_CONFIG_MODE', 'production')
if CONFIG_MODE not in ('production', 'development', 'legacy'):
    raise ValueError('OTREE_CONFIG_MODE must be production, development or legacy.')
if CONFIG_MODE == 'production':
    validate_runtime(environ)
    SESSION_CONFIGS = load_templates(environ.get('OTREE_LAB_CONFIG_FILE'))
else:
    SESSION_CONFIGS = [c for c in RETAINED_CONFIGS
                       if c['name'].startswith('dev_lab_') == (CONFIG_MODE == 'development')]
    if CONFIG_MODE == 'legacy' and environ.get('OTREE_LAB_PAYMENTS') == '1':
        raise ValueError('Legacy online mode requires a separate GBP process (unset OTREE_LAB_PAYMENTS).')

ROOMS = ([dict(name=f'lab_{size}', display_name=f'Laboratory — {size} seats',
               participant_label_file=f'_rooms/lab_{size}.txt', use_secure_urls=False)
          for size in (18,24)] if CONFIG_MODE != 'legacy' else
         [dict(name='my_room', display_name='My_room')])

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    T=10,
    real_world_currency_per_point=0.004,
    participation_fee=0.00,
    exchange_rate_text="100 points = 0.40 £",
    completion_code='CVE5GPIH',
    doc="",
)

if CONFIG_MODE == 'production':
    SESSION_CONFIG_DEFAULTS = dict(T=5, real_world_currency_per_point=0.01,
                                   participation_fee=8.00, doc='Laboratory production')

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'it'

# e.g. EUR, GBP, CNY, JPY
# oTree cash currency is process-wide. Keep GBP for legacy online servers;
# launch the separate lab/payment server with OTREE_LAB_PAYMENTS=1.
REAL_WORLD_CURRENCY_CODE = 'EUR' if environ.get('OTREE_LAB_PAYMENTS') == '1' else 'GBP'
USE_POINTS = True
# Retain legacy online Currency display precision. Laboratory economic values
# use exact rational storage, not this Currency quantization.
POINTS_DECIMAL_PLACES = 2
# Lab wallets remain exact n/d values outside Currency. The final payment app
# assigns integer cash-settlement points only after exact EUR-cent rounding;
# this legacy point precision is never used for lab economic settlement.

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = environ.get('OTREE_SECRET_KEY', '1422526959286')
