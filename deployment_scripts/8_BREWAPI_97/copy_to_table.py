import sys
import os
import boto3
from botocore.exceptions import ClientError
from dynamodb_json import json_util
import time
import json

# Tables cannot be directly renamed in DynamoDb
# We are going to losslessly duplicate a table and delete the old one


def create_supp_dist_table(dynamo_client, table_name):
    resp = dynamo_client.create_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'EntityID',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'Version',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'supplier_id',
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
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'by_supplier_id',
                'KeySchema': [
                    {
                        'AttributeName': 'supplier_id',
                        'KeyType': 'HASH'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 2,
                    'WriteCapacityUnits': 2
                }
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 2,
            'WriteCapacityUnits': 2
        }
    )
    return resp


def wait_till_creation(dynamo_client, table_name):
    for _ in range(90):
        try:
            resp = dynamo_client.describe_table(
                TableName=table_name,
            )
            if resp['Table']['TableStatus'] == 'ACTIVE':
                break
        except ClientError as ex:
            if ex.response['Error']['Code'] != 'ResourceNotFoundException':
                raise ex

        time.sleep(10)


def copy_items(source_table, dest_table,
               stage, region, total_segments=5,
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


args = sys.argv
if len(args) >= 3:
    region = args[1]
    stage = args[2]
    os.environ['STAGE'] = stage

    dynamo_client = boto3.client('dynamodb', region_name=region)

    src_table = "brewoptix-distributors"
    dest_table = "brewoptix-supplier-distributors"

    src_table_items_cnt = get_items_count(dynamo_client, src_table)

    # create new table
    resp = create_supp_dist_table(dynamo_client, dest_table)
    wait_till_creation(dynamo_client, dest_table)

    # copy items from old to new table
    copy_items(src_table, dest_table, stage, region)

    # wait for copy items to succeed
    for _ in range(60):
        dest_table_items_cnt = get_items_count(dynamo_client, dest_table)

        if dest_table_items_cnt == src_table_items_cnt:
            break

        time.sleep(10)
    else:
        print("Aborting. Waited for too long. Unable to verify count in dest table to be same as src table")

    # delete old table
    print("Data move from old to new table succeeded. Deleting old table")
    resp = dynamo_client.delete_table(
            TableName=src_table
        )

    # wait for all tables to be deleted
    for _ in range(90):
        try:
            resp = dynamo_client.describe_table(
                TableName=src_table,
            )
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'ResourceNotFoundException':
                break
            else:
                raise ex

        time.sleep(10)

    print("delete of old distributors table succeeded")
