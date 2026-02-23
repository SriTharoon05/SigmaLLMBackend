import os
import uuid
from dotenv import load_dotenv
from rich.pretty import pprint
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from sentence_transformers import SentenceTransformer

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

COLLECTION_NAME = "docs"

TEXT_DIR = r"C:\Users\sritharoon.as\Documents\GitHub\SIGMA_LLM_final\backend\Uploads_folder"

# --------------------------------------------------
# Clients
# --------------------------------------------------
qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

# SentenceTransformer model
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

VECTOR_SIZE = embedder.get_sentence_embedding_dimension()

# --------------------------------------------------
# Create collection (if not exists)
# --------------------------------------------------
existing_collections = [
    c.name for c in qdrant.get_collections().collections
]

print(f"Existing collections:", existing_collections)

if COLLECTION_NAME not in existing_collections:
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )
    print(f"Created collection: {COLLECTION_NAME}")
else:
    print(f"Collection already exists: {COLLECTION_NAME}")

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def chunk_text(text: str, chunk_size=800, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings using SentenceTransformers
    """
    embeddings = embedder.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.tolist()

# --------------------------------------------------
# Ingest .txt files
# --------------------------------------------------
points = []

for filename in os.listdir(TEXT_DIR):
    if not filename.endswith(".txt"):
        continue

    filepath = os.path.join(TEXT_DIR, filename)

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)
    embeddings = embed_texts(chunks)

    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "source": filename,
                    "chunk_id": idx,
                    "text": chunk,
                },
            )
        )

# --------------------------------------------------
# Upload to Qdrant
# --------------------------------------------------
qdrant.upsert(
    collection_name=COLLECTION_NAME,
    points=points,
)

print(f"Uploaded {len(points)} chunks into '{COLLECTION_NAME}'")
