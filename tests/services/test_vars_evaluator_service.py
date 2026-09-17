import pytest
from apitest.vars_evaluator_service import VariablesEvaluatorService
from models.apitestify_requests import (
    ApiTestRequestVM,
    AuthInfoVM,
    AuthMethod,
    ExpectedResponseVM,
    GrantType,
    HttpTokenParameter,
    ResponseValidationVM,
)
from models.apitestify_responses import ApiTestResponseVM


def build_auth_info(
    client_secret: str = "#{clientSecret}#", password: str = "#{password}#"
) -> AuthInfoVM:
    return AuthInfoVM(
        type=AuthMethod.BEARER,
        credentials=HttpTokenParameter(
            grantType=GrantType.PASSWORD,
            scope="openid profile",
            tenant="https://login.example.test/token",
            clientId="client-id",
            clientSecret=client_secret,
            user="user@example.test",
            password=password,
        ),
    )


def build_request() -> ApiTestRequestVM:
    return ApiTestRequestVM(
        id="request-id",
        url="https://example.test/#{host}#/users/#{userId}#",
        method="GET",
        headers={"X-Trace": "#{traceId}#", "X-Unknown": "#{missing}#"},
        cookies={"session": "#{session}#"},
        queryParams={"filter": "#{filter}#"},
        jsonBody={"userId": "#{userId}#", "active": True},
        variables={"nested": "#{traceId}#"},
        expectedResponse=ExpectedResponseVM(
            contentValidations={
                "$.users[#{userId}#]": ResponseValidationVM(
                    type="equals",
                    value="#{expectedName}#",
                    errorMessage="Invalid #{expectedName}#",
                )
            }
        ),
    )


def build_response(original_response: dict) -> ApiTestResponseVM:
    return ApiTestResponseVM(
        requestId="request-id",
        originalResponse=original_response,
        status=200,
        originalRequest={"method": "GET", "url": "https://example.test"},
    )


def test_replace_secrets_updates_client_secret_and_password() -> None:
    auth_info = build_auth_info()
    VariablesEvaluatorService().replace_secrets(
        {"clientSecret": "resolved-secret", "password": "resolved-password"},
        auth_info,
    )
    assert auth_info.credentials.clientSecret == "resolved-secret"
    assert auth_info.credentials.password == "resolved-password"


def test_replace_secrets_preserves_unresolved_placeholders() -> None:
    auth_info = build_auth_info()
    VariablesEvaluatorService().replace_secrets(
        {"clientSecret": "resolved-secret"}, auth_info
    )
    assert auth_info.credentials.clientSecret == "resolved-secret"
    assert auth_info.credentials.password == "#{password}#"


def test_replace_variables_updates_request_and_validations() -> None:
    request = build_request()

    VariablesEvaluatorService().replace_variables(
        {
            "host": "api.example.test",
            "userId": "42",
            "traceId": "trace-1",
            "session": "session-1",
            "filter": "active",
            "expectedName": "Alice",
        },
        request,
    )

    assert request.url == "https://example.test/api.example.test/users/42"
    assert request.headers == {"X-Trace": "trace-1", "X-Unknown": "#{missing}#"}
    assert request.cookies == {"session": "session-1"}
    assert request.queryParams == {"filter": "active"}
    assert request.jsonBody == {"userId": "42", "active": True}
    assert request.variables == {"nested": "trace-1"}
    assert request.expectedResponse.contentValidations["$.users[42]"].value == "Alice"
    assert (
        request.expectedResponse.contentValidations["$.users[42]"].errorMessage
        == "Invalid Alice"
    )


def test_replace_variables_round_trips_json_body() -> None:
    request = ApiTestRequestVM(
        id="request-id",
        url="https://example.test",
        method="POST",
        jsonBody={"count": "#{count}#", "enabled": "#{enabled}#"},
    )
    VariablesEvaluatorService().replace_variables(
        {"count": "3", "enabled": "true"}, request
    )
    assert request.jsonBody == {"count": "3", "enabled": "true"}


def test_replace_variables_does_nothing_for_empty_variables() -> None:
    request = build_request()
    VariablesEvaluatorService().replace_variables({}, request)
    assert request.url == "https://example.test/#{host}#/users/#{userId}#"


def test_store_variables_extracts_values_and_resolves_strings() -> None:
    response = build_response({"user": {"id": 42, "name": "Alice"}})
    variables_resolved, failed_validations = (
        VariablesEvaluatorService().resolve_request_variables(
            {"userId": "$.user.id", "userName": "$.user.name"}, response
        )
    )

    assert variables_resolved == {"userId": 42, "userName": "Alice"}
    assert failed_validations == []


def test_store_variables_reports_missing_json_path() -> None:
    response = build_response({"user": {"id": 42}})

    variables_resolved, failed_validations = (
        VariablesEvaluatorService().resolve_request_variables(
            {"missing": "$.user.email"}, response
        )
    )

    assert variables_resolved == {}
    assert len(failed_validations) == 1
    failure = failed_validations[0]
    assert failure.key == "missing"
    assert failure.type == "SelectToken"
    assert failure.expectedValue == "$.user.email"
    assert failure.actualValue is None
    assert "did not find any value" in failure.message


def test_store_variables_reports_invalid_json_path() -> None:
    response = build_response({"user": {"id": 42}})

    variables_resolved, failed_validations = (
        VariablesEvaluatorService().resolve_request_variables(
            {"invalid": "$["}, response
        )
    )

    assert variables_resolved == {}
    assert len(failed_validations) == 1
    failure = failed_validations[0]
    assert failure.key == "invalid"
    assert failure.type == "SelectToken"
    assert "Error processing variable 'invalid'" in failure.message


def test_store_variables_raises_for_null_original_response() -> None:
    response = build_response({})
    response.originalResponse = None

    with pytest.raises(ValueError, match="OriginalResponse is null"):
        VariablesEvaluatorService().resolve_request_variables(
            {"userId": "$.user.id"}, response
        )
