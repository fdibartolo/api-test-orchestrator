from models.apitestify_requests import ApiTestRequestVM, ExpectedResponseVM


def test_expected_response_default_status_code() -> None:
    expected_response = ExpectedResponseVM()
    assert expected_response.status == 200


def test_api_test_request_default_expected_response_status_code() -> None:
    request = ApiTestRequestVM(
        id="id",
        url="https://api.example.com/test",
        method="GET",
    )
    assert request.expectedResponse is not None
    assert request.expectedResponse.status == 200


def test_api_test_request_from_dict_default_expected_response_status_code() -> None:
    payload = {
        "id": "id",
        "url": "https://api.example.com/items",
        "method": "POST",
    }
    request = ApiTestRequestVM.model_validate(payload)
    assert request.expectedResponse.status == 200


def test_api_test_request_explicit_expected_response_status_code() -> None:
    request = ApiTestRequestVM(
        id="id",
        url="https://api.example.com/test",
        method="GET",
        expectedResponse=ExpectedResponseVM(status=201),
    )
    assert request.expectedResponse.status == 201


def test_build_request_kwargs_with_auth_token() -> None:
    request = ApiTestRequestVM(
        id="req-1",
        url="https://api.example.com/data",
        method="POST",
        headers={"Content-Type": "application/json"},
        cookies={"session": "abc"},
        queryParams={"page": "1"},
        jsonBody={"key": "value"},
    )
    kwargs = request.build_request_kwargs("secret-token")
    assert kwargs == {
        "method": "POST",
        "url": "https://api.example.com/data",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer secret-token",
        },
        "cookies": {"session": "abc"},
        "params": {"page": "1"},
        "json": {"key": "value"},
    }


def test_build_request_kwargs_without_auth_token() -> None:
    request = ApiTestRequestVM(
        id="req-2",
        url="https://api.example.com/public",
        method="GET",
    )
    kwargs = request.build_request_kwargs(None)
    assert kwargs == {
        "method": "GET",
        "url": "https://api.example.com/public",
        "headers": {},
        "cookies": None,
        "params": None,
        "json": None,
    }
