import shlex

def parse_vget(variable, output):
    for line in output.split('\n'):
        if line.find(variable + ':') > -1:
            return line.replace(variable + ':','').strip()
    return False



    
    
