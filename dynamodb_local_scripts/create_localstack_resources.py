import boto3
import os
import json


def create_sns_topic(client, topic):
    client.create_topic(
        Name=topic,
    )


def create_sqs_queue(client, queue_name):
    client.create_queue(
        QueueName=queue_name
    )


def create_s3_bucket(resource, bucket_name):
    if not resource.Bucket(bucket_name) in resource.buckets.all():
        resource.create_bucket(
            ACL='public-read-write',
            Bucket=bucket_name
        )


if __name__ == "__main__":
    stage = os.environ['STAGE']
    account_id = '000000000000'

    config_filename = 'config.' + stage + '.json'
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_filepath = os.path.join(parent_dir, config_filename)
    local_stack_filename = 'local_stack.json'
    local_stack_filepath = os.path.join(parent_dir, local_stack_filename)

    with open(config_filepath, 'r') as fp:
        config = json.load(fp)

    region = config['REGION']

    sns = boto3.client('sns', region_name=region, endpoint_url=os.environ['SNS_ENDPOINT'])
    sqs = boto3.client('sqs', region_name=region, endpoint_url=os.environ['SQS_ENDPOINT'])
    s3 = boto3.resource('s3', region_name=region, endpoint_url=os.environ['S3_ENDPOINT'])

    print(local_stack_filepath)
    with open(local_stack_filepath, 'r') as fp:
        local_stack = json.load(fp)

    sns_object_names = local_stack["sns_object_names"]
    sqs_object_names = local_stack["sqs_object_names"]
    s3_bucket_name = config['S3_UPLOADS_BUCKET_NAME']

    for obj_name in sns_object_names:
        topic = stage + '-' + obj_name
        create_sns_topic(sns, topic)

    for obj_name in sqs_object_names:
        queue_name = stage + '-' + obj_name
        create_sqs_queue(sqs, queue_name)

    create_s3_bucket(s3, s3_bucket_name)
