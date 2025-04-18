import streamlit as st

def show(conn):
    st.title("Welcome to the Demand page")
    if conn:
        st.write("🔗 Database connection is active.")
    else:
        st.write("⚠️ No DB connection.")
