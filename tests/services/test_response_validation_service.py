from http import HTTPStatus
import pytest
from apitest.response_validation_service import ResponseValidationService
from models.apitestify_requests import ResponseValidationVM
from models.apitestify_responses import ApiTestResponseVM

def build_response(content: dict, status: int = HTTPStatus.OK) -> ApiTestResponseVM:
    return ApiTestResponseVM(
        requestId="request-id",
        originalResponse=content,
        status=status,
        originalRequest={"method": "GET", "url": "https://my_fancy_api.com"},
    )

def validation(validation_type: str, value=None, error_message=None) -> ResponseValidationVM:
    return ResponseValidationVM(
        type=validation_type, 
        value=value, 
        errorMessage=error_message
    )

@pytest.fixture
def validation_service():
    return ResponseValidationService()
    
def test_validate_response_returns_no_failures_for_no_content(validation_service) -> None:
    failures = validation_service.validate_response(
        {"$.missing": validation("equals", "value")},
        build_response({}, HTTPStatus.NO_CONTENT),
    )
    assert failures == []

def test_validate_response_returns_no_failures_without_validations(validation_service) -> None:
    assert validation_service.validate_response({}, build_response({"id": 1})) == []

def test_validate_response_returns_no_failures_when_all_validations_pass(validation_service) -> None:
    failures = validation_service.validate_response(
        {
            "$.id": validation("equals", 42),
            "$.name": validation("equals", "ALICE"),
            "$.roles": validation("contains", "admin"),
            "$.roles.length": validation("equals", 2),
        },
        build_response({"id": 42, "name": "alice", "roles": ["admin", "reader"]}),
    )
    assert failures == []

def test_validate_response_reports_failed_validation(validation_service) -> None:
    failures = validation_service.validate_response(
        {"$.id": validation("equals", 42)},
        build_response({"id": 41}),
    )
    assert len(failures) == 1
    assert failures[0].key == "$.id"
    assert failures[0].type == "equals"
    assert failures[0].expectedValue == 42
    assert failures[0].actualValue == 41
    assert failures[0].message == "Validation failed for '$.id'. Expected: '42', but was: '41'."

def test_validate_response_preserves_custom_error_message(validation_service) -> None:
    failures = validation_service.validate_response(
        {"$.id": validation("equals", 42, "The id is invalid")},
        build_response({"id": 41}),
    )
    assert failures[0].message == "The id is invalid"

def test_validate_response_reports_missing_token(validation_service) -> None:
    failures = validation_service.validate_response(
        {"$.missing": validation("notempty")},
        build_response({"id": 1}),
    )
    assert failures[0].type == "SelectToken"
    assert failures[0].message == "JsonPath '$.missing' did not find a token."

def test_validate_response_reports_invalid_jsonpath(validation_service) -> None:
    failures = validation_service.validate_response(
        {"$[": validation("equals", 1)},
        build_response({"id": 1}),
    )

    assert failures[0].type == "SelectToken"
    assert failures[0].key == "$["
    assert "Error selecting token for '$['" in failures[0].message

def test_validate_response_reports_field_that_should_not_exist(validation_service) -> None:
    failures = validation_service.validate_response(
        {"$.secret": validation("fieldnotexists")},
        build_response({"secret": "value"}),
    )

    assert failures[0].expectedValue == "field should not exist"
    assert failures[0].actualValue == "field exists with value: value"

@pytest.mark.parametrize(
    ("validation_type", "actual", "expected", "is_valid"),
    [
        ("length", [1, 2], 2, True),
        ("notequals", "ready", "pending", True),
        ("notnull", "value", None, True),
        ("null", None, None, True),
        ("notempty", " value ", None, True),
        ("empty", "  ", None, True),
        ("notcontains", ["a"], "b", True),
        ("containsall", ["a", "b"], ["b", "a"], True),
        ("containspropertywithvalue", [{"id": 2}], {"id": 2}, True),
    ],
)
def test_validate_supports_validation_types(validation_type: str, actual, expected, is_valid: bool, validation_service) -> None:
    assert validation_service._validate(actual, validation(validation_type, expected)) is is_valid

def test_validate_raises_for_unsupported_validation_type(validation_service) -> None:
    with pytest.raises(ValueError, match="Validation type unsupported not supported"):
        validation_service._validate("value", validation("unsupported", "value"))
