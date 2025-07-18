import sys
import os
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from dotenv import load_dotenv
from urllib.parse import urlparse
import socket

load_dotenv()

# CONFIGURATION
# Add parent directory to Python path so that this script can find db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))

DATA_DIR = os.getenv("DATA_DIR")

def connect_to_qdrant():
    use_cloud = os.getenv("USE_QDRANT_CLOUD", "False").strip().lower() == "true"

    if use_cloud:
        url = os.getenv("QDRANT_URL", "").strip()
        api_key=os.getenv("QDRANT_KEY").strip()
        
        client = QdrantClient(
            url=url,
            api_key=api_key,
            prefer_grpc=True)
    else:
        client = QdrantClient(host="localhost", port=6333)
    
    return client
    
    
def load_embeddings(filepath, collection_name, client):
    df = pd.read_parquet(filepath)

    # compute vector size even if df is empty
    vector_size = len(df["embedding"][0]) if "embedding" in df.columns else None

    # 1) delete any old collection
    try:
        client.delete_collection(collection_name=collection_name)
    except Exception:
        pass

    # 2) create a fresh one
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
    )

    # 3) if our parquet is malformed, bail now and leave an empty collection
    if "embedding" not in df.columns or "text" not in df.columns:
        print(f"⚠️ Skipping {filepath}: missing 'embedding' or 'text' column")
        return

    # 4) upsert as before
    points = [
        PointStruct(id=i, vector=vector, payload={"text": text})
        for i, (vector, text) in enumerate(zip(df["embedding"], df["text"]))
    ]
    client.upsert(collection_name=collection_name, points=points)
    print(f"✅ Uploaded {len(points)} points to '{collection_name}'")


def main():
    # --- Load and upload each parquet file ---
    client = connect_to_qdrant()
    
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".parquet"):
            filepath = os.path.join(DATA_DIR, filename)
            collection_name = filename.replace(".parquet", "")
            load_embeddings(filepath, collection_name, client)

if __name__ == "__main__":
    main()