"""Configuration Django — Billetterie QR.

Les valeurs sensibles se lisent dans backend/.env (voir .env.example).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# override : le .env du projet prime sur d'éventuelles variables système (DB_USER…)
load_dotenv(BASE_DIR / '.env', override=True)

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-change-me')
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,*').split(',')
# Origines HTTPS autorisées pour les formulaires (admin Django derrière Nginx)
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o]

# Derrière le Nginx du VPS (HTTPS terminé par Nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Clé HMAC utilisée pour signer les QR codes (distincte de SECRET_KEY)
TICKET_SIGNING_KEY = os.getenv('TICKET_SIGNING_KEY', SECRET_KEY)
# Code d'accès du personnel (scanner + tableau de bord)
STAFF_ACCESS_CODE = os.getenv('STAFF_ACCESS_CODE', 'or2026')
# Lien de paiement marchand Wave (le montant est ajouté en paramètre ?amount=)
# Mode démonstration : « Payer avec Wave » valide le paiement immédiatement, sans passer par Wave.
# À mettre à 0 pour les vraies ventes.
PAIEMENT_SIMULE = os.getenv('PAIEMENT_SIMULE', '0') == '1'
WAVE_MERCHANT_URL = os.getenv('WAVE_MERCHANT_URL', 'https://pay.wave.com/m/M_sn_VU2qAQOJ_dLv/c/sn/')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'billetterie',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        # Backend MySQL standard, avec tolérance pour MariaDB 10.4 (XAMPP)
        'ENGINE': os.getenv('DB_ENGINE', 'billetterie.db'),
        'NAME': os.getenv('DB_NAME', 'billetterie'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4', 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
