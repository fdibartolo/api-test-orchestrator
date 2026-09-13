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
