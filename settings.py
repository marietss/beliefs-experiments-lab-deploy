"""BLESS pilot deployment: production-only configuration; no study secrets here."""
from os import environ
from lab_production import load_templates, validate_runtime

CONFIG_MODE = environ.get('OTREE_CONFIG_MODE', 'production')
if CONFIG_MODE != 'production':
    raise ValueError('This deployment repository supports production mode only.')
validate_runtime(environ)
SESSION_CONFIGS = load_templates(environ.get('OTREE_LAB_CONFIG_FILE'))
ROOMS = [dict(name=f'lab_{size}', display_name=f'Laboratory — {size} seats',
              participant_label_file=f'_rooms/lab_{size}.txt', use_secure_urls=True)
         for size in (18, 24)]
SESSION_CONFIG_DEFAULTS = dict(T=5, real_world_currency_per_point=0.01,
                               participation_fee=7.50, doc='Laboratory production')
PARTICIPANT_FIELDS = []
SESSION_FIELDS = []
LANGUAGE_CODE = 'it'
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = True
POINTS_DECIMAL_PLACES = 2
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')
DEMO_PAGE_INTRO_HTML = " "
SECRET_KEY = environ['OTREE_SECRET_KEY']
