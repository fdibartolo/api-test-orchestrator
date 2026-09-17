from http import HTTPStatus
from typing import Any
from jsonpath_ng.ext import parse as jsonpath_parse
from models.apitestify_requests import ResponseValidationVM
from models.apitestify_responses import ApiTestResponseVM, FailedValidationVM


class ResponseValidationService:
    """Validate API responses against configured JSONPath-based rules."""

    def validate_response(
        self,
        content_validations: dict[str, ResponseValidationVM],
        api_test_response: ApiTestResponseVM,
    ) -> list[FailedValidationVM]:
        """Evaluate content validations against an API response.

        A response with status ``204 No Content`` or no configured validations
        produces no failures. Each validation key is treated as a JSONPath
        expression, with support for field existence, value, collection, and
        length checks.

        Args:
            content_validations: JSONPath expressions mapped to validation rules.
            api_test_response: Response content and status to validate.

        Returns:
            A list of validation failures. Invalid JSONPath expressions and
            missing tokens are reported as ``SelectToken`` failures.
        """
        json_content = api_test_response.originalResponse

        if api_test_response.status == HTTPStatus.NO_CONTENT:
            return []

        if not content_validations:
            return []

        result = []
        for key, validation in content_validations.items():
            try:
                token = self._select_token(json_content, key)
            except Exception as ex:
                result.append(
                    FailedValidationVM(
                        key=key,
                        type="SelectToken",
                        expectedValue=None,
                        actualValue=None,
                        message=f"Error selecting token for '{key}': {ex}",
                    )
                )
                continue

            if validation.type.lower() == "fieldnotexists":
                if token is not None:
                    error_message = validation.errorMessage or (
                        f"Validation failed for '{key}'. Field should not exist, but was found."
                    )
                    result.append(
                        FailedValidationVM(
                            key=key,
                            type="fieldnotexists",
                            expectedValue="field should not exist",
                            actualValue=f"field exists with value: {token}",
                            message=error_message,
                        )
                    )
                continue

            if key.lower().endswith(".length"):
                parent_path = key[: key.rfind(".")]
                parent_token = self._select_token(json_content, parent_path)
                actual_value: Any = str(self._get_length(parent_token))
                expected_value: Any = str(validation.value)
                is_valid = actual_value == expected_value
            elif token is None:
                result.append(
                    FailedValidationVM(
                        key=key,
                        type="SelectToken",
                        expectedValue=None,
                        actualValue=None,
                        message=f"JsonPath '{key}' did not find a token.",
                    )
                )
                continue
            else:
                actual_value = token
                expected_value = validation.value
                is_valid = self._validate(actual_value, validation)

            if not is_valid:
                error_message = validation.errorMessage or (
                    f"Validation failed for '{key}'. Expected: '{expected_value}', but was: '{actual_value}'."
                )
                result.append(
                    FailedValidationVM(
                        key=key,
                        type=validation.type,
                        expectedValue=expected_value,
                        actualValue=actual_value,
                        message=error_message,
                    )
                )

        return result

    def _select_token(self, json_content: Any, path: str) -> Any:
        matches = jsonpath_parse(path).find(json_content)
        return matches[0].value if matches else None

    def _validate(self, actual_value: Any, expected: ResponseValidationVM) -> bool:
        validation_type = expected.type.lower()

        if validation_type == "length":
            return self._validate_length(actual_value, expected.value)

        if validation_type == "equals":
            return self._validate_equals(actual_value, expected.value)
        if validation_type == "notequals":
            return self._validate_not_equals(actual_value, expected.value)
        if validation_type == "notnull":
            return actual_value is not None
        if validation_type == "null":
            return actual_value is None
        if validation_type == "notempty":
            return actual_value is not None and str(actual_value).strip() != ""
        if validation_type == "empty":
            return actual_value is None or str(actual_value).strip() == ""
        if validation_type == "contains":
            return self._validate_contains(actual_value, expected.value)
        if validation_type == "notcontains":
            return self._validate_not_contains(actual_value, expected.value)
        if validation_type == "containsall":
            return self._validate_contains_all(actual_value, expected.value)
        if validation_type == "containspropertywithvalue":
            if isinstance(expected.value, dict) and len(expected.value) == 1:
                prop_name, prop_value = next(iter(expected.value.items()))
                return self._validate_contains_property_with_value(
                    actual_value, prop_name, prop_value
                )
            raise ValueError(
                f"Invalid value for containspropertywithvalue validation: {expected.value}"
            )

        raise ValueError(f"Validation type {expected.type} not supported")

    def _validate_length(self, actual: Any, expected_value: Any) -> bool:
        if not isinstance(actual, (list, dict, str)):
            return False
        try:
            return len(actual) == int(expected_value)
        except TypeError, ValueError:
            return False

    def _validate_equals(self, actual: Any, expected_value: Any) -> bool:
        if actual is None and expected_value is None:
            return True
        if actual is None or expected_value is None:
            return False

        if isinstance(actual, str) or isinstance(expected_value, str):
            return str(actual).lower() == str(expected_value).lower()

        if isinstance(actual, bool):
            return actual == bool(expected_value)

        if isinstance(actual, (int, float)):
            try:
                return float(actual) == float(expected_value)
            except TypeError, ValueError:
                return False

        return actual == expected_value

    def _validate_not_equals(self, actual: Any, expected_value: Any) -> bool:
        return not self._validate_equals(actual, expected_value)

    def _validate_contains(self, actual: Any, expected_value: Any) -> bool:
        if isinstance(actual, list):
            return any(item == expected_value for item in actual)
        if isinstance(actual, str):
            return str(expected_value).lower() in actual.lower()
        return False

    def _validate_not_contains(self, actual: Any, expected_value: Any) -> bool:
        if isinstance(actual, list):
            return not any(item == expected_value for item in actual)
        return True

    def _validate_contains_all(self, actual: Any, expected_value: Any) -> bool:
        if isinstance(actual, list) and isinstance(expected_value, list):
            return all(any(item == ev for item in actual) for ev in expected_value)
        return False

    def _validate_contains_property_with_value(
        self, actual: Any, property_name: str, property_value: Any
    ) -> bool:
        if isinstance(actual, list):
            return any(
                isinstance(item, dict) and item.get(property_name) == property_value
                for item in actual
            )
        return False

    def _get_length(self, token: Any) -> int:
        if isinstance(token, (list, dict, str)):
            return len(token)
        return 0  # unsupported types default to 0
