import boto3
from bloop import (
    BaseModel, Column, Number, String,
    Engine
)


class Deployment(BaseModel):
    class Meta:
        table_name = 'brewoptix-deployment'
        read_units = 1
        write_units = 1

    script_number = Column(Number, hash_key=True)


if __name__ == "__main__":
    if __name__ == '__main__':
        import sys
        import json
        import os

        args = sys.argv
        if len(args) >= 2:
            stage = args[1]

            config_filename = 'config.' + stage + '.json'
            parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_filepath = os.path.join(parent_dir, config_filename)

            try:
                with open(config_filepath, 'r') as fp:
                    config = json.load(fp)
            except FileNotFoundError:
                print("Cannot find config file: {0}".format(config_filename))
                sys.exit(1)

            region = config['REGION']

            client = boto3.client('dynamodb', region_name=region)
            engine = Engine(dynamodb=client)

            print("Creating deployment table in Dynamodb: ")
            print('Creating table: ', Deployment.Meta.table_name)
            engine.bind(Deployment)
