import os
import sys

# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from common import insert_repo, check_auth, check_supplier, check_supplier_or_distributor
from api_utils import get_body, get_path_parameters
from data_common.exceptions import AuroraSqlExecuteFailed, AuroraSchemaNotFound

from log_config import logger

import inventory_csv


@check_auth
@insert_repo
@check_supplier_or_distributor
def get_inventory_products_by_date_range(event, context):
    """
    Get list of counts by count_date range
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    start_date = params['start_date']
    end_date = params.get('end_date', None)

    try:
        items = context.repo.get_inventory_products_by_date_range(
            context.supplier_id,
            start_date,
            end_date)

        return {
            'statusCode': 200,
            'body': json.dumps(items)
        }
    except AuroraSqlExecuteFailed:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Error. SQL Execution failed'
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
@check_supplier
def get_details_by_date_range(event, context):
    """
    Get list of counts by count_date range
    """
    logger.debug('event: {}'.format(event))

    params = get_path_parameters(event)

    start_date = params['start_date']
    end_date = params.get('end_date', None)

    try:
        items = context.repo.get_details_by_date_range(
            context.supplier_id,
            start_date,
            end_date)

        return {
            'statusCode': 200,
            'body': json.dumps(items)
        }
    except AuroraSqlExecuteFailed:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Error. SQL Execution failed'
            })
        }
    except:
        logger.log_uncaught_exception()


def get_inventory_csv(event, context):
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
        inventory_csv_string = inventory_csv.generate(body)

        return {
            'statusCode': 200,
            'body': inventory_csv_string,
            'isBase64Encoded': True
        }
    except AuroraSqlExecuteFailed:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Error. SQL Execution failed'
            })
        }
    except:
        logger.log_uncaught_exception()