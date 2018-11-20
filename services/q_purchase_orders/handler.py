import os
import sys

# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from common import get_repo

from log_config import logger


def process_purchase_orders_queue(event, context):
    """
    Process Purchase order in queue
    """
    logger.debug('event: {}'.format(event))
    logger.debug('event: {}'.format(context))

    records = event['Records']

    for record in records:
        repo, suppliers = get_repo(record)
        obj = json.loads(record['body'])
        repo.process_purchase_orders_queue(obj)
