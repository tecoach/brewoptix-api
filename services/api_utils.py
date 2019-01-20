from api_constants import base_attributes, private_base_attributes
import copy
import json


def get_user_id(event):
    user_id = event['pathParameters']['user_id']
    return user_id


def get_body(event):
    body = event['body']
    if isinstance(body, str):
        body = json.loads(body)
    return body


def get_path_parameters(event):
    try:
        parameters = event['pathParameters']
    except KeyError:
        try:
            parameters = event['path']
        except KeyError:
            parameters = {}
    return parameters


def get_query_parameters(event):
    try:
        parameters = event['query']
    except KeyError:
        parameters = {}
    return parameters


def get_headers(event):
    try:
        headers = event['headers']
    except KeyError:
        headers = {}
    return headers


def remove_private_attrs(body):
    """
    :param body: dict to be sent as response
    :return: body, after removing few attributes
    """
    body = copy.deepcopy(body)

    for k in private_base_attributes:
        body.pop(k, None)

    return body


def remove_base_attrs(body, exclude_user_id=False):
    """
    :param body: dict to be sent as response
    :return: body, after removing few attributes
    """
    body = copy.deepcopy(body)

    for k in base_attributes:
        if k == 'user_id' and exclude_user_id:
            continue

        body.pop(k, None)

    return body


def get_token(event):
    if 'headers' in event and 'Authorization' in event['headers']:
        token = event['headers']['Authorization'].split()[1]
        return token
    else:
        return False
