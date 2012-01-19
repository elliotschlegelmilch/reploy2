from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from admin import *

admin.autodiscover()

urlpatterns = patterns( '',
                        url(r'^$', 'deploy.views.home', name='home'),
                        url(r'^site-migrate$', 'deploy.views.site_migrate'),
                        # url(r'^deploy/', include('deploy.foo.urls')),
                        # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
                        url(r'^admin/', include(admin.site.urls)),
                        url(r'^a/', include(admin.site.urls)),

)
