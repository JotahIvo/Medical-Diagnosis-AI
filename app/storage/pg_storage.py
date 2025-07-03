import os
import logging
from dotenv import load_dotenv

from agno.storage.postgres import PostgresStorage


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_url = os.getenv("DB_URL")

try: 
    pg_storage = PostgresStorage(
        table_name="agent_sessions",
        db_url=db_url,
        auto_upgrade_schema=True
    )
    logger.info("PostgresStorage initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing PostgresStorage: {e}")
    raise
