import os
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from google.cloud import aiplatform_v1
from google.protobuf.struct_pb2 import Struct
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from typing import List
from dotenv import load_dotenv
import json

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
MODEL = os.getenv("MODEL")
USE_CLOUD = os.getenv("USE_CLOUD")
QDRANT_CLOUD_URL= os.getenv("QDRANT_CLOUD_URL")   # only used when USE_CLOUD=True
QDRANT_API_KEY= os.getenv("QDRANT_API_KEY")     # only used when USE_CLOUD=True

COLLECTIONS=["assignments","products","roles","skills_matrix","teammembers","team_insights"]
TOP_K_PER_COLLECTION = 10

client = aiplatform_v1.PredictionServiceClient()

def embed(text: str) -> List[float]:
    instance = Struct()
    instance.update({
        "task_type": "RETRIEVAL_QUERY",
        "content": text
    })

    response = client.predict(
        endpoint=f"projects/{PROJECT_ID}/locations/{LOCATION}/{MODEL}",
        instances=[instance],
        parameters=Struct()
    )
    return list(response.predictions[0]['embeddings']['values'])

def search_collection(qdrant: QdrantClient, collection: str, query_vector: List[float], top_k: int):
    try:
        return qdrant.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=['text'],       # ← ask for your “text” field
        )
    except Exception as e:
        print(f"⚠️ Error searching {collection}: {e}")
        return []


def just_ask_rag_report(user_question):
    # Step 1: Embed the query
    query_vector = embed(user_question)

    # Step 2: Connect to Qdrant
    qdrant = QdrantClient(
        url="https://your-cloud-run-url" if USE_CLOUD == "True" else "http://localhost:6333",
        api_key=os.getenv("QDRANT_API_KEY") if USE_CLOUD == "True" else None
    )

    # Step 3: Run searches in parallel using ThreadPool
    print("⚙️ Running search across collections...")
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(search_collection, qdrant, collection, query_vector, TOP_K_PER_COLLECTION)
            for collection in COLLECTIONS
        ]
        all_hits = []
        for f in futures:
            all_hits.extend(f.result())

    # Step 4: Sort all results by score descending
    all_hits = sorted(all_hits, key=lambda x: x.score, reverse=True)

    print(f"\n🔎 Top {len(all_hits)} Matches:")
    for i, hit in enumerate(all_hits, 1):
        print(f"\n#{i} - Score: {hit.score}")
        print(hit.payload.get("text", "⚠️ No 'text' field"))

    response = [hit.payload.get("text", "") for hit in all_hits]
    return response