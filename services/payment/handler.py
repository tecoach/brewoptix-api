import os
import sys
# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

sys.path.append('data_dynamodb')
sys.path.append('data_common')
from data_dynamodb.dynamodb_repository import DynamoRepository

from api_utils import get_body
from common import insert_repo, check_auth
from log_config import logger


def charge_by_stripe(event, context):
    logger.debug('event: {}'.format(event))

    try:
        body = get_body(event)
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad parameter(s) in request'
            })
        }
    except:
        logger.log_uncaught_exception()

    email = body["email"]

    user_id = '00000000-0000-0000-0000-000000000000'

    try:
        repo = DynamoRepository(
            region_name=os.environ['REGION'],
            table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
            user_id=user_id,
            email=email,
            dynamodb_local_endpoint=os.environ['DYNAMO_ENDPOINT']
        )
    except KeyError:
        repo = DynamoRepository(
            region_name=os.environ['REGION'],
            table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
            user_id=user_id,
            email=email
        )
    except:
        logger.log_uncaught_exception()

    resp = repo.charge_by_stripe(body)

    if 'status' in resp and resp['status'] == 'succeeded':
        return {
            'statusCode': 200,
            'body': json.dumps(resp)
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps(resp)
        }


@check_auth
@insert_repo
def get_all_payments(event, context):
    logger.debug('event: {}'.format(event))

    items = context.repo.get_all_payments()

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }
