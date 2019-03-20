from datetime import datetime
import os
import maya
from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import purchase_order_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import PurchaseOrderRepository
from data_common.queue import SQSManager
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes

from botocore.exceptions import ClientError


class DynamoPurchaseOrderRepository(PurchaseOrderRepository, SQSManager, SnsNotifier):
    def _create_order_number(self, supplier_id):
        table = 'brewoptix-purchase-order-number'

        try:
            key = {'supplier_id': supplier_id}
            update_expr = 'SET current_order_number = current_order_number + :increment'
            expr_attr_values = {':increment': 1}
            response = self._storage.atomic_update(
                table=table,
                key=key,
                update_expression=update_expr,
                express_attr_values=expr_attr_values
            )
            order_number = str(int(response['Attributes']['current_order_number']) + 20000)
        except ClientError as ex:
            # If update item fails, its most likely because the supplier_id doesn't exist in the table
            # Create new entity with the supplier_id
            print(ex)
            try:
                # Create purchase order number entity in `brewoptix-purchase-order-number` table
                order_number_obj = {
                    'supplier_id': supplier_id,
                    'current_order_number': 1
                }

                self._storage.save_minimal('brewoptix-purchase-order-number', order_number_obj)
            except ClientError:
                raise ex

            order_number = str(20001)

        return order_number

    def get_purchase_orders_by_order_date_range(self, min_order_date, max_order_date=None,
                                                supplier_id=None, distributors=[]):
        obj_type = 'purchase-orders'

        min_order_date = maya.parse(min_order_date.split('T')[0]).epoch

        if max_order_date:
            max_order_date = maya.parse(max_order_date.split('T')[0]).epoch

        if supplier_id:
            if max_order_date:
                query = {
                    'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                    'FilterExpression':
                        Attr('latest').eq(True) & Attr('active').eq(True) & Attr('order_date').between(
                        min_order_date,
                        max_order_date),
                    'IndexName': 'by_supplier_id_and_obj_type'
                }
            else:
                query = {
                    'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                    'FilterExpression':
                        Attr('latest').eq(True) & Attr('active').eq(True) & Attr('order_date').gt(
                        min_order_date),
                    'IndexName': 'by_supplier_id_and_obj_type'
                }
            response = self._storage.get_items(query)
            response_items = response['Items']
        else:
            response_items = []
            for distributor in distributors:
                if max_order_date:
                    query = {
                        'KeyConditionExpression': Key('distributor_id').eq(distributor) & Key('obj_type').eq(obj_type),
                        'FilterExpression':
                            Attr('latest').eq(True) & Attr('active').eq(True) & Attr('order_date').between(
                            min_order_date,
                            max_order_date),
                        'IndexName': 'by_distributor_id_and_obj_type'
                    }
                else:
                    query = {
                        'KeyConditionExpression': Key('distributor_id').eq(distributor) & Key('obj_type').eq(obj_type),
                        'FilterExpression':
                            Attr('latest').eq(True) & Attr('active').eq(True) & Attr('order_date').gt(
                            min_order_date),
                        'IndexName': 'by_distributor_id_and_obj_type'
                    }
                response = self._storage.get_items(query)
                response_items.extend(response['Items'])

        if supplier_id:
            print("supplier:{}".format(response_items))
        else:
            print("distributor:{}".format(response_items))

        purchase_orders_obj = []

        for item in response_items:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # purchase_order = self._storage.get(table, entity_id)
            # purchase_order = clean(purchase_order)
            purchase_order = json_util.loads(clean(item))
            purchase_order['order_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    purchase_order['order_date']
                )
            ).split('T')[0]
            if "pack_date" in purchase_order:
                purchase_order['pack_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['pack_date']
                    )
                ).split('T')[0]
            if "ship_date" in purchase_order:
                purchase_order['ship_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['ship_date']
                    )
                ).split('T')[0]
            purchase_orders_obj.append(purchase_order)

        return purchase_orders_obj

    def get_purchase_orders_by_pack_date_range(self, min_pack_date, max_pack_date=None,
                                               supplier_id=None, distributors=[]):
        obj_type = 'purchase-orders'

        min_pack_date = maya.parse(min_pack_date.split('T')[0]).epoch

        if max_pack_date:
            max_pack_date = maya.parse(max_pack_date.split('T')[0]).epoch

        if supplier_id:
            if max_pack_date:
                query = {
                    'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                    'FilterExpression':
                        Attr('latest').eq(True) & Attr('active').eq(True) & Key('pack_date').between(
                        min_pack_date,
                        max_pack_date),
                    'IndexName': 'by_supplier_id_and_obj_type'
                }
            else:
                query = {
                    'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                    'FilterExpression':
                        Attr('latest').eq(True) & Attr('active').eq(True) & Attr('pack_date').gt(
                        min_pack_date),
                    'IndexName': 'by_supplier_id_and_obj_type'
                }
            response = self._storage.get_items(query)
            response_items = response['Items']
        else:
            response_items = []
            for distributor in distributors:
                if max_pack_date:
                    query = {
                        'KeyConditionExpression': Key('distributor_id').eq(distributor) & Key('obj_type').eq(obj_type),
                        'FilterExpression':
                            Attr('latest').eq(True) & Attr('active').eq(True) & Key('pack_date').between(
                            min_pack_date,
                            max_pack_date),
                        'IndexName': 'by_distributor_id_and_obj_type'
                    }
                else:
                    query = {
                        'KeyConditionExpression': Key('distributor_id').eq(distributor) & Key('obj_type').eq(obj_type),
                        'FilterExpression':
                            Attr('latest').eq(True) & Attr('active').eq(True) & Attr('pack_date').gt(
                            min_pack_date),
                        'IndexName': 'by_distributor_id_and_obj_type'
                    }
                response = self._storage.get_items(query)
                response_items.extend(response['Items'])

        if supplier_id:
            print("supplier:{}".format(response_items))
        else:
            print("distributor:{}".format(response_items))

        purchase_orders_obj = []

        for item in response_items:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # purchase_order = self._storage.get(table, entity_id)
            # purchase_order = clean(purchase_order)
            purchase_order = json_util.loads(clean(item))
            purchase_order['order_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    purchase_order['order_date']
                )
            ).split('T')[0]
            if "pack_date" in purchase_order:
                purchase_order['pack_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['pack_date']
                    )
                ).split('T')[0]
            if "ship_date" in purchase_order:
                purchase_order['ship_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['ship_date']
                    )
                ).split('T')[0]
            purchase_orders_obj.append(purchase_order)

        return purchase_orders_obj

    def get_purchase_orders_by_ship_date_range(self, min_ship_date, max_ship_date=None,
                                               supplier_id=None, distributors=[]):
        obj_type = 'purchase-orders'

        min_ship_date = maya.parse(min_ship_date.split('T')[0]).epoch

        if max_ship_date:
            max_ship_date = maya.parse(max_ship_date.split('T')[0]).epoch

        if supplier_id:
            if max_ship_date:
                query = {
                    'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                    'FilterExpression':
                        Attr('latest').eq(True) & Attr('active').eq(True) & Attr('ship_date').between(
                        min_ship_date,
                        max_ship_date),
                    'IndexName': 'by_supplier_id_and_obj_type'
                }
            else:
                query = {
                    'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
                    'FilterExpression':
                        Attr('latest').eq(True) & Attr('active').eq(True) & Attr('ship_date').gt(
                        min_ship_date),
                    'IndexName': 'by_supplier_id_and_obj_type'
                }
            response = self._storage.get_items(query)
            response_items = response['Items']
        else:
            response_items = []
            for distributor in distributors:
                if max_ship_date:
                    query = {
                        'KeyConditionExpression': Key('distributor_id').eq(distributor) & Key('obj_type').eq(obj_type),
                        'FilterExpression':
                            Attr('latest').eq(True) & Attr('active').eq(True) & Attr('ship_date').between(
                            min_ship_date,
                            max_ship_date),
                        'IndexName': 'by_distributor_id_and_obj_type'
                    }
                else:
                    query = {
                        'KeyConditionExpression': Key('distributor_id').eq(distributor) & Key('obj_type').eq(obj_type),
                        'FilterExpression':
                            Attr('latest').eq(True) & Attr('active').eq(True) & Attr('ship_date').gt(
                            min_ship_date),
                        'IndexName': 'by_distributor_id_and_obj_type'
                    }
                response = self._storage.get_items(query)
                response_items.extend(response['Items'])

        if supplier_id:
            print("supplier:{}".format(response_items))
        else:
            print("distributor:{}".format(response_items))

        purchase_orders_obj = []

        for item in response_items:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # purchase_order = self._storage.get(table, entity_id)
            # purchase_order = clean(purchase_order)
            purchase_order = json_util.loads(clean(item))
            purchase_order['order_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    purchase_order['order_date']
                )
            ).split('T')[0]
            if "pack_date" in purchase_order:
                purchase_order['pack_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['pack_date']
                    )
                ).split('T')[0]
            if "ship_date" in purchase_order:
                purchase_order['ship_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['ship_date']
                    )
                ).split('T')[0]
            purchase_orders_obj.append(purchase_order)

        return purchase_orders_obj

    def save_purchase_order(self, obj):
        obj_type = 'purchase-orders'

        check_for_required_keys(obj, purchase_order_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, purchase_order_attributes)

        obj['user_id'] = self._user_id

        if 'order_number' not in obj or not obj['order_number']:
            current_order_number = self._create_order_number(obj['supplier_id'])
            obj['order_number'] = current_order_number

        obj['order_date'] = maya.parse(
            obj['order_date']).epoch
        if "pack_date" in obj:
            obj['pack_date'] = maya.parse(
                obj['pack_date']).epoch
        if "ship_date" in obj:
            obj['ship_date'] = maya.parse(
                obj['ship_date']).epoch

        purchase_order_obj = self._storage.save(obj_type, obj)
        self.sns_publish("purchase-orders", obj)  # publish notification

        purchase_order = clean(purchase_order_obj)

        purchase_order['order_date'] = datetime.utcfromtimestamp(
            purchase_order['order_date']
        ).isoformat().split('T')[0]
        if "pack_date" in purchase_order:
            purchase_order['pack_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    purchase_order['pack_date']
                )
            ).split('T')[0]
        if "ship_date" in purchase_order:
            purchase_order['ship_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    purchase_order['ship_date']
                )
            ).split('T')[0]
        return purchase_order

    def add_purchase_order(self, obj):
        obj_type = 'purchase-orders'

        check_for_required_keys(obj, purchase_order_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, purchase_order_attributes)

        obj['user_id'] = self._user_id

        if 'order_number' not in obj or not obj['order_number']:
            current_order_number = self._create_order_number(obj['supplier_id'])
            obj['order_number'] = current_order_number

        # convert observation_month to epoch integer
        obj['order_date'] = maya.parse(
            obj['order_date']).epoch
        if "pack_date" in obj:
            obj['pack_date'] = maya.parse(
                obj['pack_date']).epoch
        if "ship_date" in obj:
            obj['ship_date'] = maya.parse(
                obj['ship_date']).epoch

        purchase_order_obj = self._storage.save(obj_type, obj)
        self.sns_publish("purchase-orders", obj)  # publish notification

        purchase_order = clean(purchase_order_obj)

        purchase_order['order_date'] = datetime.utcfromtimestamp(
                purchase_order['order_date']
            ).isoformat().split('T')[0]
        if "pack_date" in purchase_order:
            purchase_order['pack_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    purchase_order['pack_date']
                )
            ).split('T')[0]
        if "ship_date" in purchase_order:
            purchase_order['ship_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    purchase_order['ship_date']
                )
            ).split('T')[0]
        return purchase_order

    def update_purchase_order(self, obj):
        obj_type = 'purchase-orders'

        check_for_required_keys(obj, purchase_order_attributes)

        # check if content datatype is right
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, purchase_order_attributes)

        if 'entity_id' not in obj:
            raise BadParameters

        obj['user_id'] = self._user_id

        purchase_order = self._storage.get(obj['entity_id'])

        if not purchase_order:
            raise NoSuchEntity("Purchase Order")

        obj['order_date'] = maya.parse(
                obj['order_date']).epoch
        if "pack_date" in obj:
            obj['pack_date'] = maya.parse(
                obj['pack_date']).epoch
        if "ship_date" in obj:
            obj['ship_date'] = maya.parse(
                obj['ship_date']).epoch

        purchase_order_obj = self._storage.save(obj_type, obj)
        self.sns_publish("purchase-orders", obj)  # publish notification

        purchase_order = clean(purchase_order_obj)
        purchase_order['order_date'] = datetime.utcfromtimestamp(
                purchase_order['order_date']
            ).isoformat().split('T')[0]
        if "pack_date" in purchase_order:
            purchase_order['pack_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    purchase_order['pack_date']
                )
            ).split('T')[0]
        if "ship_date" in purchase_order:
            purchase_order['ship_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    purchase_order['ship_date']
                )
            ).split('T')[0]
        return purchase_order

    def get_purchase_order_by_id(self, entity_id, supplier_id=None, distributors=[]):
        purchase_order = self._storage.get(entity_id)
        if purchase_order:
            purchase_order = clean(purchase_order)

            if supplier_id and purchase_order["supplier_id"] != supplier_id:
                raise NoSuchEntity("Purchase Order")

            if purchase_order["distributor_id"] in distributors:
                raise NoSuchEntity("Purchase Order")

            purchase_order['order_date'] = datetime.utcfromtimestamp(
                purchase_order['order_date']
            ).isoformat().split('T')[0]
            if "pack_date" in purchase_order:
                purchase_order['pack_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['pack_date']
                    )
                ).split('T')[0]
            if "ship_date" in purchase_order:
                purchase_order['ship_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['ship_date']
                    )
                ).split('T')[0]
        else:
            raise NoSuchEntity("Purchase Order")

        return purchase_order

    def delete_purchase_order_by_id(self, entity_id, supplier_id=None, distributors=[]):
        obj_type = 'purchase-orders'

        purchase_order = self._storage.get(entity_id)

        if purchase_order:
            obj = clean(purchase_order)

            if supplier_id and obj["supplier_id"] != supplier_id:
                raise NoSuchEntity("Purchase Order")

            if obj["distributor_id"] in distributors:
                raise NoSuchEntity("Purchase Order")

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("purchase-orders", obj)  # publish notification
        else:
            raise NoSuchEntity("Purchase Order")

    def get_purchase_order_by_version(self, entity_id, version):
        obj_type = 'brewoptix-purchase-orders'

        try:
            obj = self._storage.get_by_version(entity_id, version)
            purchase_order = obj['Items'][0]
            print('purchase order:{}'.format(purchase_order))

            purchase_order = clean(purchase_order)
            purchase_order['order_date'] = datetime.utcfromtimestamp(
                purchase_order['order_date']
            ).isoformat().split('T')[0]
            if "pack_date" in purchase_order:
                purchase_order['pack_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['pack_date']
                    )
                ).split('T')[0]
            if "ship_date" in purchase_order:
                purchase_order['ship_date'] = maya.to_iso8601(
                    datetime.utcfromtimestamp(
                        purchase_order['ship_date']
                    )
                ).split('T')[0]
        except ClientError:
            print("Object not found.")
            purchase_order = {}

        return purchase_order

    def process_purchase_orders_queue(self, obj):
        print(obj)

        entity_id = obj['entity_id']
        supplier_id = obj["supplier_id"]
        pack_date = maya.to_iso8601(datetime.utcfromtimestamp(obj['pack_date'])).split("T")[0]

        # Select all records with matching entity_id
        table = "sales"
        query = """SELECT brand_id, package_type_id, sale_date
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
            "sale_date"
        ]

        record_ids = {}
        print("Records gotten from Aurora sales")
        for result in results:
            record = {}
            for i, val in enumerate(result):
                record[keys[i]] = val
            record_ids[record['brand_id'] + '_' + record['package_type_id']] = record
            print(record)

        # delete all records with matching entity_id
        table = 'sales'
        query = """
                DELETE
                FROM {TABLE}
                WHERE supplier_id='{SUPPLIER_ID}' AND entity_id='{ENTITY_ID}'
                """.format(TABLE=table,
                           SUPPLIER_ID=supplier_id,
                           ENTITY_ID=entity_id)

        resp = self._aurora_storage._execute(query)

        # add new records or update old records
        if obj['active']:
            products = obj["products"]
            distributor_id = obj["distributor_id"]

            for product in products:
                brand_id = product['brand_id']
                for brand_product in product["brandProducts"]:
                    package_type_id = brand_product['package_type_id']
                    quantity = brand_product['quantity']

                    record = {
                        "brand_id": brand_id,
                        "distributor_id": distributor_id,
                        "package_type_id": package_type_id,
                        "supplier_id": supplier_id,
                        "entity_id": entity_id,
                        "sale_date": pack_date,
                        "quantity": quantity,
                    }

                    _id = record['brand_id'] + '_' + record['package_type_id']

                    if _id not in record_ids or obj['pack_date'] < maya.parse(record_ids[_id]["sale_date"]).epoch:
                        record_ids[_id] = record

                    self._aurora_storage.save("sales", record)

        # trigger projections calculation for old records + new inserts
        for item in record_ids.values():
            brand_id = item["brand_id"]
            package_type_id = item["package_type_id"]

            # Re-calculate projections
            self.sqs_enqueue("projections", {
                'user_id': self._user_id,
                "supplier_id": supplier_id,
                'brand_id': brand_id,
                'package_type_id': package_type_id,
                'start_date': pack_date,
            })  # enqueue object