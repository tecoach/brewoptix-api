# The Global Secondary Index of OnHand table is wrong
# its set to `by_supplier_id_and_product_id`
# it has to be only `by_supplier_id` as `product_id` attribute was removed from the model
# this script creates the new GSI and deletes the only one, non-destructively

import boto3
import sys
import os
import shlex
from subprocess import Popen, PIPE
import time
from botocore.exceptions import ClientError

# Helper functions #

def get_exitcode_stdout_stderr(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    exitcode = proc.returncode

    return exitcode, out, err

# -------------------- #


def create_dist_table(dynamo_client, table_name):
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


args = sys.argv
if len(args) >= 3:
    region = args[1]
    stage = args[2]
    os.environ['STAGE'] = stage

    dynamodb = boto3.client('dynamodb', region_name=region)

    print('Create brewoptix-distributors table')
    create_dist_table(dynamodb, 'brewoptix-distributors')
    wait_till_creation(dynamodb, 'brewoptix-distributors')

    print("creating GSI: by_distributor_id_and_order_date")
    dynamodb.update_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'distributor_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'order_date',
                'AttributeType': 'N'
            }
        ],
        TableName='brewoptix-purchase-orders',
        GlobalSecondaryIndexUpdates=[
            {
                'Create': {
                    'IndexName': 'by_distributor_id_and_order_date',
                    'KeySchema': [
                        {
                            'AttributeName': 'distributor_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'order_date',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 2,
                        'WriteCapacityUnits': 2
                    }
                }
            }
        ]
    )
    time.sleep(300)
    print("creating GSI: by_distributor_id_and_pack_date")
    dynamodb.update_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'distributor_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'pack_date',
                'AttributeType': 'N'
            }
        ],
        TableName='brewoptix-purchase-orders',
        GlobalSecondaryIndexUpdates=[
            {
                'Create': {
                    'IndexName': 'by_distributor_id_and_pack_date',
                    'KeySchema': [
                        {
                            'AttributeName': 'distributor_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'pack_date',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 2,
                        'WriteCapacityUnits': 2
                    }
                }
            }
        ]
    )
    time.sleep(300)
    print("creating GSI: by_distributor_id_and_ship_date")
    dynamodb.update_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'distributor_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'ship_date',
                'AttributeType': 'N'
            }
        ],
        TableName='brewoptix-purchase-orders',
        GlobalSecondaryIndexUpdates=[
            {
                'Create': {
                    'IndexName': 'by_distributor_id_and_ship_date',
                    'KeySchema': [
                        {
                            'AttributeName': 'distributor_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'ship_date',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 2,
                        'WriteCapacityUnits': 2
                    }
                }
            }
        ]
    )

