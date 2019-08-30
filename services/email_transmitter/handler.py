import os
import boto3
import json
from botocore.exceptions import ClientError
from log_config import logger

EMAIL_TRANSMITTER_SOURCE = os.getenv('EMAIL_TRANSMITTER_SOURCE')


def email_transmitter(event, context):
    logger.debug('event: {}'.format(event))
    message_body = event['Records'][0]['body']
    process_message(message_body, EMAIL_TRANSMITTER_SOURCE)


def process_message(message_body, source):
    try:
        message = json.loads(message_body)
        destination={'ToAddresses': message['to'] }
        template = message["template"]
        data = message["data"]

        logger.debug('Source: {}'.format(source))
        logger.debug('Destination: {}'.format(destination))
        logger.debug('Template: {}'.format(template))
        logger.debug('TemplateData: {}'.format(data))

        client = boto3.client('ses')
        try:
            response = client.send_templated_email(
                Destination=destination,
                Template=template,
                TemplateData=json.dumps(data),
                Source=source
            )
        # Display an error if something goes wrong.
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            print("Email sent! Message ID:"),
            print(response['MessageId'])

    except Exception as ex:
        print(ex)