from enum import Enum
from typing import Any
from pydantic import BaseModel


class AuthMethod(str, Enum):
    ANONYMOUS = "Anonymous"
    BASIC = "Basic"
    BEARER = "Bearer"


class GrantType(str, Enum):
    CLIENT_CREDENTIALS = "client_credentials"
    PASSWORD = "password"


class HttpTokenParameter(BaseModel):
    grantType: GrantType
    scope: str
    resource: str | None = None
    tenant: str
    clientId: str
    clientSecret: str
    user: str
    password: str


class AuthInfoVM(BaseModel):
    type: AuthMethod
    credentials: HttpTokenParameter | None = None
    tokenProvided: str | None = None


class ResponseValidationVM(BaseModel):
    type: str
    value: Any | None = None
    errorMessage: str | None = None


class ExpectedResponseVM(BaseModel):
    status: int = 200
    contentValidations: dict[str, ResponseValidationVM] | None = None


class ApiTestRequestVM(BaseModel):
    id: str
    authenticationParams: AuthInfoVM | None = None
    headers: dict[str, str] | None = None
    cookies: dict[str, str] | None = None
    queryParams: dict[str, str] | None = None
    url: str
    method: str
    jsonBody: dict[str, Any] | None = None
    expectedResponse: ExpectedResponseVM = ExpectedResponseVM()
    variables: dict[str, str] | None = None
    waitForEventPropagation: str | None = None
    referenceFile: str | None = None

    def build_request_kwargs(self, auth_token: str | None) -> dict[str, Any]:
        headers = dict(self.headers) if self.headers else {}
        if auth_token:
            headers.setdefault("Authorization", f"Bearer {auth_token}")

        # TODO: add referenceFile prop - multipart
        return {
            "method": self.method,
            "url": self.url,
            "headers": headers,
            "cookies": self.cookies,
            "params": self.queryParams,
            "json": self.jsonBody,
        }


class ApiTestRequestVMList(BaseModel):
    authenticationParams: AuthInfoVM | None = None
    apiTestRequests: list[ApiTestRequestVM]
    globalVariables: dict[str, str]
