from models.apitestify_responses import ApiTestResponseVM, FailedValidationVM


def test_failed_validation_default_message_when_not_set() -> None:
    failure = FailedValidationVM(
        key="Header.Content-Type",
        type="equals",
        expectedValue="application/json",
        actualValue="text/plain",
    )
    expected_msg = (
        "Validation failed for 'Header.Content-Type'. "
        "Expected: 'application/json', but was: 'text/plain'."
    )
    assert failure.message == expected_msg


def test_failed_validation_custom_message_preserved() -> None:
    custom_msg = "Custom validation error"
    failure = FailedValidationVM(
        key="Body.id",
        type="equals",
        expectedValue=123,
        actualValue=456,
        message=custom_msg,
    )
    assert failure.message == custom_msg


def test_add_failure_for_status_code_appends_failed_validation() -> None:
    response = ApiTestResponseVM(
        requestId="req-123",
        isValidationSuccess=False,
        originalResponse={"status": 404},
        status=404,
        originalRequest={"url": "https://api.example.com/test", "method": "GET"},
    )

    response.add_failure_for_status_code(expected=200, actual=404)

    assert len(response.failedValidations) == 1
    failure = response.failedValidations[0]
    assert isinstance(failure, FailedValidationVM)
    assert failure.key == "Status Code"
    assert failure.type == "equals"
    assert failure.expectedValue == "200"
    assert failure.actualValue == "404"
    assert failure.message == "Expected status code: 200, but received: 404"


def test_add_failure_for_status_code_appends_to_existing_failures() -> None:
    existing_failure = FailedValidationVM(
        key="Header",
        type="equals",
        expectedValue="application/json",
        actualValue="text/html",
    )
    response = ApiTestResponseVM(
        requestId="req-456",
        isValidationSuccess=False,
        failedValidations=[existing_failure],
        originalResponse={"status": 500},
        status=500,
        originalRequest={"url": "https://api.example.com/items", "method": "POST"},
    )

    response.add_failure_for_status_code(expected=200, actual=500)

    assert len(response.failedValidations) == 2
    assert response.failedValidations[0] == existing_failure
    status_failure = response.failedValidations[1]
    assert status_failure.key == "Status Code"
    assert status_failure.expectedValue == "200"
    assert status_failure.actualValue == "500"
    assert status_failure.message == "Expected status code: 200, but received: 500"
