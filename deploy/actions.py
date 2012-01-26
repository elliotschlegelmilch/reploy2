from deploy.util import parse_vget, _remote_ssh, _remote_drush, _rsync_pull, _rsync_push, _check_site

import copy
import datetime
import glob
import logging
import os.path
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

def check_platform(platform):
    ok = True

    #check path
    (status, out, err) = _remote_ssh(platform, '[ -d %s ]' % (platform.path,))
    ok = ok and status 

    #check db/my.cnf
    (status, out, err) = _remote_ssh(platform, '[ -f %s ]' % ( '.my.cnf',))
    ok = ok and status
                                     
    #check for drush
    (status, out, err) = _remote_ssh(platform, 'which drush')
    ok = ok and status

    return ok



def verify(site):

    status = _check_site(site)
    if not status:
        return False
            
    (status, out, err) = _remote_drush(site, "vget maintenance_mode")

    site.unset_flag('unqueried')

    (status, out, err) = _remote_drush(site, "vget site_name")
    if status == 0:
        site.long_name = parse_vget('site_name', out)
        site.set_flag('ok')
        site.unset_flag('unqueried')
        site.unset_flag('not installed')
        site.save()
    else:
        site.unset_flag('ok')
        
    site.save()
    
    if status == 0:
        x = parse_vget('maintenance_mode', out)
        if x == 1:
            site.set_flag('maintenance')
        else:
            site.unset_flag('maintenance')

    else:
        site.unset_flag('maintenance')
        site.save()
        return False

    (status, out, err) = _remote_drush(site, "vget site_mail")
    if status == 0:
        site.contact_email = parse_vget('site_mail', out)
        site.save()
    else:
        return False

    return True
    
       
def enable(site):
    (status, out, err) = _remote_drush(site, "vset --yes maintenance_mode 0")
    return status == 0

def disable(site):
    (status, out, err) = _remote_drush(site, "vset --yes maintenance_mode 1")
    return status == 0

def cacheclear(site):
    #TODO: cacheclear: needs to handle default
    (status, out, err) = _remote_drush(site, "vp /%s" %( site.short_name,))
    (status, out, err) = _remote_drush(site, "cc --yes all")
    return status == 0
    
def cron(site):
    (status, out, err) = _remote_drush(site, "cron")
    return status == 0
    
def _backup_db(site, path):
    tmpdir = '/tmp'

    (status, remote_tempfile, err) = _remote_ssh(site.platform, 'mktemp %s' % (os.path.join(tmpdir, 'mysqldump.XXXXXXXX')))
    if status > 0:
        logger.error('_backup_db: could not open remote tempfile on host %s' % (site.platform.host,))
        return False

    logger.info('_backup_db: tempfile=%s site=%s' % (remote_tempfile, site))
    (status, out, err) = _remote_ssh(site.platform,
                                     'mysqldump --single-transaction %s > %s' % ( site.database, remote_tempfile))
    if status > 0:
        logger.error('_backup_db: could not open mysqldump to tempfile on host %s' % (site.platform.host,))
        logger.error(out)
    else:
        local_tempfile = tempfile.mkdtemp()
        logger.info('_backup_db: local sql tempfile: %s' % (local_tempfile,))
        (s,o,e) = _rsync_pull(site.platform, remote_tempfile,
                              os.path.join(path,site.database + '.sql'))
        logger.error(o)
        logger.error(e)

        _remote_ssh(site.platform, 'rm %s' % (remote_tempfile,))
        if s == 0:
            return True
   
    return False

def _backup_files(site, path):
    (s,o,e) = _rsync_pull(site.platform, site.site_dir(), path)
    if s == 0:
        return True
    else:
        print e
        print o
        return False

