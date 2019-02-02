from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import container_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import ContainerRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoContainerRepository(ContainerRepository, SnsNotifier):
    def get_all_containers(self, supplier):
        obj_type = 'containers'

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

        containers_obj = []

        for item in response_items:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # container = self._storage.get(table, entity_id)
            # container = clean(container)
            container = json_util.loads(clean(item))
            containers_obj.append(container)

        return containers_obj

    def save_container(self, obj):
        obj_type = 'containers'

        check_for_required_keys(obj, container_attributes)

        # check if content datatype is right
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, container_attributes)

        obj['user_id'] = self._user_id

        container_obj = self._storage.save(obj_type, obj)
        self.sns_publish("containers", obj)  # publish notification

        container = clean(container_obj)

        return container

    def get_container_by_id(self, supplier_id, entity_id):
        container = self._storage.get(entity_id)
        if container:
            container = clean(container)

            if container["supplier_id"] != supplier_id:
                raise NoSuchEntity
        else:
            raise NoSuchEntity

        return container

    def delete_container_by_id(self, supplier_id, entity_id):
        obj_type = 'containers'

        container = self._storage.get(entity_id)

        if container:
            obj = clean(container)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("containers", obj)  # publish notification
        else:
            raise NoSuchEntity
