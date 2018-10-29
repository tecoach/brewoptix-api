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
def get_every_adjustment(event, context):
    """
    Get all adjustments
    """
    logger.debug('event: {}'.format(event))

    items = context.repo.get_all_adjustments(context.supplier_id)

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier
def get_adjustments_by_daterange(event, context):
    """
    Get list of adjustments by adjustment_date range
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    min_adjustment_date = params['min_adjustment_date']
    max_adjustment_date = params.get('max_adjustment_date', None)

    items = context.repo.get_adjustment_by_adjustment_date_range(
        context.supplier_id,
        min_adjustment_date,
        max_adjustment_date)

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier
def add_adjustment(event, context):
    """
    Add adjustment inventory record
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
        body = context.repo.save_adjustment(body)
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
    except NoSuchEntity as ex:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': '{RESOURCE} Resource not found'.format(RESOURCE=str(ex))
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
def modify_adjustment(event, context):
    """
    Modify adjustment record
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
        item = context.repo.save_adjustment(body)

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
    Get an adjustment record by its id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        item = context.repo.get_adjustment_record_by_id(context.supplier_id, entity_id)

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
def delete_by_id(event, context):
    """
    Delete adjustment record by entity_id and version
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        context.repo.delete_adjustment_record_by_id(context.supplier_id, entity_id)
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
