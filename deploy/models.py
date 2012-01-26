from django.db import models
from actions import verify
import os.path
import logging

logger = logging.getLogger(__name__)

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
    _valid = ['deprecated', 'maintenance', 'ok', 'preproduction', 'unqueried','not installed']

    def __str__(self):
        return self.status
    def __unicode__(self):
        return self.status

    ## maintaince mode, preproduction, ok, deprecated

class Site(models.Model):
    long_name        = models.CharField(max_length=256, blank=True, help_text='this is the site name' )
    short_name       = models.CharField(max_length=32, null=False, blank=False, help_text='this is the site name, e.g.: foo to create the site www.example.org/foo')
    platform         = models.ForeignKey(Platform, help_text='Which platform should this site be created.')
    database         = models.CharField(max_length=32, null=False, blank=True)
    profile          = models.CharField(max_length=20, null=False, default='psu_primary',
                                        choices= (
                                            ('minimal','Minimal'),
                                            ('psu_home','PSU Home'),
                                            ('psu_primary','PSU Primary'),
                                            ('psu_secondary','PSU Secondary'),
                                            ('psu_syndication','Syndication'),
                                            ('standard','Standard'),
                                            ('testing','Testing'),
                                             ))

    contact_email    = models.CharField(max_length=64, help_text='this populates the site_admin field of the site')
    staff_email      = models.CharField(max_length=64)
    status           = models.ManyToManyField(Status, blank=True)

    def save(self, *args, **kwargs):
        if self.database == '':
            self.database = self.short_name
        super(Site,self).save(*args, **kwargs)

    class Meta():
        unique_together = ("short_name", "platform")            

    def __unicode__(self):
        if self.short_name == 'default':
            return u"http://%s/" %( self.platform.host, )
        else:
            return u"http://%s/%s" %( self.platform.host, self.short_name )

    def link(self):
        return '<a href="%s">%s</a>' %(self.__unicode__(),self.__unicode__())
    link.allow_tags = True

    # some helpers for the multiflag.
    def show_status(self):
        return ','.join([str(i) for i in self.status.all()])

    def set_flag(self,flag):
        status_obj = None
        try:
            status_obj = Status.objects.get(pk=flag)
        except DoesNotExist:
            pass
        
        if status_obj:
            self.status.add( status_obj)
            return True
        return False

    def unset_flag(self,flag):
        status_obj = Status.objects.get(pk=flag)
        if status_obj:
            self.status.remove( status_obj)
            return True
        return False
    
    @property
    def installed(self):
        return (self.status.filter(status = 'not installed').count() == 0)

    @property
    def local_config(self):
        return None

    @property
    def site_uri(self):
        if self.short_name == 'default':
            return u"http://%s/" %( self.platform.host, )
        else:
            return u"http://%s/%s" %( self.platform.host, self.short_name )

    @property
    def files_dir(self):
        """Returns the directory where this site lives in files. Used in database replaces.
        foo.net.bar or default."""
        
        if self.short_name == 'default':
            return u"default"
        else:
            return u"%s.%s" %( self.platform.host, self.short_name )

    def site_dir(self):
        """Returns the full filesystem path to the site. Used in database replaces.
        /var/www/html/sites/foo.net.bar or /var/www/html/sites/default"""
        
        if self.short_name == 'default':
            return os.path.join(self.platform.path, 'sites', 'default')
        else:
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

        return [ os.path.join( self.site_dir(),'files', i ) for i in d ]

    def site_symlink(self):
        return os.path.join(self.platform.path, self.short_name)

    def settings_php(self, f=None):
        inc = os.path.join(self.platform.path,'sites', self.platform.host + '.php')
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
            'local_config': self.local_config if self.local_config else ''}

        if f:
            print f
            fd = file(f, 'w')
            fd.write(settings % site_vars)
            fd.close()
        
            
        return settings % site_vars


