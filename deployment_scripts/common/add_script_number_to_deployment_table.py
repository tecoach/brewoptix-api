import sys
import boto3
from botocore.exceptions import ClientError
import os
import json
import maya
from dynamodb_json import json_util
from decimal import Decimal


if __name__ == '__main__':
    import sys

    args = sys.argv
    if len(args) >= 3:
        stage = args[1]
        script_number = args[2]

        os.environ['STAGE'] = stage

        config_filename = 'config.' + stage + '.json'
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_filepath = os.path.join(parent_dir, config_filename)

        with open(config_filepath, 'r') as fp:
            config = json.load(fp)

        region = config['REGION']

        client = boto3.client('dynamodb', region_name=region)

        # insert item
        response = client.put_item(
            TableName='brewoptix-deployment',
            Item={
                'script_number': {
                        'N': str(script_number)
                    },
                'timestamp': {
                        'S': str(maya.now().iso8601())
                    },
                'stage': {
                        'S': str(stage)
                    }
                }
            )
