import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from google.cloud import aiplatform_v1
from google.protobuf.struct_pb2 import Struct
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from typing import List

PROJECT_ID = "amw-dna-coe-working-ds-dev"
LOCATION = "us-central1"
MODEL = "publishers/google/models/gemini-embedding-001"
COLLECTIONS = ["assignments", "products", "roles", "skills_matrix", "teammembers", "team_insights"]  # Or dynamically load with /collections
TOP_K_PER_COLLECTION = 3

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
            limit=top_k
        )
    except Exception as e:
        print(f"⚠️ Error searching {collection}: {e}")
        return []

def just_ask_rag_report(query: str, use_cloud: bool = False):
    print(f"🔍 Question: {query}")

    # Step 1: Embed the query
    query_vector = embed(query)

    # Step 2: Connect to Qdrant
    qdrant = QdrantClient(
        url="https://your-cloud-run-url" if use_cloud else "http://localhost:6333",
        api_key=os.getenv("QDRANT_API_KEY") if use_cloud else None
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

    return [hit.payload.get("text", "") for hit in all_hits]

# 🔧 Example
if __name__ == "__main__":
    results = just_ask_rag_report("Tell me which team members have business analyst as a skillset, the available allocation for each team member and who their manager is?")
    print("\n📌 RAG Results:\n")
    for res in results:
        print(res)
