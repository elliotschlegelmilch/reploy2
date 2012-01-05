from django.db import models
from actions import verify
import os.path

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

class Status(models.Model):
    status = models.CharField(max_length=48, primary_key=True)
    def __str__(self):
        return self.status
    def __unicode__(self):
        return self.status

class Site(models.Model):

    long_name        = models.CharField(max_length=256, blank=True, help_text='this is the site name' )
    short_name       = models.CharField(max_length=32, null=False, blank=False, help_text='this is the site name, e.g.: foo to create the site www.example.org/foo')
    platform         = models.ForeignKey(Platform, help_text='Which platform should this site be created.')
    database         = models.CharField(max_length=32, null=False, blank=True)
    contact_email    = models.CharField(max_length=64, help_text='this populates the site_admin field of the site')
    staff_email      = models.CharField(max_length=64)
    status           = models.ManyToManyField(Status)


    def save(self, *args, **kwargs):
        if self.database == '':
            self.database = self.short_name
        super(Site,self).save(*args, **kwargs)

    class Meta():
        unique_together = ("short_name", "platform")            

    def __unicode__(self):
        return u"http://%s/%s" %( self.platform.host, self.short_name )

    # some helpers for the multiflag.
    def show_status(self):
        return ','.join([str(i) for i in self.status.all()])

    @property
    def installed(self):
        return (self.status.filter(status = 'not installed').count() == 0)

    @property
    def local_config(self):
        return None
        

    def site_dir(self):
        return os.path.join(self.platform.path, 'sites', self.platform.host + '.' +  self.short_name)

    def site_files_dir(self):
        """ returns a list of paths in the files directory. They don't always get created properly even if the parent directory has appropriate permissions"""
        d = ['', 'styles', 'css','ctools','xmlsitemap',
             'styles/large',
             'styles/pdx_collage_large',
             'styles/pdx_collage_medium',
             'styles/pdx_collage_small',
             'styles/pdx_school_home',
             'styles/square_thumbnail']

        return [ os.path.join( self.site_dir(), i ) for i in d ]

    def site_symlink(self):
        return os.path.join(self.platform.path, self.short_name)

    def settings_php(self, f=None):
        inc = os.path.join(self.platform.path, self.platform.host + '.php')
        settings = """<?php
$_db  = '%(database)s';
$_dir = '%(sitedir)s'; 
$install = %(install)s;

$_inc = '%(inc)s';
require_once($_inc);

#do not modify this line: local changes below this point

%(local_config)s
"""
        site_vars = {
            'database': self.database,
            'sitedir': self.platform.host + '.' +  self.short_name,
            'install': ('NULL' if self.installed else 'TRUE'),
            'inc': inc,
            'local_config': self.local_config }
            
        print settings
            
        print site_vars


        return settings % site_vars


