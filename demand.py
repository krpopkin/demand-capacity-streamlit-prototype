import streamlit as st
from shared_grid import render_assignments_grid

def show(engine):
    st.title("📝 Demand")
    st.markdown("You can use the table below to assign roles to team members for each product. \
        Click ➕ to add rows, ❌ to mark inactive, and 💾 to save your changes.")

    if engine is None:
        st.warning("No database connection.")
        return

    # Establish connection from engine
    with engine.connect() as conn:
        render_assignments_grid(conn)