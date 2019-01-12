import os
import sys
# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from log_config import logger
from common import insert_repo, check_auth, check_distributor
from api_utils import get_body, get_path_parameters
from data_common.exceptions import NoSuchEntity, \
    BadParameters, CannotModifyEntityStates, MissingRequiredKey

sys.path.append('data_dynamodb')
sys.path.append('data_common')

@check_auth
@insert_repo
@check_distributor
def get_every_distributor_supplier(event, context):
    """
    Get all distributor_supplier
    """
    logger.debug('event: {}'.format(event))

    items = context.repo.get_all_distributor_suppliers(context.distributor_id)

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_distributor
def add_distributor_supplier(event, context):
    """
    Add a new distributor_supplier
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

    if 'access_code' not in body or not body['access_code']:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Missing required key-value pair(s) in request body'
            })
        }

    body["distributor_id"] = context.distributor_id

    try:
        supplier_distributor_obj = context.repo.get_supplier_distributor_by_access_code(body['access_code'])
        if supplier_distributor_obj['allow_ordering']:
            body["supplier_distributor_id"] = supplier_distributor_obj['entity_id']
            body["supplier_id"] = supplier_distributor_obj['supplier_id']
        else:
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'Access denied'
                })
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

    try:
        supplier_id = body['supplier_id']
        supplier_obj = context.repo.get_supplier_by_id(supplier_id)
        body["nickname"] = supplier_obj['name']
    except NoSuchEntity:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Supplier not found'
            })
        }
    except:
        logger.log_uncaught_exception()

    try:
        body = context.repo.save_distributor_supplier(body)
        return {
            'statusCode': 200,
            'body': json.dumps(body)
        }
    except BadParameters as ex:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. The request was Malformed. Wrong type for key-val pair {KEY}'.format(KEY=str(ex))
            })
        }
    except MissingRequiredKey as ex:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. Missing required key-val pair {KEY}'.format(KEY=str(ex))
            })
        }
    except CannotModifyEntityStates:
        return {
            'statusCode': 409,
            'body': json.dumps({
                'error': 'a distributor_supplier with the same name already exists'
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_distributor
def modify_distributor_supplier(event, context):
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

    if "distributor_id" in body and body["distributor_id"] != context.distributor_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad parameter(s) in request. distributor_id in body must match x-distributor-id'
            })
        }

    body["distributor_id"] = context.distributor_id

    try:
        item = context.repo.save_distributor_supplier(body)

        return {
            'statusCode': 200,
            'body': json.dumps(item)
        }
    except BadParameters as ex:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. The request was Malformed. Wrong type for key-val pair {KEY}'.format(KEY=str(ex))
            })
        }
    except MissingRequiredKey as ex:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. Missing required key-val pair {KEY}'.format(KEY=str(ex))
            })
        }
    except CannotModifyEntityStates:
        return {
            'statusCode': 409,
            'body': json.dumps({
                'error': 'a distributor_supplier with the same name already exists'
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_distributor
def get_by_id(event, context):
    """
    Get a distributor_supplier by its id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        item = context.repo.get_distributor_supplier_by_id(context.distributor_id, entity_id)

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
@check_distributor
def delete_by_id(event, context):
    """
    Delete distributor_supplier by entity_id and version
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        context.repo.delete_distributor_supplier_by_id(context.distributor_id, entity_id)
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