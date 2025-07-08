import os
import streamlit as st
from report_just_ask_text_to_sql_tool import just_ask_text_to_sql_report
from report_just_ask_rag_tool import just_ask_rag_report
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig

load_dotenv()

###############################################################################################
# Asks the user to enter a question or request, then uses an LLM to evaluate the user's 
# entry to decide between calling the text-to-sql or RAG tool. 
###############################################################################################

DECISION_MODEL = os.getenv("DECISION_MODEL")

genai_client = genai.Client(vertexai=True)

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

def decision_prompt(user_question: str) -> str:
    prompt = f"""
        You are a decision router for a Q&A system. You must choose exactly one of:
        • text to sql  
        • RAG

        - If the question is short and only requires one or two tables to get an answer, use 
        text to sql.
        
        - If the question is longer, or uses connector words like "and" that make the query
        hard to construct, then use RAG.    

        Respond with **only** the decision keyword, in lowercase, with no extra commentary.

        User question:
        \"\"\"{user_question}\"\"\"

        Decision:
        """
    return prompt 

def just_ask_choose_tool_report(conn):
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
    
    prompt = decision_prompt(user_question)
    llm = SimpleGenAI(genai_client, DECISION_MODEL, temperature=0.0)
    decision = llm.invoke(prompt).strip().lower()
    
    if decision == 'text to sql':
        sql_query, result = just_ask_text_to_sql_report(conn, user_question)
        with st.expander("Show sql query", expanded=False):
            st.code(sql_query, language="sql")     
    else:
        result = just_ask_rag_report(user_question)  
        
    st.write(result)
 