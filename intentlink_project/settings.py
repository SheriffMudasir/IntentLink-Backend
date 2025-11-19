# intentlink_project/settings.py
import os
import logging
from dotenv import load_dotenv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent



# Load environment variables from .env file
env_path = os.path.join(BASE_DIR, '.env')
print(f"[STARTUP] Loading .env from: {env_path}")
print(f"[STARTUP] .env file exists: {os.path.exists(env_path)}")
load_dotenv(env_path)

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = True

# Log environment variable loading status
print("[STARTUP] Environment Variables Check:")
print(f"  SECRET_KEY present: {bool(SECRET_KEY)}")
print(f"  GOPLUS_API_KEY: {os.getenv('GOPLUS_API_KEY', '(NOT SET)')}")
print(f"  GOPLUS_API_SECRET present: {bool(os.getenv('GOPLUS_API_SECRET'))}")
print(f"  GOPLUS_API_SECRET value length: {len(os.getenv('GOPLUS_API_SECRET', ''))}")
print(f"  BLOCKDAG_RPC_URL: {os.getenv('BLOCKDAG_RPC_URL', '(NOT SET)')}")
print(f"  REDIS_URL: {os.getenv('REDIS_URL', '(NOT SET)')}")
print(f"  POSTGRES_DB: {os.getenv('POSTGRES_DB', '(NOT SET)')}")

# Configure logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'DEBUG',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'api_v1': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'services': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

ALLOWED_HOSTS = ["*"]


# External API Keys and Services
GOPLUS_API_KEY = os.getenv('GOPLUS_API_KEY')
GOPLUS_API_SECRET = os.getenv('GOPLUS_API_SECRET')
BLOCKDAG_RPC_URL = os.getenv('BLOCKDAG_RPC_URL')

# Log the loaded values (masked for security)
print("[STARTUP] Settings loaded:")
print(f"  GOPLUS_API_KEY: {'*' * (len(GOPLUS_API_KEY) if GOPLUS_API_KEY else 0) if GOPLUS_API_KEY else '(NOT SET)'}")
print(f"  GOPLUS_API_SECRET: {'*' * (len(GOPLUS_API_SECRET) if GOPLUS_API_SECRET else 0) if GOPLUS_API_SECRET else '(NOT SET)'}")
print(f"  BLOCKDAG_RPC_URL: {BLOCKDAG_RPC_URL if BLOCKDAG_RPC_URL else '(NOT SET)'}")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # custom apps
    'api_v1',
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


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

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


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# CELERY SETTINGS
CELERY_BROKER_URL = os.getenv('REDIS_URL')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'