import shlex

def parse_vget(variable, output):
    for line in output.split('\n'):
        if line.find(variable + ':') > -1:
            quoted = line.replace(variable + ':','').strip()
            return quoted.strip('"')
    return False



    
    
