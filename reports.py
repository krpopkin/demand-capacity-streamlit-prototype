import streamlit as st
from report_demand import demand_report
from report_capacity import capacity_report
from report_just_ask_choose_tool import just_ask_choose_tool_report

def show(engine):
    st.title("📒Reports")
    # st.markdown('For the Demand and Capacity reports you can hover over the Notes field to see the \
    #             truncated text.  The Capacity reports cell color is green if the team member is "qualified", \
    #             yellow if the team member is "building", and red if the team member is "underperforming" \
    #             for a given skill')
    
    if engine is None:
        st.warning("No database connection.")
        return

    tab1, tab2, tab3 = st.tabs(["Demand", "Capacity", "Just ask"])

    with tab1:
        with engine.connect() as conn:
            demand_report(conn)

    with tab2:
        with engine.connect() as conn:
            capacity_report(conn)
                
    with tab3:
        with engine.connect() as conn:
            just_ask_choose_tool_report(conn)