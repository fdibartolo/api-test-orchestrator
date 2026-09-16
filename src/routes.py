from fastapi import APIRouter
from apitest.orchestrator_service import OrchestratorService
from apitest.vars_evaluator_service import VariablesEvaluatorService
from apitest.response_validation_service import ResponseValidationService
from apitest.auth_service import AuthService
from apitest.dynamic_vars_evaluator_service import DynamicVarsEvaluatorService
from models.apitestify_requests import ApiTestRequestVMList

router = APIRouter()
auth_service = AuthService()
response_validation_service = ResponseValidationService()
vars_evaluator_service = VariablesEvaluatorService()
dynamic_vars_evaluator_service = DynamicVarsEvaluatorService()
orchestrator_service = OrchestratorService(
    auth_service,
    response_validation_service,
    vars_evaluator_service,
    dynamic_vars_evaluator_service
    # TODO: pass env vars for secrets replacements
)

@router.post("/validate")
def validate(request: ApiTestRequestVMList):
    response = orchestrator_service.validate(request)
    return response
