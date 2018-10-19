import boto3
from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util
import base64
import binascii
import os

from data_common.constants import brand_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity, \
    CannotModifyEntityStates, UnsupportedMediaType
from data_common.repository import BrandRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoBrandsRepository(BrandRepository, SnsNotifier):
    @staticmethod
    def base64_to_png(image_string):
        logo_filepath = "/tmp/logo.png"

        # starts with 'data:image/png;base64,'
        image_string = image_string.split("data:image/png;base64,")[-1]

        try:
            with open(logo_filepath, "wb") as fp:
                image_data = image_string.encode('utf-8')

                # fix incorrect padding issue (binascii.Error: Incorrect padding)
                missing_padding = len(image_data) % 4
                if missing_padding:
                    image_data += b'=' * (4 - missing_padding)

                fp.write(base64.decodebytes(image_data))
        except binascii.Error:
            raise UnsupportedMediaType

        return logo_filepath

    def get_all_brands(self, supplier):
        obj_type = 'brands'

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

        brands_obj = []

        for item in response_items:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # brand_resp = self._storage.get(table, entity_id)
            # brand = adjustment_resp['Items'][0]
            # brand = clean(brand)
            brand = json_util.loads(clean(item))

            brands_obj.append(brand)

        return brands_obj

    def save_brand(self, obj):
        obj_type = 'brands'

        check_for_required_keys(obj, brand_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, brand_attributes)

        obj['user_id'] = self._user_id

        # check if brand with same name already exists
        query = {
            'KeyConditionExpression': Key('name').eq(obj['name']) & Key('obj_type').eq(obj_type),
            'FilterExpression':
                Attr('latest').eq(True) & Attr('active').eq(True) & Attr('supplier_id').eq(obj['supplier_id']),
            'IndexName': 'by_name_and_obj_type'
        }

        # only gets partition keys
        response = self._storage.get_items(query)

        if response["Count"] > 0:
            if 'entity_id' in obj:
                # filter the current obj from the list. The list always returns the current obj in this case
                if len([item for item in response['Items'] if item['entity_id'] != obj['entity_id']]) > 0:
                    raise CannotModifyEntityStates
            else:
                raise CannotModifyEntityStates

        # upload logo png to s3 bucket
        image_string = None
        if "logo" in obj:
            image_string = obj.pop("logo")

        brand_obj = self._storage.save(obj_type, obj)
        self.sns_publish("brands", obj)  # publish notification

        brand = clean(brand_obj)

        if image_string:
            logo_filepath = self.base64_to_png(image_string)

            if 'S3_ENDPOINT' in os.environ:
                s3 = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT'])
            else:
                s3 = boto3.client('s3')

            bucket_name = os.environ['S3_UPLOADS_BUCKET_NAME']

            s3_filepath = "{SUPPLIER_ID}/brands/{BRAND_ID}/logo.png".format(SUPPLIER_ID=obj["supplier_id"],
                                                                            BRAND_ID=brand_obj["entity_id"])
            s3.upload_file(logo_filepath, bucket_name, s3_filepath)

        return brand

    def get_brand_by_id(self, supplier_id, entity_id):
        brand = self._storage.get(entity_id)

        if brand:
            brand = clean(brand)

            if brand["supplier_id"] != supplier_id:
                raise NoSuchEntity
        else:
            raise NoSuchEntity

        return brand

    def delete_brand_by_id(self, supplier_id, entity_id):
        obj_type = 'brands'

        brand = self._storage.get(entity_id)

        if brand:
            obj = clean(brand)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("brands", obj)  # publish notification
        else:
            raise NoSuchEntity
