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


def remove_failed():
    print('''
 |  ____/\   |_   _| |    |  ____|  __ \                 
 | |__ /  \    | | | |    | |__  | |  | |                
 |  __/ /\ \   | | | |    |  __| | |  | |                
 | | / ____ \ _| |_| |____| |____| |__| |                
 |_|/_/    \_\_____|______|______|_____/                 

Failed to remove all services.
''')


def remove_success():
    print('''
  / ____| |  | |/ ____/ ____|  ____|  ____|  __ \|  ____|  __ \ 
 | (___ | |  | | |   | |    | |__  | |__  | |  | | |__  | |  | |
  \___ \| |  | | |   | |    |  __| |  __| | |  | |  __| | |  | |
  ____) | |__| | |___| |____| |____| |____| |__| | |____| |__| |
 |_____/ \____/ \_____\_____|______|______|_____/|______|_____/ 

All services successfully removed
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

# remove other services
services = [
    f for f in os.listdir(services_dir)
    if os.path.isdir(f) and os.path.isfile(f + '/serverless.yml') and f.startswith('q_')
] + [
    f for f in os.listdir(services_dir)
    if os.path.isdir(f) and os.path.isfile(f + '/serverless.yml') and not f.startswith('q_')
]

for item in services:
    print("Starting removal of service: ", item)
    item_path = os.path.join(services_dir, item)

    os.chdir(item_path)
    if stage:
        _, sls_failure = run_command('sls remove -v --stage {STAGE}'.format(STAGE=stage))
    else:
        _, sls_failure = run_command('sls remove -v')

    if sls_failure:
        print('ERROR: Failed to remove {} service'.format(item))

os.chdir(os.pardir)
print("Starting removal of service Auth")

if stage:
    _, sls_failure = run_command('sls remove -v --stage {STAGE}'.format(STAGE=stage))
else:
    _, sls_failure = run_command('sls remove -v')

if sls_failure:
    remove_failed()
    sys.exit(0)

remove_success()
