import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

def summary_report(conn):
    # ─── 1) Pull & sort all active roles ─────────────────────────────
    roles_df = pd.read_sql(
        "SELECT id, name FROM roles WHERE is_active = TRUE",
        conn
    ).sort_values("name")
    role_ids   = roles_df["id"].tolist()
    role_names = roles_df["name"].tolist()

    # ─── 2) Compute Demand (sum allocations) & Capacity (count skills) ─
    alloc_df   = pd.read_sql(
        "SELECT role_id, allocation FROM assignments WHERE is_active = TRUE",
        conn
    )
    demand_s   = alloc_df.groupby("role_id")["allocation"].sum()

    skills_df  = pd.read_sql(
        "SELECT role_id FROM skills_matrix WHERE is_active = TRUE",
        conn
    )
    capacity_s = skills_df["role_id"].value_counts()

    # ─── 3) Build the two rows, blanking out zeros ───────────────────
    demand_row   = {"Area": "Demand"}
    capacity_row = {"Area": "Capacity"}
    for rid, name in zip(role_ids, role_names):
        dv = float(demand_s.get(rid, 0))
        cv = int(capacity_s.get(rid, 0))
        demand_row[name]   = dv if dv != 0 else None
        capacity_row[name] = cv if cv != 0 else None

    # ─── 4) Prepare the pinned-bottom “Total” = Demand – Capacity ────
    total_row = {"Area": "Total"}
    for name in role_names:
        d = demand_row[name]   or 0
        c = capacity_row[name] or 0
        diff = d - c
        total_row[name] = diff if diff != 0 else None

    # ─── 5) Build DataFrame (without Total in the main df) ──────────
    df = pd.DataFrame([demand_row, capacity_row])
    df = df[["Area"] + role_names]

    # ─── 6) Configure AgGrid just like capacity_report ──────────────
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        width=120,
        minWidth=100
    )
    # pin Area
    gb.configure_column(
        "Area",
        pinned="left",
        width=120,
        minWidth=120,
        editable=False
    )

    # cellStyle: gray background + bold, maroon font if negative (only on pinned row)
    cell_style = JsCode("""
    function(params) {
      if (params.node.rowPinned) {
        const s = { fontWeight:'bold', backgroundColor:'#f0f0f0' };
        if (params.value < 0) { s.color = 'red'; }
        return s;
      }
    }
    """)
    for col in role_names:
        gb.configure_column(col, editable=False, cellStyle=cell_style)

    # push pinned bottom row + auto-fit hook into builder
    gb.configure_grid_options(
        pinnedBottomRowData=[total_row],
        onFirstDataRendered=JsCode("function(params){params.api.sizeColumnsToFit();}")
    )

    grid_opts = gb.build()

    # ─── 7) Render with the same flags & theme as capacity_report ───
    AgGrid(
        df,
        gridOptions=grid_opts,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        theme="light",
        height=120,
        fit_columns_on_grid_load=False  # we've already auto-fit onFirstDataRendered
    )
