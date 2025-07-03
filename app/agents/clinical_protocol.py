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


async def get_clinical_protocol_agent():
    pdf_knowledge_base = await get_pdfknowledge_base()

    json_schema_definition = """
    {
      "condition": "string (opcional)",
      "severity": "string (opcional)",
      "exam_recommendations": [
        {
          "name": "Exam name",
          "justification": "Justification for the examination."
        }
      ],
      "treatment_suggestions": [
        {
          "name": "Treatment Name",
          "justification": "Justification for treatment."
        }
      ],
      "urgency": "string ('Immediate', 'Brief', ou 'Routine')",
      "justification": "General justification for the action plan."
    }
    """

    memory_clinical_protocol = Memory(
        model=Groq(id=model_llm, api_key=groq_api_key),
        db=PostgresMemoryDb(table_name="clinical_protocol_memories", db_url=db_url),
        delete_memories=False,
        clear_memories=False
    )

    agent_clinical_protocol = Agent(
        name="Clinical Protocol Agent",
        model=Groq(id=model_llm, api_key=groq_api_key),
        memory=memory_clinical_protocol,
        enable_agentic_memory=True,
        enable_user_memories=True,
        tools=[],
        instructions=[
            "You are an expert in Clinical Protocols. Given a diagnostic hypothesis, your task is to suggest appropriate examinations and treatments.",
            "**Use ONLY the information provided in the context of the knowledge base (RAG) to form your recommendations.**",
            "**Your ONLY final result MUST be a valid JSON object that fits EXACTLY into the `ClinicalAction` schema defined below. Do not use any other field names.**",
            f"Here is the required JSON schema:\n{json_schema_definition}", 
            "Do NOT include any preamble, explanatory text, code markdown (```json), or anything other than pure JSON.",
            "Your JSON must start with `{` and end with `}`.",
            "**YOU MUST INCLUDE the 'urgency' field and populate it with one of the following values: 'Immediate', 'Brief', 'Routine', based on the severity and urgency of the hypothesis.**",
            "Justify each recommendation in the 'justification' field nested within each exam and treatment object.",
            "Prioritize safety and efficacy in the action plan. If the hypothesis is uncertain or severe, emphasize the need for immediate medical consultation."
        ],
        description="Suggests examinations and treatments based on diagnostic hypotheses.",
        knowledge=pdf_knowledge_base,
        search_knowledge=False,
        storage=pg_storage,
        add_datetime_to_instructions=False,
        add_history_to_messages=True,
        num_history_runs=3,
        markdown=False,
        structured_outputs=False,
        debug_mode=True,
        tool_choice="none"
    )
    logger.info(f"Initialized Clinical Protocol Agent with model: {model_llm}")
    return agent_clinical_protocol
