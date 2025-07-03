import uuid
import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.agents_schemas import DiagnosisHypothesis, ClinicalAction


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TEST_USER = {
    "username": "testuser_agents",
    "password": "testpassword"
}
SESSION_ID = str(uuid.uuid4())

@pytest.fixture(scope="module")
def client():
    """Cria um TestClient que respeita o lifespan da aplicação."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module", autouse=True)
def setup_test_user(client: TestClient):
    """Garante que o usuário de teste para estes endpoints exista."""
    client.post("/user/register", json=TEST_USER)
    yield

def get_auth_token(client: TestClient) -> str:
    """Helper para obter um token de autenticação."""
    logger.info(f"Authenticating user '{TEST_USER['username']}' to get token...")
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

# ==========================================================================
# TESTES APRIMORADOS PARA OS ENDPOINTS DOS AGENTES
# ==========================================================================

def test_symptom_analyzer_endpoint(client: TestClient):
    """
    Testa o endpoint do Agente Analisador de Sintomas com logs e tratamento de erro.
    """
    logger.info("--- STARTING ENDPOINT TEST: /agent/symptom_analyzer ---")
    try:
        # Arrange: Preparar autenticação e dados
        logger.info("Arrange Phase: Obtaining token and preparing payload.")
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "symptoms": "High fever and persistent dry cough for three days.",
            "session_id": SESSION_ID
        }
        logger.info(f"Payload to be sent: {payload}")

        # Act: Chamar o endpoint
        logger.info("Act Phase: Sending POST request.")
        response = client.post("/agent/symptom_analyzer", headers=headers, json=payload)
        
        # Assert: Validar a resposta
        logger.info(f"Response received. Status Code: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        logger.info("Validating response content...")
        assert "diagnosis" in data
        assert "confidence" in data
        
        logger.info("Validating response schema with Pydantic...")
        DiagnosisHypothesis.model_validate(data)
        logger.info("DiagnosisHypothesis Schema successfully validated!")

    except Exception as e:
        logger.error(f"The 'symptom_analyzer' test failed with an exception: {e}", exc_info=True)
        pytest.fail(f"Unexpected exception in test 'symptom_analyzer': {e}")


def test_clinical_protocol_endpoint(client: TestClient):
    """
    Testa o endpoint do Agente de Protocolo Clínico com logs e tratamento de erro.
    """
    logger.info("--- STARTING ENDPOINT TEST: /agent/clinical protocol ---")
    try:
        # Arrange: Preparar autenticação e dados de input complexos
        logger.info("Arrange Phase: Obtaining token and preparing payload.")
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        
        diagnosis_input = {
            "diagnosis": "Suspected Pneumonia",
            "confidence": "Medium",
            "justification": "Fever and cough are consistent with a respiratory infection.",
            "severity": "Moderate"
        }
        payload = {
            "session_id": SESSION_ID,
            "diagnosis": diagnosis_input
        }
        logger.info(f"Payload to be sent: {payload}")

        # Act: Chamar o endpoint
        logger.info("Act Phase: Sending POST request.")
        response = client.post("/agent/clinical_protocol", headers=headers, json=payload)
        
        # Assert: Validar a resposta
        logger.info(f"Response received. Status Code: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        logger.info("Validating response content...")
        assert "urgency" in data
        assert "exam_recommendations" in data
        assert "treatment_suggestions" in data

        logger.info("Validating response schema with Pydantic...")
        ClinicalAction.model_validate(data)
        logger.info("ClinicalAction Schema successfully validated!")

    except Exception as e:
        logger.error(f"The 'clinical_protocol' test failed with an exception: {e}", exc_info=True)
        pytest.fail(f"Unexpected exception in 'clinical protocol' test: {e}")
