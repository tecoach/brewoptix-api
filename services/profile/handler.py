import os
import sys
# needed only for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests

from common import insert_repo, check_auth
from api_utils import get_body
from data_common.exceptions import NoSuchEntity, \
    BadParameters, CannotModifyEntityStates
from log_config import logger


@check_auth
@insert_repo
def get_or_create_profile(event, context):
    """
    Get user profile or create a new one if it doesnt exist
    """
    logger.debug('event: {}'.format(event))

    try:
        item = context.repo.get_or_create_profile()
        body = json.dumps(item)
        return {
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': body
        }
    except NoSuchEntity:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'User not found'
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
def update_profile(event, context):
    """
    Update user profile
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

    body['user_id'] = context.user_id

    try:
        item = context.repo.update_profile(body)
        return {
            'statusCode': 200,
            'body': json.dumps(item)
        }
    except NoSuchEntity:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'User not found'
            })
        }
    except BadParameters as ex:
        msg = str(ex)
        if msg:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': msg
                })
            }
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad request. '
                         'The request was Malformed'
            })
        }
    except CannotModifyEntityStates:
        return {
            'statusCode': 409,
            'body': json.dumps({
                'error': 'Update of the entity failed'
            })
        }
    except:
        logger.log_uncaught_exception()


@check_auth
@insert_repo
def delete_account(event, context):
    """
    Delete user account
    """
    logger.debug('event: {}'.format(event))

    req = requests.post(
        os.environ['AUTH0_DOMAIN'] + '/oauth/token',
        json={
            'grant_type': 'client_credentials',
            'audience': os.environ['AUTH0_AUDIENCE'],
            'client_id': os.environ['AUTH0_MANAGEMENT_API_CLIENT_ID'],
            'client_secret': os.environ['AUTH0_MANAGEMENT_API_CLIENT_SECRET']
        }
    )

    logger.debug('Getting machine-to-machine application, '
                 'access token.\nResponse: {}'.format(req.json()))

    jwt = req.json()['access_token']

    headers = {
            'Authorization': 'Bearer {}'.format(jwt),
            'Content-Type': 'application/json',
        }

    if context.user_id.find('|') == -1:
        _auth0_user_id = 'auth0|' + context.user_id
    else:
        _auth0_user_id = context.user_id

    url = os.environ['AUTH0_DOMAIN'] + \
        '/api/v2/users/' + _auth0_user_id

    resp = requests.delete(url, headers=headers)

    if resp.status_code != 204:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Something went wrong with deleting user account'
            })     # something went wrong with auth0
        }

    try:
        context.repo.delete_profile()

        return {
            'statusCode': 204
        }
    except NoSuchEntity:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'User not found'
            })
        }
    except:
        logger.log_uncaught_exception()
