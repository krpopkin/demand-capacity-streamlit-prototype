import streamlit as st
import pandas as pd
from db import get_connection

st.title("Demand Capacity")

try:
    conn = get_connection()
    df = pd.read_sql("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';", conn)
    conn.close()
    st.success("✅ Connected to PostgreSQL!")
    st.dataframe(df)
except Exception as e:
    st.error(f"❌ Failed to connect: {e}")
