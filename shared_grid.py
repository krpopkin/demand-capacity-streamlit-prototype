import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
import sqlalchemy
from sqlalchemy import text
import json
from collections import defaultdict

# ---- HISTORY LOGGING ----
def log_history(conn, table_name, operation, old_data=None, new_data=None, record_id=None):
    conn.execute(
        sqlalchemy.text("""
            INSERT INTO history_log (table_name, operation, record_id, old_data, new_data)
            VALUES (:table_name, :operation, :record_id, :old_data, :new_data)
        """),
        {
            "table_name": table_name,
            "operation": operation,
            "record_id": record_id,
            "old_data": json.dumps({k: str(v) for k, v in old_data.items()}) if old_data else None,
            "new_data": json.dumps({k: str(v) for k, v in new_data.items()}) if new_data else None,
        }
    )

# ---- GENERIC GRID FOR ADMIN TABS OF PRODUCTS AND ROLES ----
def render_tab_with_grid(
    tab_title,
    table_name,
    editable_fields,
    conn,
    on_save_cleanup=None
):
    key        = f"{table_name}_df"
    reload_key = f"{table_name}_grid_reload"

    # initialize reload counter
    if reload_key not in st.session_state:
        st.session_state[reload_key] = 0

    # load only active rows once
    if key not in st.session_state:
        cols_sql = ", ".join(["id"] + editable_fields)
        sql = f"""
            SELECT {cols_sql}
              FROM {table_name}
             WHERE is_active = TRUE
          ORDER BY id
        """
        rows = conn.execute(text(sql)).fetchall()
        df   = pd.DataFrame(rows, columns=["id"] + editable_fields)
        df["inactivate"] = False
        st.session_state[key] = df

    df = st.session_state[key]

    # Add & Save buttons
    col1, col2, _ = st.columns([1,1,1])
    with col1:
        if st.button(f"➕ Add Row to {tab_title}"):
            new = {f: "" for f in editable_fields}
            new.update({"id": None, "inactivate": False})
            st.session_state[key] = pd.concat(
                [df, pd.DataFrame([new])],
                ignore_index=True
            )
            st.session_state[reload_key] += 1
            st.rerun()
    with col2:
        save_clicked = st.button(f"💾 Save {tab_title}")

    # configure AgGrid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("id", width=50, hide=True)
    gb.configure_column("inactivate", header_name="❌ Inactivate", editable=True, checkbox=True)
    gb.configure_default_column(editable=True, width=225)
    gb.configure_grid_options(
        stopEditingWhenGridLosesFocus=True,
        singleClickEdit=True
    )

    grid = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        height=400,
        key=f"{key}_grid_{st.session_state[reload_key]}"
    )
    updated = pd.DataFrame(grid["data"])

    # drop any row where the first editable field is blank
    mask = updated[editable_fields[0]].astype(str).str.strip() != ""
    updated = updated[mask].reset_index(drop=True)

    if save_clicked:
        try:
            # partition rows
            to_inactivate = updated[(updated["inactivate"]) & updated["id"].notnull()]
            to_insert     = updated[(~updated["inactivate"]) & updated["id"].isnull()]
            to_update     = updated[(~updated["inactivate"]) & updated["id"].notnull()]

            with conn.begin():
                # 1) soft-inactivate
                for _, row in to_inactivate.iterrows():
                    conn.execute(
                        text(f"UPDATE {table_name} SET is_active = FALSE WHERE id = :id"),
                        {"id": row["id"]}
                    )
                    log_history(conn, table_name, "INACTIVATE", old_data={"id": row["id"]}, record_id=row["id"])

                # 2) insert new
                cols = ", ".join(editable_fields)
                vals = ", ".join(f":{f}" for f in editable_fields)
                for _, row in to_insert.iterrows():
                    params = {f: row[f] for f in editable_fields}
                    new_id = conn.execute(
                        text(f"""
                            INSERT INTO {table_name} ({cols})
                            VALUES ({vals})
                            RETURNING id
                        """),
                        params
                    ).scalar_one()
                    log_history(conn, table_name, "INSERT", new_data={**params, "id": new_id}, record_id=new_id)

                # 3) update existing
                set_clause = ", ".join(f"{f} = :{f}" for f in editable_fields)
                for _, row in to_update.iterrows():
                    params = {f: row[f] for f in editable_fields}
                    params["id"] = row["id"]
                    conn.execute(
                        text(f"UPDATE {table_name} SET {set_clause} WHERE id = :id"),
                        params
                    )
                    log_history(conn, table_name, "UPDATE", new_data={**params}, record_id=row["id"])

            # refresh
            del st.session_state[key]
            st.session_state[reload_key] += 1
            st.success(f"✅ {tab_title} saved successfully.")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to save {tab_title}: {e}")

