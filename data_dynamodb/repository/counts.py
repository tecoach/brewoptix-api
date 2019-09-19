from datetime import datetime

import maya
from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import count_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import CountRepository
from data_common.queue import SQSManager
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoCountRepository(CountRepository, SQSManager, SnsNotifier):
    def get_all_counts(self, supplier_id):
        obj_type = 'counts'

        query = {
            'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
            'FilterExpression':
                (Attr('latest').eq(True) & Attr('active').eq(True)),
            'IndexName': 'by_supplier_id_and_obj_type'
        }

        response = self._storage.get_items(query)

        counts_obj = []

        for item in response['Items']:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # count = self._storage.get(table, entity_id)
            # count = clean(count)
            count = json_util.loads(clean(item))
            count['count_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    count['count_date']
                )
            ).split('T')[0]
            counts_obj.append(count)

        return counts_obj

    def get_count_by_count_date_range(self, supplier_id, min_count_date, max_count_date=None):
        obj_type = 'counts'

        min_count_date = maya.parse(min_count_date.split('T')[0]).epoch

        print(min_count_date)

        if max_count_date:
            max_count_date = maya.parse(max_count_date.split('T')[0]).epoch
            print (max_count_date)

        if max_count_date:
            query = {
                'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                'FilterExpression':
                    Attr('latest').eq(True) & Attr('active').eq(True) & Attr('count_date').between(
                    min_count_date,
                    max_count_date),
                'IndexName': 'by_supplier_id_and_obj_type'
            }
        else:
            query = {
                'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                'FilterExpression':
                    Attr('latest').eq(True) & Attr('active').eq(True) & Attr('count_date').gt(
                    min_count_date),
                'IndexName': 'by_supplier_id_and_obj_type'
            }

        response = self._storage.get_items(query)

        counts_obj = []

        for item in response['Items']:
            count = json_util.loads(clean(item))
            count['count_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    count['count_date']
                )
            ).split('T')[0]
            counts_obj.append(count)

        return counts_obj

    def save_count(self, obj):
        obj_type = 'counts'

        check_for_required_keys(obj, count_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, count_attributes)

        obj['user_id'] = self._user_id

        # convert observation_month to epoch integer
        obj['count_date'] = maya.parse(
            obj['count_date']).epoch

        count_obj = self._storage.save(obj_type, obj)
        self.sns_publish("counts", obj)  # publish notification

        count = clean(count_obj)

        count['count_date'] = datetime.utcfromtimestamp(
            count['count_date']
        ).isoformat().split('T')[0]

        return count

    def get_count_by_id(self, supplier_id, entity_id):
        count = self._storage.get(entity_id)
        if count:
            count = clean(count)

            if count["supplier_id"] != supplier_id:
                raise NoSuchEntity("Count")

            count['count_date'] = datetime.utcfromtimestamp(
                count['count_date']
            ).isoformat().split('T')[0]
        else:
            raise NoSuchEntity("Count")

        return count

    def delete_count_by_id(self, supplier_id, entity_id):
        obj_type = 'counts'

        count = self._storage.get(entity_id)

        if count:
            obj = clean(count)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity("Count")

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("counts", obj)  # publish notification
        else:
            raise NoSuchEntity("Count")

    def process_counts_queue(self, obj):
        products = obj["products"]
        products_agg = {}
        supplier_id = obj["supplier_id"]

        for product in products:
            package_type_id = product['package_type_id']

            if product["unit_quantity"] is not None:
                quantity = int(product["unit_quantity"])
            else:
                quantity = 0

            if product["pallet_quantity"] is not None and product["units_per_pallet"] is not None:
                quantity += int(product["pallet_quantity"]) * int(product["units_per_pallet"])

            brand_id = product["brand_id"]
            created_on = maya.to_iso8601(datetime.utcfromtimestamp(obj['count_date'])).split("T")[0]

            unique_id = brand_id + '_' + package_type_id

            if unique_id in products_agg.keys():
                products_agg[unique_id]["quantity"] += quantity
            else:
                products_agg[unique_id] = {
                    "supplier_id": supplier_id,
                    "brand_id": brand_id,
                    "package_type_id": package_type_id,
                    "quantity": quantity,
                    "actual": True,
                    "created_on": created_on
                }

            # delete all records with matching brand_id, package_type_id, created_on, actual=true
            table = 'on_hand'
            query = """
                    DELETE
                    FROM {TABLE}
                    WHERE brand_id='{BRAND_ID}' AND package_type_id='{PACK_ID}' AND created_on='{CREATED_ON}' AND actual=true""".format(TABLE=table,
                               BRAND_ID=brand_id,
                               PACK_ID=package_type_id,
                               CREATED_ON=created_on)
            self._aurora_storage._execute(query)

        # aggregate by package_type_id
        for item in products_agg.values():
            if obj["active"] and "status" and obj["status"] == "complete":  # we are recording only for this status
                self._aurora_storage.save('on_hand', item)

            # Re-calculate projections
            created_on_minus_one = maya.parse(item['created_on']).add(days=-1).iso8601().split("T")[0]
            self.sqs_enqueue("projections", {
                'user_id': self._user_id,
                'supplier_id': supplier_id,
                'brand_id': item['brand_id'],
                'package_type_id': item['package_type_id'],
                'start_date': created_on_minus_one,
            })  # enqueue object

