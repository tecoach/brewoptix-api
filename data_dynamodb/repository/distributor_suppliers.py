from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import distributor_suppliers_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import DistributorSuppliersRepository
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoDistributorSuppliersRepository(DistributorSuppliersRepository):
    def get_all_distributor_suppliers(self, distributor_id):
        obj_type = 'distributor-suppliers'

        query = {
            'KeyConditionExpression': Key('distributor_id').eq(distributor_id) & Key('obj_type').eq(obj_type),
            'FilterExpression':
                (Attr('latest').eq(True) & Attr('active').eq(True)),
            'IndexName': 'by_distributor_id_and_obj_type'
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

    def save_distributor_supplier(self, obj):
        obj_type = 'distributor-suppliers'

        check_for_required_keys(obj, distributor_suppliers_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, distributor_suppliers_attributes)

        obj['user_id'] = self._user_id

        distributor_obj = self._storage.save(obj_type, obj)

        distributor = clean(distributor_obj)

        return distributor

    def get_distributor_supplier_by_id(self, distributor_id, entity_id):
        obj_type = 'distributor-suppliers'

        distributor = self._storage.get(entity_id)
        if distributor:
            distributor = clean(distributor)

            if distributor["distributor_id"] != distributor_id:
                raise NoSuchEntity
        else:
            raise NoSuchEntity

        return distributor

    def get_distributor_supplier_by_supplier_distributor_id(self, supplier_distributor_id):
        obj_type = 'distributor-suppliers'
        filter_expression = Attr('supplier_distributor_id').eq(supplier_distributor_id) & Attr('obj_type').eq(obj_type)
        response = self._storage.get_filtered_items(filter_expression)
        items = response['Items']
        if len(items) > 0:
            distributor = clean(items[0])
        else:
            # It is valid to have a supplier_distributor_id with no corresponding distributor_supplier so we
            # return None instead of throwing an exception
            return None

        return distributor

    def delete_distributor_supplier_by_id(self, distributor_id, entity_id):
        obj_type = 'distributor-suppliers'

        distributor = self._storage.get(entity_id)

        if distributor:
            obj = clean(distributor)

            if obj["distributor_id"] != distributor_id:
                raise NoSuchEntity

            obj["active"] = False
            self._storage.save(obj_type, obj)
        else:
            raise NoSuchEntity

    def delete_distributor_supplier_by_access_code(self, supplier_id, access_code):
        obj_type = 'distributor-suppliers'

        query = {
            'KeyConditionExpression': Key('access_code').eq(access_code) & Key('obj_type').eq(obj_type),
            'FilterExpression':
                (Attr('latest').eq(True) & Attr('active').eq(True)),
            'IndexName': 'by_access_code_and_obj_type'
        }

        response = self._storage.get_items(query)

        print(response)
        if response["Count"] > 0:
            obj = response['Items'][0]
            obj = json_util.loads(obj)
        else:
            raise NoSuchEntity

        if obj:
            cleaned_obj = clean(obj)

            if cleaned_obj["supplier_id"] != supplier_id:
                raise NoSuchEntity

            cleaned_obj["active"] = False
            self._storage.save(obj_type, cleaned_obj)
        else:
            raise NoSuchEntity
