import os

# os.system('docker network inspect tangonet')

import subprocess
import json

# out=subprocess.Popen(['docker','network','inspect','tangonet'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
# stdout,stderr=out.communicate()
out=(subprocess.getoutput('docker network inspect tangonet'))[1:-1]

outJSON=json.loads(out)

containers=outJSON['Containers']

ip=''

for values in containers.values():
    if(values['Name']=='midcbf-databaseds'):
        ip=values['IPv4Address'][0:-3]


cmd="export TANGO_HOST="+ip+":10000"
# cmd=ip+":10000"
print("run the following command:")
print(cmd)
#os.system(cmd)
# os.environ['TANGO_HOST']=cmd
# os.putenv("TANGO_HOST",cmd)

# os.system('bash -c \'echo "export a=100000" >> ~/.bashrc\'')
# os.system('bash -c \'source ~/.bashrc\'')