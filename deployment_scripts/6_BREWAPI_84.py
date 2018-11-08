import sys
import json
import os
import time
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from dynamodb_json import json_util
import maya

sys.path.append('data_dynamodb')
sys.path.append('.')

from dynamodb_repository import DynamoRepository

# helper functions
# --------------- #

import shlex
from subprocess import Popen, PIPE


def get_exitcode_stdout_stderr(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    exitcode = proc.returncode
    #
    return exitcode, out, err


def execute_sql(statement):
    for i in range(3):
        try:
            response = rds_client.execute_statement(
                secretArn=db_secret_arn,
                database=db_name,
                resourceArn=db_arn,
                sql=statement
            )

            return response
        except ClientError as ex:
            print(ex)
            print("Unknown table" not in str(ex))
            print("Attempt {0}".format(i))
            if ex.response['Error']['Code'] == 'BadRequestException':
                # if "Unknown table" in str(ex):
                #     # Table not in database, break out of loop
                #     break
                pass  # Assuming Connection Link error
            else:
                raise ex

            time.sleep(30)
    else:
        raise Exception("Mysql Connection Link Failure. Tried 3 times and failed")


def deploy_service(service):
    print("Deploying service: ")
    print(service)
    os.chdir('services/{SERVICE}'.format(SERVICE=service))
    cmd = "sls deploy --stage {STAGE}".format(STAGE=stage)
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    print(str(out))
    if exitcode:
        print(err)
    os.chdir('../..')


def remove_service(service):
    print("Removing service: ")
    print(service)
    os.chdir('services/{SERVICE}'.format(SERVICE=service))
    cmd = "sls remove --stage {STAGE}".format(STAGE=stage)
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    print(str(out))
    if exitcode:
        print(err)
        return False
    os.chdir('../..')
    return True

# --------------- #

args = sys.argv
if len(args) >= 3:
    region = args[1]
    stage = args[2]
    os.environ['STAGE'] = stage

    print("Deploying on_hand service")
    success = remove_service("on_hand")
    if success:
        deploy_service("on_hand")

    print("\n\n")
    print("* * * * * * * * * * *")
    print("6-BREWAPI-84 Changes are updated successfully")
    print("* * * * * * * * * * *")
