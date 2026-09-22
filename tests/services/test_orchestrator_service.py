from unittest.mock import MagicMock, create_autospec, patch

from apitest.auth_service import AuthService
from apitest.dynamic_vars_evaluator_service import DynamicVarsEvaluatorService
from apitest.orchestrator_service import OrchestratorService
from apitest.response_validation_service import ResponseValidationService
from apitest.vars_evaluator_service import VariablesEvaluatorService
from models.apitestify_requests import (
    ApiTestRequestVM,
    ApiTestRequestVMList,
    AuthInfoVM,
    AuthMethod,
    ExpectedResponseVM,
)


@patch("apitest.orchestrator_service.requests.request")
def test_validate_returns_successful_response_for_happy_path(
    mock_request: MagicMock,
) -> None:
    auth_service = create_autospec(AuthService, instance=True)
    response_validation_service = create_autospec(
        ResponseValidationService, instance=True
    )
    vars_evaluator_service = create_autospec(VariablesEvaluatorService, instance=True)
    dynamic_vars_evaluator_service = create_autospec(
        DynamicVarsEvaluatorService, instance=True
    )
    secrets = {"clientSecret": "resolved-secret"}
    authentication = AuthInfoVM(type=AuthMethod.BEARER, tokenProvided="provided-token")
    api_request = ApiTestRequestVM(
        id="get-user",
        url="https://api.example.test/users/42",
        method="GET",
        headers={"Accept": "application/json"},
        queryParams={"requestedAt": "{{DynamicNow}}"},
        jsonBody={"some_key": "some_value", "dynamic_field": "{{DynamicRandomGuid}}"},
        expectedResponse=ExpectedResponseVM(status=200),
        variables={"userId": "$.id"},
    )
    request_list = ApiTestRequestVMList(
        authenticationParams=authentication,
        apiTestRequests=[api_request],
        globalVariables={"environment": "test"},
    )

    auth_service.get_auth_token.return_value = "access-token"
    dynamic_vars_evaluator_service.replace_dynamic_variables.side_effect = [
        {"some_key": "some_value", "dynamic_field": "123abc"},
        {"requestedAt": "2026-09-16T12:00:00Z"},
    ]
    response_validation_service.validate_response.return_value = []
    vars_evaluator_service.resolve_request_variables.return_value = ({"userId": 42}, [])
    http_response = MagicMock()
    http_response.status_code = 200
    http_response.headers = {"Content-Type": "application/json; charset=utf-8"}
    http_response.json.return_value = {"id": 42, "name": "Ada"}
    mock_request.return_value = http_response

    orchestrator = OrchestratorService(
        auth_service,
        response_validation_service,
        vars_evaluator_service,
        dynamic_vars_evaluator_service,
        secrets,
    )
    responses = orchestrator.validate(request_list)

    vars_evaluator_service.replace_secrets.assert_called_once_with(
        secrets, authentication
    )
    auth_service.get_auth_token.assert_called_once_with(authentication)
    vars_evaluator_service.replace_variables.assert_called_once_with(
        request_list.globalVariables, api_request
    )
    mock_request.assert_called_once_with(
        method="GET",
        url="https://api.example.test/users/42",
        headers={"Accept": "application/json", "Authorization": "Bearer access-token"},
        cookies=None,
        params={"requestedAt": "2026-09-16T12:00:00Z"},
        json={"some_key": "some_value", "dynamic_field": "123abc"},
    )
    response_validation_service.validate_response.assert_called_once_with(
        None, responses[0]
    )
    vars_evaluator_service.resolve_request_variables.assert_called_once_with(
        {"userId": "$.id"}, responses[0]
    )

    assert len(responses) == 1
    assert responses[0].requestId == "get-user"
    assert responses[0].status == 200
    assert responses[0].originalResponse == {"id": 42, "name": "Ada"}
    assert responses[0].storedVariables == {"userId": 42}
    assert responses[0].failedValidations == []
    assert responses[0].isValidationSuccess is True
    assert request_list.globalVariables == {"environment": "test", "userId": 42}


