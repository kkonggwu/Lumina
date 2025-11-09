"""
WSGI config for Lumina project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.Lumina.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Lumina.settings")

application = get_wsgi_application()
