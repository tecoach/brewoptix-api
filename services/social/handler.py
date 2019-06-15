import os
import sys

# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from log_config import logger
from api_utils import get_body
from urllib.parse import urlparse, urlencode
from auth import jwt_decode, jwt_encode
from copy import deepcopy

sys.path.append('data_dynamodb')
sys.path.append('data_common')
from data_dynamodb.dynamodb_repository import DynamoRepository
from data_common.exceptions import NoSuchEntity, CannotModifyEntityStates, Auth0UnknownError, Auth0UnableToAccess

AUTH0_CLIENT_PUBLIC_KEY = os.getenv('AUTH0_CLIENT_PUBLIC_KEY')


def social_auth(event, context):
    logger.debug('event: {}'.format(event))

    if os.environ['SIGNUP_ORIGIN_URL'] is not "*":    # "*" means accept any origin
        # Check if the request is originating from a valid URI
        origin = event['headers']['origin']
        valid_origin_uri = urlparse(os.environ['SIGNUP_ORIGIN_URL'])
        request_uri = urlparse(origin)

        if request_uri.netloc not in valid_origin_uri.netloc:
            logger.error("Request origin domain: {REQ_DOM}, "
                         "Valid origin domain: {VALID_DOM}".format(REQ_DOM=request_uri.netloc,
                                                                   VALID_DOM=valid_origin_uri.netloc))
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'error': 'Unauthorized. Request originating from invalid domain'
                })
            }

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

    if 'connection' not in body or not body['connection'] or 'redirect_uri' not in body or not body['redirect_uri']:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Missing required key-value pair(s) in request body'
            })
        }

    connection = body['connection']
    redirect_uri = body['redirect_uri']

    # token access right limited openid, profile, email
    query = (('client_id', os.environ['AUTH0_CLIENT_ID']),
             ('response_type', 'code'),
             ('connection', connection),
             ('scope', 'openid profile email'),
             ('redirect_uri', redirect_uri),
             ('state', 'xyzABC123'))

    return_url = os.environ['AUTH0_DOMAIN'] + '/authorize?' + urlencode(query).replace('+', '%20')
    return {
        'statusCode': 200,
        'body': json.dumps({
            'return_url': return_url
        })
    }