# ----  SKILLS MATRIX GRID ----
def render_skills_matrix_grid(conn):
    """
    Displays:
      1) A selectbox to choose a Team Member
      2) An AgGrid showing active rows’ id, roles, skill levels, and an “❌ Inactivate” checkbox
      3) A single “Save Skills Matrix” button to INSERT new rows, UPDATE existing rows, or SOFT-INACTIVATE rows
      4) Logs history on each change via log_history()
    """
    data_key         = "skills_matrix_df"
    reload_key       = "skills_matrix_grid_reload"
    last_reload_key  = f"{data_key}_last_reload"

    # ─── init reload counter ──────────────────────────────────────────
    if reload_key not in st.session_state:
        st.session_state[reload_key] = 0

    # ─── lookup maps ─────────────────────────────────────────────────
    team_map = dict(conn.execute(text(
        "SELECT name, id FROM teammembers WHERE is_active = TRUE"
    )).fetchall())
    role_map = dict(conn.execute(text(
        "SELECT name, id FROM roles WHERE is_active = TRUE"
    )).fetchall())
    team_names = sorted(team_map.keys())

    # ─── layout: selector, add, save ─────────────────────────────────
    col1, col2, col3 = st.columns([2.25, 1.75, 2])
    with col1:
        selected_member = st.selectbox("tm", team_names, label_visibility="collapsed")
        prev = st.session_state.get("prev_selected_skills_member")
        if prev and prev != selected_member:
            st.session_state.pop(data_key, None)
            st.session_state[reload_key] += 1
            st.session_state["prev_selected_skills_member"] = selected_member
            st.rerun()
        else:
            st.session_state["prev_selected_skills_member"] = selected_member

    with col2:
        add_clicked = st.button("➕ Add Row to Skills Matrix")
    with col3:
        save_clicked = st.button("💾 Save Skills Matrix")

    if not selected_member:
        st.warning("Please select a team member.")
        return

    # ─── fetch fresh base DataFrame every run ─────────────────────────
    sql = """
        SELECT sm.id,
               r.name       AS role,
               sm.skill_level
          FROM skills_matrix sm
          JOIN roles r     ON sm.role_id = r.id
         WHERE sm.teammember_id = :tmid
           AND sm.is_active = TRUE
         ORDER BY sm.id
    """
    rows   = conn.execute(text(sql), {"tmid": team_map[selected_member]}).fetchall()
    base_df = pd.DataFrame(rows, columns=["id", "role", "skill_level"])
    base_df["inactivate"] = False

    # ─── initialize or refresh cache when reload_key bumps ────────────
    last = st.session_state.get(last_reload_key)
    now  = st.session_state[reload_key]
    if (data_key not in st.session_state) or (last != now):
        st.session_state[data_key]        = base_df.copy()
        st.session_state[last_reload_key] = now

    # ─── work off the cached DataFrame ───────────────────────────────
    df = st.session_state[data_key].reset_index(drop=True)

    # ─── add-row logic ───────────────────────────────────────────────
    if add_clicked:
        new = {"id": None, "role": "", "skill_level": "", "inactivate": False}
        st.session_state[data_key] = pd.concat(
            [df, pd.DataFrame([new])],
            ignore_index=True
        )
        # st.session_state[reload_key] += 1
        st.rerun()

    # ─── build AgGrid options ─────────────────────────────────────────
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("id", hide=True, header_name="ID", editable=False, width=50)
    gb.configure_column(
        "role",
        editable=True,
        width=300,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": sorted(role_map.keys())}
    )
    gb.configure_column(
        "skill_level",
        width=300,
        editable=True,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": ["qualified", "building", "under performing"]}
    )
    gb.configure_column("inactivate", header_name="❌ Inactivate", editable=True, checkbox=True)
    gb.configure_default_column(editable=True)
    gb.configure_grid_options(singleClickEdit=True, stopEditingWhenCellsLoseFocus=True)

    grid = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        height=350,
        key=f"{data_key}_grid_{selected_member}_{now}"
    )
    updated = pd.DataFrame(grid["data"])

    # ─── save logic ────────────────────────────────────────────────────
    if save_clicked:
        try:
            # 1) Soft-inactivate flagged existing rows
            to_inactivate = updated[(updated["inactivate"]) & (updated["id"].notnull())]
            for _, row in to_inactivate.iterrows():
                conn.execute(
                    text("UPDATE skills_matrix SET is_active = FALSE WHERE id = :id"),
                    {"id": row["id"]}
                )
                log_history(conn, "skills_matrix", "INACTIVATE", old_data={"id": row["id"]})

            # 2) Insert new rows
            to_insert = updated[(~updated["inactivate"]) & (updated["id"].isnull())]
            for _, row in to_insert.iterrows():
                new_id = conn.execute(
                    text("""INSERT INTO skills_matrix
                              (teammember_id, role_id, skill_level, is_active)
                            VALUES
                              (:tmid, :rid, :sl, TRUE)
                          RETURNING id"""),
                    {
                        "tmid": team_map[selected_member],
                        "rid":  role_map[row["role"]],
                        "sl":   row["skill_level"]
                    }
                ).scalar_one()
                log_history(
                    conn, "skills_matrix", "INSERT",
                    new_data={**row.to_dict(), "id": new_id}
                )

            # 3) Update existing rows
            to_update = updated[(~updated["inactivate"]) & (updated["id"].notnull())]
            for _, row in to_update.iterrows():
                conn.execute(
                    text("""UPDATE skills_matrix
                              SET role_id     = :rid,
                                  skill_level = :sl,
                                  is_active   = TRUE
                            WHERE id = :id"""),
                    {
                        "rid": role_map[row["role"]],
                        "sl":  row["skill_level"],
                        "id":  row["id"]
                    }
                )
                log_history(
                    conn, "skills_matrix", "UPDATE",
                    new_data=row.to_dict()
                )

            conn.commit()
            st.session_state.pop(data_key, None)
            st.session_state[reload_key] += 1
            st.success("✅ Skills matrix saved successfully.")
            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"❌ Failed to save skills matrix: {e}")


