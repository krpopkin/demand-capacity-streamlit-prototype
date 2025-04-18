import streamlit as st
from shared_grid import render_tab_with_grid

def show(conn):
    st.title("Welcome to the Admin page")

    if not conn:
        st.warning("No database connection.")
        return

    tab1, tab2, tab3 = st.tabs(["Products", "Roles", "Team Members"])

    with tab1:
        render_tab_with_grid(
            tab_title="Products",
            table_name="products",
            editable_fields=["name", "manager", "technology_executive"],
            conn=conn
        )

    with tab2:
        render_tab_with_grid(
            tab_title="Roles",
            table_name="roles",
            editable_fields=["name", "description"],
            conn=conn
        )

    with tab3:
        render_tab_with_grid(
            tab_title="Team Members",
            table_name="teammembers",
            editable_fields=["name", "manager", "level"],
            conn=conn
        )
