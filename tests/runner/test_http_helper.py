import socket
from unittest.mock import patch

import requests

from models.apitest_responses import ApiTestResponseVM, FailedValidationVM
from runner.http_helper import HttpHelper


def _create_response(request_id: str, is_validation_success: bool) -> ApiTestResponseVM:
    return ApiTestResponseVM(
        requestId=request_id,
        isValidationSuccess=is_validation_success,
        originalResponse={},
        status=200,
        originalRequest={},
    )


def test_check_apitest_response_returns_success_when_all_requests_pass() -> None:
    responses = [
        _create_response("request-1", True),
        _create_response("request-2", True),
    ]

    assert HttpHelper._check_apitest_response(responses) == (True, None)


def test_check_apitest_response_returns_first_failed_request_as_json() -> None:
    first_failure = _create_response("request-1", False)
    first_failure.failedValidations.append(
        FailedValidationVM(
            key="status",
            type="equals",
            expectedValue=200,
            actualValue=500,
        )
    )
    responses = [
        first_failure,
        _create_response("request-2", True),
        _create_response("request-3", False),
    ]

    success, failed_request = HttpHelper._check_apitest_response(responses)

    assert not success
    assert failed_request is not None
    assert failed_request.requestId == "request-1"
    assert failed_request.isValidationSuccess is False
    assert failed_request.failedValidations[0].key == "status"


def test_is_port_listening_returns_true_for_open_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        host, port = listener.getsockname()

        assert HttpHelper.is_port_listening(host, port)


def test_is_port_listening_returns_false_for_closed_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        host, port = listener.getsockname()

    assert not HttpHelper.is_port_listening(host, port)


def test_send_json_file_as_request_returns_success_and_no_error(
    tmp_path, capsys
) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch("runner.http_helper.requests.post") as post:
        post.return_value.json.return_value = [
            {
                "requestId": "request-1",
                "isValidationSuccess": True,
                "originalResponse": {},
                "status": 200,
                "originalRequest": {},
            }
        ]

        result = HttpHelper.send_json_file_as_request(str(test_file), 8000)

    assert result == (True, None)
    output = capsys.readouterr().out
    assert "Running test suite" in output
    assert "PASSED" in output
    assert len(output.splitlines()) == 1


def test_send_json_file_as_request_returns_failure_and_error(tmp_path) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch(
        "runner.http_helper.requests.post",
        side_effect=requests.ConnectionError("connection refused"),
    ):
        success, error_message = HttpHelper.send_json_file_as_request(
            str(test_file), 8000
        )

    assert not success
    assert error_message is not None
    assert "connection refused" in error_message


def test_send_json_file_as_request_rejects_non_json_response(tmp_path, capsys) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch("runner.http_helper.requests.post") as post:
        post.return_value.json.side_effect = ValueError

        result = HttpHelper.send_json_file_as_request(str(test_file), 8000)

    assert result == (False, f"Non-JSON response received for {test_file}")
    output = capsys.readouterr().out
    assert "Running test suite" in output
    assert "FAILED" in output
    assert len(output.splitlines()) == 1


def test_send_json_file_as_request_rejects_invalid_response_schema(tmp_path) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch("runner.http_helper.requests.post") as post:
        post.return_value.json.return_value = {"success": True}

        success, error_message = HttpHelper.send_json_file_as_request(
            str(test_file), 8000
        )

    assert not success
    assert error_message is not None
    assert "Invalid ApiTest response" in error_message


def test_send_json_file_as_request_reports_validation_failures(
    tmp_path, capsys
) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch("runner.http_helper.requests.post") as post:
        post.return_value.json.return_value = [
            {
                "requestId": "request-1",
                "isValidationSuccess": False,
                "failedValidations": [
                    {
                        "key": "status",
                        "type": "equals",
                        "expectedValue": 200,
                        "actualValue": 500,
                    }
                ],
                "originalResponse": {},
                "status": 500,
                "originalRequest": {},
            }
        ]

        result = HttpHelper.send_json_file_as_request(str(test_file), 8000)

    success, failed_request = result
    assert not success
    assert failed_request is not None
    assert failed_request.requestId == "request-1"
    assert failed_request.failedValidations[0].key == "status"
    assert "FAILED" in capsys.readouterr().out


def test_send_json_file_as_request_handles_missing_file(tmp_path, capsys) -> None:
    missing_file = tmp_path / "missing.json"

    result = HttpHelper.send_json_file_as_request(str(missing_file), 8000)

    assert result[0] is False
    assert result[1] is not None
    assert "Error reading" in result[1]
    output = capsys.readouterr().out
    assert "Running test suite" in output
    assert "FAILED" in output
    assert len(output.splitlines()) == 1