@patch("apitest.orchestrator_service.requests.request")
def test_validate_stops_after_first_failed_response(mock_request: MagicMock) -> None:
    auth_service = create_autospec(AuthService, instance=True)
    response_validation_service = create_autospec(
        ResponseValidationService, instance=True
    )
    vars_evaluator_service = create_autospec(VariablesEvaluatorService, instance=True)
    dynamic_vars_evaluator_service = create_autospec(
        DynamicVarsEvaluatorService, instance=True
    )
    authentication = AuthInfoVM(type=AuthMethod.BEARER, tokenProvided="provided-token")
    request_list = ApiTestRequestVMList(
        authenticationParams=authentication,
        apiTestRequests=[
            ApiTestRequestVM(
                id="failing-request",
                url="https://api.example.test/failing",
                method="GET",
                expectedResponse=ExpectedResponseVM(status=200),
            ),
            ApiTestRequestVM(
                id="skipped-request",
                url="https://api.example.test/skipped",
                method="GET",
                expectedResponse=ExpectedResponseVM(status=200),
            ),
        ],
        globalVariables={},
    )

    auth_service.get_auth_token.return_value = "access-token"
    vars_evaluator_service.resolve_request_variables.return_value = ({}, [])
    response_validation_service.validate_response.return_value = [MagicMock()]
    http_response = MagicMock()
    http_response.status_code = 200
    http_response.headers = {"Content-Type": "application/json"}
    http_response.json.return_value = {"status": "failed"}
    mock_request.return_value = http_response

    orchestrator = OrchestratorService(
        auth_service,
        response_validation_service,
        vars_evaluator_service,
        dynamic_vars_evaluator_service,
        {},
    )
    responses = orchestrator.validate(request_list)

    assert len(responses) == 1
    assert responses[0].requestId == "failing-request"
    assert responses[0].isValidationSuccess is False
    mock_request.assert_called_once()


@patch("apitest.orchestrator_service.requests.request")
def test_validate_returns_empty_response_for_no_content(
    mock_request: MagicMock,
) -> None:
    """Ensure 204 responses bypass JSON parsing and retain an empty response body."""
    auth_service = create_autospec(AuthService, instance=True)
    response_validation_service = create_autospec(
        ResponseValidationService, instance=True
    )
    vars_evaluator_service = create_autospec(VariablesEvaluatorService, instance=True)
    dynamic_vars_evaluator_service = create_autospec(
        DynamicVarsEvaluatorService, instance=True
    )
    api_request = ApiTestRequestVM(
        id="delete-user",
        url="https://api.example.test/users/42",
        method="DELETE",
        expectedResponse=ExpectedResponseVM(status=204),
    )
    request_list = ApiTestRequestVMList(
        apiTestRequests=[api_request], globalVariables={}
    )
    response_validation_service.validate_response.return_value = []
    vars_evaluator_service.resolve_request_variables.return_value = ({}, [])
    http_response = MagicMock()
    http_response.status_code = 204
    http_response.headers = {"Content-Type": "application/json"}
    mock_request.return_value = http_response

    orchestrator = OrchestratorService(
        auth_service,
        response_validation_service,
        vars_evaluator_service,
        dynamic_vars_evaluator_service,
        {},
    )
    responses = orchestrator.validate(request_list)

    assert responses[0].originalResponse == {}
    http_response.json.assert_not_called()


@patch("apitest.orchestrator_service.sleep")
@patch("apitest.orchestrator_service.requests.request")
def test_validate_waits_for_event_propagation_when_configured(
    mock_request: MagicMock, mock_sleep: MagicMock
) -> None:
    auth_service = create_autospec(AuthService, instance=True)
    response_validation_service = create_autospec(
        ResponseValidationService, instance=True
    )
    vars_evaluator_service = create_autospec(VariablesEvaluatorService, instance=True)
    dynamic_vars_evaluator_service = create_autospec(
        DynamicVarsEvaluatorService, instance=True
    )
    api_request = ApiTestRequestVM(
        id="create-user",
        url="https://api.example.test/users",
        method="POST",
        expectedResponse=ExpectedResponseVM(status=201),
        waitForEventPropagation="3",
    )
    request_list = ApiTestRequestVMList(
        apiTestRequests=[api_request], globalVariables={}
    )
    response_validation_service.validate_response.return_value = []
    vars_evaluator_service.resolve_request_variables.return_value = ({}, [])
    http_response = MagicMock()
    http_response.status_code = 201
    http_response.headers = {"Content-Type": "application/json"}
    http_response.json.return_value = {"id": 42}
    mock_request.return_value = http_response

    orchestrator = OrchestratorService(
        auth_service,
        response_validation_service,
        vars_evaluator_service,
        dynamic_vars_evaluator_service,
        {},
    )
    responses = orchestrator.validate(request_list)

    assert responses[0].isValidationSuccess is True
    mock_sleep.assert_called_once_with(3.0)


def test_get_original_response_parses_json_text_without_json_content_type() -> None:
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "text/plain"}
    response.text = '{"message": "ok"}'

    orchestrator = OrchestratorService.__new__(OrchestratorService)

    assert orchestrator._get_original_response(response) == {"message": "ok"}


def test_get_original_response_returns_error_details_for_invalid_json_text() -> None:
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "text/plain"}
    response.text = "not json"

    orchestrator = OrchestratorService.__new__(OrchestratorService)

    result = orchestrator._get_original_response(response)

    assert result["error"] == "Response body is not valid JSON"
    assert result["text"] == "not json"
    assert result["details"]
