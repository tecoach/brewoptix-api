from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import supplier_distributors_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import SupplierDistributorsRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoSupplierDistributorsRepository(SupplierDistributorsRepository, SnsNotifier):
    def get_all_supplier_distributors(self, supplier_id):
        obj_type = 'supplier-distributors'

        query = {
            'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
            'FilterExpression':
                (Attr('latest').eq(True) & Attr('active').eq(True)),
            'IndexName': 'by_supplier_id_and_obj_type'
        }

        response = self._storage.get_items(query)

        distributors_obj = []

        for item in response['Items']:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # distributor = self._storage.get(table, entity_id)
            # distributor = clean(distributor)
            distributor = json_util.loads(clean(item))
            distributors_obj.append(distributor)

        return distributors_obj

    def save_supplier_distributor(self, obj):
        obj_type = 'supplier-distributors'

        check_for_required_keys(obj, supplier_distributors_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, supplier_distributors_attributes)

        obj['user_id'] = self._user_id

        distributor_obj = self._storage.save(obj_type, obj)
        self.sns_publish("supplier-distributors", obj)  # publish notification

        distributor = clean(distributor_obj)

        return distributor

    def get_supplier_distributor_by_id(self, supplier_id, entity_id):
        distributor = self._storage.get(entity_id)
        if distributor:
            distributor = clean(distributor)

            if distributor["supplier_id"] != supplier_id:
                raise NoSuchEntity
        else:
            raise NoSuchEntity

        return distributor

    def delete_supplier_distributor_by_id(self, supplier_id, entity_id):
        obj_type = 'supplier-distributors'

        distributor = self._storage.get(entity_id)

        if distributor:
            obj = clean(distributor)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("supplier-distributors", obj)  # publish notification
        else:
            raise NoSuchEntity

    def get_supplier_distributor_by_access_code(self, access_code):
        obj_type = 'supplier-distributors'

        query = {
            'KeyConditionExpression': Key('access_code').eq(access_code) & Key('obj_type').eq(obj_type),
            'FilterExpression':
                (Attr('latest').eq(True) & Attr('active').eq(True)),
            'IndexName': 'by_access_code_and_obj_type'
        }

        response = self._storage.get_items(query)

        if len(response['Items']) > 0:
            item = response['Items'][0]
            distributor = json_util.loads(clean(item))
        else:
            raise NoSuchEntity

        return distributor
