import requests
from models.apitestify_requests import ApiTestRequestVMList
from models.apitestify_responses import ApiTestResponseVM
from .auth_service import AuthService
from .process_variables_service import ProcessVariablesService
from .response_validation_service import ResponseValidationService

class OrchestratorService:
    def __init__(
        self,
        auth_service: AuthService,
        response_validation_service: ResponseValidationService,
        process_variables_service: ProcessVariablesService
    ):
        self.auth_service = auth_service
        self.response_validation_service = response_validation_service
        self.process_variables_service = process_variables_service

    def validate(self, request: ApiTestRequestVMList):
        auth_token = self.auth_service.get_auth_token(request.authenticationParams)

        responses = []
        for api_test_request in request.apiTestRequests:
            self.process_variables_service.replace_variables(request.globalVariables, api_test_request)

            api_test_request.jsonBody = self.process_variables_service.replace_dynamic_variables(
                api_test_request.jsonBody
            )
            api_test_request.queryParams = self.process_variables_service.replace_dynamic_variables(
                api_test_request.queryParams
            )
            
            request_auth_token = auth_token
            if api_test_request.authenticationParams is not None:
                request_auth_token = self.auth_service.get_auth_token(api_test_request.authenticationParams)

            kwargs = api_test_request.build_request_kwargs(request_auth_token)
            response = requests.request(**kwargs)

            api_test_response = ApiTestResponseVM(
                requestId=api_test_request.id,
                status=response.status_code,
                originalResponse=response.json() if "application/json" in (response.headers.get("Content-Type") or "") else response.text,
                originalRequest={
                    "url": api_test_request.url,
                    "jsonBody": api_test_request.jsonBody,
                }
            )

            if api_test_request.expectedResponse.status != response.status_code:
                api_test_response.add_failure_for_status_code(api_test_request.expectedResponse.status, response.status_code)

            failed_validations = self.response_validation_service.validate_response(
                api_test_request.expectedResponse.contentValidations,
                api_test_response
            )
            api_test_response.failedValidations += failed_validations

            request_variables, failures = self.process_variables_service.resolve_request_variables(
                api_test_request.variables, api_test_response)
            api_test_response.storedVariables = request_variables
            api_test_response.failedValidations += failures

            request.globalVariables.update(request_variables)
            
            api_test_response.isValidationSuccess = api_test_response.failedValidations == []
            responses.append(api_test_response)

        return responses
    