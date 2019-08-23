from data_common.exceptions import MissingRequiredKey, BadParameters
from data_common.utils import is_right_datatype
import string
import random


def check_for_required_keys(obj, attributes, exclude=None):
    keys_required = list(attributes)
    if exclude:
        keys_required = [k for k in keys_required if k not in exclude]

    for key in keys_required:
        if key not in obj or obj[key] is "":
            raise MissingRequiredKey(key)


def check_properties_datatypes(obj, attributes):
    """
    check datatype of required key-val pairs

    :param obj:
    :param attributes:
    :param allow_optional_null: set optional fields could carry null value
    :return:
    """
    for key, val in obj.items():
        if key in attributes:
            if not is_right_datatype(val, attributes[key]):
                raise BadParameters(key)


def generate_random_password():
    """Generate a random string of fixed length """
    password_length = 12
    special_chars = "!@#$%"
    password = ""

    for _ in range(1000):
        if not (
                any(c in string.ascii_lowercase for c in password) and
                any(c in string.ascii_uppercase for c in password) and
                any(c in string.digits for c in password) and
                any(c in special_chars for c in password)
        ):
            password = ''.join(
                random.SystemRandom().choice(
                    string.ascii_lowercase + string.ascii_uppercase + string.digits + special_chars) for _ in range(password_length)
            )

    return password