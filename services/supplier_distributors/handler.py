import os
import sys
import random
import string
# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from common import insert_repo, check_auth, check_supplier
from api_utils import get_body, get_path_parameters
from data_common.exceptions import NoSuchEntity, \
    BadParameters, CannotModifyEntityStates, MissingRequiredKey

from log_config import logger

sys.path.append('data_dynamodb')
sys.path.append('data_common')


def generate_access_code():
    # Ref: https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
    affiliate_id = "OI01"
    for _ in range(1000):
        if any(k in affiliate_id for k in "OI01"):
            # generate new id
            return ''.join(
                random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))


@check_auth
@insert_repo
@check_supplier
def get_every_supplier_distributor(event, context):
    """
    Get all supplier_distributor
    """
    logger.debug('event: {}'.format(event))

    items = context.repo.get_all_supplier_distributors(context.supplier_id)

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier
def add_supplier_distributor(event, context):
    """
    Add a new supplier_distributor
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
    body['allow_ordering'] = False
    body['access_code'] = 'access-disabled'

    try:
        body = context.repo.save_supplier_distributor(body)
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
                'error': 'a supplier_distributor with the same name already exists'
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def modify_supplier_distributor(event, context):
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

    if 'allow_ordering' not in body or 'allow_order_updated' not in body:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Missing required key-value pair(s) in request body'
            })
        }

    if body['allow_order_updated']:
        if body['allow_ordering']:
            try:
                supplier_id = body["supplier_id"]
                access_code = body['access_code']
                context.repo.delete_distributor_supplier_by_access_code(supplier_id, access_code)
            except NoSuchEntity:
                pass
            body['access_code'] = 'access-disabled'
            body['allow_ordering'] = False
        else:
            body['access_code'] = generate_access_code()
            body['allow_ordering'] = True

    try:
        item = context.repo.save_supplier_distributor(body)
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
                'error': 'a supplier_distributor with the same name already exists'
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def get_by_id(event, context):
    """
    Get a supplier_distributor by its id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        item = context.repo.get_supplier_distributor_by_id(context.supplier_id, entity_id)

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
    Delete supplier_distributor by entity_id and version
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        context.repo.delete_supplier_distributor_by_id(context.supplier_id, entity_id)
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