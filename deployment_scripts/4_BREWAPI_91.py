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

# --------------- #

args = sys.argv
if len(args) >= 3:
    region = args[1]
    stage = args[2]
    os.environ['STAGE'] = stage

    # create a logs folder for storing failure records
    filedir = os.path.dirname(os.path.realpath(__file__))

    if not os.path.exists(os.path.join(filedir, "logs")):
        os.mkdir(os.path.join(filedir, "logs"))

    rds_client = boto3.client('rds-data')

    config_filename = 'config.' + stage + '.json'
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_filepath = os.path.join(parent_dir, config_filename)

    with open(config_filepath, 'r') as fp:
        config = json.load(fp)

    try:
        db_arn = config["AURORA_DB_ARN"]
        db_secret_arn = config["AURORA_DB_SECRET_ARN"]
        db_name = config["AURORA_DB_NAME"]
    except KeyError as ex:
        print("""Missing key-val pairs AURORA_DB_ARN, AURORA_DB_SECRET_ARN and/or AURORA_DB_NAME in {CONFIG}
            Unable to create SQL Tables""".format(CONFIG=config_filename))
        raise ex

    print("Checking for index 'by_entity_id_and_supplier_id' in adjustments and production tables\n"
          "Creating if not exists")
    # Adding index to adjustments
    table_name = "adjustments"
    statement = "SHOW INDEX FROM adjustments WHERE Key_name = 'by_entity_id_and_supplier_id'"
    response = rds_client.execute_statement(
        secretArn=db_secret_arn,
        database=db_name,
        resourceArn=db_arn,
        sql=statement
    )

    if not response['records']:
        statement = "CREATE INDEX by_entity_id_and_supplier_id ON adjustments (entity_id, supplier_id)"
        print('Creating index in table: ', table_name)
        response = rds_client.execute_statement(
            secretArn=db_secret_arn,
            database=db_name,
            resourceArn=db_arn,
            sql=statement
        )

    # Adding index to production
    table_name = "production"
    statement = "SHOW INDEX FROM production WHERE Key_name = 'by_entity_id_and_supplier_id'"
    response = rds_client.execute_statement(
        secretArn=db_secret_arn,
        database=db_name,
        resourceArn=db_arn,
        sql=statement
    )

    if not response['records']:
        statement = "CREATE INDEX by_entity_id_and_supplier_id ON production (entity_id, supplier_id)"
        print('Creating index in table: ', table_name)
        response = rds_client.execute_statement(
            secretArn=db_secret_arn,
            database=db_name,
            resourceArn=db_arn,
            sql=statement
        )

    print("Deploying services")

    print("adjustments")
    os.chdir('services/adjustments')
    cmd = "sls deploy --stage {STAGE}".format(STAGE=stage)
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    print(str(out))
    if exitcode:
        print(err)
    os.chdir('../..')

    print("q_adjustments")
    os.chdir('services/q_adjustments')
    cmd = "sls deploy --stage {STAGE}".format(STAGE=stage)
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    print(str(out))
    if exitcode:
        print(err)
    os.chdir('../..')

    print("production")
    os.chdir('services/production')
    cmd = "sls deploy --stage {STAGE}".format(STAGE=stage)
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    print(str(out))
    if exitcode:
        print(err)
    os.chdir('../..')

    print("q_production")
    os.chdir('services/q_production')
    cmd = "sls deploy --stage {STAGE}".format(STAGE=stage)
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    print(str(out))
    if exitcode:
        print(err)
    os.chdir('../..')

    print("\n\n")
    print("* * * * * * * * * * *")
    print("4-BREWAPI-91 Changes are updated successfully")
    print("* * * * * * * * * * *")
