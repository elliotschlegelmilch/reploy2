from deploy.actions import migrate
from deploy.forms import Migrate
from deploy.models import Platform, Site, Event
from django.contrib import messages
from django.core import urlresolvers

from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.views.decorators.csrf import csrf_protect

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
            event = Event( task_id=ctask.task_id, site=site, user=request.user)
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

def home(request):
    return redirect(urlresolvers.reverse('admin:deploy_site_changelist'))

