import os
import sys

from functools import wraps

from log_config import logger
from auth import jwt_decode
import json


AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
AUTH0_CLIENT_PUBLIC_KEY = os.getenv('AUTH0_CLIENT_PUBLIC_KEY')


class TokenError(Exception):
    """Raised when token is invalid, malformed or expired"""


def insert_repo(handler):
    @wraps(handler)
    def wrapper(event, context):
        sys.path.append('data_dynamodb')
        sys.path.append('data_common')
        from data_dynamodb.dynamodb_repository import DynamoRepository

        # While developing, dynamodb local is used. So if `DYANMODB_LOCAL_ENDPOINT` is present in env vars
        # dynamodb boto client is patched to use local db
        try:
            context.repo = DynamoRepository(
                region_name=os.environ['REGION'],
                table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
                user_id=context.user_id,
                email=context.email,
                aurora_db_arn=os.environ['AURORA_DB_ARN'],
                aurora_db_secret_arn=os.environ['AURORA_DB_SECRET_ARN'],
                aurora_db_name=os.environ['AURORA_DB_NAME'],
                dynamodb_local_endpoint=os.environ['DYNAMO_ENDPOINT']
            )

        except KeyError:
            context.repo = DynamoRepository(
                region_name=os.environ['REGION'],
                table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
                user_id=context.user_id,
                email=context.email,
                aurora_db_arn=os.environ['AURORA_DB_ARN'],
                aurora_db_secret_arn=os.environ['AURORA_DB_SECRET_ARN'],
                aurora_db_name=os.environ['AURORA_DB_NAME']
            )

        # pull and insert app_metadata
        app_metadata = context.repo.get_user_app_metadata()

        if "suppliers" in app_metadata:
            context.suppliers = app_metadata["suppliers"]
        else:
            context.suppliers = {}

        if "distributors" in app_metadata:
            context.distributors = app_metadata["distributors"]
        else:
            context.distributors = {}

        return handler(event, context)

    return wrapper


def get_repo(record):
    """This is not a decorator"""
    sys.path.append('data_dynamodb')
    sys.path.append('data_common')
    from data_common.exceptions import UserIdNotInObject
    from data_dynamodb.dynamodb_repository import DynamoRepository
    import json

    try:
        body = record['body']
        user_id = json.loads(body)['user_id']
    except KeyError:
        raise UserIdNotInObject

    # While developing, dynamodb local is used. So if `DYANMODB_LOCAL_ENDPOINT` is present in env vars
    # dynamodb boto client is patched to use local db
    try:
        repo = DynamoRepository(
            region_name=os.environ['REGION'],
            table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
            user_id=user_id,
            aurora_db_arn=os.environ['AURORA_DB_ARN'],
            aurora_db_secret_arn=os.environ['AURORA_DB_SECRET_ARN'],
            aurora_db_name=os.environ['AURORA_DB_NAME'],
            dynamodb_local_endpoint=os.environ['DYNAMO_ENDPOINT']
        )

    except KeyError:
        repo = DynamoRepository(
            region_name=os.environ['REGION'],
            table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
            user_id=user_id,
            aurora_db_arn=os.environ['AURORA_DB_ARN'],
            aurora_db_secret_arn=os.environ['AURORA_DB_SECRET_ARN'],
            aurora_db_name=os.environ['AURORA_DB_NAME']
        )

    # pull and insert app_metadata
    suppliers = {}
    if user_id:
        app_metadata = repo.get_user_app_metadata()

        if "suppliers" in app_metadata:
            suppliers = app_metadata["suppliers"]

    return repo, suppliers


def check_supplier(handler):
    """Needs to be decorated after insert_repo, otherwise will not work

    @check_auth
    @insert_repo
    @check_supplier
    def handler():
        ....
    """
    @wraps(handler)
    def wrapper(event, context):
        from api_utils import get_headers
        try:
            headers = get_headers(event)
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad parameter(s) in request. Unable to decode Request Headers.'
                })
            }

        try:
            supplier_id = headers['x-supplier-id']
        except KeyError:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad request. Missing header x-supplier-id'
                })
            }

        if supplier_id not in context.suppliers:
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'Forbidden. supplier_id is not associated with the user'
                })
            }

        context.supplier_id = supplier_id

        return handler(event, context)

    return wrapper


def check_distributor(handler):
    """Needs to be decorated after insert_repo, otherwise will not work

    @check_auth
    @insert_repo
    @check_distributor
    def handler():
        ....
    """
    @wraps(handler)
    def wrapper(event, context):
        from api_utils import get_headers
        try:
            headers = get_headers(event)
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad parameter(s) in request. Unable to decode Request Headers.'
                })
            }

        try:
            distributor_id = headers['x-distributor-id']
        except KeyError:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad request. Missing header x-distributor-id'
                })
            }

        if distributor_id not in context.distributors:
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'Forbidden. distributor_id is not associated with the user'
                })
            }

        context.distributor_id = distributor_id

        return handler(event, context)

    return wrapper


def check_supplier_or_distributor(handler):
    """Needs to be decorated after insert_repo, otherwise will not work

        @check_auth
        @insert_repo
        @check_distributor
        def handler():
            ....
        """

    @wraps(handler)
    def wrapper(event, context):
        from api_utils import get_headers
        try:
            headers = get_headers(event)
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad parameter(s) in request. Unable to decode Request Headers.'
                })
            }

        if 'x-supplier-id' in headers:
            return check_supplier(handler)(event, context)

        if 'x-distributor-id' in headers:
            return check_distributor(handler)(event, context)

        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. Missing header x-supplier-id or x-distributor-id'
            })
        }

    return wrapper


def check_auth(handler):
    @wraps(handler)
    def wrapper(event, context):
        logger.debug('event: {}'.format(event))

        try:
            token_parts = event['headers']['Authorization'].split(' ')
        except KeyError:
            return {
                'statusCode': 401,
                'body': 'The resource you are trying to access is private. '
                        'Please provide an Authorization token'
            }

        auth_token = token_parts[1]

        decoded = jwt_decode(auth_token, AUTH0_CLIENT_PUBLIC_KEY)

        if 'email' in decoded and 'sub' in decoded:
            context.email = decoded['email']
            context.user_id = decoded['sub'][6:]

            # App metadata is inserted into context in insert_repo()
        else:
            return {
                'statusCode': 401,
                'body': 'invalid_token. '
                        'The access token provided is expired, '
                        'revoked, malformed, '
                        'or invalid for other reasons'
            }

        return handler(event, context)

    return wrapper
