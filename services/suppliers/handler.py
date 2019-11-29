import os
import sys
# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from common import insert_repo, check_auth, check_supplier
from api_utils import get_body, get_path_parameters
from data_common.exceptions import NoSuchEntity, \
    BadParameters, CannotModifyEntityStates, Auth0UnableToAccess, \
    Auth0AccessDenied, Auth0UnknownError, MissingRequiredKey, \
    UnknownMainContact, NotAnAdminUser, CannotUpdateUsers, UnsupportedMediaType

from log_config import logger

from common import get_repo


@check_auth
@insert_repo
def get_every_supplier(event, context):
    """
    Get all supplier
    """
    logger.debug('event: {}'.format(event))

    items = context.repo.get_all_suppliers(context.suppliers)

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
def add_supplier(event, context):
    """
    Add a new supplier for user
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

    try:
        body = context.repo.save_supplier(body)
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
                    'error': 'Bad request. Wrong type of data for {KEY}'.format(KEY=key)
                })
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad request. The request was Malformed'
                })
            }
    except CannotUpdateUsers:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'users property cannot be updated through this endpoint'
            })
        }
    except UnsupportedMediaType:
        return {
            'statusCode': 415,
            'body': json.dumps({
                'error': 'Unsupported media type. Error with logo PNG. Unable to decode base64-PNG'
            })
        }
    except MissingRequiredKey as ex:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. Missing required key-val pair {KEY}'.format(KEY=str(ex))
            })
        }
    except Auth0AccessDenied:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': "Unable to update Auth0. App doesn't have right scopes"
            })
        }
    except Auth0UnableToAccess:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': "Couldn't access Auth0"
            })
        }
    except CannotModifyEntityStates:
        return {
            'statusCode': 409,
            'body': json.dumps({
                'error': 'The request could not be completed due to a conflict with the current state of the resource. '
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def modify_supplier(event, context):
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

    if "entity_id" in body and body["entity_id"] != context.supplier_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad parameter(s) in request. entity_id in body must match x-supplier-id'
            })
        }

    body["entity_id"] = context.supplier_id

    try:
        item = context.repo.save_supplier(body)

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
    except CannotUpdateUsers:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'users property cannot be updated through this endpoint'
            })
        }
    except UnknownMainContact:
        return {
            'statusCode': 403,
            'body': json.dumps({
                'error': 'Forbidden. Unknown Main Contact'
            })
        }
    except NoSuchEntity:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Resource not found'
            })
        }
    except UnsupportedMediaType:
        return {
            'statusCode': 415,
            'body': json.dumps({
                'error': 'Unsupported media type. Error with logo PNG. Unable to decode base64-PNG'
            })
        }
    except NotAnAdminUser:
        return {
            'statusCode': 403,
            'body': json.dumps({
                'error': "Forbidden. Admins only"
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def get_by_id(event, context):
    """
    Get a supplier by its id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        if context.supplier_id != entity_id:
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'Forbidden. x-supplier-id header must match entity_id'
                })
            }

        item = context.repo.get_supplier_by_id(entity_id)

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
    Delete supplier by entity_id and version
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        entity_id = params['entity_id']

        if context.supplier_id != entity_id:
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'Forbidden. x-supplier-id header must match entity_id'
                })
            }

        context.repo.delete_supplier_by_id(entity_id)
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
    except NotAnAdminUser:
        return {
            'statusCode': 403,
            'body': json.dumps({
                'error': "Forbidden. Admins only"
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def add_user_to_supplier(event, context):
    """
    Add a new/existing user to supplier
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

    try:
        body = context.repo.upsert_user_in_supplier(context.supplier_id, body)
        return {
            'statusCode': 204,
            'body': json.dumps(body)
        }
    except BadParameters:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. The request was Malformed'
            })
        }
    except Auth0AccessDenied:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': "Unable to update Auth0. App doesn't have right scopes"
            })
        }
    except Auth0UnknownError as ex:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': "Auth0 Error: {ERROR}".format(ERROR=str(ex))
            })
        }
    except Auth0UnableToAccess:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': "Couldn't access Auth0"
            })
        }
    except NotAnAdminUser:
        return {
            'statusCode': 403,
            'body': json.dumps({
                'error': "Forbidden. Admins only"
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def delete_user_in_supplier(event, context):
    """
    Delete user in supplier by email_id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    try:
        user_id = params['user_id']

        context.repo.delete_user_in_supplier(context.supplier_id, user_id)

        return {
            'statusCode': 204
        }
    except NoSuchEntity as ex:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': '{MSG}'.format(MSG=str(ex))
            })
        }
    except NotAnAdminUser:
        return {
            'statusCode': 403,
            'body': json.dumps({
                'error': "Forbidden. Admins only"
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def get_all_users_in_supplier(event, context):
    """
    Get all users under a supplier
    """
    logger.debug('event: {}'.format(event))

    try:
        items = context.repo.get_all_users_in_supplier(context.supplier_id)

        return {
            'statusCode': 200,
            'body': json.dumps(items)
        }
    except NoSuchEntity as ex:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': '{RESOURCE} not found'.format(RESOURCE=str(ex))
            })
        }
    except NotAnAdminUser:
        return {
            'statusCode': 403,
            'body': json.dumps({
                'error': "Forbidden. Admins only"
            })
        }
    except:
        logger.log_uncaught_exception()


def process_supplier_save(event, context):
    """
    Process supplier save notification
    """
    logger.debug('event: {}'.format(event))
    logger.debug('event: {}'.format(context))

    records = event['Records']

    for record in records:
        obj = json.loads(record['Sns']['Message'])
        if not obj['active']:
            item = {'body': json.dumps(obj)}
            repo, suppliers = get_repo(item)

            # delete supplier from app metadata of all users belonging to supplier
            user_ids = (user["user_id"] for user in obj.get("users", []))
            for user_id in user_ids:
                repo.remove_supplier_from_app_metadata(obj["entity_id"], user_id)
