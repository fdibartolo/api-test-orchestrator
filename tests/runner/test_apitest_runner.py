import json
import socket
from unittest.mock import patch

import requests

from models.apitestify_responses import ApiTestResponseVM, FailedValidationVM
from runner.apitest_runner import (
    _check_apitest_response,
    _create_parser,
    _find_json_files_recursively,
    _is_port_listening,
    _run_tests,
    _send_json_file_as_request,
    main,
)


def _create_response(request_id: str, is_validation_success: bool) -> ApiTestResponseVM:
    return ApiTestResponseVM(
        requestId=request_id,
        isValidationSuccess=is_validation_success,
        originalResponse={},
        status=200,
        originalRequest={},
    )


def test_port_defaults_to_8000() -> None:
    assert _create_parser().parse_args([]).port == 8000


def test_port_accepts_custom_value() -> None:
    assert _create_parser().parse_args(["--port", "9000"]).port == 9000


def test_main_checks_custom_port(tmp_path) -> None:
    missing_file = tmp_path / "missing.json"

    with patch("runner.apitest_runner._is_port_listening", return_value=True) as check:
        main(["--file", str(missing_file), "--port", "9000"])

    check.assert_called_once_with(port=9000)


def test_is_port_listening_returns_true_for_open_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        host, port = listener.getsockname()

        assert _is_port_listening(host, port)


def test_is_port_listening_returns_false_for_closed_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        host, port = listener.getsockname()

    assert not _is_port_listening(host, port)


def test_find_json_files_recursively_searches_recursively(tmp_path) -> None:
    nested_directory = tmp_path / "nested"
    nested_directory.mkdir()
    first_json = tmp_path / "first.json"
    second_json = nested_directory / "second.json"
    ignored_file = nested_directory / "ignored.txt"
    first_json.write_text("{}", encoding="utf-8")
    second_json.write_text("{}", encoding="utf-8")
    ignored_file.write_text("not json", encoding="utf-8")

    result = _find_json_files_recursively(str(tmp_path))

    assert set(result) == {str(first_json), str(second_json)}


def test_run_tests_collects_failed_files() -> None:
    with patch(
        "runner.apitest_runner._send_json_file_as_request",
        side_effect=[(True, None), (False, "validation failed")],
    ) as send_request:
        result = _run_tests(["passed.json", "failed.json"], 9000)

    assert result == [("failed.json", "validation failed")]
    assert send_request.call_args_list == [
        (("passed.json", 9000),),
        (("failed.json", 9000),),
    ]


def test_check_apitest_response_returns_success_when_all_requests_pass() -> None:
    responses = [
        _create_response("request-1", True),
        _create_response("request-2", True),
    ]

    assert _check_apitest_response(responses) == (True, None)


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

    success, failed_request = _check_apitest_response(responses)

    assert not success
    assert failed_request is not None
    failed_payload = json.loads(failed_request)
    assert failed_payload["requestId"] == "request-1"
    assert failed_payload["isValidationSuccess"] is False
    assert failed_payload["failedValidations"][0]["key"] == "status"


def test_send_json_file_as_request_returns_success_and_no_error(
    tmp_path, capsys
) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch("runner.apitest_runner.requests.post") as post:
        post.return_value.json.return_value = [
            {
                "requestId": "request-1",
                "isValidationSuccess": True,
                "originalResponse": {},
                "status": 200,
                "originalRequest": {},
            }
        ]

        result = _send_json_file_as_request(str(test_file), 8000)

    assert result == (True, None)
    output = capsys.readouterr().out
    assert "Running test suite" in output
    assert "PASSED" in output
    assert len(output.splitlines()) == 1


def test_send_json_file_as_request_returns_failure_and_error(tmp_path) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch(
        "runner.apitest_runner.requests.post",
        side_effect=requests.ConnectionError("connection refused"),
    ):
        success, error_message = _send_json_file_as_request(str(test_file), 8000)

    assert not success
    assert error_message is not None
    assert "connection refused" in error_message


def test_send_json_file_as_request_rejects_non_json_response(tmp_path, capsys) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch("runner.apitest_runner.requests.post") as post:
        post.return_value.json.side_effect = ValueError

        result = _send_json_file_as_request(str(test_file), 8000)

    assert result == (False, f"Non-JSON response received for {test_file}")
    output = capsys.readouterr().out
    assert "Running test suite" in output
    assert "FAILED" in output
    assert len(output.splitlines()) == 1


