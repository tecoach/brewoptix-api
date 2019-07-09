import boto3
import json
import os


class SQSManager:
    def __init__(self, region_name, user_id=None, email=''):
        # SQSManager is a co-operating class with BaseRepository and their init method signature and
        # initialized attributes should match this class will be inherited
        # along with any repository abstract class in the methods implementation
        # For e.g, in feedbacks.py the class signature is DynamoContactRepository(ContactRepository, SQSManager)

        self._region_name = region_name
        self._user_id = user_id
        self._email = email
        self._stage = os.environ["STAGE"]
        # Do not add more attributes, this initializer may never be called
        # If more attributes are required, modify SQSManager class as well to match with this signature

    def sqs_enqueue(self, object_name, obj):
        stage = os.environ["STAGE"]

        # Create an SQS client
        if 'SQS_ENDPOINT' in os.environ:
            sqs = boto3.resource('sqs', region_name=self._region_name, endpoint_url=os.environ['SQS_ENDPOINT'])
        else:
            sqs = boto3.resource('sqs', region_name=self._region_name)

        # Get the queue
        queue_name = stage + "-" + object_name
        queue = sqs.get_queue_by_name(QueueName=queue_name)

        # Create a new message
        response = queue.send_message(MessageBody=json.dumps(obj))

        # The response is NOT a resource, but gives you a message ID and MD5
        print(response.get('MessageId'))
        print(response.get('MD5OfMessageBody'))

        # Print out the response
        print(response)
        return response
