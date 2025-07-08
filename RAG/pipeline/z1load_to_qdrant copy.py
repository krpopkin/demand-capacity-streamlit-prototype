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
use_cloud = os.getenv("USE_QDRANT_CLOUD", "False").strip().lower() == "true"

if use_cloud:
    raw_url = os.getenv("QDRANT_URL", "").strip()
    if not raw_url:
        raise RuntimeError("QDRANT_URL must be set when USE_QDRANT_CLOUD=True")

    # ensure urlparse has a scheme
    url = raw_url if raw_url.startswith(("http://", "https://")) else "https://" + raw_url
    parsed = urlparse(url)

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    https_flag = (parsed.scheme == "https")

    # ─── DEBUG: verify DNS resolution before we even call QdrantClient ───
    try:
        addrs = socket.getaddrinfo(host, None)
        print(f"✅ DNS OK for {host}: {[addr[4][0] for addr in addrs]}")
    except Exception as e:
        raise RuntimeError(f"DNS lookup failed for Qdrant host {host!r}: {e}") from e

    print(f"→ Connecting to Qdrant Cloud at {host}:{port} (HTTPS={https_flag})")
    client = QdrantClient(
        host=host,
        port=port,
        https=https_flag,
        prefer_grpc=True,
        api_key=os.getenv("QDRANT_KEY").strip(),
    )
else:
    print("→ Connecting to local Qdrant on localhost:6333")
    client = QdrantClient(host="localhost", port=6333)
    
    
def load_embeddings(filepath, collection_name):
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
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".parquet"):
            filepath = os.path.join(DATA_DIR, filename)
            collection_name = filename.replace(".parquet", "")
            load_embeddings(filepath, collection_name)

if __name__ == "__main__":
    main()