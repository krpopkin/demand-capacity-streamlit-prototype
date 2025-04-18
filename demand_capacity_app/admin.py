import streamlit as st
from shared_grid import (
    render_tab_with_grid,
    render_teammember_roles_grid,
    cleanup_teammember_roles_by_teammember,
    cleanup_teammember_roles_by_role,
)

def show(conn):
    st.title("Welcome to the Admin page")

    if not conn:
        st.warning("No database connection.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["Products", "Roles", "Team Members", "Skills Matrix"])

    with tab1:
        render_tab_with_grid(
            "Products",
            "products",
            ["name", "manager", "technology_executive"],
            conn
        )

    with tab2:
        render_tab_with_grid(
            "Roles",
            "roles",
            ["name", "description"],
            conn,
            on_save_cleanup=cleanup_teammember_roles_by_role
        )

    with tab3:
        render_tab_with_grid(
            "Team Members",
            "teammembers",
            ["name", "manager", "level"],
            conn,
            on_save_cleanup=cleanup_teammember_roles_by_teammember
        )

    with tab4:
        render_teammember_roles_grid("Skills Matrix", "teammember_roles", conn)
