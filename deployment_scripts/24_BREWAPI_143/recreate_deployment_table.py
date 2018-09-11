import boto3
from bloop import (
    BaseModel, Boolean, Column, Number, String,
    UUID, Map, List, GlobalSecondaryIndex, Engine
)
from botocore.exceptions import ClientError
import os
import json
import time
from dynamodb_json import json_util


class Deployment(BaseModel):
    class Meta:
        table_name = 'brewoptix-deployment'
        read_units = 1
        write_units = 1

    script_number = Column(Number, hash_key=True)


if __name__ == '__main__':
    import sys

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

        client = boto3.client('dynamodb', region_name=region)
        engine = Engine(dynamodb=client)

        model = Deployment

        # pull all items from deployment table
        table = model.Meta.table_name
        print("Updating brewoptix-deployment with new schema")

        print("Getting all items in table")
        all_items = client.scan(TableName=table)

        # delete existing table
        print("Delete table")
        resp = client.delete_table(TableName=table)

        for _ in range(10):
            try:
                client.describe_table(TableName=model.Meta.table_name)
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("Resource Not Found")
                    break
                else:
                    raise e
            time.sleep(30)

        # create table with updated schema
        print("Create table with new schema")
        for _ in range(5):
            resp = client.list_tables()
            tables = resp['TableNames']
            if model.Meta.table_name not in tables:
                print('Creating Deployment Dynamodb Table '
                      'in Region: {REGION}'.format(REGION=region))
                print('Creating table: ', model.Meta.table_name)
                engine.bind(model)
                break
            else:
                time.sleep(30)

        # wait for table to be created
        for _ in range(5):
            try:
                resp = client.describe_table(TableName=model.Meta.table_name)
                if resp['Table']['AttributeDefinitions'][0]['AttributeName'] == 'script_number' and \
                        resp['Table']['AttributeDefinitions'][0]['AttributeType'] == 'N':
                    print("Check for new table schema passed")
                    break
            except:
                pass

            time.sleep(30)

        # add all items to table
        print("Add items back to table")
        for item in all_items["Items"]:
            item = json_util.loads(item)
            print(item)
            for _ in range(5):
                try:
                    response = client.put_item(
                        TableName='brewoptix-deployment',
                        Item={
                            'script_number': {
                                'N': str(item['script_number'])
                            },
                            'timestamp': {
                                'S': item['timestamp']
                            },
                            'stage': {
                                'S': item['stage']
                            }
                        }
                    )
                    break
                except ClientError as ex:
                    if ex.response['Error']['Code'] == 'ValidationException':
                        print("Unable to validate table schema. Waiting for dynamodb to update schema")
                    else:
                        raise ex
                time.sleep(20)

    else:
        print("""FAILED: Running dynamodb tables creation script.
                 REGION needs to be passed as a positional argument
                 while running the script""")


