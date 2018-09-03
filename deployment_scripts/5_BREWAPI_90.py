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


def add_index_to_table(table_name, index_name, index_attrs):
    table_name = table_name
    statement = "SHOW INDEX FROM {TABLE_NAME} WHERE Key_name = '{INDEX_NAME}'".format(TABLE_NAME=table_name,
                                                                                      INDEX_NAME=index_name)
    response = rds_client.execute_statement(
        secretArn=db_secret_arn,
        database=db_name,
        resourceArn=db_arn,
        sql=statement
    )

    if not response['records']:
        statement = "CREATE INDEX {INDEX_NAME} ON {TABLE_NAME} ({INDEX_ATTRS})".format(INDEX_NAME=index_name,
                                                                                       TABLE_NAME=table_name,
                                                                                       INDEX_ATTRS=", ".join(index_attrs))
        print('Creating index in table: ', table_name)
        response = rds_client.execute_statement(
            secretArn=db_secret_arn,
            database=db_name,
            resourceArn=db_arn,
            sql=statement
        )
        return response
    return response


def change_primary_key(table_name, keys):
    statement = "ALTER TABLE {TABLE_NAME} DROP PRIMARY KEY, ADD PRIMARY KEY({KEYS});".format(
        TABLE_NAME=table_name,
        KEYS=", ".join(keys)
    )
    print('Changing primary key in table: ', table_name)
    response = rds_client.execute_statement(
        secretArn=db_secret_arn,
        database=db_name,
        resourceArn=db_arn,
        sql=statement
    )


def deploy_service(service):
    print(service)
    os.chdir('services/{SERVICE}'.format(SERVICE=service))
    cmd = "sls deploy --stage {STAGE}".format(STAGE=stage)
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    print(str(out))
    if exitcode:
        print(err)
    os.chdir('../..')

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

    # Adding index to tables
    items = [
        ("on_hand", "by_created_on_and_supplier_id", ("created_on", "supplier_id")),
        ("production", "by_production_date_and_supplier_id", ("production_date", "supplier_id"),
            ("entity_id", "brand_id", "package_type_id")),
        ("adjustments", "by_adjustment_date_and_supplier_id", ("adjustment_date", "supplier_id"),
            ("entity_id", "brand_id", "package_type_id")),
        ("sales", "by_entity_id_and_supplier_id", ("entity_id", "supplier_id"),
            ("entity_id", "brand_id", "package_type_id")),
        ("sales", "by_sale_date_and_supplier_id", ("sale_date", "supplier_id")),
    ]

    for item in items:
        table_name = item[0]
        index_name = item[1]
        index_attrs = item[2]

        add_index_to_table(table_name, index_name, index_attrs)

        try:
            primary_key = item[3]
            change_primary_key(table_name, primary_key)
        except IndexError:
            pass

    print("Deploying services")
    services = [
        "on_hand",
        # "production",
        # "adjustments",
        # "sales",
    ]

    for service in services:
        deploy_service(service)

    print("\n\n")
    print("* * * * * * * * * * *")
    print("5-BREWAPI-90 Changes are updated successfully")
    print("* * * * * * * * * * *")
