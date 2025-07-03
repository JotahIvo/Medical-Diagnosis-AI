import uuid
import json
import logging

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_USER = {
    "username": "testuser_ws",
    "password": "testpassword"
}
SESSION_ID = str(uuid.uuid4())


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module", autouse=True)
def setup_test_user(client: TestClient):
    client.post("/user/register", json=TEST_USER)
    yield


def get_auth_token(client: TestClient) -> str:
    logger.info("Authenticating test user to get token...")
    login_data = {
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    }
    response = client.post("/user/login", data=login_data)
    assert response.status_code == 200, f"Falha no login: {response.text}"
    token = response.json().get("access_token")
    assert token is not None
    logger.info("Token obtained successfully.")
    return token


def test_websocket_orchestrator_successful_flow(client: TestClient):
    logger.info("--- STARTING SUCCESSFUL FLOW TEST ---")
    token = get_auth_token(client)
    
    try:
        with client.websocket_connect(f"/agent/ws/orchestrator?token={token}") as websocket:
            logger.info("WebSocket connection established.")
            symptom_data = {
                "symptoms": "Severe headache, high fever and stiff neck.",
                "session_id": SESSION_ID
            }
            websocket.send_json(symptom_data)
            logger.info(f"Sent symptom payload: {symptom_data['symptoms']}")

            messages = []
            
            for i in range(7): 
                msg = websocket.receive_json()
                logger.info(f"Received [Msg {i+1}/7]: {msg}")
                messages.append(msg)

            logger.info("Validating received messages...")
            assert "status" in messages[0] and "Analyzing symptoms" in messages[0]["status"]
            assert messages[1]["type"] == "diagnosis_result" and "diagnosis" in messages[1]["data"]
            assert "status" in messages[2] and "Saving initial diagnosis" in messages[2]["status"]
            assert "status" in messages[3] and "Generating clinical plan" in messages[3]["status"]
            assert messages[4]["type"] == "plan_result" and "exam_recommendations" in messages[4]["data"]
            assert "status" in messages[5] and "Saving clinical plan" in messages[5]["status"]
            assert messages[6]["status"] == "Completed!"
            logger.info("All messages were successfully validated.")

            print("\n\nTest Completed Successfully! Final Response from Orchestrator:")
            print("-------------------------------------------------------------------")
            
            final_diagnosis = messages[1].get("data", {})
            final_plan = messages[4].get("data", {})
            
            final_response_for_display = {
                "diagnosis_hypothesis": final_diagnosis,
                "clinical_action_plan": final_plan
            }

            print(json.dumps(final_response_for_display, indent=2, ensure_ascii=False))
            print("-------------------------------------------------------------------\n")

    except Exception as e:
        logger.error(f"The flow test failed with an exception: {e}", exc_info=True)
        pytest.fail(f"An unexpected exception occurred during flow testing: {e}")


def test_websocket_invalid_token(client: TestClient):
    logger.info("--- STARTING INVALID TOKEN TEST ---")
    with pytest.raises(WebSocketDisconnect) as e_info:
        with client.websocket_connect("/agent/ws/orchestrator?token=invalidtoken"):
            pass
    
    assert e_info.value.code == 1008
    logger.info("Invalid token test passed. Connection rejected as expected.")
