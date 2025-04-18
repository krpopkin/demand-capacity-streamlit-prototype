import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import sqlalchemy
from sqlalchemy import text
import json

def log_history(conn, table_name, operation, old_data=None, new_data=None):
    conn.execute(
        sqlalchemy.text("""
            INSERT INTO history_log (table_name, operation, old_data, new_data)
            VALUES (:table_name, :operation, :old_data, :new_data)
        """),
        {
            "table_name": table_name,
            "operation": operation,
            "old_data": json.dumps(old_data) if old_data else None,
            "new_data": json.dumps(new_data) if new_data else None
        }
    )
    conn.commit()

def render_tab_with_grid(tab_title, table_name, editable_fields, conn, on_save_cleanup=None):
    key = f"{table_name}_df"
    try:
        df = pd.read_sql(f"SELECT {', '.join(editable_fields)} FROM {table_name}", conn)
    except Exception:
        df = pd.DataFrame(columns=editable_fields)

    df["delete"] = False
    st.session_state[key] = df

    if st.button(f"➕ Add Row to {tab_title}"):
        new_row = {field: "" for field in editable_fields}
        new_row["delete"] = False
        st.session_state[key] = pd.concat([st.session_state[key], pd.DataFrame([new_row])], ignore_index=True)

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
    )

    updated_df = grid_response["data"]
    if "delete" not in updated_df.columns:
        updated_df["delete"] = False

    updated_df = updated_df[(updated_df[editable_fields[0]].str.strip() != "")]

    if st.button(f"💾 Save {tab_title}"):
        try:
            existing_df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            conn.execute(sqlalchemy.text(f"DELETE FROM {table_name}"))
            conn.commit()

            # Log deletes
            for _, row in existing_df.iterrows():
                log_history(conn, table_name, "DELETE", old_data=row.to_dict())

            # Filter out checked deletes from updated_df
            saved_df = updated_df[updated_df["delete"] == False].drop(columns=["delete"])

            for _, row in saved_df.iterrows():
                conn.execute(
                    sqlalchemy.text(f"""
                        INSERT INTO {table_name} ({', '.join(editable_fields)})
                        VALUES ({', '.join([f':{f}' for f in editable_fields])})
                    """),
                    {field: row[field] for field in editable_fields}
                )
                log_history(conn, table_name, "INSERT", new_data=row.to_dict())

            conn.commit()
            st.success(f"✅ {tab_title} saved successfully.")
            st.session_state[key] = saved_df

            if on_save_cleanup:
                on_save_cleanup(conn, saved_df)

        except Exception as e:
            st.error(f"❌ Failed to save {tab_title}: {e}")

