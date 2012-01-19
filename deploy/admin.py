from django.contrib import admin, messages
from models import Platform, Site, Status
from deploy.actions import verify, create, enable, disable, wipe_site

from django.http import HttpResponse
from django.core import serializers

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect

class SiteAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'short_name','long_name', 'contact_email','platform','show_status']
    list_filter = ['platform', 'staff_email', 'status']
    search_fields = ['long_name', 'short_name']
    ordering = ['long_name', 'short_name']
    actions = ['site_online', 'site_offline', 'site_verify', 'site_create', 'site_cacheclear', 'site_migrate', 'site_wipe']

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
             verify(i)
    def site_create(self, request, queryset):
        for i in queryset:
            create(i)

    def site_backup(self,request, queryset):
        pass

    def site_cacheclear(self, request, queryset):
        pass

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
#admin.site.register(Status)



