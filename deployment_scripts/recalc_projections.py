import sys
import json
import os
import boto3
from boto3.dynamodb.conditions import Attr
from dynamodb_json import json_util
import maya


sys.path.append('data_dynamodb')
sys.path.append('data_common')
sys.path.append('.')

from dynamodb_repository import DynamoRepository
from data_common.queue import SQSManager


def enqueue_projections(supplier_id, brand_id, package_type_id, start_date):
    q = SQSManager(region_name=region)
    q.sqs_enqueue("projections", {
        'user_id': None,
        'supplier_id': supplier_id,
        'brand_id': brand_id,
        'package_type_id': package_type_id,
        'start_date': start_date,
    })


def send_msgs_for_all_brand_package_type_pairs(start_date):
    table_name = "brewoptix-products"
    resp = None
    while True:
        if not resp:
            resp = dynamo_client.Table(table_name).scan(
                FilterExpression=Attr('Latest').eq(True) & Attr('Active').eq(True)
            )
        elif resp and 'LastEvaluatedKey' in resp:
            resp = dynamo_client.Table(table_name).scan(
                FilterExpression=Attr('Latest').eq(True) & Attr('Active').eq(True),
                ExclusiveStartKey=resp['LastEvaluatedKey']
            )
        else:
            break

        items = resp['Items']
        for item in items:
            item = json_util.loads(item)
            brand_id = item["brand_id"]
            package_type_id = item["package_type_id"]
            supplier_id = item["supplier_id"]

            enqueue_projections(supplier_id, brand_id, package_type_id, start_date)


if __name__ == "__main__":
    # date is given as arg
    args = sys.argv
    try:
        start_date = args[1]
        stage = args[2]
        region = args[3]
    except IndexError:
        print("Please enter a start date cli argument, say '2019-08-01', "
              "followed by stage, e.g 'prod', region, e.g 'us-east-1' and"
              "process_by which takes vals 'brands', 'package-types', 'both'")
        raise IndexError

    os.environ['STAGE'] = stage

    dynamo_client = boto3.resource('dynamodb', region_name=region)

    # load config envs by stage
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
        """.format(CONFIG=config_filename))
        raise ex

    repo = DynamoRepository(region_name=region,
                            aurora_db_arn=db_arn,
                            aurora_db_secret_arn=db_secret_arn,
                            aurora_db_name=db_name)

    start = maya.parse(start_date)

    send_msgs_for_all_brand_package_type_pairs(start_date)
