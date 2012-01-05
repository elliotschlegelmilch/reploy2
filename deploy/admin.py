from django.contrib import admin, messages
from models import Platform, Site, Status
from deploy.actions import verify, create


class SiteAdmin(admin.ModelAdmin):
    list_display = ['__unicode__',
                    'short_name','long_name', 'contact_email','platform','show_status']
    list_filter = ['platform','staff_email','status']
    search_fields = ['long_name','short_name']
    ordering = ['long_name', 'short_name']
    actions = ['site_online','site_offline', 'site_verify','site_create', 'site_cacheclear']

    def site_online(self, request, queryset):
        messages.add_message(request, messages.INFO, '')

    def site_offline(self, request, queryset):
        messages.add_message(request, messages.INFO, '')
             
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

    
        
    site_online.short_description = 'Maintenance Mode: disable.'
    site_offline.short_description = 'Maintenance Mode: enable.'
    site_verify.short_description = 'Verify site.'
    site_create.short_description = 'TEST: create site.'
    site_cacheclear.short_description = 'Cache clear.'

    # rename migrate backup restore delete
    
    
admin.site.register(Site,SiteAdmin)
admin.site.register(Platform)
#admin.site.register(Status)



