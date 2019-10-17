# BREWAPI-73 updates the Adjustments and Production tables with a new field `entity_id`
# This script would drop those tables, apply new schema and regenerate the items
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

sql_tables = ["adjustments", "production"]
dynamo_tables = ["brewoptix-adjustment-inventory", "brewoptix-production"]

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

    dynamo_client = boto3.resource('dynamodb', region_name=region)

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
    except KeyError:
        print("""Missing key-val pairs AURORA_DB_ARN, AURORA_DB_SECRET_ARN and/or AURORA_DB_NAME in {CONFIG}
        Unable to create SQL Tables""".format(CONFIG=config_filename))

    print("Renaming Aurora Tables: ")
    for table_name in sql_tables:
        print(table_name)
        copied_table_name = table_name + '_brewapi_73'
        statement = """SHOW TABLES LIKE '{TABLE_NAME}';""".format(TABLE_NAME=table_name)
        response = execute_sql(statement)
        if response['records']:
            statement = """RENAME TABLE `{TABLE_NAME}` TO `{RENAMED_TABLE}`;""".format(TABLE_NAME=table_name,
                                                                                   RENAMED_TABLE=copied_table_name)
            response = execute_sql(statement)

    # Create SQL tables
    print("Creating Aurora tables: ")
    cmd = "python data_dynamodb/create_tables.py {STAGE}".format(STAGE=stage)
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    print(str(out))
    if exitcode:
        print(err)

    # Get item from dynamodb and insert into SQL table
    print("Getting items from dynamodb")
    repo = DynamoRepository(region_name=region,
                            aurora_db_arn=db_arn,
                            aurora_db_secret_arn=db_secret_arn,
                            aurora_db_name=db_name)

    failed_items_filepath = os.path.join('deployment_scripts/logs', '1_BREWAPI_73_' + maya.now().iso8601().replace(":", "_") + '.txt')
    migration_succeeded = True
    for i, table_name in enumerate(dynamo_tables):
        sql_table_name = sql_tables[i]

        resp = None
        while True:
            if not resp:
                resp = dynamo_client.Table(table_name).scan(
                    FilterExpression=Attr('Latest').eq(True) & Attr('Active').eq(True)
                )
            elif resp and 'LastEvaluatedKey' in resp:
                resp = dynamo_client.Table(table_name).scan(
                    FilterExpression=Attr('Latest').eq(True) & Attr('Active').eq(True),
                    ExclusiveStartKey=resp['LastEvaluatedKey']
                )
            else:
                break

            items = resp['Items']

            for item in items:
                item = json_util.loads(item)
                item['entity_id'] = item['EntityID']

                try:
                    if sql_table_name == "adjustments":
                        repo.process_adjustments_queue(item)
                    elif sql_table_name == "production":
                        repo.process_production_queue(item)
                except KeyError as ex:
                    migration_succeeded = False
                    # possible old entity in table without required keys
                    # please update the entity and try again
                    print("Entity failed to be processed")
                    print("Exception: {EX}".format(EX=str(ex)))
                    with open(failed_items_filepath, 'at') as fp:
                        fp.write(json.dumps(item))
                        fp.write("\n\n")

    if migration_succeeded:
        print("Dropping Aurora Backup Tables: ")

        for table_name in sql_tables:
            table_name = table_name + '_brewapi_73'
            print(table_name)
            statement = """DROP TABLE IF EXISTS `{TABLE_NAME}`;""".format(TABLE_NAME=table_name)
            execute_sql(statement)

        print("Deploying updated services: ")
        print("adjustments")
        os.chdir('services/adjustments')
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

        print("\n\n")
        print("* * * * * * * * * * *")
        print("1-BREWAPI-73 Changes are updated successfully")
        print("* * * * * * * * * * *")
    else:
        print("Data migration failed")
        print("Dropping newly created Aurora Tables and renaming backup tables to original names")
        for table_name in sql_tables:
            print(table_name)
            backup_table_name = table_name + '_brewapi_73'
            statement = """DROP TABLE IF EXISTS `{TABLE_NAME}`;""".format(TABLE_NAME=table_name)
            execute_sql(statement)

            statement = """RENAME TABLE `{TABLE_NAME}` TO `{RENAMED_TABLE}`;""".format(TABLE_NAME=backup_table_name,
                                                                          RENAMED_TABLE=table_name)
            execute_sql(statement)

        print("\n\n")
        print("* * * * * * * * * * *")
        print("1-BREWAPI-73 Changes Failed. Reverted back to previous state.")
        print("* * * * * * * * * * *")
