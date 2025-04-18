import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import sqlalchemy

def render_tab_with_grid(tab_title, table_name, editable_fields, conn):
        # Initialize session state for this tab if needed
    key = f"{table_name}_df"
    if key not in st.session_state:
        try:
            df = pd.read_sql(f"SELECT {', '.join(editable_fields)} FROM {table_name}", conn)
        except Exception:
            df = pd.DataFrame(columns=editable_fields)
        df["delete"] = False
        st.session_state[key] = df

    df = st.session_state[key]
    if "delete" not in df.columns:
        df["delete"] = False

    # Add row button
    if st.button(f"➕ Add Row to {tab_title}"):
        new_row = {field: "" for field in editable_fields}
        new_row["delete"] = False
        st.session_state[key] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Grid config
    gb = GridOptionsBuilder.from_dataframe(st.session_state[key])
    gb.configure_default_column(editable=True)
    gb.configure_column("delete", header_name="❌ Delete", editable=True, checkbox=True)
    gb.configure_grid_options(stopEditingWhenGridLosesFocus=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        st.session_state[key],
        gridOptions=grid_options,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        height=400,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        allow_unsafe_jscode=True,
        key=f"{table_name}_grid_{len(st.session_state[key])}",  # <- this forces rerender
    )

    updated_df = grid_response["data"]
    
    # Make sure 'delete' column is present
    if "delete" not in updated_df.columns:
        updated_df["delete"] = False
    
    updated_df = updated_df[(updated_df[editable_fields[0]].str.strip() != "") & (updated_df["delete"] == False)]

    if st.button(f"💾 Save {tab_title}"):
        if updated_df.empty:
            st.warning(f"No valid {tab_title.lower()} to save.")
        else:
            updated_df = updated_df.drop(columns=["delete"])
            try:
                conn.execute(sqlalchemy.text(f"DELETE FROM {table_name}"))
                conn.commit()
                for _, row in updated_df.iterrows():
                    placeholders = ", ".join([f":{f}" for f in editable_fields])
                    field_list = ", ".join(editable_fields)
                    conn.execute(
                        sqlalchemy.text(f"INSERT INTO {table_name} ({field_list}) VALUES ({placeholders})"),
                        {field: row[field] for field in editable_fields}
                    )
                conn.commit()
                st.session_state[key] = updated_df
                st.success(f"✅ {tab_title} saved successfully.")
                st.rerun()  # 🔁 Force UI refresh so deleted row disappears
            except Exception as e:
                st.error(f"❌ Failed to save {tab_title.lower()}: {e}")


