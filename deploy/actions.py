from util import parse_vget
import datetime
import logging
import os.path
import shutil
import subprocess
import tempfile
from deploy.models import *

logger = logging.getLogger(__name__)

def check_platform(self):
    ok = True
    #check path
    #check db/my.cnf
    #check for drush
    #check for mysql mysqldump in path
    #check for tar + rsync

    return ok


def _remote_ssh(platform, cmd):
    """ returns tuple of (exit status, stdout, sdterr) """
    
    logger.info("_remote_ssh: enter")
    begin = datetime.datetime.now()
    remote_cmd = ['ssh', platform.canonical_host, cmd]
    logger.info("_remote_ssh: %s" % (' '.join(remote_cmd),) )

    process = subprocess.Popen(remote_cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    output,stderr = process.communicate()
    status = process.poll()

    if not status == 0:
        if status == 127:
            (s,out, err) = _remote_ssh(platform, "echo $PATH")
            logger.critical("_remote_ssh: not found: is `%s' in the remote path (%s)" % ( cmd.split(' ')[0],out))
            
        
        logger.debug("_remote_ssh: command output: %s" % (output,))
        logger.debug("_remote_ssh: command error: %s" % (stderr,))

    logger.info("_remote_ssh: returned %d" %(status,))

    t = datetime.datetime.now() - begin
    logger.info("_remote_ssh: took %d seconds." % ( t.seconds,))
        
    return (status,output,stderr)

def _remote_drush(site, args):
    """ run drush command <drush args> on remote site"""
    uri = site.short_name
    if uri == 'default':
        uri = ''
        
    cmd = "drush --root='%s' --uri='http://%s/%s' %s" % (site.platform.path.strip(),
                                                             site.platform.host.strip(),
                                                             uri.strip(), args)
    return _remote_ssh(site.platform, cmd)

def _rsync_pull(platform, remote, local):
    path = "%s:%s" % (platform.canonical_host, remote)
    cmd = ['rsync','--archive', '-pv', path, local]
    logger.info("_rsync_pull: from %s remote=%s local=%s" % ( platform, remote, local))
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    output,stderr = process.communicate()
    status = process.poll()
    return (status,output,stderr)

def _rsync_push(platform, local, remote):
    logger.info("_rsync_push: to %s remote=%s local=%s" % ( platform, remote, local))
    path = "%s:%s" % (platform.canonical_host, remote)
    cmd = ['rsync','--archive', '-pv', local, path]
    
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    output,stderr = process.communicate()
    status = process.poll()
    return (status,output,stderr)

def verify(site):
    (status, out, err) = _remote_drush(site, "vget maintenance_mode")

    site.set_flag('unqueried')

    (status, out, err) = _remote_drush(site, "vget site_name")
    if status == 0:
        site.long_name = parse_vget('site_name', out)
        site.set_flag('ok')
        site.unset_flag('unqueried')
    else:
        site.unset_flat('ok')

    site.save()
    
    if status == 0:
        x = parse_vget('maintenance_mode', out)
        if x == 1:
            site.set_flag('maintenance')
        else:
            site.unset_flag('maintenance')

    else:
        """ problem with the site"""
        pass


    (status, out, err) = _remote_drush(site, "vget site_mail")
    if status == 0:
        site.contact_email = parse_vget('site_mail', out)
        site.save()

    
       
def enable(site):
    (status, out, err) = _remote_drush(site, "vset maintenance_mode 0")
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
                                     'mysqldump --add-drop-database --single-transaction --databases %s > %s' % ( site.database, remote_tempfile))
    if status > 0:
        logger.error('_backup_db: could not open mysqldump to tempfile on host %s' % (site.platform.host,))
        logger.error(out)
    else:
        local_tempfile = tempfile.mkdtemp()
        logger.info('_backup_db: localtempfile: %s' % (local_tempfile,))
        (s,o,e) = _rsync_pull(site.platform, remote_tempfile, path)
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
        return False

