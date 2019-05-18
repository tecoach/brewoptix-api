# check latest version on deployment table
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import os
import json

from dynamodb_json import json_util

# Returns exit status 1 if issue_id (script_number) already exists or if table not found

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

        resource = boto3.resource('dynamodb', region_name=region)

        # check if table and item exists, if yes exit
        try:
            response = resource.Table('brewoptix-deployment').scan(
                Limit=1,
                FilterExpression=Attr('script_number').eq(script_number)& Attr('stage').eq(stage)
            )
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'ResourceNotFoundException':
                sys.exit(1)
            raise ex

        try:
            resp = json_util.loads(response['Items'][0])
            print("Found deployment: ")
            print(resp)
            sys.exit(1)    # means already run or no deployment table
        except (KeyError, IndexError):
            pass
