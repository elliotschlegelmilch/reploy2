from deploy.actions import migrate
from deploy.forms import Migrate
from deploy.models import Platform, Site

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
            migrate(site, platform)

        # this needs to redirect or something.
        
    data = {
        'user': request.user,
        'form': form,
        }

    resp = render_to_response('foo.html', data)
    return resp

def home(request):
    return redirect('/admin')
