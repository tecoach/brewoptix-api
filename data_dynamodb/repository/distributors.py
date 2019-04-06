from datetime import datetime
import os
import requests

from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_dynamodb.utils import generate_random_password
from data_common.constants import distributors_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity, \
    MissingRequiredKey, Auth0UnableToAccess, \
    Auth0UnknownError, NotAnAdminUser, CannotUpdateUsers
from data_common.repository import DistributorsRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean, generate_affiliate_id
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoDistributorsRepository(DistributorsRepository, SnsNotifier):
    def add_distributor_to_app_metadata(self, distributor_id, role, valid=True, user_id=None):
        # get Auth0 user profile object (in order to get app_metadata)
        if user_id:
            app_metadata = self._auth0.get_app_metadata(user_id)
        else:
            app_metadata = self._auth0.get_app_metadata()

        if "distributors" not in app_metadata:
            app_metadata["distributors"] = {}

        app_metadata["distributors"][distributor_id] = {
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

    def remove_distributor_from_app_metadata(self, distributor_id, user_id=None):
        # get Auth0 user profile object (in order to get app_metadata)
        if user_id:
            app_metadata = self._auth0.get_app_metadata(user_id)
        else:
            app_metadata = self._auth0.get_app_metadata()

        if "distributors" not in app_metadata:
            return

        app_metadata["distributors"].pop(distributor_id, None)

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

    def is_current_user_distributor_admin(self, distributor_id):
        app_metadata = self._auth0.get_app_metadata()

        if "distributors" not in app_metadata or distributor_id not in app_metadata["distributors"]:
            return False

        if app_metadata["distributors"][distributor_id]["role"] == "admin":
            return True

        return False

    def get_all_distributors(self, distributors):
        obj_type = 'distributors'

        distributor_ids = distributors.keys()

        distributors_obj = []
        for distributor_id in distributor_ids:
            distributor = self._storage.get(distributor_id)
            if distributor:
                distributor = clean(distributor)

                distributors_obj.append(distributor)

        return distributors_obj

    def save_distributor(self, obj):
        obj_type = 'distributors'

        check_for_required_keys(obj, distributors_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, distributors_attributes)

        is_new_distributor = True

        if 'entity_id' in obj:
            existing_distributor = self._storage.get(obj['entity_id'])
            if existing_distributor:
                is_new_distributor = False
                existing_distributor = clean(existing_distributor)

        if not is_new_distributor and not self.is_current_user_distributor_admin(obj['entity_id']):
            raise NotAnAdminUser

        # cannot update users field through this endpoint
        if is_new_distributor:
            if "users" in obj and obj["users"]:
                raise CannotUpdateUsers
        else:
            if "users" in obj:
                # cannot change users from this endpoint
                old_users = {}
                new_users = {}
                for user in existing_distributor['users']:
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

        if is_new_distributor:
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
            obj["users"] = existing_distributor['users']

        obj['user_id'] = self._user_id

        distributor_obj = self._storage.save(obj_type, obj)
        self.sns_publish("distributors", obj)  # publish notification

        if is_new_distributor:
            # Add distributor_id to user, to denote that this user added/updated the distributor
            self.add_distributor_to_app_metadata(distributor_id=obj['entity_id'],
                                                 role="admin",
                                                 valid=True)

        distributor = clean(distributor_obj)

        return distributor

    def get_distributor_by_id(self, entity_id):
        distributor = self._storage.get(entity_id)
        if distributor:
            distributor = clean(distributor)
        else:
            raise NoSuchEntity

        return distributor

    def delete_distributor_by_id(self, entity_id):
        obj_type = 'distributors'

        distributor = self._storage.get(entity_id)

        if distributor:
            obj = clean(distributor)

            if not self.is_current_user_distributor_admin(obj['entity_id']):
                raise NotAnAdminUser

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("distributors", obj)  # publish notification
        else:
            raise NoSuchEntity("distributor")

    def upsert_user_in_distributor(self, distributor_id, obj):
        """
        Add or update a new or existing user in a distributor object
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

        # get distributor obj
        distributor = self._storage.get(distributor_id)
        if distributor:
            distributor = clean(distributor)
        else:
            raise NoSuchEntity

        if not self.is_current_user_distributor_admin(distributor_id):
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

        # if exists get user_id and add to distributor data
        if users_resp['Count'] > 0:
            user = users_resp['Items'][0]
            user_obj = json_util.loads(clean(user))
            user_id = user_obj["entity_id"]
            user_is_new = False
        else:
            # create user (in auth0 using management API)
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

            user_obj = self._storage.save("users", user_obj)
            self.sns_publish("users", user_obj)  # publish notification

        # save distributor obj
        if "users" not in distributor:
            distributor["users"] = []

        user_info_obj = {
            "user_id": user_id,
            "name": obj["name"],
            "role": obj["role"],
            "email": obj["email"]
        }

        user_exists = False
        existing_user_index = 0
        for i, user in enumerate(distributor["users"]):
            if user["user_id"] == user_id:
                # user already there in distributors
                user_exists = True
                existing_user_index = i
                break

        if user_exists:
            distributor["users"][existing_user_index] = user_info_obj
        else:
            distributor["users"].append(user_info_obj)

        distributor_obj = self._storage.save("distributors", distributor)
        self.sns_publish("distributors", distributor)  # publish notification

        self.add_distributor_to_app_metadata(distributor_id, obj["role"], user_id=user_id)

        if user_is_new:
            self._auth0.trigger_password_reset(obj["email"])

        return user_info_obj

    def delete_user_in_distributor(self, distributor_id, retiring_user_id):
        # get distributor obj
        distributor = self._storage.get(distributor_id)
        if distributor:
            distributor = clean(distributor)
        else:
            raise NoSuchEntity("distributor")

        if not self.is_current_user_distributor_admin(distributor_id):
            raise NotAnAdminUser

        if not any(retiring_user_id == user["user_id"] for user in distributor["users"]):
            raise NoSuchEntity("User Not Associated with distributor")

        distributor["users"] = [user for user in distributor.get("users", []) if user["user_id"] != retiring_user_id]

        distributor_obj = self._storage.save("distributors", distributor)
        self.sns_publish("distributors", distributor)  # publish notification

        self.remove_distributor_from_app_metadata(distributor_id, user_id=retiring_user_id)

        return True

    def get_all_users_in_distributor(self, distributor_id):
        if not self.is_current_user_distributor_admin(distributor_id):
            raise NotAnAdminUser

        # get distributor obj
        distributor = self._storage.get(distributor_id)
        if distributor:
            distributor = clean(distributor)
        else:
            raise NoSuchEntity("distributor")

        users = []
        if "users" in distributor:
            for user in distributor["users"]:
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
