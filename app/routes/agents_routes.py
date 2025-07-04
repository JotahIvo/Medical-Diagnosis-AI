import json
import logging

from typing import Annotated
from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi import WebSocket, WebSocketDisconnect
from agno.agent import RunResponse, Agent
from starlette.websockets import WebSocketState

from app.depends.depends import token_verifier
from app.auth.auth_user import UserUseCases
from app.schemas.agents_schemas import SymptomInput, ClinicalAction, DiagnosisHypothesis, ClinicalProtocolInput


agent_router = APIRouter(prefix="/agent")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_current_user(user: Annotated[dict, Depends(token_verifier)]):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Not authenticated"
        )
    return user


async def get_symptom_analyzer_agent_dependency(request: Request) -> Agent:
    agent = getattr(request.app.state, "symptom_analyzer_agent", None)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Symptom Analyzer Agent not initialized."
        )
    return agent


async def get_clinical_protocol_agent_dependency(request: Request) -> Agent:
    agent = getattr(request.app.state, "clinical_protocol_agent", None)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Clinical Protocol Agent not initialized."
        )
    return agent


@agent_router.post("/symptom_analyzer", response_model=DiagnosisHypothesis, summary="Get Diagnostic Hypothesis")
async def analyze_symptoms(
    input_data: SymptomInput,
    user: dict = Depends(get_current_user),
    agent: Agent = Depends(get_symptom_analyzer_agent_dependency)
):
    
    logger.info(f"Calling Symptom Analyzer for session {input_data.session_id}.")

    response: RunResponse = await agent.arun(
        message=input_data.symptoms, 
        session_id=input_data.session_id, 
        user_id=str(user.get("id"))
    )
    
    final_content = response.content
    if not final_content:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Agent did not produce content."
        )

    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(final_content.strip())
        return DiagnosisHypothesis.model_validate(obj)
    except Exception as e:
        logger.error(f"Failed to parse JSON from Symptom Analyzer: {e}. Content: {final_content}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error processing diagnosis."
        )


@agent_router.post("/clinical_protocol", response_model=ClinicalAction, summary="Get Clinical Action Protocol")
async def get_clinical_protocol(
    input_data: ClinicalProtocolInput,
    user: dict = Depends(get_current_user),
    agent: Agent = Depends(get_clinical_protocol_agent_dependency)
):
    logger.info(f"Calling Clinical Protocol for session {input_data.session_id}.")
    
    agent_input = f"Diagnostic hypothesis: {input_data.diagnosis.diagnosis}. Justification: {input_data.diagnosis.justification}."
    
    response: RunResponse = await agent.arun(
        message=agent_input, 
        session_id=input_data.session_id, 
        user_id=str(user.get("id"))
    )
    
    final_content = response.content
    if not final_content:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Agent did not produce content."
        )

    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(final_content.strip())
        return ClinicalAction.model_validate(obj)
    except Exception as e:
        logger.error(f"Failed to parse JSON from Clinical Protocol Agent: {e}. Content: {final_content}")
        raise HTTPException(status_code=500, detail="Error processing clinical action protocol.")


""" async def token_verifier_ws(token: str = Query(...)):
    user = await token_verifier({"Authorization": f"Bearer {token}"})
    if not user:
        return None
    return user """


@agent_router.websocket("/ws/orchestrator")
async def websocket_orchestrator(websocket: WebSocket, token: str):
    db_session = websocket.app.state.db_session_gen()

    try:
        user_use_cases = UserUseCases(db_session=db_session)
        user = user_use_cases.verify(access_token=token)
    except Exception as auth_error:
        logger.warning(f"WebSocket auth failed for token '{token[:10]}...': {auth_error}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        db_session.close() 
        return
    finally:
        db_session.close()

    await websocket.accept()
    logger.info(f"WebSocket connection accepted for user: {user.get('sub')}")

    symptom_analyzer_agent: Agent = websocket.app.state.symptom_analyzer_agent
    clinical_protocol_agent: Agent = websocket.app.state.clinical_protocol_agent
    
    if not symptom_analyzer_agent or not clinical_protocol_agent:
        logger.error("Agents not initialized in app.state.")
        await websocket.send_json({"error": "Service not available. Agents not initialized."})
        await websocket.close()
        return

    try:
        input_data_json = await websocket.receive_json()
        input_data = SymptomInput.model_validate(input_data_json)
        user_id = user.get("user_id")
        session_id = input_data.session_id

        await websocket.send_json({"status": "Analyzing symptoms..."})
        response_agent_a: RunResponse = await symptom_analyzer_agent.arun(
            message=input_data.symptoms, 
            session_id=session_id, 
            user_id=str(user_id)
        )
        
        hypothesis_content = response_agent_a.content
        if not hypothesis_content:
            raise ValueError("Symptom Analyzer Agent did not produce any content.")
        
        obj, _ = json.JSONDecoder().raw_decode(hypothesis_content.strip())
        diagnosis_hypothesis = DiagnosisHypothesis.model_validate(obj)
        await websocket.send_json({
            "type": "diagnosis_result",
            "data": diagnosis_hypothesis.model_dump()
        })

        await websocket.send_json({"status": "Saving initial diagnosis to memory..."})
        memory_task_a = f"Based on our last interaction, please save this to your memory: The user's symptoms are '{input_data.symptoms}' and the diagnosis was '{diagnosis_hypothesis.diagnosis}'."
        await symptom_analyzer_agent.arun(
            message=memory_task_a, 
            session_id=session_id, 
            user_id=str(user_id)
        )

        await websocket.send_json({"status": "Generating clinical protocol..."})
        clinical_input_message = f"Diagnostic hypothesis: {diagnosis_hypothesis.diagnosis}. Justification: {diagnosis_hypothesis.justification}. Severity: {diagnosis_hypothesis.severity}."
        response_agent_b: RunResponse = await clinical_protocol_agent.arun(
            message=clinical_input_message, 
            session_id=session_id, 
            user_id=str(user_id)
        )
        action_content = response_agent_b.content
        if not action_content:
            raise ValueError("Clinical Protocol Agent did not produce any content.")

        obj, _ = json.JSONDecoder().raw_decode(action_content.strip())
        clinical_action = ClinicalAction.model_validate(obj)
        await websocket.send_json({
            "type": "protocol_result",
            "data": clinical_action.model_dump()
        })
        
        await websocket.send_json({"status": "Saving clinical protocol to memory..."})
        memory_task_b = f"For the diagnosis of '{diagnosis_hypothesis.diagnosis}', the suggested clinical protocol has an urgency of '{clinical_action.urgency}'."
        await clinical_protocol_agent.arun(
            message=memory_task_b, 
            session_id=session_id, 
            user_id=str(user_id)
        )

        await websocket.send_json({"status": "Completed!"})

    except WebSocketDisconnect:
        logger.info(f"Client {websocket.client.host} disconnected.")
    except Exception as e:
        error_message = f"An error occurred: {e}"
        logger.error(f"WebSocket Error for user {user.get('sub')}: {error_message}", exc_info=True)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.send_json({"error": error_message})
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()
            logger.info(f"WebSocket connection closed for user: {user.get('sub')}")
            