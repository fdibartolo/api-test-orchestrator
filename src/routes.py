from fastapi import APIRouter #, HTTPException, Depends
from apitest.orchestrator_service import OrchestratorService
from apitest.process_variables_service import ProcessVariablesService
from apitest.response_validation_service import ResponseValidationService
from apitest.auth_service import AuthService
from models.apitestify_requests import ApiTestRequestVMList

router = APIRouter()
auth_service = AuthService()
response_validation_service = ResponseValidationService()
process_variables_service = ProcessVariablesService()
orchestrator_service = OrchestratorService(
    auth_service,
    response_validation_service,
    process_variables_service,
    # TODO: pass env vars for secrets replacements
)

@router.post("/validate")
def validate(request: ApiTestRequestVMList):
    response = orchestrator_service.validate(request)
    return response