def backup(site):
    """Returns a path to a backup or false if it doesn't succeed."""
    path = tempfile.mkdtemp(prefix='sdt',dir='/tmp/x')

    logger.info('backup: temporary_path=%s' % (path,))
    db = _backup_db(site,path)
    fs = _backup_files(site,path)

    site_name = site.platform.host + '.' + site.short_name

    
    friendly_backup_path = os.path.join('/tmp', site_name + '-' + datetime.datetime.now().strftime('%Y%m%d.%H%M%S'))
    logger.info('backup: destination_path=%s' %(friendly_backup_path,))

    with tarfile.open(friendly_backup_path + '.tgz'):

        pass
    
    #shutil.rmtree( pre_stage )
    #move temporary path to a better name.

    
    return True


def migrate(site, new_platform):

    dest_site = site
    dest_site.platform = new_platform

    backup_result = backup(site)

    if not backup_result:
        logger.info('migrate: backup didn\'t succeed, bail')
        return False

    if not is_clean(dest_site):
        logger.info('migrate: destination site not clean, bail')
        return False

    #create destination site paths.
    result = _create_site_dirs(dest_site)

    #copy site temporary location.
    (status, out, err) = _remote_ssh(site.platform, '[ -L %s ]' % (site.site_symlink(),))

    pre_stage = tempfile.mkdtemp()
    logger.info('migrate: pre_stage area is %d. ' % (pre_stage,))

    #rsync files to pre_stage
    rsync_cmd = 'rsync --archive -p %s:%s %s' % (site.platform.host,
                                                 site.site_dir(),
                                                 pre_stage)

    logger.info('migrate: rsync command: %s' %(rsync_cmd,))

    
    shutil.rmtree( pre_stage )


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
    _remote_ssh(site.platform, '/bin/ln %s %s' % (site.platform.path, site.site_symlink()))
    _remote_ssh(site.platform, 'mkdir %s' % (site.site_dir(), ))
    
    for directory in site.site_files_dir():
        _remote_ssh(site.platform, 'mkdir %s' % (directory, ))
        _remote_ssh(site.platform, 'chmod 2775 %s' % (directory, ))
        
    return True

def _create_site_database(site):
    (status, out, err) = _remote_ssh(site.platform, 'mysql -e "create database %s;"' % (site.database,))
    return status == 0
    
    
def create(site, force=False):
    #create db
    logger.info("create: enter")

    if not is_clean(site):
        return False

    if _create_site_database(site):
         
        logger.info("create: sitedir: %s" % (site.site_dir(),))
        if _create_site_dirs(site):

            install_status, output, err = _remote_drush(site, "site-install --site-name='%s' --sites-subdir='%s' %s"
                                                        %( site.long_name,
                                                           self.platform.host + '.' +  self.short_name,
                                                           site.profile) )
            if install_status:
                return True
            else:
                logger.error("create(): create site failed. %s" %(output,))
        else:
            logger.error("create(): create sitedirs failed")
            
        delete_site(site)

    else:
        logger.error('create database failed %s' % (out,))
        return False

    
    #drush --uri=http://localhost/foo site-install --sites-subdir=localhost.foo  --site-name=foo psu_primary 

    logger.info("create: leave")
    
    
def delete_site(site):
    logger.debug("delete_site(): called")

    if site.short_name == 'default':
        logger.error("delete_site(): site=%s default sites can't be deleted." %(site,))
        return False

    if is_clean(site):
        logger.error("delete_site(): site=%s is already clean." %(site,))
        return True


    #todo: report more nicely about specific exit statuses.
    
    _remote_ssh(site.platform, 'rm -Rf %s' % (site.site_dir(),))
    _remote_ssh(site.platform, 'unlink %s' % (site.site_symlink(),))
    _remote_ssh(site.platform, 'mysql -e "drop database %s;"' % (site.database,))

    return True
