import requests
import os
import json
from data_common.exceptions import Auth0UnableToAccess, Auth0AccessDenied


class Auth0:
    def __init__(self, user_id):
        self._user_id = user_id

    @staticmethod
    def _get_token(scope):
        # get Auth0 user profile object (in order to get app_metadata)
        resp = requests.post(
            os.environ['AUTH0_DOMAIN'] + '/oauth/token',
            json={
                'grant_type': 'client_credentials',
                'client_id': os.environ['AUTH0_MANAGEMENT_API_CLIENT_ID'],
                'client_secret': os.environ['AUTH0_MANAGEMENT_API_CLIENT_SECRET'],
                'audience': os.environ['AUTH0_AUDIENCE'],
                'scope': scope
            },
            headers={
                'content-type': "application/json"
            }

        )
        return resp

    def get_app_metadata(self, user_id=None):
        """
        Gets auth0 account app_metadata
        If user_id is provided, that user's account is retreived
        """

        resp = self._get_token('read:users')

        users_token_body = resp.json()

        if "error" in users_token_body and users_token_body["error"] == "access_denied":
            raise Auth0AccessDenied

        if 'access_token' in users_token_body:
            _access_token = users_token_body['access_token']

            if user_id:
                _auth0_user_id = 'auth0|' + user_id
            else:
                _auth0_user_id = 'auth0|' + self._user_id

            resp = requests.get(
                os.environ['AUTH0_DOMAIN'] + '/api/v2/users/{ID}'.format(ID=_auth0_user_id),
                headers={
                    'content-type': "application/json",
                    'Authorization': 'Bearer {ACCESS_TOKEN}'.format(ACCESS_TOKEN=_access_token)
                }

            )

            users_body = resp.json()
            if "app_metadata" not in users_body:
                app_metadata = {}
            else:
                app_metadata = users_body["app_metadata"]

            return app_metadata
        else:
            raise Auth0UnableToAccess

    def update_app_metadata(self, app_metadata, user_id=None):
        """
        Updates auth0 account app_metadata
        If user_id is provided, that user's account is updated
        """
        app_metadata = app_metadata.copy()    # avoid mutation. Security risk

        resp = self._get_token('update:users')

        users_token_body = resp.json()

        if "error" in users_token_body and users_token_body["error"] == "access_denied":
            raise Auth0AccessDenied

        if 'access_token' in users_token_body:
            _access_token = users_token_body['access_token']

            if user_id:
                _auth0_user_id = 'auth0|' + user_id
            else:
                _auth0_user_id = 'auth0|' + self._user_id

            payload = json.dumps({"app_metadata": app_metadata})
            resp = requests.patch(
                os.environ['AUTH0_DOMAIN'] + '/api/v2/users/{ID}'.format(ID=_auth0_user_id),
                payload,
                headers={
                    'content-type': "application/json",
                    'Authorization': 'Bearer {ACCESS_TOKEN}'.format(ACCESS_TOKEN=_access_token)
                }

            )

            print("After auth0 metadata update")
            print(resp.json())

            return resp.status_code
        else:
            raise Auth0UnableToAccess

    def update_profile(self, profile):
        """
        Updates auth0 account app_metadata
        The `profile` object should be a dict that matches key-val pairs in
        https://auth0.com/docs/api/management/v2#!/Users/patch_users_by_id
        """

        resp = self._get_token('update:users')

        users_token_body = resp.json()

        if "error" in users_token_body and users_token_body["error"] == "access_denied":
            raise Auth0AccessDenied

        if 'access_token' in users_token_body:
            _access_token = users_token_body['access_token']

            _auth0_user_id = 'auth0|' + self._user_id

            payload = json.dumps(profile)
            resp = requests.patch(
                os.environ['AUTH0_DOMAIN'] + '/api/v2/users/{ID}'.format(ID=_auth0_user_id),
                payload,
                headers={
                    'content-type': "application/json",
                    'Authorization': 'Bearer {ACCESS_TOKEN}'.format(ACCESS_TOKEN=_access_token)
                }

            )

            print("After auth0 profile update")
            print(resp.json())

            return resp
        else:
            raise Auth0UnableToAccess

    def trigger_password_reset(self, email):

        resp = self._get_token('update:users')

        users_token_body = resp.json()

        if "error" in users_token_body and users_token_body["error"] == "access_denied":
            raise Auth0AccessDenied

        resp = None
        if 'access_token' in users_token_body:
            _access_token = users_token_body['access_token']

            resp = requests.post(
                os.environ['AUTH0_DOMAIN'] + "/dbconnections/change_password",
                json={
                    'email': email,
                    'client_id': os.environ['AUTH0_MANAGEMENT_API_CLIENT_ID'],
                    'connection': os.environ['AUTH0_CONNECTION'],
                },
                headers={
                    'Authorization': 'Bearer {TOKEN}'.format(TOKEN=_access_token),
                    'content-type': "application/json"
                })

        return resp