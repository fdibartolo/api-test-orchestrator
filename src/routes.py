from fastapi import APIRouter #, HTTPException, Depends
from apitest.orchestrator_service import OrchestratorService
from apitest.response_validation_service import ResponseValidationService
from apitest.auth_service import AuthService
from models.apitestify_requests import ApiTestRequestVMList

router = APIRouter()
auth_service = AuthService()
response_validation_service = ResponseValidationService()
orchestrator_service = OrchestratorService(auth_service, response_validation_service)

@router.post("/validate")
def validate(request: ApiTestRequestVMList):
    response = orchestrator_service.validate(request)
    return response
