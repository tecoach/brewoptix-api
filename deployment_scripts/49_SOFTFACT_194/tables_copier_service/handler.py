import boto3
from botocore.exceptions import ClientError
import time
import random


def copy_items(dynamo_client, source_table, dest_table, obj_type,
               segment, total_segments):
    """Adds obj_type to source item and saves to dest_table"""
    print("Copy items from table: {SRC_TABLE} to {DEST_TABLE} "
          "for Object Type: {OBJ_TYPE}".format(SRC_TABLE=source_table,
                                               DEST_TABLE=dest_table,
                                               OBJ_TYPE=obj_type))

    # copy over item
    item_count = 0
    paginator = dynamo_client.get_paginator('scan')

    for page in paginator.paginate(
            TableName=source_table,
            Select='ALL_ATTRIBUTES',
            ReturnConsumedCapacity='NONE',
            ConsistentRead=True,
            Segment=segment,
            TotalSegments=total_segments,
            PaginationConfig={"PageSize": 25}):

        batch = []
        for item in page['Items']:
            item_count += 1
            item['obj_type'] = {'S': obj_type}
            batch.append({
                'PutRequest': {
                    'Item': item
                }
            })

        print("Process segment %d of %d. putting %d items into %s" % (segment, total_segments, item_count, dest_table))
        if batch:
            backoff_waits = [0, ]
            while True:
                try:
                    dynamo_client.batch_write_item(
                        RequestItems={
                           dest_table: batch
                        }
                    )
                    backoff_waits = [0, ]
                    break
                except ClientError as ex:
                    if ex.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                        print("ProvisionedThroughputExceededException: waiting 1sec")
                        backoff_waits.append(2 ** (len(backoff_waits) - 1))
                        time.sleep(backoff_waits[random.randint(0, len(backoff_waits) - 1)])
                    else:
                        raise ex


def copy_tables(event, context):
    print(event)
    region = event['region']
    source_table = event['source_table']
    dest_table = event['dest_table']
    obj_type = event['obj_type']
    total_segments = event['total_segments']

    client = boto3.client('dynamodb', region_name=region)

    for segment in range(total_segments):
        copy_items(client, source_table, dest_table, obj_type, segment, total_segments)
