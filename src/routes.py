from fastapi import APIRouter #, HTTPException, Depends
from apitestpy.orchestrator_service import OrchestratorService
from models.apitestify_requests import ApiTestRequestVMList

router = APIRouter()
orchestrator_service = OrchestratorService()

@router.post("/validate")
def validate(request: ApiTestRequestVMList):
    response = orchestrator_service.validate(request)
    return response
