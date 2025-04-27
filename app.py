import streamlit as st
import demand
import reports
import admin
import history_log
from db import get_engine

st.set_page_config(page_title="Demand Capacity App", layout="wide")
st.sidebar.title("Navigation")

engine = get_engine()

# Test DB connection
try:
    with engine.connect() as conn:
        st.sidebar.success("✅ DB Connected")
except Exception as e:
    engine = None
    st.sidebar.error(f"❌ DB Connection failed: {e}")

# Page Navigation
page = st.sidebar.radio("Go to", ["Demand", "Reports", "Admin", "History Log"])

# Pass engine to all modules
if page == "Demand":
    demand.show(engine)
elif page == "Reports":
    reports.show(engine)
elif page == "Admin":
    admin.show(engine)
elif page == "History Log":
    history_log.show(engine)