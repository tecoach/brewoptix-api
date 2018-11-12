import boto3


def copy_items(dynamo_client, source_table, dest_table,
               segment, total_segments, reserved_keys_convertion=False):
    print("Copy items from table: {SRC_TABLE} to {DEST_TABLE}".format(SRC_TABLE=source_table,
                                                                      DEST_TABLE=dest_table))

    def convert_reserved_to_underscore(item):
        reserved_keys_map = {
            'EntityID': 'entity_id',
            'Version': 'version',
            'PreviousVersion': 'previous_version',
            'Active': 'active',
            'Latest': 'latest',
            'ChangedByID': 'changed_by_id',
            'ChangedOn': 'changed_on'
        }

        for reserved_key, new_key in reserved_keys_map.items():
            if reserved_key in item:
                item[new_key] = item.pop(reserved_key)

        return item

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
        if reserved_keys_convertion:
            for item in page['Items']:
                item_count += 1
                batch.append({
                    'PutRequest': {
                        'Item': convert_reserved_to_underscore(item)
                    }
                })
        else:
            for item in page['Items']:
                item_count += 1
                batch.append({
                    'PutRequest': {
                        'Item': item
                    }
                })

        print("Process %d put %d items into %s" % (segment, item_count, dest_table))
        if batch:
            dynamo_client.batch_write_item(
                RequestItems={
                   dest_table: batch
                }
            )


def copy_tables(event, context):
    print(event)
    region = event['region']
    source_table = event['source_table']
    dest_table = event['dest_table']
    total_segments = event['total_segments']
    reserved_keys_convertion = event['reserved_keys_convertion']

    client = boto3.client('dynamodb', region_name=region)

    for segment in range(total_segments):
        copy_items(client, source_table, dest_table, segment, total_segments, reserved_keys_convertion)
