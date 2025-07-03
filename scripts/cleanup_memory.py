import logging
from sqlalchemy import text
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.connection import engine as db_engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def clear_agents_memory():
    """
    Executa um TRUNCATE nas tabelas de memória dos agentes para limpá-las.
    """
    logger.info("Executing scheduled memory cleanup...")
    try:
        with db_engine.connect() as connection:
            connection.execute(text("TRUNCATE TABLE clinical_protocol_memories, symptom_analyzer_memories;"))
            connection.commit()
        logger.info("Agent memory tables truncated successfully.")
    except Exception as e:
        logger.error(f"Failed to clear agent memories: {e}")

scheduler = AsyncIOScheduler()
