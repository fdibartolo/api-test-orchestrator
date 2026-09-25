import socket

import requests
from pydantic import TypeAdapter, ValidationError

from models.apitestify_responses import ApiTestResponseVM
from runner.constants import GREEN, RED, RESET, YELLOW

DEFAULT_HOST = "127.0.0.1"
API_TEST_RESPONSES_ADAPTER = TypeAdapter(list[ApiTestResponseVM])


class HttpHelper:
    @staticmethod
    def is_port_listening(
        host: str = DEFAULT_HOST, port: int = 8000, timeout: float = 1.0
    ) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    @staticmethod
    def send_json_file_as_request(
        file_path: str, port: int
    ) -> tuple[bool, str | ApiTestResponseVM | None]:
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
                response_payload = API_TEST_RESPONSES_ADAPTER.validate_python(
                    response_json
                )
            except ValidationError as error:
                print(f"{RED}✗ FAILED{RESET}")
                return False, f"Invalid ApiTest response for {file_path}: {error}"

            valid, failed_request = HttpHelper._check_apitest_response(response_payload)
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
    ) -> tuple[bool, ApiTestResponseVM | None]:
        failed_requests = [r for r in response if not r.isValidationSuccess]

        if failed_requests:
            # by design, no more than one failed request can be present, so [0] is safe
            return False, failed_requests[0]
        return True, None
