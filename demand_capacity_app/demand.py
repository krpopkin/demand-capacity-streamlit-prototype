import streamlit as st
from shared_grid import render_assignments_grid

def show(conn):
    st.title("Welcome to the Demand page")
    if not conn:
        st.warning("No database connection.")
        return

    render_assignments_grid(conn)