# ---- ASSIGNMENTS TAB ----
#########################################
def render_assignments_grid(conn):
    """
    Displays:
      1) A selectbox to choose a Product
      2) An AgGrid showing active rows’ id, roles, team members, allocation, and an ❌ Inactivate checkbox
      3) A single Save button to INSERT new rows, UPDATE existing rows, or SOFT-INACTIVATE rows
      4) Logs history on each change via log_history()
    """
    data_key        = "assignments_df"
    reload_key      = "assignments_grid_reload"
    last_reload_key = f"{data_key}_last_reload"

    # ─── init reload counter ──────────────────────────────────────────
    if reload_key not in st.session_state:
        st.session_state[reload_key] = 0

    # ─── lookup maps ──────────────────────────────────────────────────
    product_map = dict(conn.execute(text(
        "SELECT name, id FROM products WHERE is_active = TRUE"
    )).fetchall())
    role_map = dict(conn.execute(text(
        "SELECT name, id FROM roles WHERE is_active = TRUE"
    )).fetchall())
    team_map = dict(conn.execute(text(
        "SELECT name, id FROM teammembers WHERE is_active = TRUE"
    )).fetchall())

    # ─── build role→team_member map from skills_matrix ───────────────
    skill_map = defaultdict(list)
    skill_sql = """
        SELECT r.name AS role, t.name AS team_member
          FROM skills_matrix sm
          JOIN roles r        ON sm.role_id       = r.id
          JOIN teammembers t  ON sm.teammember_id = t.id
         WHERE sm.is_active = TRUE
    """
    for role_name, tm_name in conn.execute(text(skill_sql)).fetchall():
        skill_map[role_name].append(tm_name)
    skill_map = dict(skill_map)  # for JSON serialization

    # ─── selector / add / save layout ─────────────────────────────────
    col1, col2, col3 = st.columns([2.25, 1.75, 2])
    with col1:
        selected_product = st.selectbox(
            "Select product",
            sorted(product_map.keys()),
            label_visibility="collapsed"
        )
        prev = st.session_state.get("previous_selected_product")
        if prev and prev != selected_product:
            st.session_state.pop(data_key, None)
            st.session_state[reload_key] += 1
            st.session_state["previous_selected_product"] = selected_product
            st.rerun()
        st.session_state["previous_selected_product"] = selected_product

    if not selected_product:
        st.warning("Please select a product.")
        return

    with col2:
        add_clicked = st.button("➕ Add Row to Assignments")
    with col3:
        save_clicked = st.button("💾 Save Assignments")

    # ─── fetch fresh base DataFrame every run ─────────────────────────
    sql = """
        SELECT a.id,
               r.name   AS role,
               t.name   AS team_member,
               a.allocation
          FROM assignments a
          JOIN roles r        ON a.role_id       = r.id
          JOIN teammembers t  ON a.teammember_id = t.id
         WHERE a.product_id = :pid
           AND a.is_active  = TRUE
         ORDER BY a.id
    """
    rows    = conn.execute(text(sql), {"pid": product_map[selected_product]}).fetchall()
    base_df = pd.DataFrame(rows, columns=["id", "role", "team_member", "allocation"])
    base_df["inactivate"] = False

    # ─── init or refresh cache when reload_key bumps ───────────────────
    last = st.session_state.get(last_reload_key)
    now  = st.session_state[reload_key]
    if (data_key not in st.session_state) or (last != now):
        st.session_state[data_key]        = base_df.copy()
        st.session_state[last_reload_key] = now

    df = st.session_state[data_key].reset_index(drop=True)

    # ─── add-row logic ───────────────────────────────────────────────
    if add_clicked:
        new_row = {"id": None, "role": "", "team_member": "", "allocation": 0.25, "inactivate": False}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        st.session_state[data_key] = df
        #st.session_state[reload_key] += 1
        st.rerun()

    # ─── configure AgGrid ────────────────────────────────────────────
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("id", hide=True)
    gb.configure_column(
        "role",
        editable=True,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": sorted(role_map.keys())}
    )
    js_code = JsCode(f"""
    function(params) {{
      const skillMap = {json.dumps(skill_map)};
      const allTMs   = {json.dumps(sorted(team_map.keys()))};
      const role     = params.data.role;
      if (!role) return allTMs;
      return skillMap[role] || [];
    }}
    """)
    gb.configure_column(
        "team_member",
        editable=True,
        cellEditor="agRichSelectCellEditor",
        cellEditorParams={"values": js_code}
    )
    gb.configure_column("allocation", editable=True)
    gb.configure_column("inactivate", header_name="❌ Inactivate", editable=True, checkbox=True)
    gb.configure_grid_options(
        singleClickEdit=True,
        stopEditingWhenCellsLoseFocus=True,
        onCellValueChanged="params.api.stopEditing();"
    )

    grid = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        height=400,
        key=f"assignments_grid_{now}"
    )
    updated = pd.DataFrame(grid["data"])

    # ─── save logic ───────────────────────────────────────────────────
    if save_clicked:
        try:
            updated["allocation"] = updated["allocation"].replace("", 0.25)

            # 1) soft-inactivate flagged rows
            to_inactivate = updated[(updated["inactivate"]) & (updated["id"].notnull())]
            for _, row in to_inactivate.iterrows():
                conn.execute(
                    text("UPDATE assignments SET is_active = FALSE WHERE id = :id"),
                    {"id": row["id"]}
                )
                log_history(conn, "assignments", "INACTIVATE", old_data={"id": row["id"]})

            # 2) insert new rows
            to_insert = updated[(~updated["inactivate"]) & (updated["id"].isnull())]
            for _, row in to_insert.iterrows():
                new_id = conn.execute(
                    text("""
                        INSERT INTO assignments
                          (product_id, role_id, teammember_id, allocation)
                        VALUES
                          (:pid, :rid, :tid, :alloc)
                        RETURNING id
                    """),
                    {
                        "pid":   product_map[selected_product],
                        "rid":   role_map[row["role"]],
                        "tid":   team_map[row["team_member"]],
                        "alloc": row["allocation"]
                    }
                ).scalar_one()
                log_history(conn, "assignments", "INSERT", new_data={**row.to_dict(), "id": new_id})

            # 3) update existing rows
            to_update = updated[(~updated["inactivate"]) & (updated["id"].notnull())]
            for _, row in to_update.iterrows():
                conn.execute(
                    text("""
                        UPDATE assignments
                           SET role_id       = :rid,
                               teammember_id = :tid,
                               allocation     = :alloc,
                               is_active      = TRUE
                         WHERE id = :id
                    """),
                    {
                        "id":    row["id"],
                        "rid":   role_map[row["role"]],
                        "tid":   team_map[row["team_member"]],
                        "alloc": row["allocation"]
                    }
                )
                log_history(conn, "assignments", "UPDATE", new_data=row.to_dict())

            conn.commit()
            st.session_state.pop(data_key, None)
            st.session_state[reload_key] += 1
            st.success("✅ Assignments saved successfully.")
            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"❌ Failed to save assignments: {e}")
