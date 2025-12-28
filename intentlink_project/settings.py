# intentlink_project/settings.py
import os
import logging
from dotenv import load_dotenv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

# Parse ALLOWED_HOSTS from comma-separated string
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]

# CORS Configuration - Parse from environment
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',') if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

GOPLUS_API_KEY = os.getenv('GOPLUS_API_KEY')
GOPLUS_API_SECRET = os.getenv('GOPLUS_API_SECRET')
GOPLUS_API_BASE = os.getenv('GOPLUS_API_BASE', 'https://api.gopluslabs.io/api/v1')
BLOCKDAG_RPC_URL = os.getenv('BLOCKDAG_RPC_URL')
POLYGON_AMOY_RPC_URL = os.getenv('POLYGON_AMOY_RPC_URL')

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

# Multi-Chain Network Configuration
NETWORK_CONFIG = {
    1043: {  # BlockDAG Awakening Testnet
        "name": "BlockDAG Awakening Testnet",
        "chain_id": 1043,
        "currency": "BDAG",
        "rpc_url": BLOCKDAG_RPC_URL,
        "contracts": {
            # V2 Intent Wallet with portfolio aggregator
            "IntentWallet": os.getenv('BLOCKDAG_INTENT_WALLET', '0xe3dad1813a5c75fba505780a386a81fd3b8777e4'),
            "IntentWalletV2": os.getenv('BLOCKDAG_INTENT_WALLET', '0xe3dad1813a5c75fba505780a386a81fd3b8777e4'),
            # Legacy V1 (kept for reference)
            "IntentWalletV1": os.getenv('BLOCKDAG_INTENT_WALLET_V1', '0x718a09981d305c2293d0c85e9d957ad25cb2a1c7'),
            "MockDEX": os.getenv('BLOCKDAG_MOCK_DEX', '0xbC47d9625e7c102C6E9C08D29BbD3A76514eCB56'),
            # V4 Contracts with improved StakeFor logic
            "MockStaking": os.getenv('BLOCKDAG_MOCK_STAKING', '0xa0Cb7e7052c88A19335Ba6FD961c5B61Ac07fdb7'),
            "MockStakingV4": os.getenv('BLOCKDAG_MOCK_STAKING', '0xa0Cb7e7052c88A19335Ba6FD961c5B61Ac07fdb7'),
            # Legacy
            "MockStakingV3": os.getenv('BLOCKDAG_MOCK_STAKING_V3', '0x0aD823F27D89dDEf66833849df2e1CD36d06a652'),
            "MockStakingV2": os.getenv('BLOCKDAG_MOCK_STAKING_V2', '0xb39a039ba3abd16d97334f6c3c5bda9b8e59dae6'),
            "MockLending": os.getenv('BLOCKDAG_MOCK_LENDING', '0xa23bDd28F9221F275897D8A26A8eb97A341cd257'),
            "MockUSDT": os.getenv('BLOCKDAG_MOCK_USDT', '0x3a06d4bb208bddb40044630f2b269449e9119c4d'),
        },
        "tokens": {
            "USDT": {
                "address": os.getenv('BLOCKDAG_MOCK_USDT', '0x3a06d4bb208bddb40044630f2b269449e9119c4d'),
                "decimals": 18,
                "symbol": "USDT",
            },
        },
        "whitelisted_protocols": {
            "dex": [os.getenv('BLOCKDAG_MOCK_DEX', '0xbC47d9625e7c102C6E9C08D29BbD3A76514eCB56')],
            # V4 Staking
            "staking": [os.getenv('BLOCKDAG_MOCK_STAKING', '0xa0Cb7e7052c88A19335Ba6FD961c5B61Ac07fdb7')],
            "lending": [os.getenv('BLOCKDAG_MOCK_LENDING', '0xa23bDd28F9221F275897D8A26A8eb97A341cd257')],
        }
    },
    80002: {  # Polygon Amoy Testnet
        "name": "Polygon Amoy Testnet",
        "chain_id": 80002,
        "currency": "POL",
        "rpc_url": POLYGON_AMOY_RPC_URL,
        "contracts": {
            # V2 Intent Wallet with portfolio aggregator
            "IntentWallet": os.getenv('POLYGON_INTENT_WALLET', '0x0881a837699208342675591b48910e3f5cfd951d'),
            "IntentWalletV2": os.getenv('POLYGON_INTENT_WALLET', '0x0881a837699208342675591b48910e3f5cfd951d'),
            # Legacy V1 (kept for reference)
            "IntentWalletV1": os.getenv('POLYGON_INTENT_WALLET_V1', '0x718a09981d305c2293d0c85e9d957ad25cb2a1c7'),
            "MockDEX": os.getenv('POLYGON_MOCK_DEX', '0xbC47d9625e7c102C6E9C08D29BbD3A76514eCB56'),
            # V4 Contracts with improved StakeFor logic
            "MockStaking": os.getenv('POLYGON_MOCK_STAKING', '0xC9e70051Cf274074F301288E1baDa32724c2BA98'),
            "MockStakingV4": os.getenv('POLYGON_MOCK_STAKING', '0xC9e70051Cf274074F301288E1baDa32724c2BA98'),
            # Legacy
            "MockStakingV3": os.getenv('POLYGON_MOCK_STAKING_V3', '0x3c26f13764F3d48f21325cf3cE48972d015bCf21'),
            "MockStakingV2": os.getenv('POLYGON_MOCK_STAKING_V2', '0x90cf57776668a181f2ac483879173e2a8b09cf1b'),
            "MockLending": os.getenv('POLYGON_MOCK_LENDING', '0x1b227df9c8d34cab880774737fbf426e66ba98ed'),
            "MockUSDT": os.getenv('POLYGON_MOCK_USDT', '0x0e454e74e925cd61e76d13c99b0d09b11250e091'),
        },
        "tokens": {
            "USDT": {
                "address": os.getenv('POLYGON_MOCK_USDT', '0x0e454e74e925cd61e76d13c99b0d09b11250e091'),
                "decimals": 18,
                "symbol": "USDT",
            },
        },
        "whitelisted_protocols": {
            "dex": [os.getenv('POLYGON_MOCK_DEX', '0xbC47d9625e7c102C6E9C08D29BbD3A76514eCB56')],
            # V4 Staking
            "staking": [os.getenv('POLYGON_MOCK_STAKING', '0xC9e70051Cf274074F301288E1baDa32724c2BA98')],
            "lending": [os.getenv('POLYGON_MOCK_LENDING', '0x1b227df9c8d34cab880774737fbf426e66ba98ed')],
        }
    }
}

