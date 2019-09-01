import os
import sys
import json
import boto3
from botocore.exceptions import ClientError

if __name__ == '__main__':

    args = sys.argv
    if len(args) >= 2:
        stage = args[1]

        os.environ['STAGE'] = stage

        config_filename = 'config.' + stage + '.json'
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        config_filepath = os.path.join(parent_dir, config_filename)

        with open(config_filepath, 'r') as fp:
            config = json.load(fp)

        region = config['REGION']

        ses = boto3.client('ses', region_name=region)

        with open('./purchase_order_email_template.json') as json_file:
            email_template = json.load(json_file)

            try:
                response = ses.create_template(Template=email_template['Template'])
                print(response)
            except ClientError as e:
                if e.response['Error']['Code'] == 'AlreadyExists':
                    response = ses.update_template(Template=email_template['Template'])
                else:
                    print("Unexpected error: %s" % e)