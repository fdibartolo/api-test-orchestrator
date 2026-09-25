import argparse

from models.apitestify_responses import ApiTestResponseVM
from runner.constants import GREEN, RED, RESET, YELLOW
from runner.file_helper import FileHelper
from runner.http_helper import HttpHelper


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="API Test Orchestrator")
    parser.add_argument(
        "-f",
        "--file",
        metavar="PATH",
        nargs="+",
        default=["."],
        help="Path(s)/directory/wildcard pattern(s) containing the API test scripts to run",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="API Test Orchestrator tcp port (default: 8000)",
    )
    return parser


def _run_tests(
    files: list[str], port: int
) -> list[tuple[str, str | ApiTestResponseVM]]:
    failed_tests = []
    for file in files:
        success, error = HttpHelper.send_json_file_as_request(file, port)
        if not success:
            failed_tests.append((file, error))
    return failed_tests


def _format_failed_tests(
    failed_tests: list[tuple[str, str | ApiTestResponseVM]],
) -> str:
    formatted_entries = []
    for file_path, error in failed_tests:
        pretty_error = (
            error.model_dump_json(indent=2)
            if isinstance(error, ApiTestResponseVM)
            else error
        )
        formatted_entries.append(
            f" ---------- File: {file_path} ----------\n\n{pretty_error}"
        )
    return "\n\n".join(formatted_entries)


def main(argv: list[str] | None = None) -> None:
    args = _create_parser().parse_args(argv)

    if not HttpHelper.is_port_listening(port=args.port):
        print(
            f"{RED} ✗ API Test Orchestrator is not listening on port {args.port}\n   Use '--port <PORT>{RED}' to specify a different one{RESET}"
        )
        return

    files: list[str] = []
    for path in args.file:
        resolved = FileHelper.resolve_files(path)
        if resolved is None:
            print(f"{RED} ✗ '{path}' is not a valid file or directory{RESET}")
            return
        if not resolved:
            print(f"{YELLOW} ✗ No test files found matching '{path}'{RESET}")
            return
        files.extend(resolved)
    files = list(dict.fromkeys(files))

    failed_tests = _run_tests(files, args.port)
    if not failed_tests:
        print(f"{GREEN} ✓ All tests have passed!{RESET}")
    else:
        print(
            f"{RED} ✗ Some tests have failed:\n\n{_format_failed_tests(failed_tests)}{RESET}"
        )
