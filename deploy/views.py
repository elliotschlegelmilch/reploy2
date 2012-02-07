from deploy.actions import migrate
from deploy.forms import Migrate
from deploy.models import Platform, Site, Event
from django.conf import settings
from django.contrib import messages
from django.core import urlresolvers
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect

import csv
import datetime

#@csrf_protect
def site_migrate(request):

    form = Migrate(request.POST if request.POST else None)

    if form.is_valid():
        #what sites:
        l = request.GET['ids'].split(',')
        site_ids = [int(i) for i in l]
        sites = Site.objects.filter(pk__in=site_ids)
        platform = Platform.objects.get(pk=request.POST['new_platform'])
        for site in sites:
            ctask = migrate.delay(site, platform)
            event = Event( task_id=ctask.task_id, site=site, user=request.user, event='migrate')
            event.save()
            messages.add_message(request, messages.INFO, "The migration of the site %s has been queued: %s" % ( site, ctask.task_id) )

        # this needs to redirect or something.
        return redirect(
            urlresolvers.reverse('admin:deploy_site_changelist')
            )
         
    data = {
        'user': request.user,
        'form': form,
        }

    return render_to_response('migrate.html', data)


def platform_status(request, platform=None):
    p = get_object_or_404( Platform, pk=Platform)
    _heading = ['url', 'short_name', 'long_name', 'database', 'contact_email']
    filename = "platform.status.%s.%s.csv" %( platform, datetime.datetime.now().strftime(settings.CSV_FORMAT))

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s' %( filename,)
    writer = csv.writer(response)

    writer.writerow( _heading )

    for s in Site.objects.filter(platform = p):
        writer.writerow([ s.__getattribute__(column) for column in _heading ])

    return response

def home(request):
    return redirect(urlresolvers.reverse('admin:deploy_site_changelist'))

