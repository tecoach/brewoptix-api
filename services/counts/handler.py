import os
import sys
# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from common import insert_repo, check_auth, check_supplier, get_repo
from api_utils import get_body, get_path_parameters
from data_common.exceptions import NoSuchEntity, \
    BadParameters, CannotModifyEntityStates

from log_config import logger
import count_sheet


@check_auth
@insert_repo
@check_supplier
def get_every_count(event, context):
    """
    Get all counts
    """
    logger.debug('event: {}'.format(event))

    items = context.repo.get_all_counts(context.supplier_id)

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier
def get_counts_by_daterange(event, context):
    """
    Get list of counts by count_date range
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    min_count_date = params['min_count_date']
    max_count_date = params.get('max_count_date', None)

    items = context.repo.get_count_by_count_date_range(
        context.supplier_id,
        min_count_date,
        max_count_date)

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier
def add_count(event, context):
    """
    Add count inventory record
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
        body = context.repo.save_count(body)
        return {
            'statusCode': 200,
            'body': json.dumps(body)
        }
    except BadParameters:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. The request was Malformed'
            })
        }
    except NoSuchEntity as ex:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': '{RESOURCE} Resource not found'.format(RESOURCE=str(ex))
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def modify_count(event, context):
    """
    Modify count record
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
        item = context.repo.save_count(body)

        return {
            'statusCode': 200,
            'body': json.dumps(item)
        }
    except BadParameters:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. The request was Malformed'
            })
        }
    except NoSuchEntity as ex:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': '{RESOURCE} Resource not found'.format(RESOURCE=str(ex))
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def get_by_id(event, context):
    """
    Get an count record by its id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        item = context.repo.get_count_by_id(context.supplier_id, entity_id)

        return {
            'statusCode': 200,
            'body': json.dumps(item)
        }
    except NoSuchEntity as ex:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': '{RESOURCE} Resource not found'.format(RESOURCE=str(ex))
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def get_count_sheet_by_id(event, context):
    """
    Get an count record by its id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        item = context.repo.get_count_by_id(context.supplier_id, entity_id)

        count_sheet_string = count_sheet.generate(item)

        return {
            'statusCode': 200,
            'body': count_sheet_string,
            'isBase64Encoded': True
        }
    except NoSuchEntity as ex:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': '{RESOURCE} Resource not found'.format(RESOURCE=str(ex))
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def delete_by_id(event, context):
    """
    Delete count record by entity_id and version
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        context.repo.delete_count_by_id(context.supplier_id, entity_id)
        return {
            'statusCode': 204
        }
    except NoSuchEntity as ex:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': '{RESOURCE} Resource not found'.format(RESOURCE=str(ex))
            })
        }
    except:
        logger.log_uncaught_exception()


def process_counts_queue(event, context):
    """
    Delete count record by entity_id and version
    """
    logger.debug('event: {}'.format(event))
    logger.debug('event: {}'.format(context))

    records = event['Records']

    for record in records:
        repo, suppliers = get_repo(record)
        obj = json.loads(record['body'])
        repo.process_counts_queue(obj)
