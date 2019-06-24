import boto3
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

        client = boto3.client('dynamodb', region_name=region)

        # check if table and item exists, if yes exit
        try:
            response = client.get_item(
                TableName='brewoptix-deployment',
                Key={
                    'script_number': {
                        'N': str(script_number)
                    }
                }
            )
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'ResourceNotFoundException':
                sys.exit(1)
            raise ex

        try:
            resp = json_util.loads(response['Item'])
            print(resp)
            sys.exit(1)
        except KeyError:
            pass
