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
    status: int
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
    expectedResponse: ExpectedResponseVM | None = None
    variables: dict[str, str] | None = None
    waitForEventPropagation: str | None = None
    referenceFile: str | None = None

class ApiTestRequestVMList(BaseModel):
    authenticationParams: AuthInfoVM | None = None
    apiTestRequests: list[ApiTestRequestVM]
    globalVariables: dict[str, str]
