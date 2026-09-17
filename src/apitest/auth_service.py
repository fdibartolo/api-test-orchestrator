from datetime import UTC, datetime, timedelta

import requests

from models.apitestify_requests import AuthInfoVM, GrantType


class AuthService:
    """Acquire and cache bearer tokens for authentication requests.

    The service returns a caller-provided token when available, reuses a cached
    token while it is unexpired and matches the request credentials, or obtains
    a new token using the configured client-credentials or password grant.
    """

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

    def _auth_token_is_present_and_valid(self, auth_params: AuthInfoVM) -> bool:
        return (
            self.refresh_token is not None
            and self.expired_time_token is not None
            and self.expired_time_token > datetime.now(UTC)
            and self.client_id == auth_params.credentials.clientId
            and self.client_secret == auth_params.credentials.clientSecret
            and self.user == auth_params.credentials.user
            and self.password == auth_params.credentials.password
            and self.scope == auth_params.credentials.scope
            and self.resource == auth_params.credentials.resource
            and self.grant_type == auth_params.credentials.grantType
        )

    def get_auth_token(self, auth_params: AuthInfoVM) -> str:
        """Return an access token for the supplied authentication parameters.

        A valid cached token is preferred, followed by a token supplied in
        ``auth_params``. If neither is available, this method requests a new
        token using the configured client-credentials or password grant and
        caches it until it expires.

        Args:
            auth_params: Authentication settings, credentials, or a
                pre-existing token.

        Returns:
            The access token to use for authenticated requests.

        Raises:
            Exception: If credentials are missing or the token endpoint rejects
                the request.
        """
        if self._auth_token_is_present_and_valid(auth_params):
            return self.refresh_token

        if auth_params.tokenProvided:
            return auth_params.tokenProvided

        if auth_params.credentials is None:
            raise ConnectionError("Failed to acquire token: missing credentials")

        if auth_params.credentials.grantType == GrantType.CLIENT_CREDENTIALS:
            data = {
                "grant_type": "client_credentials",
                "client_id": auth_params.credentials.clientId,
                "client_secret": auth_params.credentials.clientSecret,
                "Resource": auth_params.credentials.resource or "",
            }
        else:
            data = {
                "grant_type": "password",
                "client_id": auth_params.credentials.clientId,
                "client_secret": auth_params.credentials.clientSecret,
                "username": auth_params.credentials.user,
                "password": auth_params.credentials.password,
                "scope": auth_params.credentials.scope,
            }

        response = requests.post(auth_params.credentials.tenant, data=data)
        result = response.json()

        if not response.ok:
            raise ConnectionError(f"Failed to acquire token: {response.text}")

        self.refresh_token = result["access_token"]
        self.expired_time_token = datetime.now(UTC) + timedelta(
            seconds=result["expires_in"]
        )
        self.client_id = auth_params.credentials.clientId
        self.client_secret = auth_params.credentials.clientSecret
        self.user = auth_params.credentials.user
        self.password = auth_params.credentials.password
        self.scope = auth_params.credentials.scope
        self.resource = auth_params.credentials.resource
        self.grant_type = auth_params.credentials.grantType

        return result["access_token"]
