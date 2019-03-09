import os
import sys
import boto3
from botocore.exceptions import ClientError

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

SQS_EMAIL_TRANSMITTER = os.getenv('SQS_EMAIL_TRANSMITTER')
NEW_USER_NOTIFICATION_LIST = os.getenv('NEW_USER_NOTIFICATION_LIST')
USER_REGISTER_EMAIL_TEMPLATE = os.getenv('USER_REGISTER_EMAIL_TEMPLATE')


def login(event, context):
    event_log = deepcopy(event)
    try:
        event_log["body"].pop("password")
    except KeyError:
        pass
    logger.debug('event: {}'.format(event_log))

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

    if not all([k in body for k in ['username', 'password']]) or \
            not all([body[k] for k in ['username', 'password']]):
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Both username and password are required.'
            })
        }

    # Authenticate and get tokens
    req = requests.post(
        os.environ['AUTH0_DOMAIN'] + '/oauth/token',
        json={
            'grant_type': 'password',
            'username': body['username'],
            'password': body['password'],
            'audience': os.environ['AUTH0_AUDIENCE'],
            'client_id': os.environ['AUTH0_CLIENT_ID'],
            'client_secret': os.environ['AUTH0_CLIENT_SECRET'],
            'scope': 'openid'
        }
    )

    body = req.json()

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

    # get Auth0 user profile object (in order to get app_metadata)
    resp = requests.post(
        os.environ['AUTH0_DOMAIN'] + '/oauth/token',
        json={
            'grant_type': 'client_credentials',
            'client_id': os.environ['AUTH0_MANAGEMENT_API_CLIENT_ID'],
            'client_secret': os.environ['AUTH0_MANAGEMENT_API_CLIENT_SECRET'],
            'audience': os.environ['AUTH0_AUDIENCE'],
            'scope': 'read:users'
        },
        headers={
            'content-type': "application/json"
        }

    )

    users_token_body = resp.json()

    if 'access_token' in users_token_body:
        _access_token = users_token_body['access_token']
        _auth0_user_id = payload['sub']
        resp = requests.get(
            os.environ['AUTH0_DOMAIN'] + '/api/v2/users/{ID}'.format(ID=_auth0_user_id),
            headers={
                'content-type': "application/json",
                'Authorization': 'Bearer {ACCESS_TOKEN}'.format(ACCESS_TOKEN=_access_token)
            }

        )

        users_body = resp.json()
        if "app_metadata" not in users_body:
            app_metadata = {}
        else:
            app_metadata = users_body["app_metadata"]

        # update app_metadata in users object
        # While developing, dynamodb local is used. So if `DYANMODB_LOCAL_ENDPOINT` is present in env vars
        # dynamodb boto client is patched to use local db
        email = payload['email']
        user_id = payload['sub'][6:]
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

        try:
            repo.update_user_app_metadata(app_metadata)
        except NoSuchEntity:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'User not found'
                })
            }
        except:
            logger.log_uncaught_exception()
    else:
        if 'error_description' in users_token_body:
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
        'scope',
        'expires_in',
        'token_type'
    ]):
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


