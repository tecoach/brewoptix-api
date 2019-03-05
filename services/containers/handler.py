import os
import sys
# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from common import insert_repo, check_auth, check_supplier, check_supplier_or_distributor
from api_utils import get_body, get_path_parameters
from data_common.exceptions import NoSuchEntity, \
    BadParameters, CannotModifyEntityStates, MissingRequiredKey

from log_config import logger

sys.path.append('data_dynamodb')
sys.path.append('data_common')


@check_auth
@insert_repo
@check_supplier_or_distributor
def get_every_container(event, context):
    """
    Get all containers
    """
    logger.debug('event: {}'.format(event))

    if hasattr(context, 'supplier_id'):
        supplier = context.supplier_id
    else:
        distributor_id = context.distributor_id
        supplier_distributors = context.repo.get_all_distributor_suppliers(distributor_id)
        supplier = [item['supplier_id'] for item in supplier_distributors]

    items = context.repo.get_all_containers(supplier)

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier
def add_container(event, context):
    """
    Add a new container
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
        body = context.repo.save_container(body)
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
    except CannotModifyEntityStates:
        return {
            'statusCode': 409,
            'body': json.dumps({
                'error': 'The request could not be completed due to a conflict with the current state of the resource. '
                         'This error could be because, a supplier with the same name already exists'
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
def modify_container(event, context):
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
        item = context.repo.save_container(body)

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
    Get a container by its id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        item = context.repo.get_container_by_id(context.supplier_id, entity_id)

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
    Delete container by entity_id and version
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        context.repo.delete_container_by_id(context.supplier_id, entity_id)
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
