import streamlit as st
from shared_grid import (
    render_tab_with_grid, render_skills_matrix_grid,
)

def show(engine):
    st.title("📊 Capacity")
    st.markdown("Across the tabs below you can add, rename, and deactivate, Products, Roles, and \
        Team Members.  In the Skills Matrix you can designate if a team member is qualified, \
        building, or underperforming in each role you give them.")

    if engine is None:
        st.warning("No database connection.")
        return

    tab1, tab2, tab3 = st.tabs(["Roles", "Team Members", "Skills Matrix"])

    with tab1:
        with engine.connect() as conn:
            render_tab_with_grid(
                "Roles",
                "roles",
                ["name", "description"],
                conn,
            )

    with tab2:
        with engine.connect() as conn:
            render_tab_with_grid(
                "Team Members",
                "teammembers",
                ["name", "manager", "level"],
                conn,
            )
            
    with tab3:
        with engine.connect() as conn:
            render_skills_matrix_grid(conn)
