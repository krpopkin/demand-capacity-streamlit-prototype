from langchain.prompts import PromptTemplate
from langchain_google_vertexai import ChatVertexAI
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from db import get_engine
import streamlit as st
import make_answer_friendly

def just_ask_report(conn):
    #Intro (collapsible)
    with st.expander("Click for description", expanded=False):
        st.markdown(
            """
            The objective of 'Just Ask' is to enable a Q&A capability. This is experimental and 
            the answer you get is very dependent on how you word your question.

            For example, asking…
            'Who is working on Product X?' returns no results.  
            but rewording the question to…
            'Which team members are assigned to Product X?' returns the team members
            assigned to this product.  
            """)

    user_question = st.text_input(
        "Ask a question:",
        placeholder="e.g., Which team members are assigned to Product X?"
    )
    if not user_question:
        return

    with st.spinner("Thinking…"):
        try:
            # 1) Instantiate Gemini 1.5 Pro via ADC
            llm = ChatVertexAI(
                model="gemini-1.5-pro-002",
                temperature=0
            )

            # 2) Wrap your SQLAlchemy engine for LangChain
            engine = get_engine()
            db = SQLDatabase(engine)

            # 3) Build a custom prompt that uses {table_info}
            sql_prompt = PromptTemplate(
                input_variables=["input", "table_info", "dialect"],
                template="""
You are an expert SQL generator. Given the database schema (as table_info) and a user question,
output exactly one valid SQL query—no explanations, no Markdown fences.

Here are the tables and their columns:
{table_info}

User question:
{input}

Write a single SQL statement using {dialect} syntax and return only the SQL text.
"""
            )

            chain = SQLDatabaseChain.from_llm(
                llm=llm,
                db=db,
                prompt=sql_prompt,
                verbose=False
            )

            # 4) Run the chain; {table_info} and {dialect} will be auto‐filled for you
            raw_sql = chain.run(user_question)

            #st.success("Generated SQL:")
            #st.code(raw_sql)

            # 5) Execute that plain SQL against the database
            result = db.run(raw_sql)
            friendly_result = make_answer_friendly.format_result(user_question, result, llm)
            #st.success("Answer:")
            st.write(friendly_result)

        except Exception as e:
            st.error("❌ An error occurred while answering your question.")
            st.exception(e)
