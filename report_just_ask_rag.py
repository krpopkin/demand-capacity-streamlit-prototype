import os
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from google.cloud import aiplatform_v1
from google.protobuf.struct_pb2 import Struct
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from typing import List
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
MODEL = os.getenv("MODEL")
COLLECTIONS = os.getenv("COLLECTIONS")
TOP_K_PER_COLLECTION = os.getenv("TOP_K_PER_COLLECTION")

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


def just_ask_rag_report(use_cloud: bool = False):
    with st.expander("Click for description", expanded=False):
        st.markdown(
            """
            The objective of 'Just Ask' is to enable a Q&A conversation.  This is experimental and 
            the answer you get is very dependent on how you word your question.

            For example, asking a multi-faceted question such as, 
            "Tell me which team members have business analyst as a skillset, the available allocation
            for each team member and who their manager is?"
            is highly likely to return an incomplete and/or inaccurate result.  
            
            Asking for the same information via single questions and a conversational chat,
            for example:
            
            Human: Which team members have business analysts as a skillset?
            AI: responds
            
            Human: What is the total allocation of each business analyst?
            AI responds
            
            Human: For business analysts with <100 percent allocation, who is there manager? 
            AI responds
            
            You now now who is available and who to reach out to, to request a BA for your project. 
            """)

    user_question = st.text_input(
        "Ask a question to start a conversation:",
        placeholder="e.g., Which team members are assigned to Product X?"
    )
    if not user_question:
        return

    # Step 1: Embed the query
    query_vector = embed(user_question)

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

    # return [hit.payload.get("text", "") for hit in all_hits]
    response = [hit.payload.get("text", "") for hit in all_hits]
    st.write(response)