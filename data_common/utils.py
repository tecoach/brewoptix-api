import copy
import random
import string
import dateutil
import uuid
import maya
from datetime import datetime

from data_common.constants import base_attributes, private_base_attributes


def clean(obj):
    remove_variables = [
        'previous_version',
        'active',
        'latest',
        'changed_by_id',
        'obj_type'
    ]
    for key in remove_variables:
        obj.pop(key, None)

    if obj and 'changed_on' in obj:
        obj['changed_on'] = maya.to_iso8601(
            datetime.utcfromtimestamp(
                obj['changed_on']
            )
        )

    return obj


def is_right_datatype(variable, datatype):
    if datatype == int:
        return type(variable) == int
    if datatype == float:
        return type(variable) == int or type(variable) == float
    if datatype == str:
        return type(variable) == str
    if datatype == list:
        return type(variable) == list
    if datatype == bool:
        return type(variable) == bool
    if datatype == dict:
        return type(variable) == dict
    if datatype == list([list([str])]):
        return type(variable) == list and all(type(item) == list for item in variable) and all(type(item) == str for row in variable for item in row)
    if datatype == "date" or datatype == "timestamp":
        try:
            dateutil.parser.parse(variable)
        except ValueError:
            return False
    if datatype == "uuid":
        try:
            uuid.UUID(variable, version=4)
        except Exception:
            return False
    return True


def remove_private_attrs(body):
    """

    :param body: dict to be sent as response 
    :return: body, after removing few attributes
    """
    body = copy.deepcopy(body)
    for k in private_base_attributes:
        body.pop(k, None)

    return body


def remove_base_attrs(body):
    """

    :param body: dict to be sent as response
    :return: body, after removing few attributes
    """
    body = copy.deepcopy(body)

    for k in base_attributes:
        body.pop(k, None)

    return body


def generate_affiliate_id():
    # Ref: https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
    affiliate_id = "OI01"
    for _ in range(1000):
        if any(k in affiliate_id for k in "OI01"):
            # generate new id
            return ''.join(
                random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))
