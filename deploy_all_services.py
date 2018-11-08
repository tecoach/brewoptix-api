import os
import subprocess
import shlex
import sys


def run_command(command):
    failure = False
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        x = process.poll()
        # print(output, x, output == '' and not x)
        if output == b'' and not process.poll():
            break
        if output:
            print(output.strip())
            if not failure:
                failure = b'Serverless: Operation failed!' in output.strip() or b'Serverless Error' in output.strip()
        else:
            break

    rc = process.poll()
    return rc, failure


def deploy_failed():
    print('''   _____ ______ _______      _______ _____ ______  _____ 
  / ____|  ____|  __ \ \    / /_   _/ ____|  ____|/ ____|
 | (___ | |__  | |__) \ \  / /  | || |    | |__  | (___  
  \___ \|  __| |  _  / \ \/ /   | || |    |  __|  \___ \ 
  ____) | |____| | \ \  \  /   _| || |____| |____ ____) |
 |_____/|______|______\_ \/   ______\____________|_____/ 
 |  __ \|  ____|  __ \| |    / __ \ \   / /              
 | |  | | |__  | |__) | |   | |  | \ \_/ /               
 | |  | |  __| |  ___/| |   | |  | |\   /                
 | |__| | |____| |    | |___| |__| | | |                 
 |______|__________ _ |________________|                 
 |  ____/\   |_   _| |    |  ____|  __ \                 
 | |__ /  \    | | | |    | |__  | |  | |                
 |  __/ /\ \   | | | |    |  __| | |  | |                
 | | / ____ \ _| |_| |____| |____| |__| |                
 |_|/_/    \_\_____|______|______|_____/                 

Failed to deploy all services.
''')


def deploy_success():
    print('''
       _____ ______ _______      _______ _____ ______  _____        
  / ____|  ____|  __ \ \    / /_   _/ ____|  ____|/ ____|       
 | (___ | |__  | |__) \ \  / /  | || |    | |__  | (___         
  \___ \|  __| |  _  / \ \/ /   | || |    |  __|  \___ \        
  ____) | |____| | \ \  \  /   _| || |____| |____ ____) |       
 |_____/|______|______\_ \/   ______\____________|_____/        
 |  __ \|  ____|  __ \| |    / __ \ \   / /                     
 | |  | | |__  | |__) | |   | |  | \ \_/ /                      
 | |  | |  __| |  ___/| |   | |  | |\   /                       
 | |__| | |____| |    | |___| |__| | | |                        
 |______|______|______|____________ ______ _____  ______ _____  
  / ____| |  | |/ ____/ ____|  ____|  ____|  __ \|  ____|  __ \ 
 | (___ | |  | | |   | |    | |__  | |__  | |  | | |__  | |  | |
  \___ \| |  | | |   | |    |  __| |  __| | |  | |  __| | |  | |
  ____) | |__| | |___| |____| |____| |____| |__| | |____| |__| |
 |_____/ \____/ \_____\_____|______|______|_____/|______|_____/ 

All services successfully deployed
    ''')


services_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'services'
)

stage = None
args = sys.argv
if len(args) > 1 and args[1] == '--stage':
    stage = args[2]

os.chdir('services')
print("Starting deploy of service Auth")

if stage:
    _, sls_failure = run_command('sls deploy -v --stage {STAGE}'.format(STAGE=stage))
else:
    _, sls_failure = run_command('sls deploy -v')

if sls_failure:
    deploy_failed()
    sys.exit(0)

# deploy other services

services = [
    f for f in os.listdir(services_dir)
    if os.path.isdir(f) and os.path.isfile(f + '/serverless.yml') and not f.startswith('q_')
] + [
    f for f in os.listdir(services_dir)
    if os.path.isdir(f) and os.path.isfile(f + '/serverless.yml') and f.startswith('q_')
]


for item in services:
    print("Starting deploy of service: ", item)
    item_path = os.path.join(services_dir, item)

    os.chdir(item_path)
    if stage:
        _, sls_failure = run_command('sls deploy -v --stage {STAGE}'.format(STAGE=stage))
        print('sls deploy -v --stage {STAGE}'.format(STAGE=stage))
    else:
        _, sls_failure = run_command('sls deploy -v')
        print('sls deploy -v'.format(STAGE=stage))

    if sls_failure:
        deploy_failed()
        sys.exit(0)

deploy_success()
