# intentlink_project/__init__.py

"""IntentLink Django project initialization."""
from .celery import app as celery_app

__all__ = ('celery_app',)