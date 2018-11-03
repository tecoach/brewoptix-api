# The Global Secondary Index of OnHand table is wrong
# its set to `by_supplier_id_and_product_id`
# it has to be only `by_supplier_id` as `product_id` attribute was removed from the model
# this script creates the new GSI and deletes the only one, non-destructively

import boto3
from botocore.exceptions import ClientError
from time import sleep
import sys
import os
import shlex
from subprocess import Popen, PIPE


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


args = sys.argv
if len(args) >= 3:
    region = args[1]
    stage = args[2]
    os.environ['STAGE'] = stage

    dynamodb = boto3.client('dynamodb', region_name=region)

    print("creating GSI: by_supplier_id")
    dynamodb.update_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'supplier_id',
                'AttributeType': 'S'
            },
        ],
        TableName='brewoptix-on-hand-inventory',
        GlobalSecondaryIndexUpdates=[
            {
                'Create': {
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
                }
            }
        ]
    )

    for _ in range(15):
        sleep(60)
        print("Deleting GSI: by_supplier_id_and_product_id")
        try:
            # delete by_supplier_id_and_product_id
            dynamodb.update_table(
                TableName='brewoptix-on-hand-inventory',
                GlobalSecondaryIndexUpdates=[
                    {
                        'Delete': {
                            'IndexName': 'by_supplier_id_and_product_id'
                        }
                    }
                ]
            )
        except ClientError as e:

            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                break

            if not (e.response['Error']['Code'] == 'ResourceInUseException' or
                    e.response['Error']['Code'] == 'LimitExceededException'):
                raise e

            print("Attempting again...")

    print("deploying on_hand service")
    os.chdir('services/on_hand')
    cmd = "sls deploy --stage {STAGE}".format(STAGE=stage)
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)
    print(str(out))
    if exitcode:
        print(err)
    os.chdir('../..')
