import requests
from datetime import datetime, timedelta
from models.apitestify_requests import AuthInfoVM, GrantType

class AuthService:
    def __init__(self):
        self.refresh_token = None
        self.expired_time_token = None
        self.client_id = None
        self.client_secret = None
        self.user = None
        self.password = None
        self.scope = None
        self.resource = None
        self.grant_type = None
    
    def __auth_token_is_present_and_valid(self, auth_params: AuthInfoVM):
        return (self.refresh_token is not None
            and self.expired_time_token is not None
            and self.expired_time_token > datetime.now()
            and self.client_id == auth_params.credentials.clientId
            and self.client_secret == auth_params.credentials.clientSecret
            and self.user == auth_params.credentials.user
            and self.password == auth_params.credentials.password
            and self.scope == auth_params.credentials.scope
            and self.resource == auth_params.credentials.resource
            and self.grant_type == auth_params.credentials.grantType)

    def get_auth_token(self, auth_params: AuthInfoVM):
        if self.__auth_token_is_present_and_valid(auth_params):
            return self.refresh_token
        
        if auth_params.tokenProvided:
            return auth_params.tokenProvided

        if auth_params.credentials is None:
            raise Exception(f"Failed to acquire token: missing credentials")
        
        if auth_params.credentials.grantType == GrantType.CLIENT_CREDENTIALS:
            data = {
                "grant_type": "client_credentials",
                "client_id": auth_params.credentials.clientId,
                "client_secret": auth_params.credentials.clientSecret,
                "Resource": auth_params.credentials.resource or ""
            }
        else:
            data = {
                "grant_type": "password",
                "client_id": auth_params.credentials.clientId,
                "client_secret": auth_params.credentials.clientSecret,
                "username": auth_params.credentials.user,
                "password": auth_params.credentials.password,
                "scope": auth_params.credentials.scope
            }

        response = requests.post(auth_params.credentials.tenant, data=data)
        result = response.json()

        if not response.ok:
            # return (f"Failed to acquire token: {response.text}")
            raise Exception(f"Failed to acquire token: {response.text}")

        self.refresh_token = result["access_token"]
        self.expired_time_token = datetime.now() + timedelta(seconds=result["expires_in"])
        self.client_id = auth_params.credentials.clientId
        self.client_secret = auth_params.credentials.clientSecret
        self.user = auth_params.credentials.user
        self.password = auth_params.credentials.password
        self.scope = auth_params.credentials.scope
        self.resource = auth_params.credentials.resource
        self.grant_type = auth_params.credentials.grantType

        return result["access_token"]        
