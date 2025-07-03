import uuid
import json
import logging

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app


# --- 1. Configuração de Logs ---
# Configura um logger para este arquivo de teste para dar mais detalhes durante a execução.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Dados de Teste ---
TEST_USER = {
    "username": "testuser_ws",
    "password": "testpassword"
}
SESSION_ID = str(uuid.uuid4())


# --- Fixtures (sem alterações) ---
@pytest.fixture(scope="module")
def client():
    """
    Cria um TestClient para todo o módulo, garantindo que o lifespan
    seja executado apenas uma vez.
    """
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module", autouse=True)
def setup_test_user(client: TestClient):
    """
    Garante que o usuário de teste exista. Depende do fixture 'client'
    e é executado automaticamente uma vez por módulo.
    """
    client.post("/user/register", json=TEST_USER)
    yield


def get_auth_token(client: TestClient) -> str:
    """Helper para obter um token de autenticação."""
    logger.info("Autenticando usuário de teste para obter token...")
    login_data = {
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    }
    response = client.post("/user/login", data=login_data)
    assert response.status_code == 200, f"Falha no login: {response.text}"
    token = response.json().get("access_token")
    assert token is not None
    logger.info("Token obtido com sucesso.")
    return token


def test_websocket_orchestrator_successful_flow(client: TestClient):
    """
    Testa o fluxo completo e bem-sucedido do orquestrador WebSocket,
    com logs detalhados, tratamento de erro e visualização da resposta.
    """
    logger.info("--- INICIANDO TESTE DE FLUXO BEM-SUCEDIDO ---")
    token = get_auth_token(client)
    
    # --- 2. Tratamento de Erros ---
    # O bloco try/except garante que, se algo falhar, teremos um log detalhado do erro.
    try:
        with client.websocket_connect(f"/agent/ws/orchestrator?token={token}") as websocket:
            logger.info("Conexão WebSocket estabelecida.")
            symptom_data = {
                "symptoms": "Dor de cabeça intensa, febre alta e rigidez no pescoço.",
                "session_id": SESSION_ID
            }
            websocket.send_json(symptom_data)
            logger.info(f"Enviado payload de sintomas: {symptom_data['symptoms']}")

            # Lista para armazenar as mensagens recebidas
            messages = []
            
            # Loop para receber todas as mensagens esperadas
            for i in range(7): # Esperamos 7 mensagens no total
                msg = websocket.receive_json()
                logger.info(f"Recebido [Msg {i+1}/7]: {msg}")
                messages.append(msg)

            # Validações
            logger.info("Validando as mensagens recebidas...")
            assert "status" in messages[0] and "Analyzing symptoms" in messages[0]["status"]
            assert messages[1]["type"] == "diagnosis_result" and "diagnosis" in messages[1]["data"]
            assert "status" in messages[2] and "Saving initial diagnosis" in messages[2]["status"]
            assert "status" in messages[3] and "Generating clinical plan" in messages[3]["status"]
            assert messages[4]["type"] == "plan_result" and "exam_recommendations" in messages[4]["data"]
            assert "status" in messages[5] and "Saving clinical plan" in messages[5]["status"]
            assert messages[6]["status"] == "Completed!"
            logger.info("Todas as mensagens foram validadas com sucesso.")

            # --- 3. Visualização da Resposta ---
            # Se todos os asserts passaram, imprime o resultado final consolidado.
            print("\n\nTeste Concluído com Sucesso! Resposta final do Orquestrador:")
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
        logger.error(f"O teste de fluxo falhou com uma exceção: {e}", exc_info=True)
        pytest.fail(f"Ocorreu uma exceção inesperada durante o teste de fluxo: {e}")


def test_websocket_invalid_token(client: TestClient):
    """
    Testa a falha de conexão do WebSocket com um token inválido.
    """
    logger.info("--- INICIANDO TESTE DE TOKEN INVÁLIDO ---")
    with pytest.raises(WebSocketDisconnect) as e_info:
        with client.websocket_connect("/agent/ws/orchestrator?token=invalidtoken"):
            pass
    
    # Verifica o código de desconexão diretamente.
    assert e_info.value.code == 1008
    logger.info("Teste de token inválido passou. Conexão rejeitada como esperado.")
