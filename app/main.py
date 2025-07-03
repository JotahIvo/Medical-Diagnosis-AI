import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from app.routes.agents_routes import agent_router
from app.routes.user_routes import user_router, test_router
from app.storage.rag import load_pdf_knowledge_base
from app.agents.symptom_analyzer import get_symptom_analyzer_agent
from app.agents.clinical_protocol import get_clinical_protocol_agent
from app.db.connection import Session as DbSessionGenerator
from scripts.cleanup_memory import clear_agents_memory, scheduler


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup initiated...")
    app.state.symptom_analyzer_agent = None  
    app.state.clinical_protocol_agent = None

    app.state.db_session_gen = DbSessionGenerator

    logger.info("Starting lifespan: Loading knowledge base and agents...")
    try:
        await load_pdf_knowledge_base()
        logger.info("Initializing Symptom Analyzer Agent...")
        app.state.symptom_analyzer_agent = await get_symptom_analyzer_agent()
        logger.info(f"Symptom Analyzer Agent initialized: {app.state.symptom_analyzer_agent is not None}")

        logger.info("Initializing Clinical Protocol Agent...")
        app.state.clinical_protocol_agent = await get_clinical_protocol_agent()
        logger.info(f"Clinical Protocol Agent initialized: {app.state.clinical_protocol_agent is not None}")

        if app.state.symptom_analyzer_agent is None or app.state.clinical_protocol_agent is None:
            raise RuntimeError("One or both agents failed to initialize and are None.")
        
        scheduler.add_job(clear_agents_memory, 'interval', hours=24)
        scheduler.start()
        logger.info("Scheduler started. Memory cleanup job scheduled.")
        
        logger.info("Agents and knowledge base loaded and ready!")

    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise

    yield

    logger.info("Application shutdown initiated...")
    scheduler.shutdown()
    logger.info("Scheduler shut down.")
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="Simulated Medical Diagnostic System",
    description="API for simulated medical diagnosis using intelligent agents and RAG.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get('/')
async def health_check(request: Request):
    sa_status = "Ready" if getattr(request.app.state, 'symptom_analyzer_agent', None) else "Not Ready"
    cp_status = "Ready" if getattr(request.app.state, 'clinical_protocol_agent', None) else "Not Ready"
    return {"message": "Welcome to the FastAPI application!",
            "symptom_analyzer_agent_status": sa_status,
            "clinical_protocol_agent_status": cp_status}


app.include_router(user_router)
app.include_router(test_router)
app.include_router(agent_router)
