# report_just_ask_text_to_sql_tool.py

import os
import json
import streamlit as st
from dotenv import load_dotenv

# Google Gen AI SDK
from google import genai
from google.genai.types import GenerateContentConfig

# DB runner
from langchain_community.utilities.sql_database import SQLDatabase
from db import get_engine

# if text to sql fails to create a query, then RAG will get used.  
from report_just_ask_rag_tool import just_ask_rag_report

# ─── Load & validate .env ─────────────────────────────────────
load_dotenv()
SCHEMA_PATH = "text_to_sql/text_to_sql_schema_definition.json"
MODEL_ID    = os.getenv("TEXT_TO_SQL_MODEL")
PROJECT_ID  = os.getenv("PROJECT_ID")
LOCATION    = os.getenv("LOCATION")

if not PROJECT_ID or not LOCATION:
    raise RuntimeError("PROJECT_ID and LOCATION must be set in your .env")

# ─── Init Gen AI SDK for Vertex AI ───────────────────────────
os.environ["GOOGLE_CLOUD_PROJECT"]      = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"]     = LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
genai_client = genai.Client()

class SimpleGenAI:
    """Wrap google-genai to provide .invoke(prompt)->str"""
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

def load_schema_dict() -> dict:
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)

def just_ask_text_to_sql_report(conn, user_question: str):
    """
    1) Embed JSON schema in the prompt
    2) Ask Gemini SQL statement
    3) Run it against Postgres
    4) Ask Gemini to explain the results
    Returns (raw_sql, friendly_answer) or (None, None) on error.
    """
    with st.spinner("Thinking…"):
        try:
            # a) Load & dump schema JSON
            schema = load_schema_dict()
            schema_json = json.dumps(schema, indent=2)

            # b) Prepare DB & dialect
            engine = get_engine()
            db     = SQLDatabase(engine)
            dialect = db.dialect

            # c) Prompt to generate SQL
            sql_prompt = (
                "You are an expert SQL generator.\n"
                "Below is the exact database schema in JSON:\n"
                f"{schema_json}\n\n"
                "User question:\n"
                f"{user_question}\n\n"
                f"Write exactly one valid SQL statement (no markdown fences) "
                f"using {dialect} syntax to answer the question.\n"
            )
            llm = SimpleGenAI(genai_client, MODEL_ID, temperature=0.0)
            raw_sql = llm.invoke(sql_prompt)

            # d) Execute the SQL
            rows = db.run(raw_sql)  # list[dict]
            rows_json = json.dumps(rows, default=str, indent=2)

            # e) Prompt to explain results
            explain_prompt = (
                "The human asked: " + user_question + "\n\n"
                "I ran this SQL:\n"
                + raw_sql + "\n\n"
                "and got these rows in JSON:\n"
                + rows_json + "\n\n"
                "Please write a concise, plain-English answer based only on those results."
            )
            friendly_answer = llm.invoke(explain_prompt)

            return raw_sql, friendly_answer

        except Exception as e:
            st.error("""❌ An error occurred while answering your question. Please
                     try asking it a different way or make the question less complex""")
            return None, None
