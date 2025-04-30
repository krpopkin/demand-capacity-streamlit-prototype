import streamlit as st
from shared_grid import render_tab_with_grid, render_assignments_grid

def show(engine):
    st.title("📝 Demand")
    st.markdown("You can use the table below to assign roles to team members for each product. \
        Click ➕ to add rows, ❌ to mark inactive, and 💾 to save your changes.")

    if engine is None:
        st.warning("No database connection.")
        return
    
    tab1, tab2 = st.tabs(["Products", "Assignments"])

    with tab1:
        with engine.connect() as conn:
            render_tab_with_grid(
                "Products",
                "products",
                ["name", "manager", "technology_executive"],
                conn
            )
            
    with tab2:
        with engine.connect() as conn:
            render_assignments_grid(conn)