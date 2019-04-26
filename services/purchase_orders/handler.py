import os
import sys
# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from common import insert_repo, check_auth, check_supplier_or_distributor, get_repo
from api_utils import get_body, get_path_parameters
from data_common.exceptions import NoSuchEntity, \
    BadParameters, MissingRequiredKey

from log_config import logger

sys.path.append('data_dynamodb')
sys.path.append('data_common')


@check_auth
@insert_repo
@check_supplier_or_distributor
def get_purchase_orders_by_order_date(event, context):
    """
    Get list of purchase orders by order_date range
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    min_order_date = params['min_order_date']
    max_order_date = params.get('max_order_date', None)

    if hasattr(context, 'supplier_id'):
        supplier_id = context.supplier_id
        distributors = []
    else:
        supplier_id = None
        distributor_id = context.distributor_id
        supplier_distributors = context.repo.get_all_distributor_suppliers(distributor_id)
        distributors = [item['supplier_distributor_id'] for item in supplier_distributors]

    items = context.repo.get_purchase_orders_by_order_date_range(
        min_order_date,
        max_order_date,
        supplier_id,
        distributors
    )

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier_or_distributor
def get_purchase_orders_by_pack_date(event, context):
    """
    Get list of purchase orders by pack_date range
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    min_pack_date = params['min_pack_date']
    max_pack_date = params.get('max_pack_date', None)

    if hasattr(context, 'supplier_id'):
        supplier_id = context.supplier_id
        distributors = []
    else:
        supplier_id = None
        distributor_id = context.distributor_id
        supplier_distributors = context.repo.get_all_distributor_suppliers(distributor_id)
        distributors = [item['supplier_distributor_id'] for item in supplier_distributors]

    items = context.repo.get_purchase_orders_by_pack_date_range(
        min_pack_date,
        max_pack_date,
        supplier_id,
        distributors
    )

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier_or_distributor
def get_purchase_orders_by_ship_date(event, context):
    """
    Get list of purchase orders by ship_date range
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    min_ship_date = params['min_ship_date']
    max_ship_date = params.get('max_ship_date', None)

    if hasattr(context, 'supplier_id'):
        supplier_id = context.supplier_id
        distributors = []
    else:
        supplier_id = None
        distributor_id = context.distributor_id
        supplier_distributors = context.repo.get_all_distributor_suppliers(distributor_id)
        distributors = [item['supplier_distributor_id'] for item in supplier_distributors]

    items = context.repo.get_purchase_orders_by_ship_date_range(
        min_ship_date,
        max_ship_date,
        supplier_id,
        distributors
    )

    return {
        'statusCode': 200,
        'body': json.dumps(items)
    }


@check_auth
@insert_repo
@check_supplier_or_distributor
def add_purchase_order(event, context):
    """
    Add a purchase order
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
        body = context.repo.save_purchase_order(body)
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
@check_supplier_or_distributor
def modify_purchase_order(event, context):
    """
    Modify purchase order
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
        item = context.repo.save_purchase_order(body)

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
@check_supplier_or_distributor
def get_by_id(event, context):
    """
    Get an count record by its id
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    if hasattr(context, 'supplier_id'):
        supplier_id = context.supplier_id
        distributors = []
    else:
        supplier_id = None
        distributor_id = context.distributor_id
        supplier_distributors = context.repo.get_all_distributor_suppliers(distributor_id)
        distributors = [item['supplier_distributor_id'] for item in supplier_distributors]

    try:
        entity_id = params['entity_id']

        item = context.repo.get_purchase_order_by_id(entity_id, supplier_id, distributors)

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
@check_supplier_or_distributor
def delete_by_id(event, context):
    """
    Delete count record by entity_id and version
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    if hasattr(context, 'supplier_id'):
        supplier_id = context.supplier_id
        distributors = []
    else:
        supplier_id = None
        distributor_id = context.distributor_id
        supplier_distributors = context.repo.get_all_distributor_suppliers(distributor_id)
        distributors = [item['supplier_distributor_id'] for item in supplier_distributors]

    try:
        entity_id = params['entity_id']

        context.repo.delete_purchase_order_by_id(entity_id, supplier_id, distributors)
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
