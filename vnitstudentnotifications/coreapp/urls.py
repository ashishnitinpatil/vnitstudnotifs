from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView


urlpatterns = patterns('vnitstudentnotifications.coreapp.views',
    # Coreapp url patterns
    url(r'^$', 'home', name='home'),
    url(r'^check/$', 'cron', name='cron'),
    url(r'^checkurl/$', 'cron_url', name='cron_url'),
    url(r'^about/$', TemplateView.as_view(template_name='about.html'),
        name='about'),
    url(r'^changelog/$', TemplateView.as_view(template_name='changelog.html'),
        name='changelog'),
)
