"""
WSGI config for Blockhouse project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import ddtrace
from ddtrace import tracer

ddtrace.patch_all()


from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Blockhouse.settings')

application = get_wsgi_application()
