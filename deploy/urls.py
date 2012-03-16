from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from admin import *

admin.autodiscover()

urlpatterns = patterns( '',
                        url(r'^$', 'deploy.views.home', name='home'),
                        url(r'^site-migrate$', 'deploy.views.site_migrate'),
                        url(r'^site-drush$', 'deploy.views.site_drush'),
                        url(r'^platform-status/(?P<platform>.+)/$', 'deploy.views.platform_status'),
                        url(r'^site-manage/(?P<sid>.+)/$', 'deploy.views.site_manage'),
                        url(r'^ajax$', 'deploy.views.ajax'),
                        url(r'^admin/', include(admin.site.urls)),
                        url(r'^accounts/login/$', 'django_cas.views.login'),
                        url(r'^accounts/logout/$', 'django_cas.views.logout'),

)
