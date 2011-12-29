from django.db import models
from actions import verify

PLATFORM_CHOICES = (
    ('pro','production'),
    ('sta','stage'),
    ('dev','development'),
    )

class Platform(models.Model):
    name = models.CharField(max_length=48, primary_key=True)
    host = models.CharField(max_length=48)
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
    long_name = models.CharField(max_length=256, blank=True)
    short_name = models.CharField(max_length=32, primary_key=True)
    contact_email = models.CharField(max_length=64)
    staff_email = models.CharField(max_length=64)
    pre_production = models.BooleanField()
    maintenance_mode = models.BooleanField()
    platform =  models.ForeignKey(Platform)

    def __unicode__(self):
        return u"<Site %s/%s>" %( self.platform.host, self.short_name )

    def action_verify(self):
        verify(self)

