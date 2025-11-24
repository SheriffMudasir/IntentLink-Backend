# intentlink_project/urls.py
"""URL configuration for IntentLink project."""
from django.contrib import admin
from django.urls import path
from .api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls), 
]