def social_signup(event, context):
    logger.debug('event: {}'.format(event))

    if os.environ['SIGNUP_ORIGIN_URL'] is not "*":    # "*" means accept any origin
        # Check if the request is originating from a valid URI
        origin = event['headers']['origin']
        valid_origin_uri = urlparse(os.environ['SIGNUP_ORIGIN_URL'])
        request_uri = urlparse(origin)

        if request_uri.netloc not in valid_origin_uri.netloc:
            logger.error("Request origin domain: {REQ_DOM}, "
                         "Valid origin domain: {VALID_DOM}".format(REQ_DOM=request_uri.netloc,
                                                                   VALID_DOM=valid_origin_uri.netloc))
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'error': 'Unauthorized. Request originating from invalid domain'
                })
            }

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

    if 'authorization_code' not in body or not body['authorization_code']:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Missing authorization_code in request body'
            })
        }

    authorization_code = body['authorization_code']

    # get access token
    resp = requests.post(
        url=os.environ['AUTH0_DOMAIN'] + '/oauth/token',
        data={
            'grant_type': 'authorization_code',
            'client_id': os.environ['AUTH0_CLIENT_ID'],
            'client_secret': os.environ['AUTH0_CLIENT_SECRET'],
            'code': authorization_code,
            'redirect_uri': 'https://localhost:8080/callback'
        },
        headers={
            'content-type': "application/x-www-form-urlencoded"
        }
    )

    body = resp.json()

    if all(k in body for k in [
        'access_token',
        'id_token',
        'expires_in',
        'token_type'
    ]):
        pass    # to the next section of code
    elif 'error_description' in body:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': body['error_description']
            })
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Unknown Error happened'
            })
        }

    # extract payload for jwt token
    if 'id_token' in body:
        _id_token = body['id_token']
        payload = jwt_decode(_id_token, AUTH0_CLIENT_PUBLIC_KEY)
    else:
        if 'error_description' in body:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': body['error_description']
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Unknown Error happened'
                })
            }

    if all(k in payload for k in [
        'email',
        'sub'
    ]):
        # extract user id, social user id format: social-type|user_id
        user_id = payload['sub']
        email = payload['email']

        # Make a repo object
        sys.path.append('data_dynamodb')
        sys.path.append('data_common')
        from data_dynamodb.dynamodb_repository import DynamoRepository

        # While developing, dynamodb local is used. So if `DYANMODB_LOCAL_ENDPOINT` is present in env vars
        # dynamodb boto client is patched to use local db
        try:
            repo = DynamoRepository(
                region_name=os.environ['REGION'],
                table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
                user_id=user_id,
                email=email,
                dynamodb_local_endpoint=os.environ['DYNAMO_ENDPOINT']
            )

        except KeyError:
            repo = DynamoRepository(
                region_name=os.environ['REGION'],
                table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
                user_id=user_id,
                email=email
            )
        except:
            logger.log_uncaught_exception()

        # create new user in `brewoptix-users` table
        user_obj = repo.get_or_create_profile()

        if 'name' in payload:
            user_obj['name'] = payload['name']
        if 'picture' in payload:
            user_obj['picture'] = payload['picture']
        if 'nickname' in payload:
            user_obj['nickname'] = payload['nickname']
        if 'email_verified' in payload:
            user_obj['email_verified'] = payload['email_verified']
        if 'blocked' in payload:
            user_obj['blocked'] = payload['blocked']

        user_obj = repo.update_profile(user_obj)
        return {
            'statusCode': 200,
            'body': json.dumps(body)
        }
    elif 'message' in body:
        return {
            'statusCode': body.get('statusCode', 400),
            'body': json.dumps({
                'error': body['message']
            })
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Unknown Error happened'
            })
        }


def social_signin(event, context):
    event_log = deepcopy(event)

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

    if 'authorization_code' not in body or not body['authorization_code']:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Missing authorization_code in request body'
            })
        }

    authorization_code = body['authorization_code']

    # get access token
    resp = requests.post(
        url=os.environ['AUTH0_DOMAIN'] + '/oauth/token',
        data={
            'grant_type': 'authorization_code',
            'client_id': os.environ['AUTH0_CLIENT_ID'],
            'client_secret': os.environ['AUTH0_CLIENT_SECRET'],
            'code': authorization_code,
            'redirect_uri': 'https://localhost:8080/callback'
        },
        headers={
            'content-type': "application/x-www-form-urlencoded"
        }
    )

    body = resp.json()

    # extract payload for jwt token
    if 'id_token' in body:
        _id_token = body['id_token']
        payload = jwt_decode(_id_token, AUTH0_CLIENT_PUBLIC_KEY)
    else:
        if 'error_description' in body:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': body['error_description']
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Unknown Error happened'
                })
            }

    if 'access_token' in body:
        _access_token = body['access_token']

        # While developing, dynamodb local is used. So if `DYANMODB_LOCAL_ENDPOINT` is present in env vars
        # dynamodb boto client is patched to use local db
        email = payload['email']
        user_id = payload['sub']
        try:
            repo = DynamoRepository(
                region_name=os.environ['REGION'],
                table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
                user_id=user_id,
                email=email,
                dynamodb_local_endpoint=os.environ['DYNAMO_ENDPOINT']
            )

        except KeyError:
            repo = DynamoRepository(
                region_name=os.environ['REGION'],
                table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
                user_id=user_id,
                email=email
            )
        except:
            logger.log_uncaught_exception()

    else:
        if 'error_description' in body:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': body['error_description']
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Unknown Error happened'
                })
            }

    if all(k in body for k in [
        'access_token',
        'id_token',
        'expires_in',
        'token_type'
    ]):
        body['scope'] = 'openid profile email'
        return {
            'statusCode': 200,
            'body': json.dumps(body)
        }
    elif 'error_description' in body:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': body['error_description']
            })
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Unknown Error happened'
            })
        }