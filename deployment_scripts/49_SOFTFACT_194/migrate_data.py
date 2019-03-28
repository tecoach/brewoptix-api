import sys
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import os
import json
import time
import sys
import random


sys.path.insert(0, os.getcwd())
sys.path.insert(0, 'data_dynamodb')

from data_dynamodb.autoscaling_utils import AutoScaleDynamodb

table_obj_type_map = {
    "brewoptix-users": "users",
    "brewoptix-suppliers": "suppliers",
    "brewoptix-brands": "brands",
    "brewoptix-package-types": "package-types",
    "brewoptix-products": "products",
    "brewoptix-on-hand-inventory": "on-hand-inventory",
    "brewoptix-adjustment-inventory": "adjustment-inventory",
    "brewoptix-payments": "payments",
    "brewoptix-containers": "containers",
    "brewoptix-retail-packages": "retail-packages",
    "brewoptix-production": "production",
    "brewoptix-counts": "counts",
    "brewoptix-purchase-orders": "purchase-orders",
    "brewoptix-supplier-distributors": "supplier-distributors",
    "brewoptix-distributor-suppliers": "distributor-suppliers",
    "brewoptix-distributors": "distributors",
    "brewoptix-merchandise": "merchandise",
}


def autoscale_dest(table, region,
                   dynamo_target_utilization,
                   scale_in_cooldown,
                   scale_out_cooldown,
                   min_capacity=20,
                   max_capacity=10000,
                   only_read=False):
    autoscaler = AutoScaleDynamodb(dynamo_target_utilization,
                                   scale_in_cooldown,
                                   scale_out_cooldown,
                                   region_name=region)

    if not only_read:
        autoscaler.autoscale_table(table,
                                   unit_type='write',
                                   min_capacity=min_capacity,
                                   max_capacity=max_capacity)

        autoscaler.attach_scaling_policy(table, unit_type='write')

    autoscaler.autoscale_table(table,
                               unit_type='read',
                               min_capacity=min_capacity,
                               max_capacity=max_capacity)
    autoscaler.attach_scaling_policy(table, unit_type='read')


def get_items_count(region, table_name, obj_type=None):
    item_count = 0
    dynamo_client = boto3.resource('dynamodb', region_name=region)

    backoff_waits = [0, ]
    while True:
        try:
            if obj_type:
                response = dynamo_client.Table(table_name).scan(
                    Select='COUNT',
                    FilterExpression=Attr('obj_type').eq(obj_type),
                    ConsistentRead=True
                )
            else:
                # print("No obj type")
                response = dynamo_client.Table(table_name).scan(
                    Select='COUNT',
                    ConsistentRead=True
                )
            backoff_waits = [0, ]
            break
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                print("ProvisionedThroughputExceededException: waiting")
                backoff_waits.append(2**(len(backoff_waits)-1) * 5)
                time.sleep(backoff_waits[random.randint(0, len(backoff_waits)-1)])
            else:
                raise ex

    item_count += response['Count']

    while 'LastEvaluatedKey' in response:
        backoff_waits = [0, ]
        while True:
            try:
                if obj_type:
                    response = dynamo_client.Table(table_name).scan(
                        Select='COUNT',
                        FilterExpression=Attr('obj_type').eq(obj_type),
                        ConsistentRead=True,
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                else:
                    response = dynamo_client.Table(table_name).scan(
                        Select='COUNT',
                        ConsistentRead=True,
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                backoff_waits = [0, ]
                break
            except ClientError as ex:
                if ex.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                    print("ProvisionedThroughputExceededException: waiting")
                    backoff_waits.append(2 ** (len(backoff_waits) - 1) * 5)
                    time.sleep(backoff_waits[random.randint(0, len(backoff_waits) - 1)])
                else:
                    raise ex

        item_count += response['Count']

    print("Table, obj_type, Items count = {TABLE}, {OBJ}, {COUNT}".format(TABLE=table_name,
                                                                          OBJ=obj_type,
                                                                          COUNT=item_count))
    return item_count


def copy_items(source_table, dest_table,
               stage, region, obj_type, total_segments=5,
               ):
    print("Invoke copy items from table: {SRC_TABLE} to {DEST_TABLE}".format(SRC_TABLE=source_table,
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
                'obj_type': obj_type,
            }
        )
    )

    return response


args = sys.argv
if len(args) >= 2:
    start_time = time.time()
    print("Start time: ", start_time)
    stage = args[1]
    os.environ['STAGE'] = stage

    config_filename = 'config.' + stage + '.json'
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_filepath = os.path.join(parent_dir, config_filename)

    with open(config_filepath, 'r') as fp:
        config = json.load(fp)

    region = config["REGION"]

    dynamo_target_utilization = config['DYNAMODB_TARGET_UTILIZATION']
    scale_in_cooldown = config['DYNAMODB_SCALE_IN_COOLDOWN_SECS']
    scale_out_cooldown = config['DYNAMODB_SCALE_OUT_COOLDOWN_SECS']

    dest_table = "brewoptix-{STAGE}".format(STAGE=stage)

    autoscale_dest(dest_table,
                   region,
                   dynamo_target_utilization,
                   scale_in_cooldown,
                   scale_out_cooldown)

    src_table_counts = {}
    failed_tables = []
    first_invoke = True
    for src_table, obj_type in table_obj_type_map.items():
        if not first_invoke:
            print("Waiting 5secs")
            time.sleep(5)

        src_table_items_cnt = get_items_count(region, src_table)
        dest_table_items_cnt = get_items_count(region, dest_table, obj_type)
        src_table_counts[src_table] = src_table_items_cnt
        if src_table_items_cnt == dest_table_items_cnt:
            print("Skipping copying of table: {TABLE}".format(TABLE=src_table))
            continue

        response = copy_items(src_table, dest_table,
                   stage, region, obj_type, total_segments=5)
        verified = False
        first_run = True
        attempts = 0
        while not verified:
            if first_run:
                print("Waiting 60secs...")
                time.sleep(60)
                first_run = False
            else:
                print("Waiting 5secs...")
                time.sleep(5)

            dest_table_items_cnt = get_items_count(region, dest_table, obj_type)
            print("\nVerifying... {SRC} and {OBJ} count".format(SRC=src_table, OBJ=obj_type))
            print(dest_table_items_cnt)
            print(src_table_counts[src_table])
            print("----\n")

            if dest_table_items_cnt == src_table_counts[src_table]:
                verified = True
            else:
                attempts += 1

            if attempts > 25:  # 14.5mins
                print("Aborting. Waited for too long. Unable to verify success for copying table: {TABLE}".format(TABLE=src_table))
                print("Trying next table")
                failed_tables.append(src_table)

    if failed_tables:
        print("Some tables failed to copy")
        print("Failed tables: ", failed_tables)

    end_time = time.time()
    print("Total time taken(secs): ", end_time-start_time)

