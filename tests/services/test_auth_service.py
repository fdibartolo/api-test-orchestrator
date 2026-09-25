from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from apitest.auth_service import AuthService
from models.apitest_requests import (
    AuthInfoVM,
    AuthMethod,
    GrantType,
    HttpTokenParameter,
)


@pytest.fixture
def client_credentials_auth_info() -> AuthInfoVM:
    return AuthInfoVM(
        type=AuthMethod.BEARER,
        credentials=HttpTokenParameter(
            grantType=GrantType.CLIENT_CREDENTIALS,
            scope="https://graph.microsoft.com/.default",
            resource="https://graph.microsoft.com",
            tenant="https://login.microsoftonline.com/tenant-id/oauth2/v2.0/token",
            clientId="client-123",
            clientSecret="secret-456",
            user="user@example.com",
            password="password123",
        ),
    )


@pytest.fixture
def password_auth_info() -> AuthInfoVM:
    return AuthInfoVM(
        type=AuthMethod.BEARER,
        credentials=HttpTokenParameter(
            grantType=GrantType.PASSWORD,
            scope="openid profile",
            resource=None,
            tenant="https://login.example.com/oauth/token",
            clientId="client-789",
            clientSecret="secret-000",
            user="user@example.com",
            password="password123",
        ),
    )


def test_get_auth_token_returns_provided_token() -> None:
    auth_service = AuthService()
    auth_info = AuthInfoVM(type=AuthMethod.BEARER, tokenProvided="pre-existing-token")

    token = auth_service.get_auth_token(auth_info)
    assert token == "pre-existing-token"


def test_get_auth_token_raises_when_credentials_missing() -> None:
    auth_service = AuthService()
    auth_info = AuthInfoVM(type=AuthMethod.BEARER, credentials=None, tokenProvided=None)

    with pytest.raises(
        ConnectionError, match="Failed to acquire token: missing credentials"
    ):
        auth_service.get_auth_token(auth_info)


@patch("apitest.auth_service.requests.post")
def test_get_auth_token_client_credentials_success(
    mock_post: MagicMock, client_credentials_auth_info: AuthInfoVM
) -> None:
    auth_service = AuthService()
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "access_token": "token-client-cred",
        "expires_in": 3600,
    }
    mock_post.return_value = mock_response

    token = auth_service.get_auth_token(client_credentials_auth_info)

    assert token == "token-client-cred"
    mock_post.assert_called_once_with(
        "https://login.microsoftonline.com/tenant-id/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "client-123",
            "client_secret": "secret-456",
            "Resource": "https://graph.microsoft.com",
        },
    )
    assert auth_service.refresh_token == "token-client-cred"
    assert auth_service.client_id == "client-123"
    assert auth_service.client_secret == "secret-456"


@patch("apitest.auth_service.requests.post")
def test_get_auth_token_password_grant_success(
    mock_post: MagicMock, password_auth_info: AuthInfoVM
) -> None:
    auth_service = AuthService()
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "access_token": "token-password-grant",
        "expires_in": 1800,
    }
    mock_post.return_value = mock_response

    token = auth_service.get_auth_token(password_auth_info)

    assert token == "token-password-grant"
    mock_post.assert_called_once_with(
        "https://login.example.com/oauth/token",
        data={
            "grant_type": "password",
            "client_id": "client-789",
            "client_secret": "secret-000",
            "username": "user@example.com",
            "password": "password123",
            "scope": "openid profile",
        },
    )


@patch("apitest.auth_service.requests.post")
def test_get_auth_token_reuses_cached_valid_token(
    mock_post: MagicMock, client_credentials_auth_info: AuthInfoVM
) -> None:
    auth_service = AuthService()
    auth_service.refresh_token = "cached-valid-token"
    auth_service.expired_time_token = datetime.now(UTC) + timedelta(seconds=600)
    auth_service.client_id = "client-123"
    auth_service.client_secret = "secret-456"
    auth_service.user = "user@example.com"
    auth_service.password = "password123"
    auth_service.scope = "https://graph.microsoft.com/.default"
    auth_service.resource = "https://graph.microsoft.com"
    auth_service.grant_type = GrantType.CLIENT_CREDENTIALS

    token = auth_service.get_auth_token(client_credentials_auth_info)

    assert token == "cached-valid-token"
    mock_post.assert_not_called()


@patch("apitest.auth_service.requests.post")
def test_get_auth_token_fetches_new_token_when_cached_token_expired(
    mock_post: MagicMock, client_credentials_auth_info: AuthInfoVM
) -> None:
    auth_service = AuthService()
    auth_service.refresh_token = "expired-token"
    auth_service.expired_time_token = datetime.now(UTC) - timedelta(seconds=10)
    auth_service.client_id = "client-123"
    auth_service.client_secret = "secret-456"
    auth_service.user = "user@example.com"
    auth_service.password = "password123"
    auth_service.scope = "https://graph.microsoft.com/.default"
    auth_service.resource = "https://graph.microsoft.com"
    auth_service.grant_type = GrantType.CLIENT_CREDENTIALS

    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "access_token": "fresh-token",
        "expires_in": 3600,
    }
    mock_post.return_value = mock_response

    token = auth_service.get_auth_token(client_credentials_auth_info)

    assert token == "fresh-token"
    mock_post.assert_called_once()


@patch("apitest.auth_service.requests.post")
def test_get_auth_token_http_error_raises_exception(
    mock_post: MagicMock, client_credentials_auth_info: AuthInfoVM
) -> None:
    auth_service = AuthService()
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.text = "Unauthorized client"
    mock_post.return_value = mock_response

    with pytest.raises(
        ConnectionError, match="Failed to acquire token: Unauthorized client"
    ):
        auth_service.get_auth_token(client_credentials_auth_info)
