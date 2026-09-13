import requests
from models.apitestify_requests import ApiTestRequestVM, ApiTestRequestVMList
from models.apitestify_responses import ApiTestResponseVM
from .auth_service import AuthService

class OrchestratorService:
    def __init__(self):
        self.auth_service = AuthService()

    def __build_request_kwargs(self, api_test_request: ApiTestRequestVM, auth_token: str):
        headers = dict(api_test_request.headers) if api_test_request.headers else {}
        headers.setdefault("Authorization", f"Bearer {auth_token}")

        # TODO: add referenceFile prop - multipart
        return {
            "method": api_test_request.method,
            "url": api_test_request.url,
            "headers": headers,
            "cookies": api_test_request.cookies,
            "params": api_test_request.queryParams,
            "json": api_test_request.jsonBody,
        }

    def validate(self, request: ApiTestRequestVMList):
        auth_token = self.auth_service.get_auth_token(request.authenticationParams)

        # TODO: replace global vars into requests

        responses = []
        for api_test_request in request.apiTestRequests:
            # TODO: replace vars
            # TODO: evaluate dynamic expressions
            
            request_auth_token = auth_token
            if api_test_request.authenticationParams is not None:
                request_auth_token = self.auth_service.get_auth_token(api_test_request.authenticationParams)

            kwargs = self.__build_request_kwargs(api_test_request, request_auth_token)
            response = requests.request(**kwargs)

            api_test_response = ApiTestResponseVM(
                requestId=api_test_request.id,
                status=response.status_code,
                # TODO: add storedVariables
                originalResponse=response.json() if response.headers.get("Content-Type") == "application/json" else response.text,
                originalRequest={
                    "url": api_test_request.url,
                    "jsonBody": api_test_request.jsonBody,
                }
            )

            if api_test_request.expectedResponse.status != response.status_code:
                api_test_response.add_failure_for_status_code(api_test_request.expectedResponse.status, response.status_code)

            # TODO: validate all content validations
                
            api_test_response.isValidationSuccess = api_test_response.failedValidations == []
            responses.append(api_test_response)

        return {"responses": responses}
    