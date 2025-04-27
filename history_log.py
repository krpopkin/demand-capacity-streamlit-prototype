import streamlit as st
import pandas as pd
import sqlalchemy
import json

def log_history(conn, table_name, operation, old_data=None, new_data=None, record_id=None):
    conn.execute(
        sqlalchemy.text("""
            INSERT INTO history_log (table_name, operation, record_id, old_data, new_data)
            VALUES (:table_name, :operation, :record_id, :old_data, :new_data)
        """),
        {
            "table_name": table_name,
            "operation": operation,
            "record_id": record_id,
            "old_data": json.dumps(old_data) if old_data else None,
            "new_data": json.dumps(new_data) if new_data else None
        }
    )
    
def show(conn):
    st.title("📜 History Log")
    st.markdown("At present this log only contains inserts and deletes.  If needed update tracking can be added.")
    if not conn:
        st.warning("No database connection.")
        return

    try:
        df = pd.read_sql("SELECT * FROM history_log ORDER BY timestamp DESC", conn)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        st.dataframe(df, use_container_width=True, height=600)
    except Exception as e:
        st.error(f"❌ Failed to load history log: {e}")