def signup(event, context):
    event_log = deepcopy(event)
    try:
        event_log["body"].pop("password")
    except KeyError:
        pass
    logger.debug('event: {}'.format(event_log))

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

    if 'email' not in body or not body['email'] or 'password' not in body or not body['password']:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Missing required key-value pair(s) in request body'
            })
        }

    email = body['email']
    password = body['password']
    name = body.get('name', '')
    company_name = body.get('company_name', '')
    is_distributor = body.get('is_distributor', False)
    website = body.get('website', '')

    # get Machine-to-machine access token
    resp = requests.post(
        os.environ['AUTH0_DOMAIN'] + '/oauth/token',
        json={
            'grant_type': 'client_credentials',
            'client_id': os.environ['AUTH0_MANAGEMENT_API_CLIENT_ID'],
            'client_secret': os.environ['AUTH0_MANAGEMENT_API_CLIENT_SECRET'],
            'audience': os.environ['AUTH0_AUDIENCE'],
            'scope': 'create:users'
        },
        headers={
            'content-type': "application/json"
        }

    )

    body = resp.json()

    if all(k in body for k in [
        'access_token',
        'scope',
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

    access_token = body['access_token']

    payload = {
        'email': email,
        'password': password,
        'email_verified': True,
        'blocked': False,
        'connection': os.environ['AUTH0_CONNECTION'],
    }

    if name:
        payload['name'] = name

    resp = requests.post(
        os.environ['AUTH0_DOMAIN'] + "/api/v2/users",
        json=payload,
        headers={
            'Authorization': 'Bearer {TOKEN}'.format(TOKEN=access_token),
            'content-type': "application/json"
    })

    body = resp.json()
    print(body)

    if all(k in body for k in [
        'user_id',
        'email'
    ]):
        user_id = body['user_id'][6:]
        email = body['email']

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

        if 'name' in body:
            user_obj['name'] = body['name']
        if 'picture' in body:
            user_obj['picture'] = body['picture']
        if 'nickname' in body:
            user_obj['nickname'] = body['nickname']
        if 'email_verified' in body:
            user_obj['email_verified'] = body['email_verified']
        if 'blocked' in body:
            user_obj['blocked'] = body['blocked']

        user_obj = repo.update_profile(user_obj)

        # check if "company_name" in request body and create supplier
        if company_name:
            if not is_distributor:
                supplier = {
                    "name": company_name,
                    "website": website
                }

                supplier_obj = repo.save_supplier(supplier)

                # add user to distributors's users list
                supplier_id = supplier_obj["entity_id"]
                user_info = {
                    "email": email,
                    "role": "admin",
                    "name": user_obj.get("name", "")
                }
                try:
                    repo.upsert_user_in_supplier(supplier_id, user_info)
                except Auth0UnknownError as ex:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({
                            'error': "User created. Auth0 error: {ERROR}".format(ERROR=str(ex))
                        })
                    }
                except Auth0UnableToAccess:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({
                            'error': "User created. But app_metadata update failed, Unable to access Auth0"
                        })
                    }
                except:
                    logger.log_uncaught_exception()
            else:
                distributor = {
                    "name": company_name,
                    "website": website
                }

                distributor_obj = repo.save_distributor(distributor)

                # add user to distributors's users list
                distributor_id = distributor_obj["entity_id"]
                user_info = {
                    "email": email,
                    "role": "admin",
                    "name": user_obj.get("name", "")
                }
                try:
                    repo.upsert_user_in_distributor(distributor_id, user_info)
                except Auth0UnknownError as ex:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({
                            'error': "User created. Auth0 error: {ERROR}".format(ERROR=str(ex))
                        })
                    }
                except Auth0UnableToAccess:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({
                            'error': "User created. But app_metadata update failed, Unable to access Auth0"
                        })
                    }
                except:
                    logger.log_uncaught_exception()

        email_data = {'email': email, 'name': name, 'website': website,
                      'company_name': company_name}
        if is_distributor:
            email_data['brewery_distributor'] = "Distributor"
        else:
            email_data['brewery_distributor'] = "Brewery"

        to_list = NEW_USER_NOTIFICATION_LIST.split(',')
        to_email_list = []
        for item in to_list:
            to_email_list.append(item.strip())

        # Send the SQS message
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=SQS_EMAIL_TRANSMITTER)
        try:
            message_body = {
                "template": USER_REGISTER_EMAIL_TEMPLATE,
                "to": to_email_list,
                "data": email_data
            }
            print(message_body)
            response = queue.send_message(MessageBody=json.dumps(message_body))
            logger.debug('response: {}'.format(response))
        except ClientError as e:
            logger.debug('error: {}'.format(e))
        except:
            logger.log_uncaught_exception()

        return {
            'statusCode': 200,
            'body': json.dumps(user_obj)
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


def password_reset(event, context):
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

    if "email" not in body or not body["email"]:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Missing required key-value pair(s) in request body'
            })
        }

    email = body["email"]

    # get Machine-to-machine access token
    resp = requests.post(
        os.environ['AUTH0_DOMAIN'] + '/oauth/token',
        json={
            'grant_type': 'client_credentials',
            'client_id': os.environ['AUTH0_MANAGEMENT_API_CLIENT_ID'],
            'client_secret': os.environ['AUTH0_MANAGEMENT_API_CLIENT_SECRET'],
            'audience': os.environ['AUTH0_AUDIENCE'],
            'scope': 'update:users'
        },
        headers={
            'content-type': "application/json"
        }

    )

    body = resp.json()

    if all(k in body for k in [
        'access_token',
        'scope',
        'expires_in',
        'token_type'
    ]):
        pass  # to the next section of code
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

    access_token = body['access_token']

    resp = requests.post(
        os.environ['AUTH0_DOMAIN'] + "/dbconnections/change_password",
        json={
            'email': email,
            'client_id': os.environ['AUTH0_MANAGEMENT_API_CLIENT_ID'],
            'connection': os.environ['AUTH0_CONNECTION'],
        },
        headers={
            'Authorization': 'Bearer {TOKEN}'.format(TOKEN=access_token),
            'content-type': "application/json"
        })

    if resp.status_code == 200:
        return {
            'statusCode': 204
        }
    elif resp.status_code != 200 and 'message' in body:
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
