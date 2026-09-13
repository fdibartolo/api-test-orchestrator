from fastapi import APIRouter #, HTTPException, Depends
from apitestpy.orchestrator_service import OrchestratorService
from apitestpy.auth_service import AuthService
from models.apitestify_requests import ApiTestRequestVMList

router = APIRouter()

auth_service = AuthService()
orchestrator_service = OrchestratorService(auth_service)

@router.post("/validate")
def validate(request: ApiTestRequestVMList):
    response = orchestrator_service.validate(request)
    return response
