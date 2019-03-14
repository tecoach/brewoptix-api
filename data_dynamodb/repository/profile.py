from boto3.dynamodb.conditions import Key, Attr

from data_common.exceptions import BadParameters, NoSuchEntity
from data_common.repository import ProfileRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean, generate_affiliate_id

import json


class DynamoProfileRepository(ProfileRepository, SnsNotifier):
    def get_or_create_profile(self):
        obj_type = 'users'

        user_obj = self._storage.get_by_user_id(self._user_id)
        if not user_obj:
            for _ in range(1000):
                affiliate_id = generate_affiliate_id()

                query = {
                    'KeyConditionExpression':
                        Key('affiliate_id').eq(affiliate_id) & Key('obj_type').eq('user'),
                    'IndexName': 'by_affiliate_id_and_obj_type'
                }

                response = self._storage.get_items(query)

                if response['Count'] <= 0:
                    break

            user_obj = {
                'entity_id': self._user_id,
                'user_id': self._user_id,
                'firstname': '',
                'lastname': '',
                'email': self._email,
                'affiliate_id': affiliate_id,
            }
            user_obj = self._storage.save(obj_type, user_obj)
            self.sns_publish("users", user_obj)  # publish notification

        user_obj = clean(user_obj)

        return user_obj

    def update_profile(self, obj):
        obj_type = 'users'

        # check if the entity_id in obj exists
        try:
            entity_id = obj["entity_id"]
            profile = self._storage.get(entity_id)
            if not profile:
                raise NoSuchEntity
        except KeyError:
            raise BadParameters

        if 'name' in obj:
            profile['name'] = obj['name']
        if 'picture' in obj:
            profile['picture'] = obj['picture']

        user_obj = self._storage.save(obj_type, profile)
        self.sns_publish("users", obj)  # publish notification

        user_obj = clean(user_obj)

        # check auth0/social, social profile can't update here
        if user_obj['entity_id'].find('|') < 0:
            name = ""
            if "name" in user_obj:
                name = user_obj["name"]
            else:
                if user_obj.get('firstname', False):
                    name += user_obj['firstname']

                if user_obj.get('lastname', False):
                    name += " " + user_obj['firstname']

                name = name.lstrip()

            if name:
                # update Auth0 Profile and update all suppliers of user with the name field in supplier["users"]
                auth0_profile = {"name": name}

                resp = self._auth0.update_profile(auth0_profile)
                if resp.status_code != 200:
                    error = resp.json()

                    msg = 'Unable to update Auth0 profile. Unknown error.'
                    if 'message' in error:
                        msg = error['message']

                    raise BadParameters(msg)

                # find suppliers list
                app_metadata = self.get_user_app_metadata()

                if "suppliers" in app_metadata:
                    suppliers = app_metadata["suppliers"]

                    for supplier_id in suppliers:
                        # get supplier obj
                        supplier = self._storage.get(supplier_id)
                        if supplier:
                            supplier = clean(supplier)

                            if "users" in supplier:
                                users = supplier["users"]

                                for i, user in enumerate(users):
                                    if user["user_id"] == self._user_id:
                                        break
                                else:
                                    i = None

                                if i is not None:
                                    supplier["users"][i]["name"] = name
                                    supplier_obj = self._storage.save("suppliers", supplier)
                                    self.sns_publish("suppliers", supplier)  # publish notification

                if "distributors" in app_metadata:
                    distributors = app_metadata["distributors"]

                    for distributor_id in distributors:
                        # get distributor obj
                        distributor = self._storage.get(distributor_id)
                        if distributor:
                            distributor = clean(distributor)

                            if "users" in distributor:
                                users = distributor["users"]

                                for i, user in enumerate(users):
                                    if user["user_id"] == self._user_id:
                                        break
                                else:
                                    i = None

                                if i is not None:
                                    distributor["users"][i]["name"] = name
                                    distributor_obj = self._storage.save("distributors", distributor)
                                    self.sns_publish("distributors", distributor)  # publish notification

            # update password if existing in request
            password = ""
            if "password" in user_obj:
                password = user_obj["password"]

                # update Auth0 Profile password
                auth0_profile = {"password": password}

                resp = self._auth0.update_profile(auth0_profile)

                # adding a flag, might help in UI changes like signing out a user upon password update
                if resp.status_code != 200:
                    error = resp.json()

                    msg = 'Unable to update Auth0 profile. Unknown error.'
                    if 'message' in error:
                        msg = error['message']

                    raise BadParameters(msg)
                else:
                    user_obj.pop('password')
                    user_obj['password_updated'] = True

        return user_obj

    def update_user_app_metadata(self, app_metadata):
        obj_type = 'users'

        # get user profile
        user_obj = self._storage.get_by_user_id(self._user_id)

        if not user_obj:
            raise NoSuchEntity

        user_obj = clean(user_obj)

        # check if an update is required
        if "app_metadata" in user_obj:
            old_app_metadata = user_obj["app_metadata"]
            old_hash = json.dumps(old_app_metadata, sort_keys=True)
            new_hash = json.dumps(app_metadata, sort_keys=True)
            if old_hash == new_hash:
                return user_obj

        # update app_metadata
        user_obj["app_metadata"] = app_metadata
        user_obj = self._storage.save(obj_type, user_obj)
        self.sns_publish("users", user_obj)  # publish notification

        return user_obj

    def get_user_app_metadata(self):
        obj_type = 'users'

        # get user profile
        user_obj = self._storage.get_by_user_id(self._user_id)

        if not user_obj:
            raise NoSuchEntity

        user_obj = clean(user_obj)

        app_metadata = user_obj.get("app_metadata", {})
        return app_metadata

    def delete_profile(self):
        obj_type = 'users'

        profile = self._storage.get(self._user_id)

        if profile:
            obj = clean(profile)

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("users", obj)  # publish notification
        else:
            raise NoSuchEntity
