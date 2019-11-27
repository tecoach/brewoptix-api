import boto3
from botocore.exceptions import ClientError
import sys
import json
import os
import time
import shlex
from subprocess import Popen, PIPE


tables = [
    'brewoptix-users',
    'brewoptix-suppliers',
    'brewoptix-brands',
    'brewoptix-package-types',
    'brewoptix-products',
    'brewoptix-on-hand-inventory',
    'brewoptix-adjustment-inventory',
    'brewoptix-payments',
    'brewoptix-containers',
    'brewoptix-retail-packages',
    'brewoptix-production',
    'brewoptix-counts',
    'brewoptix-purchase-orders',
    'brewoptix-supplier-distributors',
    'brewoptix-distributors',
    'brewoptix-merchandise'
]


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


def create_table(dynamo_client, table_name):
    """
    Creates table with schema EntityID, Version as hash and range keys
    :param table_name:
    :return:
    """
    print("Create table: {TABLE}".format(TABLE=table_name))
    try:
        resp = dynamo_client.describe_table(
            TableName=table_name,
        )

        for i in range(6):
            if resp['Table']['TableStatus'] != 'DELETING':
                if i == 0:
                    print("Table {TABLE} already exists".format(TABLE=table_name))
                return
            else:
                time.sleep(10)

    except ClientError as ex:
        if not ex.response['Error']['Code'] == 'ResourceNotFoundException':
            raise ex

    resp = dynamo_client.create_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'EntityID',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'Version',
                'AttributeType': 'S'
            }
        ],
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'EntityID',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'Version',
                'KeyType': 'RANGE'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 20,
            'WriteCapacityUnits': 20
        }
    )
    return resp


def copy_items(source_table, dest_table,
               stage, region, total_segments,
               reserved_keys_convertion=False):
    print("Copy items from table: {SRC_TABLE} to {DEST_TABLE}".format(SRC_TABLE=source_table,
                                                                      DEST_TABLE=dest_table))
    lambda_client = boto3.client('lambda', region_name=region)

    response = lambda_client.invoke(
        FunctionName="{STAGE}-BREWOPTIX-TABLES-COPIER-FN-copy-tables".format(STAGE=stage),
        InvocationType='Event',
        Payload=json.dumps(
            {
                'source_table': source_table,
                'dest_table': dest_table,
                'region': region,
                'total_segments': total_segments,
                'reserved_keys_convertion': reserved_keys_convertion,
            }
        )
    )

    return response


def get_items_count(dynamo_client, table_name):
    item_count = 0
    paginator = dynamo_client.get_paginator('scan')

    for page in paginator.paginate(
            TableName=table_name,
            Select='COUNT',
            ReturnConsumedCapacity='NONE',
            ConsistentRead=True,
            PaginationConfig={"PageSize": 25}):

        item_count += page['Count']
    return item_count


def delete_table(dynamo_client, table_name):
    print("Delete table: {TABLE}".format(TABLE=table_name))
    try:
        resp = dynamo_client.describe_table(
                TableName=table_name,
            )
        if resp['Table']['TableStatus'] != 'DELETING':
            # delete
            dynamo_client.delete_table(
                TableName=table_name
            )
    except ClientError as ex:
        if not ex.response['Error']['Code'] == 'ResourceNotFoundException':
            raise ex


def backup(table):
    return table + '-backup'


if __name__ == "__main__":
    args = sys.argv
    region = args[1]
    stage = args[2]
    os.environ['STAGE'] = stage
    total_segments = int(args[3])
    client = boto3.client('dynamodb', region_name=region)

    item_counts = {}
    for table in tables:
        print(table)
        item_counts[table] = get_items_count(client, table)
        print("table: {TABLE}, item_count: {COUNT}".format(TABLE=table, COUNT=item_counts[table]))
    # create backup tables
    for table in tables:
        create_table(client, backup(table))


    # wait for all tables to be created
    for _ in range(90):
        num_active = 0
        for table in tables:
            try:
                resp = client.describe_table(
                    TableName=table,
                )
                if resp['Table']['TableStatus'] == 'ACTIVE':
                    num_active += 1
            except ClientError as ex:
                if ex.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise ex

        if num_active == len(tables):
            break

        time.sleep(10)

    # copy items from tables
    for table in tables:
        copy_items(table, backup(table), stage, region, total_segments, False)

    # check and wait till all counts of all tables are same in original vs backup
    for _ in range(90):
        backup_item_counts = {}
        for table in tables:
            backup_item_counts[backup(table)] = get_items_count(client, backup(table))

        if all(backup_item_counts[backup(table)] == item_counts[table] for table in tables):
            break

        time.sleep(10)
    else:
        print("Aborting. Waited for too long. Unable to verify count in backup to be same as originals. Deleting backups")

        # delete backup tables
        for table in tables:
            delete_table(client, backup(table))
        sys.exit(1)

    # delete original tables
    for table in tables:
        delete_table(client, table)

    # wait for all tables to be deleted
    for _ in range(90):
        num_deleted = 0
        for table in tables:
            try:
                resp = client.describe_table(
                    TableName=table,
                )
            except ClientError as ex:
                if ex.response['Error']['Code'] == 'ResourceNotFoundException':
                    num_deleted += 1

        if num_deleted == len(tables):
            break

        time.sleep(10)

    # create tables with new schema
    print("Creating tables with modified schema (entity_id, version)")
    exitcode, out, err = get_exitcode_stdout_stderr(
        'python ./create_tables_107.py {REGION} {STAGE}'.format(
            REGION=region,
            STAGE=stage
        ))

    print(exitcode, out, err)

    time.sleep(10)

    # copy items from tables
    new_original_items_count = {}
    for table in tables:
        copy_items(backup(table), table, stage, region, total_segments, True)


    # check and wait till all counts of all tables are same in original vs backup
    for _ in range(90):
        backup_item_counts = {}
        for table in tables:
            backup_item_counts[backup(table)] = get_items_count(client, backup(table))
            new_original_items_count[table] = get_items_count(client, table)

        if all(backup_item_counts[backup(table)] == new_original_items_count[table] for table in tables):
            break

        time.sleep(10)
    else:
        print("Something happened when converting and copying from backup to tables with new schema")

    # delete backup tables
    for table in tables:
        delete_table(client, backup(table))
