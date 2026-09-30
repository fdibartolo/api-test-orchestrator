import os

from dotenv import dotenv_values
from fastapi import APIRouter

from apitest.auth_service import AuthService
from apitest.dynamic_vars_evaluator_service import DynamicVarsEvaluatorService
from apitest.orchestrator_service import OrchestratorService
from apitest.response_validation_service import ResponseValidationService
from apitest.vars_evaluator_service import VariablesEvaluatorService
from models.apitest_requests import ApiTestRequestVMList
from models.apitest_responses import ApiTestResponseVM

router = APIRouter()
auth_service = AuthService()
response_validation_service = ResponseValidationService()
vars_evaluator_service = VariablesEvaluatorService()
dynamic_vars_evaluator_service = DynamicVarsEvaluatorService()
secrets = dotenv_values(".env") if os.path.exists(".env") else {}
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
