import sys
import boto3
from boto3.dynamodb.conditions import Attr
from dynamodb_json import json_util
import os

data_common = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
             "data_common")
print(data_common)
sys.path.append(data_common)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data_common.notifications import SnsNotifier

args = sys.argv
if len(args) >= 3:
    region = args[1]
    stage = args[2]
    os.environ['STAGE'] = stage

    dynamo_client = boto3.resource('dynamodb', region_name=region)

    dynamo_table_name = 'brewoptix-purchase-orders'

    notifier = SnsNotifier(region_name=region)

    resp = None
    while True:
        if not resp:
            resp = dynamo_client.Table(dynamo_table_name).scan(
                FilterExpression=Attr('latest').eq(True) & Attr('active').eq(True)
            )
        elif resp and 'LastEvaluatedKey' in resp:
            resp = dynamo_client.Table(dynamo_table_name).scan(
                FilterExpression=Attr('latest').eq(True) & Attr('active').eq(True),
                ExclusiveStartKey=resp['LastEvaluatedKey']
            )
        else:
            break

        items = resp['Items']
        print("Sending notifications for {N} items".format(N=len(items)))

        for item in items:
            item = json_util.loads(item)
            notifier.sns_publish("purchase-orders", item)
