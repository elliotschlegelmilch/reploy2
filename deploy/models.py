from django.db import models
from actions import verify

PLATFORM_CHOICES = (
    ('pro','production'),
    ('sta','stage'),
    ('dev','development'),
    )

class Platform(models.Model):
    name = models.CharField(max_length=48, primary_key=True, help_text='common or convenience name for this platform. e.g.: production')
    canonical_host = models.CharField(max_length=48, help_text='hostname of the machine. e.g.: redrum.example.org')
    host = models.CharField(max_length=48, help_text='hostname of the sites this platform serves. e.g.: www.example.org')
    path = models.CharField(max_length=200, default='/var/www/drupal')
    database = models.CharField(max_length=48)
    use = models.CharField(max_length=3,
                           choices= ( ('pro','production'),
                                      ('sta','stage'),
                                      ('dev','development'), ) 
                           )

    def __unicode__(self):
        return self.name


class Site(models.Model):

    long_name = models.CharField(max_length=256, blank=True, help_text='this is the site name' )
    short_name = models.CharField(max_length=32, null=False, blank=False, help_text='this is the site name, e.g.: foo to create the site www.example.org/foo')
    contact_email = models.CharField(max_length=64,help_text='this populates the site_admin field of the site')
    staff_email = models.CharField(max_length=64)
    pre_production = models.BooleanField(default=True, help_text='Is this a site that has never been deployed to production.')
    maintenance_mode = models.BooleanField()
    platform =  models.ForeignKey(Platform, help_text='Which platform should this site be created.')

    class Meta():
        unique_together = ("short_name", "platform")            

    def __unicode__(self):
        return u"<Site %s/%s>" %( self.platform.host, self.short_name )

    def action_verify(self):
        verify(self)

