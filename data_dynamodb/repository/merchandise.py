from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
from dynamodb_json import json_util

from data_common.constants import merchandise_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import MerchandiseRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoMerchandiseRepository(MerchandiseRepository, SnsNotifier):
    def get_all_merchandises(self, supplier):
        obj_type = 'merchandise'

        if isinstance(supplier, list):
            response_items = []
            for item in supplier:
                query = {
                    'KeyConditionExpression': Key('supplier_id').eq(item) & Key('obj_type').eq(obj_type),
                    'FilterExpression':
                        (Attr('latest').eq(True) & Attr('active').eq(True)),
                    'IndexName': 'by_supplier_id_and_obj_type'
                }
                response = self._storage.get_items(query)
                response_items.extend(response['Items'])

        else:
            query = {
                'KeyConditionExpression': Key('supplier_id').eq(supplier) & Key('obj_type').eq(obj_type),
                'FilterExpression':
                    (Attr('latest').eq(True) & Attr('active').eq(True)),
                'IndexName': 'by_supplier_id_and_obj_type'
            }
            response = self._storage.get_items(query)
            response_items = response['Items']

        merchandises_obj = []

        for item in response_items:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # merchandise = self._storage.get(table, entity_id)
            # merchandise = clean(merchandise)
            merchandise = json_util.loads(clean(item))
            merchandises_obj.append(merchandise)

        return merchandises_obj

    def save_merchandise(self, obj):
        obj_type = 'merchandise'

        check_for_required_keys(obj, merchandise_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, merchandise_attributes)

        obj['user_id'] = self._user_id

        merchandise_obj = self._storage.save(obj_type, obj)

        self.sns_publish("merchandise", obj)  # publish notification

        merchandise = clean(merchandise_obj)

        return merchandise

    def get_merchandise_by_id(self, supplier_id, entity_id):
        merchandise = self._storage.get(entity_id)
        if merchandise:
            merchandise = clean(merchandise)

            if merchandise["supplier_id"] != supplier_id:
                raise NoSuchEntity
        else:
            raise NoSuchEntity

        return merchandise

    def delete_merchandise_by_id(self, supplier_id, entity_id):
        obj_type = 'merchandise'

        merchandise = self._storage.get(entity_id)

        if merchandise:
            obj = clean(merchandise)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity

            # dynamodb data_adapter cannot process float type inside nested dict
            # type casting to help data_adapter
            sizes = []
            if "sizes" in obj:
                for item in obj["sizes"]:
                    if "price" in item and isinstance(item["price"], float):
                        item["price"] = Decimal('{val:.3f}'.format(val=item["price"]))
                    sizes.append(item)
                obj["sizes"] = sizes

            obj["active"] = False
            self._storage.save(obj_type, obj)
            # type-casting decimal to float for dicts in list
            sizes = []
            if "sizes" in obj:
                for item in obj["sizes"]:
                    if "price" in item and isinstance(item["price"], Decimal):
                        item["price"] = float(item["price"])
                    sizes.append(item)
                obj["sizes"] = sizes
            self.sns_publish("merchandise", obj)  # publish notification
        else:
            raise NoSuchEntity