def _db_replace(old_site, new_site):

    if old_site.short_name == 'default':
        logger.critical('_db_replace: Can not run on default sites.')
        return False

    cols = [
        ('field_revision_field_link', 'field_link_url'),
        ('field_revision_body', 'body_value'),
        ('field_revision_body', 'body_summary'),
        ('field_data_body', 'body_value'),
        ('field_data_body', 'body_summary'),
        ('field_revision_field_link', 'field_link_url'),
        ('field_data_field_link', 'field_link_url'),
        ('field_data_field_slide_link', 'field_slide_link_value'),
        ('field_revision_field_slide_link', 'field_slide_link_value'),
        ('menu_links', 'link_path'),
        ('block_custom', 'body'),
        ('variable', 'value'),
        ]

    for i in cols:
        (table, col) = i
        sql1 = 'UPDATE %s SET %s = REPLACE(%s, "%s", "%s");' %( table, col, col, old_site.site_uri, new_site.site_uri )
        sql2 = 'UPDATE %s SET %s = REPLACE(%s, "%s", "%s");' % ( table, col, col, old_site.files_dir, new_site.files_dir )
                    
        (status, out, err) = _remote_ssh(new_site.platform, 'mysql %s -e "%s"' % (new_site.database,sql1) )
        (status, out, err) = _remote_ssh(new_site.platform, 'mysql %s -e "%s"' % (new_site.database,sql2) )
        
    return True


def backup(site):
    """Returns a path to a backup or false if it doesn't succeed."""
    path = tempfile.mkdtemp(prefix='sdt',dir='/tmp/')

    logger.info('backup: temporary_path=%s' % (path,))
    db = _backup_db(site,path)
    fs = _backup_files(site,path)

    site_name = site.platform.host + '.' + site.short_name

    friendly_backup_path = os.path.join('/tmp', site_name + '-' + datetime.datetime.now().strftime('%Y%m%d.%H%M%S') + '.tgz')
    logger.info('backup: destination_path=%s' %(friendly_backup_path,))

    cmd = ['tar','-C', path, '-cpzf', friendly_backup_path, '.']
    logger.info('backup: command is: %s' % (cmd,))
    
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    output,stderr = process.communicate()
    status = process.poll()

    #remove temporary directory
    shutil.rmtree(path)

    if status == 0:
        return True

    return False

def _find_backup_file(site):
    """returns the most recent backup tarball."""
    logger.info('_find_backup_file: looking for a recent backup of ' + str(site))
    backup_location = '/tmp'
    site_name = site.platform.host + '.' + site.short_name
    l = glob.glob( os.path.join(backup_location, site_name + '-*') )
    l.sort()
    l.reverse()
    
    if len(l) > 0:
        logger.info('_find_backup_file: found a backup: ' + l[0])
        return l[0]
    
    return None

def migrate(site, new_platform):

    #backup_result = backup(site)

    backup_result = True
    
    if not backup_result:
        logger.critical("migrate: backup didn't succeed, bail")
        return False

    dest_site = copy.deepcopy(site)
    dest_site.id = None
    dest_site.platform = new_platform
    dest_site.save()
    dest_site.set_flag('unqueried')
    dest_site.save()
    
    if not is_clean(dest_site):
        logger.critical('migrate: destination site not clean, bail')
        return False

    # find the backup to use
    tarball = _find_backup_file(site)
    if tarball == None:
        logger.critical('migrate: backup succeeded but now where is it? help.')
        return False

    #push the tarball into place.
    _rsync_push(new_platform, tarball, '/tmp')

    #from the tarball, only extract foo.pdx.edu.baz into the sites/ directory
    _remote_ssh(new_platform,
                "tar -zxvf %s -C %s %s" % (os.path.join('/tmp/',tarball),
                                           os.path.join(new_platform.path, 'sites'),
                                           dest_site.platform.host + '.' + dest_site.short_name))
    
    _remote_ssh(new_platform,
                "tar -zxvf %s -C %s %s" % (os.path.join('/tmp/',tarball),
                                           '/tmp/',
                                           dest_site.database + '.sql'))

    #create and fill database
    #todo: stage database + replacements first.
    _create_site_database(dest_site)
    (status, out, err) = _remote_ssh(dest_site.platform,
                                     'mysql %s < %s' % (
                                         dest_site.database,
                                         os.path.join('/tmp',dest_site.database + '.sql')
                                         ))
    
    #put in a settings.php
    settings = tempfile.mkstemp()[1]
    dest_site.settings_php(settings)
    (status, out, err) = _rsync_push(dest_site.platform,
                                     settings,
                                     dest_site.site_dir())


    

    _create_site_dirs(dest_site)

    #search / replace database.
    status = _db_replace(site, dest_site)


