import streamlit as st
import pandas as pd

def show(conn):
    st.title("📜 History Log")

    if not conn:
        st.warning("No database connection.")
        return

    try:
        df = pd.read_sql("SELECT * FROM history_log ORDER BY timestamp DESC", conn)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.rename(columns={
            "table_name": "Table",
            "operation": "Action",
            "record_id": "Record ID",
            "old_data": "Before",
            "new_data": "After",
            "timestamp": "Timestamp"
        })

        st.dataframe(df, use_container_width=True, height=600)
    except Exception as e:
        st.error(f"❌ Failed to load history log: {e}")
