"""WSGI entrypoint used by gunicorn on Render (and any WSGI-compatible host)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
