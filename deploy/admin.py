from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.http import HttpResponseRedirect, HttpResponse

from deploy.models import Platform, Site, Status, Event
from deploy.actions import verify, create, enable, disable, wipe_site, cacheclear, backup


class SiteAdmin(admin.ModelAdmin):
    list_display = ['link', 'short_name','long_name', 'contact_email',
                    'platform','show_status' ]
    list_filter = ['platform', 'user', 'status']
    list_display_links = ['short_name']
    search_fields = ['long_name', 'short_name']
    ordering = ['long_name', 'short_name']
    actions = ['site_online', 'site_offline', 'site_verify', 'site_create',
               'site_cacheclear', 'site_migrate', 'site_wipe', 'site_backup']
    exclude =['status']

    def site_online(self, request, queryset):
        for i in queryset:
            s = enable(i)
            if s:
                messages.add_message(request, messages.INFO, "The site %s is now online." % (i,) )
                
    def site_offline(self, request, queryset):
        for i in queryset:
            s = disable(i)
            if s:
                messages.add_message(request, messages.INFO, "The site %s is now offline." % (i,) )
                
    def site_verify(self, request,queryset):
         for i in queryset:
             s = verify(i)
             if s:
                 messages.add_message(request, messages.SUCCESS, "%s has been verified." %(i,))
             else:
                 messages.add_message(request, messages.ERROR, "%s could not be verified." % (i,))

    def site_create(self, request, queryset):
        for i in queryset:
            create(i)

    def site_backup(self,request, queryset):
        for i in queryset:
            s = backup(i)
            if s:
                messages.add_message(request,
                                     messages.INFO, "the site, %s, has been backuped." %( i, ))


    def site_cacheclear(self, request, queryset):
        for i in queryset:
            s = cacheclear(i)
            if s:
                messages.add_message(request, messages.INFO, "The cache of site %s has been cleared." % (i,) )

    
    def json(self, request, queryset):
        response = HttpResponse(mimetype="text/javascript")
        serializers.serialize("json", queryset, stream=response)
        return response

    def site_migrate(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        ct = ContentType.objects.get_for_model(queryset.model)
        return HttpResponseRedirect("/site-migrate?ct=%s&ids=%s" % (ct.pk, ",".join(selected)))
    
    def site_wipe(self, request, queryset):
        for i in queryset:
            wipe_site(i)
            
        
    site_online.short_description = 'Maintenance Mode: disable.'
    site_offline.short_description = 'Maintenance Mode: enable.'
    site_verify.short_description = 'Verify site.'
    site_create.short_description = 'TEST: create site.'
    site_cacheclear.short_description = 'Cache clear.'
    site_wipe.short_description = 'wipe... obliterate.'
    # rename migrate backup restore delete

    
admin.site.register(Site,SiteAdmin)
admin.site.register(Platform)
admin.site.register(Status)
admin.site.register(Event)



