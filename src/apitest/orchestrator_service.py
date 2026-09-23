import json
from http import HTTPStatus
from time import sleep

import requests

from models.apitestify_requests import ApiTestRequestVMList
from models.apitestify_responses import ApiTestResponseVM

from .auth_service import AuthService
from .dynamic_vars_evaluator_service import DynamicVarsEvaluatorService
from .response_validation_service import ResponseValidationService
from .vars_evaluator_service import VariablesEvaluatorService


class OrchestratorService:
    """Coordinate API test execution, response validation, and variable storage."""

    def __init__(
        self,
        auth_service: AuthService,
        response_validation_service: ResponseValidationService,
        variables_evaluator_service: VariablesEvaluatorService,
        dynamic_vars_evaluator_service: DynamicVarsEvaluatorService,
        secrets: dict[str, str],
    ):
        self.auth_service = auth_service
        self.response_validation_service = response_validation_service
        self.vars_evaluator_service = variables_evaluator_service
        self.dynamic_vars_evaluator_service = dynamic_vars_evaluator_service
        self.secrets = secrets

    def validate(self, request: ApiTestRequestVMList):
        """Execute and validate all API test requests in a request list.

        Authentication, static variables, and dynamic variables are resolved
        before each HTTP request is sent. Each response is then checked against
        its expected status and content validations, and any extracted request
        variables are added to the shared global variables. Processing stops
        after the first response that fails validation.

        Args:
            request: Authentication settings, global variables, and API test
                requests to execute.

        Returns:
            A list of response models containing execution results and any
            validation failures, in request order.
        """
        if request.authenticationParams is not None:
            self.vars_evaluator_service.replace_secrets(
                self.secrets, request.authenticationParams
            )
            auth_token = self.auth_service.get_auth_token(request.authenticationParams)
        else:
            auth_token = None

        responses = []
        for api_test_request in request.apiTestRequests:
            self.vars_evaluator_service.replace_variables(
                request.globalVariables, api_test_request
            )

            api_test_request.jsonBody = (
                self.dynamic_vars_evaluator_service.replace_dynamic_variables(
                    api_test_request.jsonBody
                )
            )
            api_test_request.queryParams = (
                self.dynamic_vars_evaluator_service.replace_dynamic_variables(
                    api_test_request.queryParams
                )
            )

            request_auth_token = auth_token
            if api_test_request.authenticationParams is not None:
                self.vars_evaluator_service.replace_secrets(
                    self.secrets, api_test_request.authenticationParams
                )
                request_auth_token = self.auth_service.get_auth_token(
                    api_test_request.authenticationParams
                )

            kwargs = api_test_request.build_request_kwargs(request_auth_token)
            response = requests.request(**kwargs)

            api_test_response = ApiTestResponseVM(
                requestId=api_test_request.id,
                status=response.status_code,
                originalResponse=self._get_original_response(response),
                originalRequest={
                    "url": api_test_request.url,
                    "body": api_test_request.jsonBody,
                },
            )

            if api_test_request.expectedResponse.status != response.status_code:
                api_test_response.add_failure_for_status_code(
                    api_test_request.expectedResponse.status, response.status_code
                )

            failed_validations = self.response_validation_service.validate_response(
                api_test_request.expectedResponse.contentValidations, api_test_response
            )
            api_test_response.failedValidations += failed_validations

            request_variables, failures = (
                self.vars_evaluator_service.resolve_request_variables(
                    api_test_request.variables, api_test_response
                )
            )
            api_test_response.storedVariables = request_variables
            api_test_response.failedValidations += failures

            request.globalVariables.update(request_variables)

            api_test_response.isValidationSuccess = (
                api_test_response.failedValidations == []
            )
            responses.append(api_test_response)

            if not api_test_response.isValidationSuccess:
                break

            if api_test_request.waitForEventPropagation is not None:
                sleep(float(api_test_request.waitForEventPropagation))

        return responses

    def _get_original_response(self, response: requests.Response):
        if response.status_code == HTTPStatus.NO_CONTENT:
            return {}

        content_type = response.headers.get("Content-Type") or ""
        if (
            "application/json" in content_type
            or "application/vnd.api+json" in content_type
        ):
            original_response = response.json()
            return (
                original_response
                if not isinstance(original_response, list)
                else {"data": original_response}
            )

        try:
            original_response = json.loads(response.text)
            return (
                original_response
                if not isinstance(original_response, list)
                else {"data": original_response}
            )
        except json.JSONDecodeError as error:
            return {
                "error": "Response body is not valid JSON",
                "text": response.text,
                "details": str(error),
            }
