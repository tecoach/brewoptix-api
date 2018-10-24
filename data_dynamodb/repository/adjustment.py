from datetime import datetime

import maya
from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import adjustment_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import AdjustmentRepository
from data_common.queue import SQSManager
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoAdjustmentRepository(AdjustmentRepository, SQSManager, SnsNotifier):
    def is_product_exists(self, supplier_id, product_id):
        product_type = self._storage.get(product_id)

        if not product_type:
            raise NoSuchEntity("Product")
        else:
            product_type = clean(product_type)

            if product_type["supplier_id"] != supplier_id:
                raise NoSuchEntity("Product")

    def get_all_adjustments(self, supplier_id):
        obj_type = 'adjustment-inventory'

        query = {
            'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
            'FilterExpression':
                (Attr('latest').eq(True) & Attr('active').eq(True)),
            'IndexName': 'by_supplier_id_and_obj_type'
        }

        response = self._storage.get_items(query)

        adjustments_obj = []

        for item in response['Items']:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # adjustment_resp = self._storage.get(table, entity_id)
            # adjustment = adjustment_resp['Items'][0]
            # adjustment = clean(adjustment)
            adjustment = json_util.loads(clean(item))

            adjustment['adjustment_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    adjustment['adjustment_date']
                )
            ).split('T')[0]
            adjustments_obj.append(adjustment)

        return adjustments_obj

    def get_adjustment_by_adjustment_date_range(self, supplier_id, min_adjustment_date, max_adjustment_date=None):
        obj_type = 'adjustment-inventory'

        min_adjustment_date = maya.parse(min_adjustment_date.split('T')[0]).epoch

        if max_adjustment_date:
            max_adjustment_date = maya.parse(max_adjustment_date.split('T')[0]).epoch

        if max_adjustment_date:
            query = {
                'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(
                    obj_type),
                'FilterExpression':
                    Attr('latest').eq(True) & Attr('active').eq(True) &
                    Attr('adjustment_date').between(min_adjustment_date,
                                                    max_adjustment_date),
                'IndexName': 'by_supplier_id_and_obj_type'
            }
        else:
            query = {
                'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(
                    obj_type),
                'FilterExpression':
                    Attr('latest').eq(True) & Attr('active').eq(True) & Attr('adjustment_date').gt(
                    min_adjustment_date),
                'IndexName': 'by_supplier_id_and_obj_type'
            }

        response = self._storage.get_items(query)

        adjustments_obj = []

        for item in response['Items']:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # adjustment_resp = self._storage.get(table, entity_id)
            # adjustment = adjustment_resp['Items'][0]
            # adjustment = clean(adjustment)
            adjustment = json_util.loads(clean(item))

            adjustment['adjustment_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    adjustment['adjustment_date']
                )
            ).split('T')[0]
            adjustments_obj.append(adjustment)

        return adjustments_obj

    def save_adjustment(self, obj):
        obj_type = 'adjustment-inventory'

        check_for_required_keys(obj, adjustment_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, adjustment_attributes)

        obj['user_id'] = self._user_id

        # convert observation_month to epoch integer
        obj['adjustment_date'] = maya.parse(
            obj['adjustment_date']).epoch

        self.is_product_exists(obj["supplier_id"], obj["product_id"])

        adjustment_obj = self._storage.save(obj_type, obj)
        self.sns_publish("adjustments", obj)  # publish notification

        adjustment = clean(adjustment_obj)

        adjustment['adjustment_date'] = datetime.utcfromtimestamp(
            adjustment['adjustment_date']
        ).isoformat().split('T')[0]

        return adjustment

    def get_adjustment_record_by_id(self, supplier_id, entity_id):
        adjustment = self._storage.get(entity_id)
        if adjustment:
            adjustment = clean(adjustment)

            if adjustment["supplier_id"] != supplier_id:
                raise NoSuchEntity("Adjustment")

            adjustment['adjustment_date'] = datetime.utcfromtimestamp(
                adjustment['adjustment_date']
            ).isoformat().split('T')[0]
        else:
            raise NoSuchEntity("Adjustment")

        return adjustment

    def delete_adjustment_record_by_id(self, supplier_id, entity_id):
        obj_type = 'adjustment-inventory'

        adjustment = self._storage.get(entity_id)

        if adjustment:
            obj = clean(adjustment)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity("Adjustment")

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("adjustments", obj)  # publish notification
        else:
            raise NoSuchEntity("Adjustment")

    def process_adjustments_queue(self, obj):
        print(obj)

        supplier_id = obj["supplier_id"]
        entity_id = obj['entity_id']
        adjustment_date = maya.to_iso8601(datetime.utcfromtimestamp(obj['adjustment_date'])).split("T")[0]

        # Select all records with matching entity_id
        table = "adjustments"
        query = """SELECT brand_id, package_type_id, adjustment_date
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
            "adjustment_date"
        ]

        record_ids = {}
        for result in results:
            record = {}
            for i, val in enumerate(result):
                record[keys[i]] = val
            record_ids[record['brand_id'] + '_' + record['package_type_id']] = record

        # delete all by entity_id from table
        table = "adjustments"
        query = """
                DELETE
                FROM `{TABLE}`
                WHERE entity_id='{ENTITY_ID}' AND supplier_id='{SUPPLIER_ID}'
                """.format(TABLE=table,
                           ENTITY_ID=entity_id,
                           SUPPLIER_ID=supplier_id)
        resp = self._aurora_storage._execute(query)

        if obj['active']:  # put or post
            brand_id = obj['brand_id']
            package_type_id = obj['package_type_id']
            quantity = obj['quantity']

            item = {
                "brand_id": brand_id,
                "entity_id": entity_id,
                "package_type_id": package_type_id,
                "supplier_id": supplier_id,
                "adjustment_date": adjustment_date,
                "quantity": quantity,
            }

            _id = item['brand_id'] + '_' + item['package_type_id']

            if _id not in record_ids or obj['adjustment_date'] < maya.parse(record_ids[_id]["adjustment_date"]).epoch:
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
                'start_date': item['adjustment_date'],
            })  # enqueue object
