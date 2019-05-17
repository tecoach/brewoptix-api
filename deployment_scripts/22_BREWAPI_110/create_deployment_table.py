import boto3
from bloop import (
    BaseModel, Boolean, Column, Number, String,
    UUID, Map, List, GlobalSecondaryIndex, Engine
)
import os
import json
import time


class Deployment(BaseModel):
    class Meta:
        table_name = 'brewoptix-deployment'
        read_units = 1
        write_units = 1

    script_number = Column(String, hash_key=True)


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

        resp = client.list_tables()
        tables = resp['TableNames']

        model = Deployment

        if model.Meta.table_name not in tables:
            print('Creating Deployment Dynamodb Table '
                  'in Region: {REGION}'.format(REGION=region))
            print('Creating table: ', model.Meta.table_name)
            engine.bind(model)

        # waif for table to be created
        for _ in range(5):
            try:
                client.describe_table(TableName=model.Meta.table_name)
            except:
                time.sleep(10)
    else:
        print("""FAILED: Running dynamodb tables creation script.
                 REGION needs to be passed as a positional argument
                 while running the script""")


