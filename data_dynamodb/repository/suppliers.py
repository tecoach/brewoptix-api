import os
import requests
import base64
import binascii
import boto3

from boto3.dynamodb.conditions import Key, Attr

from data_dynamodb.utils import generate_random_password
from data_common.constants import supplier_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity, \
    MissingRequiredKey, UnknownMainContact, Auth0UnableToAccess, \
    Auth0UnknownError, NotAnAdminUser, CannotUpdateUsers, UnsupportedMediaType
from data_common.repository import SupplierRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean, generate_affiliate_id
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoSuppliersRepository(SupplierRepository, SnsNotifier):
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

    def add_supplier_to_app_metadata(self, supplier_id, role, valid=True, user_id=None):
        # get Auth0 user profile object (in order to get app_metadata)
        if user_id:
            app_metadata = self._auth0.get_app_metadata(user_id)
        else:
            app_metadata = self._auth0.get_app_metadata()

        if "suppliers" not in app_metadata:
            app_metadata["suppliers"] = {}

        app_metadata["suppliers"][supplier_id] = {
            "role": role,
            "valid": valid
        }

        if user_id:
            self._auth0.update_app_metadata(app_metadata, user_id)
        else:
            self._auth0.update_app_metadata(app_metadata)

        # Update user table item with app_metadata
        obj_type = 'users'

        # get user profile
        if user_id:
            user_obj = self._storage.get_by_user_id(user_id)
        else:
            user_obj = self._storage.get_by_user_id(self._user_id)

        if not user_obj:
            raise NoSuchEntity

        user_obj = clean(user_obj)

        # update app_metadata
        user_obj["app_metadata"] = app_metadata
        user_obj = self._storage.save(obj_type, user_obj)
        self.sns_publish("users", user_obj)  # publish notification

        if "app_metadata" in user_obj:
            return True
        return False

    def remove_supplier_from_app_metadata(self, supplier_id, user_id=None):
        # get Auth0 user profile object (in order to get app_metadata)
        if user_id:
            app_metadata = self._auth0.get_app_metadata(user_id)
        else:
            app_metadata = self._auth0.get_app_metadata()

        if "suppliers" not in app_metadata:
            return

        app_metadata["suppliers"].pop(supplier_id, None)

        if user_id:
            self._auth0.update_app_metadata(app_metadata, user_id)
        else:
            self._auth0.update_app_metadata(app_metadata)

        # Update user table item with app_metadata
        obj_type = 'users'

        # get user profile
        if user_id:
            user_obj = self._storage.get_by_user_id(user_id)
        else:
            user_obj = self._storage.get_by_user_id(self._user_id)

        if not user_obj:
            raise NoSuchEntity

        user_obj = clean(user_obj)

        # update app_metadata
        user_obj["app_metadata"] = app_metadata
        user_obj = self._storage.save(obj_type, user_obj)
        self.sns_publish("users", user_obj)  # publish notification

        if "app_metadata" in user_obj:
            return True
        return False

    def is_current_user_admin(self, supplier_id):
        app_metadata = self._auth0.get_app_metadata()

        if "suppliers" not in app_metadata or supplier_id not in app_metadata["suppliers"]:
            return False

        if app_metadata["suppliers"][supplier_id]["role"] == "admin":
            return True

        return False

    def get_all_suppliers(self, suppliers):
        supplier_ids = suppliers.keys()

        suppliers_obj = []
        for supplier_id in supplier_ids:
            supplier = self._storage.get(supplier_id)
            if supplier:
                supplier = clean(supplier)

                suppliers_obj.append(supplier)

        return suppliers_obj

    def save_supplier(self, obj):
        obj_type = 'suppliers'

        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, supplier_attributes)
        check_for_required_keys(obj, supplier_attributes, exclude=["main_contact_id"])

        is_new_supplier = True

        if 'entity_id' in obj:
            existing_supplier = self._storage.get(obj['entity_id'])
            if existing_supplier:
                is_new_supplier = False
                existing_supplier = clean(existing_supplier)

        if not is_new_supplier and not self.is_current_user_admin(obj['entity_id']):
            raise NotAnAdminUser

        if 'main_contact_id' not in obj:
            obj['main_contact_id'] = self._user_id

        if is_new_supplier:
            if "users" in obj and obj["users"]:
                raise CannotUpdateUsers
        else:
            if "users" in obj:
                # cannot change users from this endpoint
                old_users = {}
                new_users = {}
                for user in existing_supplier['users']:
                    old_users[user['user_id']] = user
                for user in obj['users']:
                    new_users[user['user_id']] = user

                if any(user_id not in old_users.keys() for user_id in new_users):
                    raise CannotUpdateUsers

                for user_id in new_users:
                    new_role = new_users[user_id]['role']
                    old_role = old_users[user_id]['role']
                    if new_role != old_role:
                        raise CannotUpdateUsers

        if is_new_supplier:
            # get user name
            user_obj = self._storage.get_by_user_id(self._user_id)
            if user_obj:
                user_obj = clean(user_obj)
                user_name = user_obj.get('firstname', '') + " " + user_obj.get('lastname', '')
                user_name = user_name.rstrip()
                if not user_name or user_name.startswith(" "):
                    user_name = self._email
            else:
                user_name = self._email

            obj["users"] = [
                {
                    "user_id": self._user_id,
                    "user_name": user_name,
                    "role": "admin"
                }
            ]
        else:
            obj["users"] = existing_supplier['users']

        obj['user_id'] = self._user_id

        # upload/replace logo png to s3 bucket
        image_string = None
        if "logo" in obj:
            image_string = obj.pop("logo")

        if "has_logo" not in obj:
            obj["has_logo"] = False

        supplier_obj = self._storage.save(obj_type, obj)
        self.sns_publish("suppliers", obj)  # publish notification

        if is_new_supplier:
            # Add supplier_id to user, to denote that this user added/updated the supplier
            self.add_supplier_to_app_metadata(supplier_id=obj['entity_id'],
                                              role="admin",
                                              valid=True)

        supplier = clean(supplier_obj)

        if image_string:
            logo_filepath = self.base64_to_png(image_string)

            if 'S3_ENDPOINT' in os.environ:
                s3 = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT'])
            else:
                s3 = boto3.client('s3')

            bucket_name = os.environ['S3_UPLOADS_BUCKET_NAME']

            s3_filepath = "{SUPPLIER_ID}/logo.png".format(SUPPLIER_ID=supplier["entity_id"])
            resp = s3.upload_file(logo_filepath, bucket_name, s3_filepath)

        return supplier

    def get_supplier_by_id(self, entity_id):
        supplier = self._storage.get(entity_id)
        if supplier:
            supplier = clean(supplier)
        else:
            raise NoSuchEntity

        return supplier

    def delete_supplier_by_id(self, entity_id):
        obj_type = 'suppliers'

        supplier = self._storage.get(entity_id)

        if supplier:
            obj = clean(supplier)

            if not self.is_current_user_admin(obj['entity_id']):
                raise NotAnAdminUser

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("suppliers", obj)  # publish notification
        else:
            raise NoSuchEntity

    def upsert_user_in_supplier(self, supplier_id, obj):
        """
        Add or update a new or existing user in a supplier object
        """
        # checks
        attributes = ["email", "name", "role"]
        for key in list(obj.keys()):
            if key not in attributes:
                del obj[key]

        for key, val in obj.items():
            if type(val) != str:    # all are strings
                raise BadParameters

        for key in attributes:
            if key not in obj:
                raise MissingRequiredKey(key)

        # get supplier obj
        supplier = self._storage.get(supplier_id)
        if supplier:
            supplier = clean(supplier)
        else:
            raise NoSuchEntity

        if not self.is_current_user_admin(supplier_id):
            raise NotAnAdminUser

        name = obj["name"]
        email = obj["email"]

        # get by user email
        query = {
            'KeyConditionExpression': Key('email').eq(email) & Key('obj_type').eq('users'),
            'FilterExpression':
                Attr('latest').eq(True) & Attr('active').eq(True),
            'IndexName': 'by_email_and_obj_type'
        }

        users_resp = self._storage.get_items(query)

        user_is_new = True

        # if exists get user_id and add to supplier data
        if users_resp['Count'] > 0:
            user = users_resp['Items'][0]
            user_obj = clean(user)
            user_id = user_obj["entity_id"]
            user_is_new = False
        else:
            # get Machine-to-machine access token
            resp = requests.post(
                os.environ['AUTH0_DOMAIN'] + '/oauth/token',
                json={
                    'grant_type': 'client_credentials',
                    'client_id': os.environ['AUTH0_MANAGEMENT_API_CLIENT_ID'],
                    'client_secret': os.environ['AUTH0_MANAGEMENT_API_CLIENT_SECRET'],
                    'audience': os.environ['AUTH0_AUDIENCE'],
                    'scope': 'create:users'
                },
                headers={
                    'content-type': "application/json"
                }

            )

            body = resp.json()

            if all(k in body for k in [
                'access_token',
                'scope',
                'expires_in',
                'token_type'
            ]):
                pass  # to the next section of code
            elif 'error_description' in body:
                raise Auth0UnknownError(body['error_description'])
            else:
                raise Auth0UnableToAccess

            access_token = body['access_token']

            resp = requests.post(
                os.environ['AUTH0_DOMAIN'] + "/api/v2/users",
                json={
                    'email': email,
                    'name': name,
                    'password': generate_random_password(),
                    'email_verified': True,
                    'blocked': False,
                    'connection': os.environ['AUTH0_CONNECTION'],
                },
                headers={
                    'Authorization': 'Bearer {TOKEN}'.format(TOKEN=access_token),
                    'content-type': "application/json"
                })

            body = resp.json()
            print(body)

            if 'statusCode' in body and body['statusCode'] != 201 and 'error' in body:
                raise Auth0UnknownError(body['message'])

            if all(k in body for k in [
                'user_id',
                'email'
            ]):
                user_id = body['user_id'][6:]

            # else create user (in auth0 using management API)
            for _ in range(1000):
                affiliate_id = generate_affiliate_id()

                query = {
                    'KeyConditionExpression':
                        Key('affiliate_id').eq(affiliate_id) & Key('obj_type').eq('users'),
                    'IndexName': 'by_affiliate_id_and_obj_type'
                }

                response = self._storage.get_items(query)

                if response['Count'] <= 0:
                    break

            name_parts = name.split(" ")
            if len(name_parts) >= 2:
                firstname = name_parts[0]
                lastname = name_parts[1]
            else:
                firstname = name_parts[0]
                lastname = ""

            user_obj = {
                'entity_id': user_id,
                'user_id': user_id,
                'firstname': firstname,
                'lastname': lastname,
                'email': email,
                'affiliate_id': affiliate_id
            }

            user_obj = self._storage.save('users', user_obj)
            self.sns_publish("users", user_obj)  # publish notification

        # save supplier obj
        if "users" not in supplier:
            supplier["users"] = []

        user_info_obj = {
            "user_id": user_id,
            "name": obj["name"],
            "role": obj["role"],
            "email": obj["email"]
        }

        user_exists = False
        existing_user_index = 0
        for i, user in enumerate(supplier["users"]):
            if user["user_id"] == user_id:
                # user already there in suppliers
                user_exists = True
                existing_user_index = i
                break

        if user_exists:
            supplier["users"][existing_user_index] = user_info_obj
        else:
            supplier["users"].append(user_info_obj)

        supplier_obj = self._storage.save('suppliers', supplier)
        self.sns_publish("suppliers", supplier)  # publish notification

        self.add_supplier_to_app_metadata(supplier_id, obj["role"], user_id=user_id)

        if user_is_new:
            self._auth0.trigger_password_reset(obj["email"])

        return user_info_obj

    def delete_user_in_supplier(self, supplier_id, retiring_user_id):
        # get supplier obj
        supplier = self._storage.get(supplier_id)
        if supplier:
            supplier = clean(supplier)
        else:
            raise NoSuchEntity("Supplier")

        if not self.is_current_user_admin(supplier_id):
            raise NotAnAdminUser

        if not any(retiring_user_id == user["user_id"] for user in supplier["users"]):
            raise NoSuchEntity("User Not Associated with Supplier")

        supplier["users"] = [user for user in supplier.get("users", []) if user["user_id"] != retiring_user_id]

        supplier_obj = self._storage.save("suppliers", supplier)
        self.sns_publish("suppliers", supplier)  # publish notification

        self.remove_supplier_from_app_metadata(supplier_id, user_id=retiring_user_id)

        return True

    def get_all_users_in_supplier(self, supplier_id):
        if not self.is_current_user_admin(supplier_id):
            raise NotAnAdminUser

        # get supplier obj
        supplier = self._storage.get(supplier_id)
        if supplier:
            supplier = clean(supplier)
        else:
            raise NoSuchEntity("Supplier")

        users = []
        if "users" in supplier:
            for user in supplier["users"]:
                user_id = user["user_id"]
                # get email id
                user_obj = self._storage.get_by_user_id(user_id)

                if not user_obj:
                    raise NoSuchEntity

                user_obj = clean(user_obj)

                users.append(
                    {
                        "email": user_obj["email"],
                        "name": user.get("user_name", None) or user["name"],
                        "role": user["role"],
                        "user_id": user_id
                    }
                )

        return users