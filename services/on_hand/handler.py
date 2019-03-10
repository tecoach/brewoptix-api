import os
import sys
# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from common import insert_repo, check_auth, check_supplier, get_repo
from api_utils import get_body, get_path_parameters
from data_common.exceptions import NoSuchEntity, \
    BadParameters, MissingRequiredKey

from log_config import logger


@check_auth
@insert_repo
@check_supplier
def get_every_on_hand(event, context):
    """
    Get all on_hand
    """
    logger.debug('event: {}'.format(event))

    items = context.repo.get_all_on_hands(context.supplier_id)

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier
def add_on_hand(event, context):
    """
    Add on-hand inventory record
    """
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

    body["supplier_id"] = context.supplier_id

    try:
        body = context.repo.save_on_hand(body)
        return {
            'statusCode': 200,
            'body': json.dumps(body)
        }
    except BadParameters as ex:
        key = str(ex)
        if key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad request. The request was Malformed. Wrong type for key-val pair {KEY}'.format(KEY=key)
                })
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad request. The request was Malformed'
                })
            }
    except MissingRequiredKey as ex:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. Missing required key-val pair {KEY}'.format(KEY=str(ex))
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def modify_on_hand(event, context):
    """
    Modify on-hand record
    """
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

    if "supplier_id" in body and body["supplier_id"] != context.supplier_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad parameter(s) in request. supplier_id in body must match x-supplier-id'
            })
        }

    body["supplier_id"] = context.supplier_id

    try:
        item = context.repo.save_on_hand(body)

        return {
            'statusCode': 200,
            'body': json.dumps(item)
        }
    except BadParameters as ex:
        key = str(ex)
        if key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad request. The request was Malformed. Wrong type for key-val pair {KEY}'.format(KEY=key)
                })
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad request. The request was Malformed'
                })
            }
    except MissingRequiredKey as ex:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. Missing required key-val pair {KEY}'.format(KEY=str(ex))
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def get_by_id(event, context):
    """
    Get an on-hand record by its id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        item = context.repo.get_on_hand_record_by_id(context.supplier_id, entity_id)

        return {
            'statusCode': 200,
            'body': json.dumps(item)
        }
    except NoSuchEntity:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Resource not found'
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def delete_by_id(event, context):
    """
    Delete on-hand record by entity_id and version
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        context.repo.delete_on_hand_record_by_id(context.supplier_id, entity_id)
        return {
            'statusCode': 204
        }
    except NoSuchEntity:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Resource not found'
            })
        }
    except:
        logger.log_uncaught_exception()


def process_projections_queue(event, context):
    """
    Process SQS queue projections
    """
    logger.debug('event: {}'.format(event))
    logger.debug('event: {}'.format(context))

    records = event['Records']

    for record in records:
        repo, suppliers = get_repo(record)
        obj = json.loads(record['body'])
        supplier_id = obj['supplier_id']
        brand_id = obj['brand_id']
        package_type_id = obj['package_type_id']
        start_date = obj['start_date']
        repo.process_projections_queue(supplier_id, brand_id, package_type_id,
                                       start_date, context.aws_request_id)
