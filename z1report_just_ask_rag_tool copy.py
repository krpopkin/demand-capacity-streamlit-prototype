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
from google.genai.types import GenerateContentConfig, HttpOptions

# Qdrant
from qdrant_client import QdrantClient

# ─── 1) Load & normalize your .env ────────────────────────────
load_dotenv()
PROJECT_ID       = os.getenv("PROJECT_ID", "").strip()
LOCATION         = os.getenv("LOCATION",   "").strip()
USE_CLOUD        = os.getenv("USE_CLOUD",     "False") == "True"
QDRANT_CLOUD_URL = os.getenv("QDRANT_CLOUD_URL", "").strip()
QDRANT_API_KEY   = os.getenv("QDRANT_API_KEY",   "").strip()
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "").strip()
RAW_MODEL        = os.getenv("SYNTHESIS_MODEL",  "gemini-2.5-pro").strip()

if not PROJECT_ID or not LOCATION:
    raise RuntimeError("PROJECT_ID and LOCATION must be set in your .env")

MODEL_ID = RAW_MODEL

# ─── 2) Configure GenAI for Vertex & instantiate client ───────
os.environ["GOOGLE_CLOUD_PROJECT"]      = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"]     = LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

genai_client = genai.Client(vertexai=True)

# ─── 3) Embedding helper (unchanged) ─────────────────────────
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

# ─── 4) Qdrant search helper ─────────────────────────────────
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

# ─── 5) Prompt builder ────────────────────────────────────────
def build_synthesis_prompt(question: str, contexts: List[str]) -> str:
    numbered = "\n".join(f"{i+1}. {c}" for i, c in enumerate(contexts))
    return textwrap.dedent(f"""
    You are an expert AI assistant. Use the numbered contexts to answer concisely,
    integrating them into a coherent answer and citing “[Context X]” inline.

    **User Question:**
    {question}

    **Contexts:**
    {numbered}

    Now generate your final answer.
    """).strip()

# ─── 6) GenAI thin wrapper ────────────────────────────────────
class SimpleGenAI:
    def __init__(self, client, model: str, temperature: float = 0.0):
        self.client      = client
        self.model       = model
        self.temperature = temperature

    def invoke(self, prompt: str) -> str:
        cfg = GenerateContentConfig(temperature=self.temperature)
        resp = self.client.models.generate_content(
            model=self.model,    # <-- now ALWAYS a valid 'google/...'
            contents=prompt,
            config=cfg,
        )
        return resp.text.strip()

# ─── 7) The one RAG function ──────────────────────────────────
def just_ask_rag_report(user_question: str) -> str:
    """
    1) Embed the question
    2) Retrieve from Qdrant in parallel
    3) One Gemini 2.5 Pro call with normalized MODEL_ID
    4) Return the answer text
    """
    # A) Embed
    query_vec = embed(user_question)

    # B) Qdrant
    qdrant = QdrantClient(
        url=QDRANT_CLOUD_URL if USE_CLOUD else "http://localhost:6333",
        api_key=(QDRANT_API_KEY if USE_CLOUD else None),
    )

    # C) Parallel retrieval
    collections = ["assignments","products","roles","skills_matrix","teammembers","team_insights"]
    with ThreadPoolExecutor() as ex:
        futures = [ex.submit(search_collection, qdrant, col, query_vec, 10) for col in collections]
        hits = [hit for f in futures for hit in f.result()]

    hits.sort(key=lambda h: h.score, reverse=True)
    contexts = [h.payload.get("text","") for h in hits]

    # D) Generate answer
    prompt = build_synthesis_prompt(user_question, contexts)
    llm    = SimpleGenAI(genai_client, MODEL_ID, temperature=0.0)
    return llm.invoke(prompt)
