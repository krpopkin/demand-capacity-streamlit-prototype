import sys
import os
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from dotenv import load_dotenv

load_dotenv()

# CONFIGURATION
# Add parent directory to Python path so that this script can find db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))

DATA_DIR = os.getenv("DATA_DIR")
USE_CLOUD = os.getenv("USE_CLOUD")

# --- Cloud / Local Qdrant Setup ---
if USE_CLOUD == "False":
    QDRANT_URL = os.getenv("QDRANT_CLOUD_URL")  # e.g. "https://qdrant-yourid.a.run.app"
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )
else:
    client = QdrantClient(host="localhost", port=6333)

def load_embeddings(filepath, collection_name):
    df = pd.read_parquet(filepath)

    if "embedding" not in df.columns or "text" not in df.columns:
        print(f"⚠️ Skipping {filepath}: missing 'embedding' or 'text' column")

    else:
        # Ensure fresh collection
        vector_size = len(df['embedding'][0])
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )

        # Upload points
        points = [
            PointStruct(id=i, vector=vector, payload={"text": text})
            for i, (vector, text) in enumerate(zip(df["embedding"], df["text"]))
        ]
        client.upsert(collection_name=collection_name, points=points)

        print(f"✅ Uploaded {len(points)} points to collection '{collection_name}'")

def main():
    # --- Load and upload each parquet file ---
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".parquet"):
            filepath = os.path.join(DATA_DIR, filename)
            collection_name = filename.replace(".parquet", "")
            load_embeddings(filepath, collection_name)

if __name__ == "__main__":
    main()