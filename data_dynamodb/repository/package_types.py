from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import package_type_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import PackageTypeRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoPackageTypeRepository(PackageTypeRepository, SnsNotifier):
    def get_all_package_types(self, supplier):
        obj_type = 'package-types'

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

        package_types_obj = []

        for item in response_items:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # package_type = self._storage.get(table, entity_id)
            # package_type = clean(package_type)
            package_type = json_util.loads(clean(item))
            package_types_obj.append(package_type)

        # sort by ordinal
        # To keep things backward compatible the sorting is handled the way below
        # TODO: remove this backward comaptible logic in future
        package_types_obj = sorted([item for item in package_types_obj if "ordinal" in item],
                                   key=lambda item: item["ordinal"]) + \
                            [item for item in package_types_obj if "ordinal" not in item]

        return package_types_obj

    def save_package_type(self, obj):
        obj_type = 'package-types'

        check_for_required_keys(obj, package_type_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, package_type_attributes)

        obj['user_id'] = self._user_id

        package_type_obj = self._storage.save(obj_type, obj)
        self.sns_publish("package-types", obj)  # publish notification

        package_type = clean(package_type_obj)

        return package_type

    def get_package_type_by_id(self, supplier_id, entity_id):
        package_type = self._storage.get(entity_id)
        if package_type:
            package_type = clean(package_type)

            if package_type["supplier_id"] != supplier_id:
                raise NoSuchEntity
        else:
            raise NoSuchEntity

        return package_type

    def delete_package_type_by_id(self, supplier_id, entity_id):
        obj_type = 'package-types'

        package_type = self._storage.get(entity_id)

        if package_type:
            obj = clean(package_type)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("package-types", obj)  # publish notification
        else:
            raise NoSuchEntity
