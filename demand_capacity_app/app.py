import streamlit as st
import demand
import reports
import admin
import history_log  # ⬅️ New module
from db import get_connection

st.set_page_config(page_title="Demand Capacity App", layout="wide")
st.sidebar.title("Navigation")

# Page Navigation
page = st.sidebar.radio("Go to", ["Demand", "Reports", "Admin", "History Log"])

# Connect to DB just-in-time
def connect_and_run(func):
    try:
        with get_connection() as conn:
            st.sidebar.success("✅ DB Connected")
            func(conn)
    except Exception as e:
        st.sidebar.error(f"❌ DB Connection failed: {e}")

# Pass the DB connection to each page
if page == "Demand":
    connect_and_run(demand.show)
elif page == "Reports":
    connect_and_run(reports.show)
elif page == "Admin":
    connect_and_run(admin.show)
elif page == "History Log":
    connect_and_run(history_log.show)
