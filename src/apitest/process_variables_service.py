import json
import re
from typing import Any

from jsonpath_ng.ext import parse as jsonpath_parse
from models.apitestify_requests import ApiTestRequestVM
from models.apitestify_responses import ApiTestResponseVM, FailedValidationVM

_VARIABLE_PATTERN = re.compile(r"#\{(.+?)\}#")

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
