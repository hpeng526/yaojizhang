#-*- coding:utf-8 -*-
from django.conf import settings
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.conf.urls.static import static
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'yaojizhang.views.home', name='home'),
    # url(r'^yaojizhang/', include('yaojizhang.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^connect$', 'yjz.views.handle_request'),
    url(r'^export-csv/(?P<id_user>\S*)/$', 'yjz.views.export_csv'),
    # url(r'^static/export/css/(?P<path>.*)$', 'django.views.static.serve',
    #     {'document_root': '/static/export/css'}),
    # url(r'^export/(?P.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
)

