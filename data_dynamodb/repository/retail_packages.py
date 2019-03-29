from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import retail_package_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity, CannotModifyEntityStates
from data_common.repository import RetailPackageRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoRetailPackageRepository(RetailPackageRepository, SnsNotifier):
    def get_all_retail_packages(self, supplier):
        obj_type = 'retail-packages'

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

        retail_packages_obj = []

        for item in response_items:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # retail_package = self._storage.get(table, entity_id)
            # retail_package = clean(retail_package)
            retail_package = json_util.loads(clean(item))
            retail_packages_obj.append(retail_package)

        return retail_packages_obj

    def save_retail_package(self, obj):
        obj_type = 'retail-packages'

        check_for_required_keys(obj, retail_package_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, retail_package_attributes)

        obj['user_id'] = self._user_id

        retail_package_obj = self._storage.save(obj_type, obj)
        self.sns_publish("retail-packages", obj)  # publish notification

        retail_package = clean(retail_package_obj)

        return retail_package

    def get_retail_package_by_id(self, supplier_id, entity_id):
        retail_package = self._storage.get(entity_id)
        if retail_package:
            retail_package = clean(retail_package)

            if retail_package["supplier_id"] != supplier_id:
                raise NoSuchEntity
        else:
            raise NoSuchEntity

        return retail_package

    def delete_retail_package_by_id(self, supplier_id, entity_id):
        obj_type = 'retail-packages'

        retail_package = self._storage.get(entity_id)

        if retail_package:
            obj = clean(retail_package)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("retail-packages", obj)  # publish notification
        else:
            raise NoSuchEntity
