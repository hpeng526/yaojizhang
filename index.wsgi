import sae

from yaojizhang import wsgi

application = sae.create_wsgi_app(wsgi.application)

