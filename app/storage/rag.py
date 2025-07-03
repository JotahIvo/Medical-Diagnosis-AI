import os
import logging
from dotenv import load_dotenv

from agno.embedder.google import GeminiEmbedder
from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
from agno.vectordb.qdrant import Qdrant
from agno.document.chunking.agentic import AgenticChunking


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

qdrant_api_key = os.getenv("QDRANT_API_KEY")
qdrant_url = os.getenv("QDRANT_URL")
collection_name = "pdf_rag"
google_api_key = os.getenv("GOOGLE_API_KEY")

if not qdrant_url or not qdrant_api_key or not google_api_key:
    raise ValueError("QDRANT_URL, QDRANT_API_KEY or GOOGLE_API_KEY were not provided.")

logger.info(f"RAG Config: QDRANT_URL={qdrant_url}, QDRANT_API_KEY={'***' if qdrant_api_key else 'None'}, GOOGLE_API_KEY={'***' if google_api_key else 'None'}")

gemini_embedder_instance = GeminiEmbedder(api_key=google_api_key)

vector_db = Qdrant(
    url=qdrant_url,
    api_key=qdrant_api_key,
    collection=collection_name,
    embedder=gemini_embedder_instance
)

pdf_knowledge_base = PDFKnowledgeBase(
    path="data/pdfs",
    vector_db=vector_db,
    reader=PDFReader(chunk=True),
    chunking_strategy=AgenticChunking()
)

async def load_pdf_knowledge_base():
    logger.info("Loading knowledge base to QDRANT... (Initiated by Agno)")
    try:
        await pdf_knowledge_base.aload(recreate=True)
        logger.info("Knowledge base uploaded to QDRANT with success!")
    except Exception as e:
        logger.error(f"Failed to load knowledge base to QDRANT: {e}", exc_info=True)
        raise

async def get_pdfknowledge_base():
    return pdf_knowledge_base
