from django.db import models
from django.contrib.auth.models import User

import os.path
import logging
import uuid

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
    _states = {
        'deprecated': "This site is no longer in use and may be removed at any time.",
        'error': "A serious error has been detected with this site. It may be necessary to fix manually or re-install",        
        'maintenance': "This site has been put into maintenance; it may be broken or not be ready to be published",
        'not installed': "The site is clean; it may be deleted or installed.",
        'ok': "No problems with the site are detected.",
        'preproduction' : "Undergoing content or other development.",
        'unqueried': "No additional information is available.",
        }

    @property
    def description(self):
        return self._states[self.status]
    
    def __str__(self):
        return self.status
    def __unicode__(self):
        return self.status

class Statistic(models.Model): 
    site    = models.ForeignKey('Site',db_index=True)
    date    = models.DateTimeField(db_index=True, auto_now=True)
    metric  = models.CharField(max_length=36, blank=False)
    value   = models.CharField(max_length=36, blank=False, null=True)

    @property
    def is_statistic(self):
        return self.event == 'statistic'

    def __unicode__(self):
        return "<%s %s:%s>" %( self.site, self.metric, self.value)

class Event(models.Model):
    site    = models.ForeignKey('Site')
    event   = models.CharField(max_length=36, blank=True)
    user    = models.ForeignKey(User, null=True, blank=True)
    date    = models.DateTimeField(db_index=True, auto_now=True)
    status  = models.NullBooleanField(default=None)
    message = models.TextField(null=True)
    task_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid1 )

    def __unicode__(self):
        return "%s did something to %s and the result was %s (%s)" %( self.user, self.site, self.status, self.task_id)


    def simple(self):
        return {'status' : self.status, 'message' : self.message}


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
    user             = models.ForeignKey(User)

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

    @property
    def url(self):
        return self.__unicode__()
    
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
            logger.debug('site::set_flag; flag=%s site=%s' %( str(flag), str(self)))
            self.status.add( status_obj)
            self.save()
            return True
        logger.debug('site::set_flag; UNKNOWN flag=%s site=%s' %( str(flag), str(self)))
        return False

    def unset_flag(self,flag):
        status_obj = None
        try:
            status_obj = Status.objects.get(pk=flag)
        except DoesNotExist:
            pass

        if status_obj:
            logger.debug('site::unset_flag; flag=%s site=%s' %( str(flag), str(self)))
            self.status.remove( status_obj)
            self.save()
            return True
        logger.critical('site::unset_flag; UNKNOWN flag=%s site=%s' %( str(flag), str(self)))
        return False

    def get_flags(self):
        l = [s.status for s in self.status.all()]
        logger.debug('site::get_flags: flag=%s site=%s' %( ','.join(l), str(self)))
        return self.status.all()
    
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
        logger.debug('settings_php; got file=%s, my platform=%s' %(str(f), str(self.platform.host)))
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
            'sitedir': '' if self.short_name == 'default' else self.platform.host + '.' +  self.short_name,
            'install': ('NULL' if self.installed else 'TRUE'),
            'inc': inc,
            'local_config': self.local_config if self.local_config else ''}

        if f:
            fd = file(f, 'w')
            fd.write(settings % site_vars)
            fd.close()
        
            
        return settings % site_vars

