import sys
import boto3
from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util
import os
import json

data_common = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
             "data_common")
print(data_common)
sys.path.append(data_common)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data_common.notifications import SnsNotifier

args = sys.argv
if len(args) >= 2:
    stage = args[1]
    os.environ['STAGE'] = stage

    config_filename = 'config.' + stage + '.json'
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_filepath = os.path.join(parent_dir, config_filename)

    with open(config_filepath, 'r') as fp:
        config = json.load(fp)

    region = config["REGION"]

    dynamo_client = boto3.resource('dynamodb', region_name=region)

    dynamo_table_name = 'brewoptix-counts'

    notifier = SnsNotifier(region_name=region)

    resp = None
    while True:
        if not resp:
            resp = dynamo_client.Table(dynamo_table_name).scan(
                FilterExpression=Attr('latest').eq(True) & Attr('active').eq(False)
            )
        elif resp and 'LastEvaluatedKey' in resp:
            resp = dynamo_client.Table(dynamo_table_name).scan(
                FilterExpression=Attr('latest').eq(True) & Attr('active').eq(False),
                ExclusiveStartKey=resp['LastEvaluatedKey']
            )
        else:
            break

        items = resp['Items']
        print("Sending notifications for {N} items".format(N=len(items)))

        for item in items:
            item = json_util.loads(item)

            # pull previous version
            entity_id = item['entity_id']
            previous_version = item['previous_version']

            resp = dynamo_client.Table(dynamo_table_name).query(
                KeyConditionExpression=Key('entity_id').eq(entity_id) & Key('version').eq(previous_version)
            )

            obj = json_util.loads(resp['Items'][0])

            notifier.sns_publish("counts", obj)
