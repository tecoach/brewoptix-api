from datetime import datetime

import maya
from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import production_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import ProductionRepository
from data_common.queue import SQSManager
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoProductionRepository(ProductionRepository, SQSManager, SnsNotifier):
    def get_all_production(self, supplier_id):
        obj_type = 'production'

        query = {
            'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
            'FilterExpression':
                (Attr('latest').eq(True) & Attr('active').eq(True)),
            'IndexName': 'by_supplier_id_and_obj_type'
        }

        response = self._storage.get_items(query)

        production_obj = []

        for item in response['Items']:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # production = self._storage.get(table, entity_id)
            # production = clean(production)
            production = json_util.loads(clean(item))
            production['production_date'] = datetime.utcfromtimestamp(
                production['production_date']
            ).isoformat().split('T')[0]
            production_obj.append(production)

        return production_obj

    def get_production_by_production_date_range(self, supplier_id, min_production_date, max_production_date=None):
        obj_type = 'production'

        min_production_date = maya.parse(min_production_date.split('T')[0]).epoch

        if max_production_date:
            max_production_date = maya.parse(max_production_date.split('T')[0]).epoch

        if max_production_date:
            query = {
                'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                'FilterExpression':
                    Attr('latest').eq(True) & Attr('active').eq(True) & Attr('production_date').between(min_production_date,
                                                                                                       max_production_date),
                'IndexName': 'by_supplier_id_and_obj_type'
            }
        else:
            query = {
                'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                'FilterExpression':
                    Attr('latest').eq(True) & Attr('active').eq(True) & Attr('production_date').gt(min_production_date),
                'IndexName': 'by_supplier_id_and_obj_type'
            }

        response = self._storage.get_items(query)

        production_obj = []

        for item in response['Items']:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # production = self._storage.get(table, entity_id)
            # production = clean(production)
            production = json_util.loads(clean(item))
            production['production_date'] = datetime.utcfromtimestamp(
                production['production_date']
            ).isoformat().split('T')[0]
            production_obj.append(production)

        return production_obj

    def save_production(self, obj):
        obj_type = 'production'

        check_for_required_keys(obj, production_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, production_attributes)

        obj['user_id'] = self._user_id

        # convert production_date to epoch integer
        obj['production_date'] = maya.parse(
            obj['production_date']).epoch

        production_obj = self._storage.save(obj_type, obj)
        self.sns_publish("production", obj)  # publish notification

        production = clean(production_obj)
        production['production_date'] = datetime.utcfromtimestamp(
            production['production_date']
        ).isoformat().split('T')[0]
        return production

    def get_production_by_id(self, supplier_id, entity_id):
        production = self._storage.get(entity_id)
        if production:
            production = clean(production)

            if production["supplier_id"] != supplier_id:
                raise NoSuchEntity

            production['production_date'] = datetime.utcfromtimestamp(
                production['production_date']
            ).isoformat().split('T')[0]
        else:
            raise NoSuchEntity

        return production

    def delete_production_by_id(self, supplier_id, entity_id):
        obj_type = 'production'

        production = self._storage.get(entity_id)

        if production:
            obj = clean(production)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("production", obj)  # publish notification
        else:
            raise NoSuchEntity

    def process_production_queue(self, obj):
        print(obj)

        supplier_id = obj["supplier_id"]
        entity_id = obj['entity_id']
        production_date = maya.to_iso8601(datetime.utcfromtimestamp(obj['production_date'])).split("T")[0]

        # Select all records with matching entity_id
        table = "production"
        query = """SELECT brand_id, package_type_id, production_date
                FROM {TABLE}
                USE INDEX (by_entity_id_and_supplier_id)
                WHERE supplier_id='{SUPPLIER_ID}' AND entity_id='{ENTITY_ID}'
                """.format(
            TABLE=table,
            SUPPLIER_ID=supplier_id,
            ENTITY_ID=entity_id
        )

        results = self._aurora_storage.get_items(query)

        # convert from response
        keys = [
            "brand_id",
            "package_type_id",
            "production_date"
        ]

        record_ids = {}
        for result in results:
            record = {}
            for i, val in enumerate(result):
                record[keys[i]] = val
            record_ids[record['brand_id'] + '_' + record['package_type_id']] = record

        # delete all by entity_id from table
        table = "production"
        query = """
                DELETE
                FROM `{TABLE}`
                WHERE entity_id='{ENTITY_ID}' AND supplier_id='{SUPPLIER_ID}'
                """.format(TABLE=table,
                           ENTITY_ID=entity_id,
                           SUPPLIER_ID=supplier_id)

        resp = self._aurora_storage._execute(query)

        if obj['active']:  # put or post
            products = obj["products"]
            for product in products:
                brand_id = product['brand_id']
                package_type_id = product['package_type_id']
                quantity = product['quantity']

                item = {
                    "brand_id": brand_id,
                    "entity_id": entity_id,
                    "package_type_id": package_type_id,
                    "supplier_id": supplier_id,
                    "production_date": production_date,
                    "quantity": quantity,
                }

                _id = item['brand_id'] + '_' + item['package_type_id']
                if _id not in record_ids or obj['production_date'] < maya.parse(record_ids[_id]["production_date"]).epoch:
                    record_ids[_id] = item

                # insert into aurora table
                self._aurora_storage.save(table, item)

        # trigger projections calculation for old records + new inserts
        for item in record_ids.values():
            brand_id = item["brand_id"]
            package_type_id = item["package_type_id"]
            # Re-calculate projections
            self.sqs_enqueue("projections", {
                'user_id': self._user_id,
                'supplier_id': supplier_id,
                'brand_id': brand_id,
                'package_type_id': package_type_id,
                'start_date': item["production_date"],
            })  # enqueue object
