import os
from dotenv import load_dotenv

from qdrant_client import QdrantClient


load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

try:
    print(client.count(collection_name="pdf_rag", exact=True))
    print("Connection to Qdrant Cloud successful and collection 'pdf_rag' accessed.")
except Exception as e:
    print(f"Error connecting/accessing Qdrant Cloud: {e}")
    