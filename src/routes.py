import os
from fastapi import APIRouter
from apitest.orchestrator_service import OrchestratorService
from apitest.vars_evaluator_service import VariablesEvaluatorService
from apitest.response_validation_service import ResponseValidationService
from apitest.auth_service import AuthService
from apitest.dynamic_vars_evaluator_service import DynamicVarsEvaluatorService
from models.apitestify_requests import ApiTestRequestVMList
from models.apitestify_responses import ApiTestResponseVM

router = APIRouter()
auth_service = AuthService()
response_validation_service = ResponseValidationService()
vars_evaluator_service = VariablesEvaluatorService()
dynamic_vars_evaluator_service = DynamicVarsEvaluatorService()
secrets = {
    "G_CTWR-Secrets-Env-AzureAD_ClientSecret": os.getenv("AZURE_AD_CLIENT_SECRET"),
    "G_CTWR-Secrets-Env-TestId_Password": os.getenv("TEST_ID_PASSWORD"),
}
orchestrator_service = OrchestratorService(
    auth_service,
    response_validation_service,
    vars_evaluator_service,
    dynamic_vars_evaluator_service,
    secrets,
)


@router.post(
    "/validate",
    response_model=list[ApiTestResponseVM],
    summary="Validate API test requests",
    description=(
        "Execute the submitted API test requests and validate each response "
        "against its expected status and content rules."
    ),
    response_description="Validation results for each submitted API test request.",
)
def validate(request: ApiTestRequestVMList):
    response = orchestrator_service.validate(request)
    return response
