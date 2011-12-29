from util import parse_vget
import subprocess
import logging

logger = logging.getLogger(__name__)

def _remote_ssh(cmd):
    """ returns tuple of (exit status, stdout, sdterr) """
    logger.info("_remote_ssh: enter")
    logger.info("_remote_ssh: %s" %(cmd,) )
    process = subprocess.Popen(cmd,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    output,stderr = process.communicate()
    status = process.poll()
    logger.info("_remote_ssh: returned %d" %(status,))
    return (status,output,stderr)


def _remote_drush(site, args):
    """ run drush command <drush args> on remote site"""
    uri = site.short_name
    if uri == 'default':
        uri = ''
        
    cmd = "drush --root='%s' --uri='http://%s/%s' %s" % (site.platform.path.strip(),
                                                             site.platform.host.strip(),
                                                             uri.strip(), args)
    return _remote_ssh(cmd)

def verify(site):
    (status, out, err) = _remote_drush(site, "vget maintenance_mode")

    if status == 0:
        x = parse_vget('maintenance_mode', out)
        if x == 1:
            site.maintenance_mode = True
        else:
            site.maintenance_mode = False
        site.save()
    else:
        """ problem with the site"""
        pass


    (status, out, err) = _remote_drush(site, "vget site_name")
    if status == 0:
        site.long_name = parse_vget('site_name', out)
        site.save()
        
    
    
def create(site, force=False):
    #create db
    logger.info("create: enter")
    
    (status, out, err) = _remote_ssh('mysql -e "create database %s;"' % (site.database,))


    drush --uri=http://localhost/foo site-install --sites-subdir=localhost.foo  --site-name=foo psu_primary 

    logger.info("create: leave")
    
    
