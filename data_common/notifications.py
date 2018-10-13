import boto3
import json
import os


class SnsNotifier:
    def __init__(self, region_name, user_id=None, email=''):
        # SnsNotifier is a co-operating class with BaseRepository and their init method signature should match
        # this class will be inherited along with any repository abstract class in the methods implementation
        # For e.g, in feedbacks.py the class signature is DynamoFeedbacksRepository(FeedbacksRepository, SnsNotifier)

        self._region_name = region_name
        self._stage = os.environ["STAGE"]
        self._user_id = user_id
        self._email = email

    def sns_publish(self, object_name, obj):
        # Create an SNS client
        if 'SNS_ENDPOINT' in os.environ:
            # local development
            sns = boto3.client('sns', region_name=self._region_name, endpoint_url=os.environ['SNS_ENDPOINT'])
            account_id = '000000000000'
        else:
            sns = boto3.client('sns', region_name=self._region_name)
            account_id = boto3.client('sts').get_caller_identity().get('Account')

        topic = "{STAGE}-{OBJECT_NAME}".format(STAGE=self._stage,
                                               OBJECT_NAME=object_name)

        # Publish a simple message to the specified SNS topic
        response = sns.publish(
            TopicArn='arn:aws:sns:{REGION}:{ACCOUNT_ID}:{TOPIC}'.format(REGION=self._region_name,
                                                                        ACCOUNT_ID=account_id,
                                                                        TOPIC=topic),
            Message=json.dumps(obj),
        )

        return response
