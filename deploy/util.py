import datetime
import logging
import shlex
import subprocess
import urllib2

logger = logging.getLogger(__name__)

def parse_vget(variable, output):
    """ Extract a desired variable from a 'drush vget'. """
    for line in output.split('\n'):
        if line.find(variable + ':') > -1:
            quoted = line.replace(variable + ':','').strip()
            return quoted.strip('"')
    return False

def parse_status(variable, output):
    """ Extract a desired variable from a 'drush status'. """
    for line in output.split('\n'):
        if line.find(variable) > -1:
            quoted = line.split(':')[-1].strip()
            return quoted.strip('"')
    return False    

def _remote_ssh(platform, cmd):
    """ returns tuple of (exit status, stdout, sdterr) """
    
    #logger.info("_remote_ssh: enter")
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
            
        
        logger.info("_remote_ssh: command output: %s" % (output,))
        logger.info("_remote_ssh: command error: %s" % (stderr,))

    t = datetime.datetime.now() - begin
    logger.info("_remote_ssh: took %d seconds. exit status %d." % ( t.seconds,status))
        
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
    cmd = ['rsync','--archive', '--numeric-ids', '-pv', path, local]
    logger.info("_rsync_pull: from %s remote=%s local=%s" % ( platform, remote, local))
    begin = datetime.datetime.now()
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    output,stderr = process.communicate()
    status = process.poll()
    t = datetime.datetime.now() - begin
    logger.info('_rsync_pull: took %d seconds. returned %d.' % (t.seconds, status))
    return (status,output,stderr)

def _rsync_push(platform, local, remote):
    logger.info("_rsync_push: to %s remote=%s local=%s" % ( platform, remote, local))
    path = "%s:%s" % (platform.canonical_host, remote)
    cmd = ['rsync','--archive', '--numeric-ids', '-pv', local, path]
    begin = datetime.datetime.now()
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    output,stderr = process.communicate()
    status = process.poll()
    t = datetime.datetime.now() - begin
    logger.info('_rsync_pull: took %d seconds. returned %d.' % (t.seconds, status))
    return (status,output,stderr)


def _check_site(site):
    logger.info('_check_site: site: ' + str(site))

    http_status = 200
    
    req = urllib2.Request(str(site))
    try:
        urllib2.urlopen(req)
    except urllib2.URLError, e:
        http_status = e.code
        logger.critical('_check_site: site=%s httpstatus=%d' % (str(site),http_status))
        
    return http_status == 200
