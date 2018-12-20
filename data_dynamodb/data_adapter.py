import time
import uuid
from decimal import Decimal
import functools

import boto3
from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.data_interface import DataInterface


def paginate(function=None, first_match=False):
    # first_match: break from loop upon finding items
    def with_pagination(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            def get_items(resp):
                items = resp['Items']
                count = resp['Count']

                if first_match and items:
                    return items, count

                while "LastEvaluatedKey" in resp:
                    kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
                    resp = func(self, *args, **kwargs)
                    items.extend(resp['Items'])
                    count += resp['Count']

                    if first_match and items:
                        return items, count

                return items, count

            response = func(self, *args, **kwargs)
            response['Items'], response['Count'] = get_items(response)
            return response

        return wrapper

    if function:
        return with_pagination(function)

    return with_pagination


class DynamoStorage(DataInterface):
    def __init__(self, table, user_id, *args, **kwargs):
        self._table = table
        self._user_id = user_id
        self._client = boto3.resource(
            'dynamodb',
            *args,
            **kwargs
        )

    @property
    def client(self):
        """boto3 client"""
        return self._client

    @client.setter
    def client(self, client):
        """Setter for boto3 client. Used for tests"""
        self._client = client

    @staticmethod
    def _clean_empty(d):
        if not isinstance(d, (dict, list)):
            return d
        if isinstance(d, list):
            return [v for v in (DynamoStorage._clean_empty(v) for v in d) if v is not ""]
        return {k: v for k, v in ((k, DynamoStorage._clean_empty(v)) for k, v in d.items()) if v is not ""}

    @staticmethod
    def _float_to_decimal(d):
        if not isinstance(d, (dict, list)):
            if isinstance(d, float):
                return Decimal('{val:.3f}'.format(val=d))
            return d
        if isinstance(d, list):
            return [v for v in (DynamoStorage._float_to_decimal(v) for v in d)]
        return {k: v for k, v in ((k, DynamoStorage._float_to_decimal(v)) for k, v in d.items())}

    def save(self, obj_type, obj):
        # if entity_id not provided, its assumed as new entity
        if 'entity_id' not in obj or not obj['entity_id']:
            obj['entity_id'] = str(uuid.uuid4())

        # if active is not set externally, its assumed as active
        if 'active' not in obj:
            obj['active'] = True

        response = self._client.Table(self._table).query(
            KeyConditionExpression=Key('entity_id').eq(obj['entity_id']),
            FilterExpression=Attr('latest').eq(True)
        )

        if 'version' in obj:
            obj['previous_version'] = obj['version']
        else:
            obj['previous_version'] = '00000000-0000-0000-0000-000000000000'

        for item in response["Items"]:
            self._client.Table(self._table).update_item(
                Key={
                    'entity_id': item['entity_id'],
                    'version': item["version"]
                },
                UpdateExpression=('SET latest = :latest'),
                ExpressionAttributeValues={
                    ':latest': False
                }
            )

        # convert to/assign private attrs
        obj['version'] = str(uuid.uuid4())
        obj['latest'] = True
        obj['changed_by_id'] = self._user_id
        obj['changed_on'] = int(time.time())
        obj['obj_type'] = obj_type

        obj = self._clean_empty(obj)
        obj = self._float_to_decimal(obj)

        self._client.Table(self._table).put_item(
            Item=obj
        )

        obj = json_util.loads(obj)
        return obj

    def save_minimal(self, table, obj):
        """
        Saves without Big8 attributes
        """
        obj = self._clean_empty(obj)
        obj = self._float_to_decimal(obj)

        self._client.Table(table).put_item(
            Item=obj
        )
        obj = json_util.loads(obj)
        return obj

    def atomic_update(self, table, key, update_expression, express_attr_values):
        """
        Updates an item in the table based on the update expression and returns the updated item.
        `key` refers to the id of the item in primary index
        Ref: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.AtomicCounters
        """
        response = self._client.Table(table).update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=express_attr_values,
            ReturnValues='UPDATED_NEW'
        )
        return response

    def get_by_user_id(self, user_id):
        for attempt in range(0, 4):
            obj = self.get(user_id)
            if obj:
                return obj
            else:
                time.sleep(attempt)
        else:
            return None

    def get(self, entity_id):
        @paginate(first_match=True)
        def run_query(entity_id, **kwargs):
            return self._client.Table(self._table).query(
                KeyConditionExpression=Key('entity_id').eq(entity_id),
                FilterExpression=Attr('latest').eq(True) & Attr('active').eq(True),
                **kwargs
            )

        response = run_query(entity_id)

        if response["Count"] > 0:
            obj = response['Items'][0]
            obj = json_util.loads(obj)

            return obj
        else:
            return None

    @paginate
    def get_items(self, query, **kwargs):
        return self._client.Table(self._table).query(**{**query, **kwargs})

    @paginate
    def get_all_items(self, obj_type, **kwargs):
        return self._client.Table(self._table).scan(
            FilterExpression=Attr('latest').eq(True) & Attr('active').eq(True) & Attr('obj_type').eq(obj_type),
            **kwargs
        )

    @paginate
    def get_filtered_items(self, filter_expression, **kwargs):
        return self._client.Table(self._table).scan(
            FilterExpression=Attr('latest').eq(True) & Attr('active').eq(True) & filter_expression,
            **kwargs
        )

    @paginate(first_match=True)
    def get_by_version(self, entity_id, version, **kwargs):
        return self._client.Table(self._table).query(
            KeyConditionExpression=Key('entity_id').eq(entity_id) & Key('version').eq(version),
            **kwargs
        )

    @paginate
    def scan_items(self, expression, **kwargs):
        return self._client.Table(self._table).scan(**{**expression, **kwargs})

    def __repr__(self):
        return '<DynamoStorage>'


class DataStorage:
    def __init__(self, storage):
        self._storage = storage

    def __getattr__(self, attr):
        return getattr(self._storage, attr)