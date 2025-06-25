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

def llm_to_decide_tool():
    #decision = 'text to sql'
    decision = 'RAG'
    return decision

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
    
    decision = llm_to_decide_tool()
    if decision == 'text to sql':
        result = just_ask_text_to_sql_report(conn, user_question)
    else:
        result = just_ask_rag_report(user_question)  
    
    st.write(result)