def test_send_json_file_as_request_rejects_invalid_response_schema(tmp_path) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch("runner.apitest_runner.requests.post") as post:
        post.return_value.json.return_value = {"success": True}

        success, error_message = _send_json_file_as_request(str(test_file), 8000)

    assert not success
    assert error_message is not None
    assert "Invalid ApiTest response" in error_message


def test_send_json_file_as_request_reports_validation_failures(
    tmp_path, capsys
) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch("runner.apitest_runner.requests.post") as post:
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

        result = _send_json_file_as_request(str(test_file), 8000)

    success, failed_request = result
    assert not success
    assert failed_request is not None
    failed_payload = json.loads(failed_request)
    assert failed_payload["requestId"] == "request-1"
    assert failed_payload["failedValidations"][0]["key"] == "status"
    assert "FAILED" in capsys.readouterr().out


def test_send_json_file_as_request_handles_missing_file(tmp_path, capsys) -> None:
    missing_file = tmp_path / "missing.json"

    result = _send_json_file_as_request(str(missing_file), 8000)

    assert result[0] is False
    assert result[1] is not None
    assert "Error reading" in result[1]
    output = capsys.readouterr().out
    assert "Running test suite" in output
    assert "FAILED" in output
    assert len(output.splitlines()) == 1


def test_main_stops_when_port_is_not_listening(capsys) -> None:
    with (
        patch("runner.apitest_runner._is_port_listening", return_value=False),
        patch("runner.apitest_runner._run_tests") as run_tests,
    ):
        main(["--port", "9000"])

    assert "not listening on port 9000" in capsys.readouterr().out
    run_tests.assert_not_called()


def test_main_reports_empty_directory(tmp_path, capsys) -> None:
    with patch("runner.apitest_runner._is_port_listening", return_value=True):
        main(["--file", str(tmp_path)])

    assert "No test files found" in capsys.readouterr().out


def test_main_runs_json_files_from_directory(tmp_path) -> None:
    nested_directory = tmp_path / "nested"
    nested_directory.mkdir()
    first_file = tmp_path / "first.json"
    second_file = nested_directory / "second.json"
    first_file.write_text("{}", encoding="utf-8")
    second_file.write_text("{}", encoding="utf-8")

    with (
        patch("runner.apitest_runner._is_port_listening", return_value=True),
        patch("runner.apitest_runner._run_tests", return_value=[]) as run_tests,
    ):
        main(["--file", str(tmp_path)])

    discovered_files = run_tests.call_args.args[0]
    assert set(discovered_files) == {str(first_file), str(second_file)}
    assert run_tests.call_args.args[1] == 8000


def test_main_runs_json_files_matching_wildcard(tmp_path) -> None:
    matching_file = tmp_path / "prefix-one.json"
    other_file = tmp_path / "other.json"
    matching_file.write_text("{}", encoding="utf-8")
    other_file.write_text("{}", encoding="utf-8")

    with (
        patch("runner.apitest_runner._is_port_listening", return_value=True),
        patch("runner.apitest_runner._run_tests", return_value=[]) as run_tests,
    ):
        main(["--file", str(tmp_path / "prefix*.json")])

    run_tests.assert_called_once_with([str(matching_file)], 8000)


def test_main_reports_no_files_matching_wildcard(tmp_path, capsys) -> None:
    with patch("runner.apitest_runner._is_port_listening", return_value=True):
        main(["--file", str(tmp_path / "prefix*.json")])

    assert "No test files found matching" in capsys.readouterr().out


def test_main_runs_single_file_and_reports_success(tmp_path, capsys) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with (
        patch("runner.apitest_runner._is_port_listening", return_value=True),
        patch("runner.apitest_runner._run_tests", return_value=[]) as run_tests,
    ):
        main(["--file", str(test_file), "--port", "9000"])

    run_tests.assert_called_once_with([str(test_file)], 9000)
    assert "All tests have passed" in capsys.readouterr().out


def test_main_reports_failed_tests(tmp_path, capsys) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")
    failures = [(str(test_file), "validation failed")]

    with (
        patch("runner.apitest_runner._is_port_listening", return_value=True),
        patch("runner.apitest_runner._run_tests", return_value=failures),
    ):
        main(["--file", str(test_file)])

    output = capsys.readouterr().out
    assert "Some tests have failed" in output
    assert "validation failed" in output


def test_main_reports_invalid_path(tmp_path, capsys) -> None:
    missing_file = tmp_path / "missing.json"

    with patch("runner.apitest_runner._is_port_listening", return_value=True):
        main(["--file", str(missing_file)])

    assert "is not a valid file or directory" in capsys.readouterr().out