RELAYER_PRIVATE_KEY = os.getenv('RELAYER_PRIVATE_KEY')

# Log warning if missing (for dev safety)
if not RELAYER_PRIVATE_KEY:
    print("WARNING: RELAYER_PRIVATE_KEY is not set. Real transactions will fail.")
else:
    print(f"[STARTUP] Relayer Key loaded (length: {len(RELAYER_PRIVATE_KEY)})")


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'api_v1',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'intentlink_project.urls'

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

WSGI_APPLICATION = 'intentlink_project.wsgi.application'

# Database configuration
# Support both individual env vars (for docker-compose) and DATABASE_URL (for Render)
import dj_database_url

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB'),
            'USER': os.getenv('POSTGRES_USER'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
            'HOST': os.getenv('POSTGRES_HOST'),
            'PORT': os.getenv('POSTGRES_PORT'),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


CELERY_BROKER_URL = os.getenv('REDIS_URL')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'


# Logging Configuration
# In production (Render), use console-only logging
# In development, optionally use file logging
LOG_HANDLERS = ['console'] if not DEBUG else ['console', 'file']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'colored': {
            'format': '{levelname} {asctime} [{name}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'api_v1': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'services': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'services.signature_service': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'services.security_service': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Add file handler only in DEBUG mode (local development)
if DEBUG:
    LOGGING['handlers']['file'] = {
        'level': 'DEBUG',
        'class': 'logging.FileHandler',
        'filename': os.path.join(BASE_DIR, 'logs', 'intentlink.log'),
        'formatter': 'verbose',
    }
    for logger_name in ['api_v1', 'services', 'services.signature_service', 'services.security_service']:
        if logger_name in LOGGING['loggers']:
            LOGGING['loggers'][logger_name]['handlers'] = ['console', 'file']