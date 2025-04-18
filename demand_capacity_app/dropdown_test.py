import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

st.title("Dropdown Test Grid")

# Test data
df = pd.DataFrame({
    "product": ["Product A", "Product B"],
    "role": ["Role 1", "Role 2"],
    "team_member": ["Alice", "Bob"],
    "allocation": [0.5, 1.0],
    "delete": [False, False]
})

# Dropdown options
product_options = ["Product A", "Product B", "Product C"]
role_options = ["Role 1", "Role 2", "Role 3"]
team_member_options = ["Alice", "Bob", "Charlie"]

# Configure grid
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("product", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": product_options})
gb.configure_column("role", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": role_options})
gb.configure_column("team_member", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": team_member_options})
gb.configure_column("allocation", editable=True)
gb.configure_column("delete", editable=True, checkbox=True)
gb.configure_grid_options(
    stopEditingWhenCellsLoseFocus=True,
    singleClickEdit=True,
)

grid_options = gb.build()

# Render grid
AgGrid(
    df,
    gridOptions=grid_options,
    editable=True,
    update_mode=GridUpdateMode.MANUAL,
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True
)