def render_teammember_roles_grid(tab_title, table_name, conn):
    st.subheader(tab_title)

    try:
        teammembers_df = pd.read_sql("SELECT id, name FROM teammembers", conn)
        roles_df = pd.read_sql("SELECT id, name FROM roles", conn)
        teammembers_map = dict(teammembers_df.values)
        roles_map = dict(roles_df.values)
    except Exception:
        st.error("❌ Failed to load team members or roles.")
        return

    skill_levels = ["qualified", "building", "under performing"]
    teammembers_rev = {v: k for k, v in teammembers_map.items()}
    roles_rev = {v: k for k, v in roles_map.items()}

    key = f"{table_name}_df"
    try:
        raw_df = pd.read_sql("""
            SELECT tr.id, t.name AS team_member, r.name AS role, tr.skill_level
            FROM teammember_roles tr
            JOIN teammembers t ON tr.teammember_id = t.id
            JOIN roles r ON tr.roles_id = r.id
        """, conn)
    except Exception:
        raw_df = pd.DataFrame(columns=["team_member", "role", "skill_level"])

    raw_df["delete"] = False
    st.session_state[key] = raw_df

    if st.button(f"➕ Add Row to {tab_title}"):
        st.session_state[key] = pd.concat([
            st.session_state[key],
            pd.DataFrame([{"team_member": "", "role": "", "skill_level": "", "delete": False}])
        ], ignore_index=True)

    gb = GridOptionsBuilder.from_dataframe(st.session_state[key])
    gb.configure_column("team_member", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": list(teammembers_rev.keys())})
    gb.configure_column("role", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": list(roles_rev.keys())})
    gb.configure_column("skill_level", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": skill_levels})
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
    )

    updated_df = grid_response["data"]
    if "delete" not in updated_df.columns:
        updated_df["delete"] = False

    updated_df = updated_df[
        (updated_df["team_member"].str.strip() != "") &
        (updated_df["role"].str.strip() != "")
    ]

    if st.button(f"💾 Save {tab_title}"):
        try:
            existing_rows = pd.read_sql("""
                SELECT tr.id, t.name AS team_member, r.name AS role, tr.skill_level
                FROM teammember_roles tr
                JOIN teammembers t ON tr.teammember_id = t.id
                JOIN roles r ON tr.roles_id = r.id
            """, conn)

            conn.execute(sqlalchemy.text(f"DELETE FROM {table_name}"))
            conn.commit()

            for _, row in existing_rows.iterrows():
                log_history(conn, table_name, "DELETE", old_data=row.to_dict())

            rows_to_save = updated_df[updated_df["delete"] == False].drop(columns=["delete"])

            for _, row in rows_to_save.iterrows():
                conn.execute(
                    sqlalchemy.text(f"""
                        INSERT INTO {table_name} (teammember_id, roles_id, skill_level)
                        VALUES (:teammember_id, :roles_id, :skill_level)
                    """),
                    {
                        "teammember_id": teammembers_rev.get(row["team_member"]),
                        "roles_id": roles_rev.get(row["role"]),
                        "skill_level": row["skill_level"]
                    }
                )
                log_history(conn, table_name, "INSERT", new_data=row.to_dict())

            conn.commit()
            st.success(f"✅ {tab_title} saved successfully.")
            st.session_state[key] = rows_to_save

        except Exception as e:
            st.error(f"❌ Failed to save {tab_title}: {e}")

def cleanup_teammember_roles_by_teammember(conn, updated_df):
    valid_names = updated_df["name"].dropna().unique().tolist()
    conn.execute(sqlalchemy.text("""
        DELETE FROM teammember_roles
        WHERE teammember_id IN (
            SELECT id FROM teammembers
            WHERE name NOT IN :valid_names
        )
    """), {"valid_names": tuple(valid_names)})
    conn.commit()

def cleanup_teammember_roles_by_role(conn, updated_df):
    valid_names = updated_df["name"].dropna().unique().tolist()
    conn.execute(sqlalchemy.text("""
        DELETE FROM teammember_roles
        WHERE roles_id IN (
            SELECT id FROM roles
            WHERE name NOT IN :valid_names
        )
    """), {"valid_names": tuple(valid_names)})
    conn.commit()
    
def render_assignments_grid(conn):
    st.subheader("Assignments")

    # Build lookup dictionaries from the database
    product_map = dict(conn.execute(text("SELECT name, id FROM products")).fetchall())
    role_map = dict(conn.execute(text("SELECT name, id FROM roles")).fetchall())
    team_map = dict(conn.execute(text("SELECT name, id FROM teammembers")).fetchall())

    product_names = list(product_map.keys())
    role_names = list(role_map.keys())
    team_names = list(team_map.keys())

    # Load current assignments into session state
    key = "assignments_df"
    if key not in st.session_state:
        result = conn.execute(text("""
            SELECT p.name AS product, r.name AS role, t.name AS team_member, a.allocation
            FROM assignments a
            JOIN products p ON a.product_id = p.id
            JOIN roles r ON a.role_id = r.id
            JOIN teammembers t ON a.teammember_id = t.id
            ORDER BY a.id
        """)).fetchall()
        df = pd.DataFrame(result, columns=["product", "role", "team_member", "allocation"])
        df["delete"] = False
        st.session_state[key] = df

    df = st.session_state[key]

    # Add Row Button
    if st.button("➕ Add Row to Assignments"):
        new_row = {"product": "", "role": "", "team_member": "", "allocation": "", "delete": False}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        st.session_state[key] = df

    # Configure grid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("product", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": product_names})
    gb.configure_column("role", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": role_names})
    gb.configure_column("team_member", editable=True, cellEditor="agSelectCellEditor", cellEditorParams={"values": team_names})
    gb.configure_column("allocation", editable=True)
    gb.configure_column("delete", header_name="❌ Delete", editable=True, checkbox=True)
    gb.configure_grid_options(singleClickEdit=True, stopEditingWhenCellsLoseFocus=True)
    grid_options = gb.build()

    # Show editable grid
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.VALUE_CHANGED,   # Live changes
        data_return_mode=DataReturnMode.AS_INPUT,   # No Update button
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        editable=True,
        height=400,
        key="assignments_grid"
)

    updated_df = grid_response["data"]

    # Save Button
    if st.button("💾 Save Assignments"):
        # Filter valid rows
        valid_rows = updated_df[
            (updated_df["product"].str.strip() != "") &
            (updated_df["role"].str.strip() != "") &
            (updated_df["team_member"].str.strip() != "") &
            (updated_df["allocation"] != "") &
            (~updated_df["delete"])
        ]

        # Clear existing data
        conn.execute(text("DELETE FROM assignments"))

        # Re-insert all valid rows
        for _, row in valid_rows.iterrows():
            conn.execute(text("""
                INSERT INTO assignments (product_id, role_id, teammember_id, allocation)
                VALUES (:product_id, :role_id, :teammember_id, :allocation)
            """), {
                "product_id": product_map[row["product"]],
                "role_id": role_map[row["role"]],
                "teammember_id": team_map[row["team_member"]],
                "allocation": row["allocation"]
            })
            log_history(conn, "assignments", "insert", None)

        conn.commit()
        st.session_state[key] = valid_rows.drop(columns=["delete"])
        st.success("✅ Assignments saved successfully.")

