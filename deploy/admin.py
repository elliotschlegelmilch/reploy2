from django.contrib import admin, messages
from models import Platform, Site
from actions import verify, create


class SiteAdmin(admin.ModelAdmin):
    list_display = ['short_name','long_name', 'contact_email','maintenance_mode', 'pre_production']
    list_filter = ['platform','maintenance_mode']
    search_fields = ['long_name','short_name']
    ordering = ['long_name', 'short_name']
    actions = ['site_online','site_verify','site_create']

    def site_online(self, request, queryset):
        messages.add_message(request, messages.INFO, '')
             
    def site_verify(self, request,queryset):
         for i in queryset:
             verify(i)

    def site_create(self, request, queryset):
        for i in queryset:
            create(i)

        
    site_online.short_description = 'Maintenance Mode: disable.'
    site_verify.short_description = 'Verify site.'
    site_create.short_description = 'TEST: create site.'

    # verify enable disable rename migrate backup restore flush-cache delete
    
admin.site.register(Site,SiteAdmin)
admin.site.register(Platform)



