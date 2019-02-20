import sys
import boto3
from boto3.dynamodb.conditions import Attr
import os
import json

data_common = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
             "data_common")
print(data_common)
sys.path.append(data_common)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data_common.queue import SQSManager

args = sys.argv
if len(args) >= 2:
    stage = args[1]

    os.environ['STAGE'] = stage

    config_filename = 'config.' + stage + '.json'
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_filepath = os.path.join(parent_dir, config_filename)

    with open(config_filepath, 'r') as fp:
        config = json.load(fp)

    region = config['REGION']

    dynamo_client = boto3.resource('dynamodb', region_name=region)

    dynamo_table_name = 'brewoptix-products'

    queue = SQSManager(region_name=region)

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
        print("Enqueuing {N} items".format(N=len(items)))

        # trigger projections calculation for old records + new inserts
        for item in items:
            brand_id = item["brand_id"]
            package_type_id = item["package_type_id"]
            supplier_id = item["supplier_id"]
            user_id = item["user_id"]

            # Re-calculate projections
            queue.sqs_enqueue("projections", {
                'user_id': None,
                "supplier_id": supplier_id,
                'brand_id': brand_id,
                'package_type_id': package_type_id,
                'start_date': '2019-07-01',
            })  # enqueue object