def is_clean(site):
    """ return true of if there is no trace of the site. this includes symlink, database, sites directory"""
    #TODO: handle default 
    clean = True
    message = ''
    
    (status, out, err) = _remote_ssh(site.platform, '[ -L %s ]' % (site.site_symlink(),))
    logger.info("is_clean: site_symlink: %d" % (status,)) 
    clean = clean and status

    (status, out, err) = _remote_ssh(site.platform, '[ -d %s ]' % (site.site_dir(),))
    logger.info("is_clean: site_dir: %d" % (status,) )
    clean = clean and status

    (status, out, err) = _remote_ssh(site.platform, 'mysql mysql -e "use %s;"' % (site.database,))
    logger.info("is_clean: mysql: %d" % (status,) )
    clean = clean and status

    logger.info("is_clean: site is clean: %d" % (clean,) )
    return clean


def _create_site_dirs(site):
    #link
    _remote_ssh(site.platform, '/bin/ln -s %s %s' % (
        site.platform.path,
        site.site_symlink(),
        ) )

    _remote_ssh(site.platform, 'mkdir %s' % (site.site_dir(), ))
    
    for directory in site.site_files_dir():
        _remote_ssh(site.platform, 'mkdir %s' % (directory, ))
        _remote_ssh(site.platform, 'chmod 2775 %s' % (directory, ))
        
    return True

def _create_site_database(site):
    (status, out, err) = _remote_ssh(site.platform, 'mysql -e "create database %s;"' % (site.database,))
    return status == 0


def _create_settings_php(site):
    settings = tempfile.mkstemp()[1]
    site.settings_php(settings)
    (status, out, err) = _rsync_push(site.platform,
                                     settings,
                                     os.path.join( site.site_dir(), 'settings.php')
                                     )
    return status == 0

def _set_site_permissions(site):
    (status, out, err) = _remote_ssh(site.platform, 'chmod 664 %s;' % ( os.path.join( site.site_dir(), 'settings.php' ),) )
    (status, out, err) = _remote_ssh(site.platform, 'chmod 775 %s;' % ( site.site_dir(), ) )
    
    return status == 0

def create(site, force=False):
    #create db
    logger.info("create: ")

    if not is_clean(site) and not force:
        logger.info("create: forced")
        return False

    if _create_site_database(site) or force:
         
        logger.info("create: sitedir: %s" % (site.site_dir(),))
        if _create_site_dirs(site) or force:

            #put in a settings.php
            settings = _create_settings_php(site)
            if settings:
                install_status, output, err = _remote_drush(site, "site-install -y --site-name='%s' --sites-subdir='%s' --site-email='%s' %s"
                                                        %( site.long_name,
                                                           site.platform.host + '.' +  site.short_name,
                                                           site.contact_email,
                                                           site.profile) )
                if install_status:
                    site.unset_flag('not installed')
                    site.save()
                    perm = _set_site_permissions(site)
                    return True

                return False

            else:
                print output
                print err
                logger.error("create(): create site failed. %s" %(output,))
        else:
            logger.error("create(): create sitedirs failed")
            
            wipe_site(site)

    else:
        logger.error('create database failed %s' % (site.database,))
        return False

    
    #drush --uri=http://localhost/foo site-install --sites-subdir=localhost.foo  --site-name=foo psu_primary 

    logger.info("create: leave")
    
    
def wipe_site(site):
    logger.debug("wipe_site(): called")

    if site.short_name == 'default':
        logger.error("wipe_site(): site=%s default sites can't be deleted." %(site,))
        return False

    if is_clean(site):
        logger.error("wipe_site(): site=%s is already clean." %(site,))
        return True


    #todo: report more nicely about specific exit statuses.
    
    #chmod some files that the installer restricts.
    #  shouldn't be necessary normally, but needed for rollback.

    _remote_ssh(site.platform, 'chmod -R 777 %s' %(site.site_dir(),))
    _remote_ssh(site.platform, 'rm -Rf %s' % (site.site_dir(),))
    _remote_ssh(site.platform, 'unlink %s' % (site.site_symlink(),))
    _remote_ssh(site.platform, 'mysql -e "drop database %s;"' % (site.database,))

    return True
