import os
import streamlit as st
from report_just_ask_text_to_sql_tool import just_ask_text_to_sql_report
from report_just_ask_rag_tool import just_ask_rag_report
from dotenv import load_dotenv

load_dotenv()

###############################################################################################
# Asks the user to enter a question or request, then uses an LLM to evaluate the user's 
# entry to decide between calling the text-to-sql or RAG tool. 
###############################################################################################

def llm_to_decide_tool(model_choice):
    return model_choice.lower()  # returns 'text to sql' or 'rag'

def just_ask_choose_tool_report(conn):
    with st.expander("Click for description", expanded=False):
        st.markdown(
            """
            The objective of 'Just Ask' is to enable a Q&A conversation. This is experimental and 
            the answer you get is very dependent on how you word your question.
            """
        )

    col1, col2 = st.columns([6, 2])
    with col1:
        user_question = st.text_input(
            "Ask a question to start a conversation:",
            placeholder="e.g., Which team members are assigned to Product X?")
    with col2:
        model_choice = st.selectbox("Model", options=["Text to SQL", "RAG"])
        

    if not user_question:
        return

    decision = llm_to_decide_tool(model_choice)

    if decision == 'text to sql':
        sql_query, result = just_ask_text_to_sql_report(conn, user_question)
        with st.expander("Show SQL query", expanded=False):
            st.code(sql_query, language="sql")
    else:
        result = just_ask_rag_report(user_question)

    st.write(result)
