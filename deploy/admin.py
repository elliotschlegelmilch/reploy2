from django.contrib import admin, messages
from models import Platform, Site


class SiteAdmin(admin.ModelAdmin):
    list_display = ['short_name','long_name', 'contact_email','maintenance_mode', 'pre_production']
    list_filter = ['platform','maintenance_mode']
    search_fields = ['long_name','short_name']
    ordering = ['long_name', 'short_name']
    actions = ['online','verify']

    def online(self, request, queryset):
        messages.add_message(request, messages.INFO, 'Hello world.')
             
    def verify(self, request,queryset):
         for i in queryset:
             i.action_verify()
            
    online.short_description = 'put site into online mode'
    verify.short_description = 'verigy site'
    # verify enable disable rename migrate backup restore flush-cache delete
    
admin.site.register(Site,SiteAdmin)
admin.site.register(Platform)



