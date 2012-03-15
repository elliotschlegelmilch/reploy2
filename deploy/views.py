from deploy.actions import migrate, rename, drush, update_events, update_statistic, get_site_status, enable, disable, cacheclear, verify, varnishclear

from deploy.forms import Migrate, Clone, Drush
from deploy.models import Platform, Site, Event, Statistic
from django.conf import settings
from django.contrib import messages
from django.core import urlresolvers
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect, get_object_or_404

import csv
import datetime
import json

def site_manage(request, sid):
    site = get_object_or_404( Site, pk=sid)
    events = Event.objects.filter( site= site ).order_by('date')
    callbacks = Event.objects.filter( site= site, event='status' ).order_by('date')

    op = request.POST.get('submit', None)

    form_instance = request.POST if request.method == 'POST' else None
    
    forms = {'clone'  : Clone(form_instance),
             'migrate': Migrate(form_instance),
             'drush'  : Drush(form_instance),
             }

    ctask = None
    
    if not op == None:
        if op == 'enable':
            ctask = enable.delay(site)
        elif op == 'disable':
            ctask = disable.delay(site)
        elif op == 'cache':
            ctask = cacheclear.delay(site)
        elif op == 'varnish':
            ctask = varnishclear.delay(site)
        elif op == 'verify':
            ctask = verify.delay(site)
        elif op == 'migrate':
            if forms['migrate'].is_valid():
                new_platform = Platform.objects.get(pk = forms['migrate'].cleaned_data['new_platform'])
                if new_platform:
                    ctask = migrate.delay(site, new_platform)
        elif op == 'clone' or op == 'rename':
            if forms['clone'].is_valid():
                new_short_name = forms['clone'].cleaned_data['new_name']
                ctask = rename.delay(site, new_name, op == 'clone')

        if not ctask == None:
            #record the task as an event, that way it will display in the task log.
            event = Event( task_id=ctask.task_id, site=site, user=request.user, event=op)
            event.save()
    




    update_events()
    update_statistic()
    
    data = {'events'    : events,
            'user'      : request.user,
            'site'      : site,
            'callbacks' : callbacks,
            'forms'     : forms
            }
    
    return render_to_response('site-manage.html', data)
    


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


def site_drush(request):
    form = Drush(request.POST if request.POST else None)

    if form.is_valid():
        #what sites:
        l = request.GET['ids'].split(',')
        site_ids = [int(i) for i in l]
        sites = Site.objects.filter(pk__in=site_ids)

        
        cmd = request.POST['drush_command']
        for site in sites:
            ctask = drush.delay(site, cmd)
            event = Event( task_id=ctask.task_id, site=site, user=request.user, event='drush')
            event.save()
            messages.add_message(request, messages.INFO, "The drush command on the site %s has been queued: %s" % ( site, ctask.task_id) )

        # this needs to redirect or something.
        return redirect(
            urlresolvers.reverse('admin:deploy_site_changelist')
            )
         
    data = {
        'user': request.user,
        'form': form,
        }

    return render_to_response('drush.html', data)


def site_clone(request):

    l = request.GET['ids'].split(',')
    site_id = [int(i) for i in l][0]
    site = get_object_or_404( Site, pk=site_id)

    default_name = "%s_copy" % (site.short_name,)

    form = Clone(request.POST if request.POST else None,
                 initial={'new_name': default_name})

    if form.is_valid():
        #what sites:
        
        do_clone = form.cleaned_data['clone']
        
        ctask = rename.delay( site, form.cleaned_data['new_name'], do_clone)
        event = Event( task_id=ctask.task_id, site=site, user=request.user, event='migrate')
        event.save()
        messages.add_message(request, messages.INFO, "The clone of the site %s has been queued: %s" % ( site, ctask.task_id) )

        return redirect(
            urlresolvers.reverse('admin:deploy_site_changelist')
            )
         
    data = {
        'user': request.user,
        'form': form,
        }

    return render_to_response('clone.html', data)



def platform_status(request, platform=None):
    p = get_object_or_404( Platform, pk=platform)
    _heading = ['url', 'short_name', 'long_name', 'database', 'contact_email']
    filename = "platform.status.%s.%s.csv" %( platform, datetime.datetime.now().strftime(settings.CSV_FORMAT))

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s' %( filename,)
    writer = csv.writer(response)

    writer.writerow( _heading )

    for s in Site.objects.filter(platform = p):
        writer.writerow([ s.__getattribute__(column).encode('ascii','replace') for column in _heading ])

    return response

def ajax(request):
    data = {'status': False }
    site = get_object_or_404( Site, pk= request.POST.get(u'site') )
    statistics = Statistic.objects.filter(site=site)
    if len(statistics) > 0:
        stats = {}
        data['status'] = True
        for s in statistics:
            stats.update( {s.metric: s.value} )
        data['stats'] = stats
    
    return HttpResponse( json.dumps( data ), 'application/json' )

def home(request):
    return redirect(urlresolvers.reverse('admin:deploy_site_changelist'))

