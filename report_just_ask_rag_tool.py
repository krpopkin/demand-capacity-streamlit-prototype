# report_just_ask_rag_tool.py

import os
import textwrap
from concurrent.futures import ThreadPoolExecutor
from typing import List

import streamlit as st
from dotenv import load_dotenv

# Embeddings
from google.cloud import aiplatform_v1
from google.protobuf.struct_pb2 import Struct

# Gen AI SDK
from google import genai
from google.genai.types import GenerateContentConfig

# Qdrant
from qdrant_client import QdrantClient

# ─── 1) Load & normalize your .env ────────────────────────────
load_dotenv()
PROJECT_ID       = os.getenv("PROJECT_ID")
LOCATION         = os.getenv("LOCATION")
# Parse USE_QDRANT_CLOUD as a real boolean (True => use cloud, False => use local)
USE_QDRANT_CLOUD = os.getenv("USE_QDRANT_CLOUD", "False").lower() in ("true", "1")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_KEY   = os.getenv("QDRANT_KEY")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL")
SYNTHESIS_MODEL  = os.getenv("SYNTHESIS_MODEL")

TOP_K = 50
TOP_K_SENT_TO_LLM = 20  

if not PROJECT_ID or not LOCATION:
    raise RuntimeError("PROJECT_ID and LOCATION must be set in your .env")

# ─── 2) Configure GenAI for Vertex & instantiate client ───────
os.environ["GOOGLE_CLOUD_PROJECT"]      = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"]     = LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

genai_client = genai.Client(vertexai=True)

# ─── 3) Embedding helper ───────────────────────────────────────
aiplatform_client = aiplatform_v1.PredictionServiceClient()
def embed(text: str) -> List[float]:
    inst = Struct()
    inst.update({"task_type": "RETRIEVAL_QUERY", "content": text})
    resp = aiplatform_client.predict(
        endpoint=f"projects/{PROJECT_ID}/locations/{LOCATION}/{EMBEDDINGS_MODEL}",
        instances=[inst],
        parameters=Struct(),
    )
    return list(resp.predictions[0]["embeddings"]["values"])

# ─── 4) Qdrant search helper ───────────────────────────────────
def search_collection(qdrant: QdrantClient, collection: str, query_vector: List[float], top_k: int):
    try:
        return qdrant.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=["text"],
        )
    except Exception as e:
        st.warning(f"Error searching {collection}: {e}")
        return []

# ─── 5) Prompt builder ─────────────────────────────────────────
def build_synthesis_prompt(question: str, contexts: List[str]) -> str:
    numbered = "\n".join(f"{i+1}. {c}" for i, c in enumerate(contexts))
    return textwrap.dedent(f"""
    You are an expert AI assistant. Use the numbered contexts to answer concisely,
    integrating them into a coherent answer.

    **User Question:**
    {question}

    **Contexts:**
    {numbered}

    Now generate your final answer.
    """).strip()

# ─── 6) GenAI thin wrapper ─────────────────────────────────────
class SimpleGenAI:
    def __init__(self, client, model: str, temperature: float = 0.0):
        self.client      = client
        self.model       = model
        self.temperature = temperature

    def invoke(self, prompt: str) -> str:
        cfg = GenerateContentConfig(temperature=self.temperature)
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=cfg,
        )
        return resp.text.strip()

# ─── 7) The one RAG function ──────────────────────────────────
def just_ask_rag_report(user_question: str) -> str:
    """
    1) Embed the question
    2) Retrieve from Qdrant in parallel
    3) Call the model
    4) Return the answer text
    """
    # A) Embed
    query_vec = embed(user_question)

    # B) Qdrant client instantiation based on USE_QDRANT_CLOUD
    if USE_QDRANT_CLOUD:
        qdrant = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_KEY,
        )
    else:
        qdrant = QdrantClient(host="localhost", port=6333)

    # C) Parallel retrieval
    collections = ["assignments", "products", "roles", "skills_matrix", "teammembers", "team_insights"]
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(search_collection, qdrant, col, query_vec, TOP_K)
            for col in collections
        ]
        hits = [hit for future in futures for hit in future.result()]

    # Sort and extract contexts
    hits.sort(key=lambda h: h.score, reverse=True)
    contexts = [h.payload.get("text", "") for h in hits[:TOP_K_SENT_TO_LLM]]

    # D) Generate answer
    prompt = build_synthesis_prompt(user_question, contexts)
    llm    = SimpleGenAI(genai_client, SYNTHESIS_MODEL, temperature=0.0)
    return llm.invoke(prompt)
