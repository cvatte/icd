import datetime

from datetime import timedelta
from onthology_app import Serializer
from flask import current_app
from onthology_app.status.messages import messages

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from msal import ConfidentialClientApplication

ph = PasswordHasher()


# To avoid circular import
# from samchitam_api.models.owlfile import OwlFile

class User(Serializer):

    def serialize(self):
        d = Serializer.serialize(self)
        del d['password']
        del d['owl_files']
        del d['created_at']
        del d['updated_at']
        return d

    @staticmethod
    def authenticate(username, password):
        client_id = current_app.config['CLIENT_ID']
        tenant_id = current_app.config['TENANT_ID']

        app = ConfidentialClientApplication(
                client_id=client_id,
                authority="https://login.microsoftonline.com/" + tenant_id,
                client_credential=current_app.config['CLIENT_SECRET']
            )
        scope = [current_app.config['SCOPE']]


        acquire_tokens_result = app.acquire_token_by_username_password(
                username=username,
                password=password,
                scopes=scope
            )

        if 'error' in acquire_tokens_result:
            print("Error: " + acquire_tokens_result['error'])
            print("Description: " + acquire_tokens_result['error_description'])
            return {"error": messages["acquire-token-error"]}
        else:
            print("Access token:\n")
            print(acquire_tokens_result['access_token'])
            print("\nRefresh token:\n")
            print(acquire_tokens_result['refresh_token'])
            print("complete result")
            print(acquire_tokens_result)
            expTime = datetime.datetime.fromtimestamp(acquire_tokens_result['id_token_claims']['exp']).isoformat()
            issued_time = datetime.datetime.strptime(expTime, '%Y-%m-%dT%H:%M:%S')
            token_valid_till = str(issued_time) + " UTC"
            token_issued_time = str(issued_time + timedelta(hours=-24)) + " UTC"
            return {
                'name': acquire_tokens_result['id_token_claims']['name'],
                'username': acquire_tokens_result['id_token_claims']['preferred_username'],
               'access_token': acquire_tokens_result['access_token'],
               'refresh_token': acquire_tokens_result['refresh_token'],
                'subscription_key': current_app.config['SUBSCRIPTION_KEY'],
                'token_type': acquire_tokens_result['token_type'],
                'token_issued_time': token_issued_time,
                'token_valid_till': token_valid_till
            }
    @staticmethod
    def get_access_token(refresh_token):
        client_id = current_app.config['CLIENT_ID']
        tenant_id = current_app.config['TENANT_ID']
        client_secret = current_app.config['CLIENT_SECRET']
        scope = [current_app.config['SCOPE']]

        app = ConfidentialClientApplication(
            client_id=client_id,
            authority="https://login.microsoftonline.com/" + tenant_id,
            client_credential=client_secret
        )

        acquire_tokens_result = app.acquire_token_by_refresh_token(
            refresh_token=refresh_token,
            scopes=scope
        )

        if 'error' in acquire_tokens_result:
            print("Error: " + acquire_tokens_result['error'])
            print("Description: " + acquire_tokens_result['error_description'])
            return {"error": messages["refresh-token-expired"]}


        else:
            return {
                'access_token': acquire_tokens_result['access_token'],
                'refresh_token': acquire_tokens_result['refresh_token'],
            }
