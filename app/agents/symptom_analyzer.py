import os
import logging
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.groq import Groq
from agno.memory.v2.memory import Memory
from agno.memory.v2.db.postgres import PostgresMemoryDb

from app.storage.pg_storage import pg_storage
from app.storage.rag import get_pdfknowledge_base


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_api_key = os.getenv("GROQ_API_KEY")
model_llm = "qwen/qwen3-32b"
db_url = os.getenv("DB_URL")


async def get_symptom_analyzer_agent():
    pdf_knowledge_base = await get_pdfknowledge_base()

    json_schema_definition = """
    {
        "diagnosis": "Potential Condition Name",
        "confidence": "High",
        "justification": "The justification for the diagnosis based on the provided context.",
        "severity": "Moderate"
    }
    """

    memory_symptom_analyzer = Memory(
        model=Groq(id=model_llm, api_key=groq_api_key),
        db=PostgresMemoryDb(table_name="symptom_analyzer_memories", db_url=db_url),
        delete_memories=False,
        clear_memories=False
    )

    agent_symptom_analyzer = Agent(
        name="Symptom Analyzer Agent",
        model=Groq(id=model_llm, api_key=groq_api_key),
        memory=memory_symptom_analyzer,
        enable_agentic_memory=True,
        enable_user_memories=True,
        tools=[],
        instructions=[
            "**DO NOT use any tools. Your ONLY task is to return a JSON object with the diagnosis.**",
            "You are an experienced Symptom Analyzer. Given a list of symptoms, your task is to suggest a diagnostic hypothesis.",
            "**Use ONLY the information provided in the context of the knowledge base (RAG) to form your hypothesis.**",
            "**Your ONLY final result MUST be a valid JSON object that fits EXACTLY into the `DiagnosisHypothesis` schema.**",
            "Do NOT include any preamble, explanatory text, code markdown (```json), or anything other than pure JSON.",
            "Your JSON must start with `{` and end with `}`.",
            "**Do NOT include fields like 'recommended_next_steps' or any other that is not explicitly in the `DiagnosisHypothesis` schema.**",
            "Your output JSON must contain these exact keys: 'diagnosis', 'confidence', 'severity', 'justification'.",
            f"Here is a perfect example of the output format: \n{json_schema_definition}",
            "Justify your hypothesis based on the symptoms and the knowledge information provided. If the information is not sufficient, indicate low confidence.",
            "Consider the severity of the symptoms and the urgency when determining the 'severity'.",
            "Ensure the 'justification' is clear and concise."
        ],
        description="Analyzes patient symptoms to suggest diagnostic hypotheses.",
        knowledge=pdf_knowledge_base,
        storage=pg_storage,
        add_datetime_to_instructions=False,
        add_history_to_messages=True,
        num_history_runs=3,
        markdown=False,
        structured_outputs=False,
        debug_mode=True,
        tool_choice="none"
    )
    logger.info(f"Initialized Symptom Analyzer Agent with model: {model_llm}")
    return agent_symptom_analyzer
