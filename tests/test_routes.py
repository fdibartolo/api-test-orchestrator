import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import app
from models.apitest_requests import ApiTestRequestVM, ApiTestRequestVMList
from models.apitest_responses import ApiTestResponseVM
from src import routes


def test_validate_delegates_to_orchestrator_service() -> None:
    request_payload = ApiTestRequestVMList(
        apiTestRequests=[
            ApiTestRequestVM(
                id="request-1",
                url="https://api.example.test/items",
                method="GET",
                expectedResponse={"status": 200},
            )
        ],
        globalVariables={},
    )
    expected_response = [
        ApiTestResponseVM(
            requestId="request-1",
            isValidationSuccess=True,
            failedValidations=[],
            originalResponse={"ok": True},
            storedVariables={"itemCount": 1},
            status=200,
            originalRequest={"method": "GET", "url": "https://api.example.test/items"},
        )
    ]

    with patch.object(routes, "orchestrator_service") as mock_orchestrator:
        mock_orchestrator.validate.return_value = expected_response

        result = routes.validate(request_payload)

    mock_orchestrator.validate.assert_called_once_with(request_payload)
    assert result == expected_response


def test_validate_endpoint_returns_orchestrator_results() -> None:
    expected_response = [
        ApiTestResponseVM(
            requestId="request-2",
            isValidationSuccess=False,
            failedValidations=[],
            originalResponse={"error": "bad request"},
            storedVariables={},
            status=400,
            originalRequest={"method": "POST", "url": "https://api.example.test/items"},
        )
    ]

    with patch.object(routes, "orchestrator_service") as mock_orchestrator:
        mock_orchestrator.validate.return_value = expected_response

        client = TestClient(app)
        response = client.post(
            "/validate",
            json={
                "apiTestRequests": [
                    {
                        "id": "request-2",
                        "url": "https://api.example.test/items",
                        "method": "POST",
                        "expectedResponse": {"status": 400},
                    }
                ],
                "globalVariables": {},
            },
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "requestId": "request-2",
            "isValidationSuccess": False,
            "failedValidations": [],
            "originalResponse": {"error": "bad request"},
            "storedVariables": {},
            "status": 400,
            "originalRequest": {
                "method": "POST",
                "url": "https://api.example.test/items",
            },
        }
    ]
    mock_orchestrator.validate.assert_called_once()
