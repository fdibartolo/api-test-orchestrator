import pytest
import re
from apitest.process_variables_service import ProcessVariablesService
from models.apitestify_requests import ApiTestRequestVM, ExpectedResponseVM, ResponseValidationVM
from models.apitestify_responses import ApiTestResponseVM

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

def test_replace_variables_updates_request_and_validations() -> None:
    request = build_request()

    ProcessVariablesService().replace_variables(
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
    assert request.expectedResponse.contentValidations["$.users[42]"].errorMessage == "Invalid Alice"

def test_replace_variables_round_trips_json_body() -> None:
    request = ApiTestRequestVM(
        id="request-id",
        url="https://example.test",
        method="POST",
        jsonBody={"count": "#{count}#", "enabled": "#{enabled}#"},
    )

    ProcessVariablesService().replace_variables(
        {"count": "3", "enabled": "true"},
        request,
    )

    assert request.jsonBody == {"count": "3", "enabled": "true"}

def test_replace_variables_does_nothing_for_empty_variables() -> None:
    request = build_request()

    ProcessVariablesService().replace_variables({}, request)

    assert request.url == "https://example.test/#{host}#/users/#{userId}#"

def test_store_variables_extracts_values_and_resolves_strings() -> None:
    response = build_response({"user": {"id": 42, "name": "Alice"}})
    variables_resolved, failed_validations = ProcessVariablesService().resolve_request_variables(
        {"userId": "$.user.id", "userName": "$.user.name"}, response)

    assert variables_resolved == {"userId": 42, "userName": "Alice"}
    assert failed_validations == []

def test_store_variables_reports_missing_json_path() -> None:
    response = build_response({"user": {"id": 42}})

    variables_resolved, failed_validations = ProcessVariablesService().resolve_request_variables(
        {"missing": "$.user.email"}, response)

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

    variables_resolved, failed_validations = ProcessVariablesService().resolve_request_variables(
        {"invalid": "$["}, response)

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
        ProcessVariablesService().resolve_request_variables({"userId": "$.user.id"}, response)

def test_replace_dynamic_variables_replaces_today_with_default_format() -> None:
    result = ProcessVariablesService().resolve_dynamic_value("date={{DynamicToday}}")
    assert re.fullmatch(r"date=\d{4}-\d{2}-\d{2}", result)

def test_replace_dynamic_variables_replaces_custom_datetime_format() -> None:
    result = ProcessVariablesService().resolve_dynamic_value(
        "at={{DynamicNow}}:yy-MM-dd"
    )
    assert re.fullmatch(r"at=\d{2}-\d{2}-\d{2}", result)

@pytest.mark.parametrize("token", ["DynamicFuture", "DynamicPast"])
def test_replace_dynamic_variables_replaces_relative_datetime(token: str) -> None:
    result = ProcessVariablesService().resolve_dynamic_value(
        f"{{{{{token}}}}}:1d:yyyy-MM-dd"
    )
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", result)

def test_replace_dynamic_variables_generates_random_number() -> None:
    result = ProcessVariablesService().resolve_dynamic_value(
        "{{DynamicRandomNumber}}:8"
    )
    assert re.fullmatch(r"\d{8}", result)

def test_replace_dynamic_variables_generates_guid() -> None:
    result = ProcessVariablesService().resolve_dynamic_value("{{DynamicRandomGuid}}")
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        result,
    )

def test_replace_dynamic_variables_returns_empty_values_unchanged() -> None:
    assert ProcessVariablesService().resolve_dynamic_value(None) is None
    assert ProcessVariablesService().resolve_dynamic_value("") == ""

def test_replace_dynamic_variables_in_json_walks_nested_values() -> None:
    data = {
        "date": "{{DynamicToday}}",
        "nested": {
            "items": ["{{DynamicRandomGuid}}", 42, "plain text {{DynamicToday}}"],
        }
    }
    result = ProcessVariablesService().replace_dynamic_variables(data)

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", result["date"])
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        result["nested"]["items"][0],
    )
    assert result["nested"]["items"][1] == 42
    assert result["nested"]["items"][2] == "plain text {{DynamicToday}}"

def test_replace_dynamic_variables_in_json_handles_null_values() -> None:
    assert ProcessVariablesService().replace_dynamic_variables(None) is None
