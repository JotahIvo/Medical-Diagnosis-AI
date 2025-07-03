@agent_router.post("/orchestrator", response_model=MedicalDiagnosisResponse)
async def orchestrator_diagnosis(
    input_data: SymptomInput,
    user: dict = Depends(get_current_user),
    symptom_analyzer_agent: Agent = Depends(get_symptom_analyzer_agent_dependency),
    clinical_protocol_agent: Agent = Depends(get_clinical_protocol_agent_dependency)
):
    user_id = user.get("id")
    session_id = input_data.session_id

    # --- AGENTE A: Obter Diagnóstico ---
    logger.info(f"Orchestrator receiving symptoms for session {session_id} from user: {user_id}.")
    logger.info("Orchestrator: Step 1/4 - Getting diagnosis from Symptom Analyzer...")
    
    response_agent_a: RunResponse = await symptom_analyzer_agent.arun(
        message=input_data.symptoms,
        session_id=session_id,
        user_id=str(user_id)
    )
    
    hypothesis_final_content = response_agent_a.content
    if not hypothesis_final_content:
        raise HTTPException(status_code=500, detail="Agent A did not produce any content.")

    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(hypothesis_final_content.strip())
        diagnosis_hypothesis = DiagnosisHypothesis.model_validate(obj)
        logger.debug("JSON extracted and validated from Agent A.")
    except Exception as e:
        logger.error(f"Failed to parse JSON from Agent A: {e}. Content: {hypothesis_final_content}")
        raise HTTPException(status_code=500, detail="Error processing initial diagnosis.")

    # --- AGENTE A: Mandar Memorizar ---
    logger.info("Orchestrator: Step 2/4 - Requesting Agent A to save to memory...")
    memory_task_a = f"Based on our last interaction, please save this to your memory: The user's symptoms are '{input_data.symptoms}' and the diagnosis was '{diagnosis_hypothesis.diagnosis}'."
    await symptom_analyzer_agent.arun(message=memory_task_a, session_id=session_id, user_id=str(user_id))


    # --- AGENTE B: Obter Plano Clínico ---
    logger.info("Orchestrator: Step 3/4 - Getting clinical plan from Protocol Agent...")
    clinical_input_message = f"Diagnostic hypothesis: {diagnosis_hypothesis.diagnosis}. Justification: {diagnosis_hypothesis.justification}. Severity: {diagnosis_hypothesis.severity}."
    
    response_agent_b: RunResponse = await clinical_protocol_agent.arun(
        message=clinical_input_message,
        session_id=session_id,
        user_id=str(user_id)
    )

    action_final_content = response_agent_b.content
    if not action_final_content:
        raise HTTPException(status_code=500, detail="Agent B did not produce any content.")

    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(action_final_content.strip())
        clinical_action = ClinicalAction.model_validate(obj)
        logger.debug("JSON extracted and validated from Agent B.")
    except Exception as e:
        logger.error(f"Failed to parse JSON from Agent B: {e}. Content: {action_final_content}")
        raise HTTPException(status_code=500, detail="Error processing clinical action plan.")

    # --- AGENTE B: Mandar Memorizar ---
    logger.info("Orchestrator: Step 4/4 - Requesting Agent B to save to memory...")
    memory_task_b = f"For the diagnosis of '{diagnosis_hypothesis.diagnosis}', the suggested clinical plan has an urgency of '{clinical_action.urgency}'."
    await clinical_protocol_agent.arun(message=memory_task_b, session_id=session_id, user_id=str(user_id))


    # --- RESPOSTA FINAL ---
    final_response = MedicalDiagnosisResponse(
        diagnosis=diagnosis_hypothesis,
        action_plan=clinical_action,
        rag_sources=[],
        notes="Remember that this is a simulated diagnosis and is not a substitute for the evaluation of a healthcare professional. Seek medical attention immediately in case of an emergency."
    )

    logger.info("Orchestrator: Diagnosis and Action Plan completed successfully.")
    return final_response
