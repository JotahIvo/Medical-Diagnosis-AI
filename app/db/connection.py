import logging

from decouple import config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = config('DB_URL')

try: 
    engine = create_engine(DB_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    logger.info(f"Database connection established successfully: {DB_URL}")
except Exception as e:
    logger.error(f"Error connecting to database: {e}")
    raise 
