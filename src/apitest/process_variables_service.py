import json
import re
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from jsonpath_ng.ext import parse as jsonpath_parse
from models.apitestify_requests import ApiTestRequestVM
from models.apitestify_responses import ApiTestResponseVM, FailedValidationVM

_VARIABLE_PATTERN = re.compile(r"#\{(.+?)\}#")
_DYNAMIC_TODAY_PATTERN = re.compile(r"\{\{DynamicToday\}\}(?::([^:{}]+))?")
_DYNAMIC_NOW_PATTERN = re.compile(r"\{\{DynamicNow\}\}(?::([^:{}]+))?")
_DYNAMIC_FUTURE_PATTERN = re.compile(r"\{\{DynamicFuture\}\}:(\d+)([dhm])(?::([^:{}]+))?")
_DYNAMIC_PAST_PATTERN = re.compile(r"\{\{DynamicPast\}\}:(\d+)([dhm])(?::([^:{}]+))?")
_DYNAMIC_RANDOM_NUMBER_PATTERN = re.compile(r"\{\{DynamicRandomNumber\}\}:(\d+)")
_DYNAMIC_RANDOM_GUID_PATTERN = re.compile(r"\{\{DynamicRandomGuid\}\}")

class ProcessVariablesService:
    def replace_variables(self, variables: dict[str, str], api_test_request: ApiTestRequestVM) -> None:
        if not variables:
            return

        for section in ("headers", "cookies", "queryParams", "variables"):
            values = getattr(api_test_request, section)
            if values is not None:
                setattr(api_test_request, section, {
                    key: self._replace_value(value, variables) for key, value in values.items()
                })

        api_test_request.url = self._replace_value(api_test_request.url, variables)

        if api_test_request.jsonBody is not None:
            serialized_body = json.dumps(api_test_request.jsonBody, separators=(",", ":"))
            api_test_request.jsonBody = json.loads(self._replace_value(serialized_body, variables))

        validations = api_test_request.expectedResponse.contentValidations
        if validations is not None:
            updated_validations = {}
            for key, validation in validations.items():
                if isinstance(validation.value, str):
                    validation.value = self._replace_value(validation.value, variables)
                if validation.errorMessage:
                    validation.errorMessage = self._replace_value(validation.errorMessage, variables)
                updated_key = self._replace_value(key, variables)
                updated_validations[updated_key] = validation
            api_test_request.expectedResponse.contentValidations = updated_validations

    def _replace_value(self, value: Any, variables: dict[str, str]) -> Any:
        if not isinstance(value, str):
            return value
        return _VARIABLE_PATTERN.sub(lambda match: variables.get(match.group(1), match.group(0)), value)

    def resolve_request_variables(self, variables: dict[str, str], response: ApiTestResponseVM) -> tuple[dict[str, Any], list[FailedValidationVM]]:
        if response.originalResponse is None:
            raise ValueError("OriginalResponse is null")

        variables_resolved: dict[str, Any] = {}
        failed_validations: list[FailedValidationVM] = []

        if not variables:
            return variables_resolved, failed_validations

        for key, json_path in variables.items():
            try:
                matches = jsonpath_parse(json_path).find(response.originalResponse)
                if matches:
                    variables_resolved[key] = matches[0].value
                    continue

                failed_validations.append(FailedValidationVM(
                    key=key,
                    type="SelectToken",
                    expectedValue=json_path,
                    actualValue=None,
                    message=f"JsonPath '{json_path}' did not find any value for variable '{key}'."
                ))
            except Exception as ex:
                failed_validations.append(FailedValidationVM(
                    key=key,
                    type="SelectToken",
                    expectedValue=json_path,
                    actualValue=None,
                    message=f"Error processing variable '{key}' with JsonPath '{json_path}': {ex}"
                ))

        return variables_resolved, failed_validations

    def replace_dynamic_variables(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self.replace_dynamic_variables(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.replace_dynamic_variables(item) for item in value]
        if isinstance(value, str) and value.startswith("{{"):
            return self.resolve_dynamic_value(value)
        return value

    def resolve_dynamic_value(self, value: str | None) -> str | None:
        if not value:
            return value

        utc_now = datetime.now(timezone.utc)
        today_match = _DYNAMIC_TODAY_PATTERN.search(value)
        if today_match:
            date_format = today_match.group(1) or "yyyy-MM-dd"
            value = value.replace(
                today_match.group(0),
                self._format_dynamic_datetime(utc_now, date_format),
            )

        now_match = _DYNAMIC_NOW_PATTERN.search(value)
        if now_match:
            date_format = now_match.group(1) or "u"
            value = value.replace(
                now_match.group(0),
                self._format_dynamic_datetime(utc_now, date_format),
            )

        for pattern, sign in ((_DYNAMIC_FUTURE_PATTERN, 1), (_DYNAMIC_PAST_PATTERN, -1)):
            date_match = pattern.search(value)
            if date_match:
                amount = int(date_match.group(1)) * sign
                unit = date_match.group(2)
                date_format = date_match.group(3) or "u"
                delta = {
                    "d": timedelta(days=amount),
                    "h": timedelta(hours=amount),
                    "m": timedelta(minutes=amount),
                }[unit]
                value = value.replace(
                    date_match.group(0),
                    self._format_dynamic_datetime(utc_now + delta, date_format),
                )

        random_number_match = _DYNAMIC_RANDOM_NUMBER_PATTERN.search(value)
        if random_number_match:
            digits = int(random_number_match.group(1))
            minimum = 10 ** (digits - 1)
            maximum = 10 ** digits - 1
            return str(random.randint(minimum, maximum))

        if _DYNAMIC_RANDOM_GUID_PATTERN.search(value):
            return str(uuid.uuid4())

        return value

    def _format_dynamic_datetime(self, value: datetime, date_format: str) -> str:
        if date_format == "u":
            return value.strftime("%Y-%m-%d %H:%M:%SZ")

        python_format = date_format
        replacements = (
            ("yyyy", "%Y"),
            ("yy", "%y"),
            ("MM", "%m"),
            ("dd", "%d"),
            ("HH", "%H"),
            ("mm", "%M"),
            ("ss", "%S"),
        )
        for input_token, python_token in replacements:
            python_format = python_format.replace(input_token, python_token)
        return value.strftime(python_format)
