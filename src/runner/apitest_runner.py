import argparse
import glob
import socket
from pathlib import Path

import requests
from pydantic import TypeAdapter, ValidationError

from models.apitestify_responses import ApiTestResponseVM

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[00m"
DEFAULT_HOST = "127.0.0.1"
API_TEST_RESPONSES_ADAPTER = TypeAdapter(list[ApiTestResponseVM])


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


def _is_port_listening(
    host: str = DEFAULT_HOST, port: int = 8000, timeout: float = 1.0
) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _find_json_files_recursively(dir: str) -> list[str]:
    return [str(json_file) for json_file in Path(dir).rglob("*.json")]


def _is_glob_pattern(path: str) -> bool:
    return any(char in path for char in ("*", "?", "["))


def _resolve_files(path: str) -> list[str] | None:
    if _is_glob_pattern(path):
        return sorted(glob.glob(path, recursive=True))
    if Path(path).is_dir():
        return _find_json_files_recursively(path)
    if Path(path).is_file():
        return [path]
    return None


def _run_tests(files: list[str], port: int) -> list[str]:
    failed_tests = []
    for file in files:
        success, error_message = _send_json_file_as_request(file, port)
        if not success:
            failed_tests.append((file, error_message))
    return failed_tests


def _send_json_file_as_request(file_path: str, port: int) -> tuple[bool, str | None]:
    try:
        print(
            f"• Running test suite {YELLOW}{file_path}{RESET}...",
            end=" ",
            flush=True,
        )

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        response = requests.post(
            f"http://{DEFAULT_HOST}:{port}/validate",
            data=content,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        try:
            response_json = response.json()
        except ValueError:
            print(f"{RED}✗ FAILED{RESET}")
            return False, f"Non-JSON response received for {file_path}"

        try:
            response_payload = API_TEST_RESPONSES_ADAPTER.validate_python(response_json)
        except ValidationError as error:
            print(f"{RED}✗ FAILED{RESET}")
            return False, f"Invalid ApiTest response for {file_path}: {error}"

        valid, failed_request = _check_apitest_response(response_payload)
        if not valid:
            print(f"{RED}✗ FAILED{RESET}")
            return False, failed_request

        print(f"{GREEN}✓ PASSED{RESET}")
        return True, None

    except FileNotFoundError as error:
        print(f"{RED}✗ FAILED{RESET}")
        return False, f"Error reading {file_path}: {error}"
    except requests.RequestException as error:
        print(f"{RED}✗ FAILED{RESET}")
        return False, f"HTTP request failed for {file_path}: {error}"


def _check_apitest_response(
    response: list[ApiTestResponseVM],
) -> tuple[bool, str | None]:
    failed_requests = [r for r in response if not r.isValidationSuccess]

    if failed_requests:
        return False, failed_requests[0].model_dump_json()
    return True, None


def main(argv: list[str] | None = None) -> None:
    args = _create_parser().parse_args(argv)

    if not _is_port_listening(port=args.port):
        print(
            f"{RED} ✗ API Test Orchestrator is not listening on port {args.port}\n   Use '--port <PORT>{RED}' to specify a different one{RESET}"
        )
        return

    files: list[str] = []
    for path in args.file:
        resolved = _resolve_files(path)
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
        print(f"{RED} ✗ Some tests have failed:\n\n{failed_tests}{RESET}")
