from unittest.mock import patch

from runner.apitest_runner import (
    _create_parser,
    _run_tests,
    main,
)


def test_port_defaults_to_8000() -> None:
    assert _create_parser().parse_args([]).port == 8000


def test_port_accepts_custom_value() -> None:
    assert _create_parser().parse_args(["--port", "9000"]).port == 9000


def test_main_checks_custom_port(tmp_path) -> None:
    missing_file = tmp_path / "missing.json"

    with patch(
        "runner.apitest_runner.HttpHelper.is_port_listening", return_value=True
    ) as check:
        main(["--file", str(missing_file), "--port", "9000"])

    check.assert_called_once_with(port=9000)


def test_run_tests_collects_failed_files() -> None:
    with patch(
        "runner.apitest_runner.HttpHelper.send_json_file_as_request",
        side_effect=[(True, None), (False, "validation failed")],
    ) as send_request:
        result = _run_tests(["passed.json", "failed.json"], 9000)

    assert result == [("failed.json", "validation failed")]
    assert send_request.call_args_list == [
        (("passed.json", 9000),),
        (("failed.json", 9000),),
    ]


def test_main_stops_when_port_is_not_listening(capsys) -> None:
    with (
        patch("runner.apitest_runner.HttpHelper.is_port_listening", return_value=False),
        patch("runner.apitest_runner._run_tests") as run_tests,
    ):
        main(["--port", "9000"])

    assert "not listening on port 9000" in capsys.readouterr().out
    run_tests.assert_not_called()


def test_main_reports_empty_directory(tmp_path, capsys) -> None:
    with patch("runner.apitest_runner.HttpHelper.is_port_listening", return_value=True):
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
        patch("runner.apitest_runner.HttpHelper.is_port_listening", return_value=True),
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
        patch("runner.apitest_runner.HttpHelper.is_port_listening", return_value=True),
        patch("runner.apitest_runner._run_tests", return_value=[]) as run_tests,
    ):
        main(["--file", str(tmp_path / "prefix*.json")])

    run_tests.assert_called_once_with([str(matching_file)], 8000)


def test_main_reports_no_files_matching_wildcard(tmp_path, capsys) -> None:
    with patch("runner.apitest_runner.HttpHelper.is_port_listening", return_value=True):
        main(["--file", str(tmp_path / "prefix*.json")])

    assert "No test files found matching" in capsys.readouterr().out


def test_main_runs_single_file_and_reports_success(tmp_path, capsys) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with (
        patch("runner.apitest_runner.HttpHelper.is_port_listening", return_value=True),
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
        patch("runner.apitest_runner.HttpHelper.is_port_listening", return_value=True),
        patch("runner.apitest_runner._run_tests", return_value=failures),
    ):
        main(["--file", str(test_file)])

    output = capsys.readouterr().out
    assert "Some tests have failed" in output
    assert "validation failed" in output


def test_main_reports_invalid_path(tmp_path, capsys) -> None:
    missing_file = tmp_path / "missing.json"

    with patch("runner.apitest_runner.HttpHelper.is_port_listening", return_value=True):
        main(["--file", str(missing_file)])

    assert "is not a valid file or directory" in capsys.readouterr().out
