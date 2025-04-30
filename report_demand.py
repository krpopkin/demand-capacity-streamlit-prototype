from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import pandas as pd
import streamlit as st
import io

def demand_report(conn):
    # 1) Load raw tables
    assignments = pd.read_sql(
        "SELECT teammember_id, product_id, role_id, allocation "
        "FROM assignments WHERE is_active = TRUE",
        conn
    )
    teammembers = pd.read_sql(
        "SELECT id AS teammember_id, name AS team_member "
        "FROM teammembers WHERE is_active = TRUE",
        conn
    )
    products = pd.read_sql(
        "SELECT id AS product_id, name AS product, manager "
        "FROM products WHERE is_active = TRUE",
        conn
    )
    roles = pd.read_sql(
        "SELECT id AS role_id, name AS role "
        "FROM roles WHERE is_active = TRUE",
        conn
    )

    # 2) Merge so we have manager, product, team_member, role, allocation
    df = (
        assignments
        .merge(teammembers, on="teammember_id", how="left")
        .merge(products,    on="product_id",    how="left")
        .merge(roles,       on="role_id",       how="left")
    )

    # 3) Build Notes per manager+product
    def make_notes(g):
        parts = []
        for _, row in g.iterrows():
            pct = f"{row['allocation']*100:.0f}%"
            parts.append(f"{row['role']}: {row['team_member']}@{pct}")
        return "; ".join(parts)

    notes_df = (
        df
        .groupby(["manager", "product"])
        .apply(make_notes)
        .reset_index(name="Notes")
    )

    # 4) Pivot to get one row per Manager/Product, cols=roles
    pivot = df.pivot_table(
        index=["manager", "product"],
        columns="role",
        values="allocation",
        aggfunc="sum",
        fill_value=0
    )
    all_roles = roles["role"].tolist()
    report = (
        pivot
        .reindex(columns=all_roles, fill_value=0)
        .reset_index()
        .rename(columns={"manager":"Manager","product":"Product"})
    )

    # 5) Blank zeros → None
    fixed   = ["Product", "Manager"]              # <— switch order here
    dynamic = [c for c in report.columns if c not in fixed]
    report[dynamic] = report[dynamic].replace(0, None)

    # 6) Merge in Notes
    notes_df = notes_df.rename(columns={"manager":"Manager","product":"Product"})
    report = report.merge(notes_df, on=fixed, how="left")

    # 7) Add a per-row Total
    report["Total"] = report[dynamic].sum(axis=1, skipna=True)

    # 8) Prepend Grand Total row
    grand = {col: report[col].sum(skipna=True) for col in dynamic}
    grand["Notes"]       = ""
    grand["Total"]       = report["Total"].sum(skipna=True)
    grand["Manager"]     = "Grand Total"
    grand["Product"]     = ""
    report = pd.concat(
        [pd.DataFrame([grand], columns=report.columns), report],
        ignore_index=True
    )

    # 9) Reorder so Product is first, Manager second, then roles, then Notes & Total
    dynamic = [c for c in report.columns if c not in fixed + ["Notes","Total"]]
    report = report[fixed + dynamic + ["Notes", "Total"]]

    # 10) Build AgGrid options
    gb = GridOptionsBuilder.from_dataframe(report)
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        width=95,
        minWidth=95
    )
    
    gb.configure_column("Notes",  wrapText=False,  autoHeight=False, maxWidth=200, tooltipField="Notes")
    
    # pin only Product
    gb.configure_column("Product", pinned="left", width=120, minWidth=120)
    # style the Total column
    gb.configure_column("Total", cellStyle=JsCode("""
      function(params) {
        return { fontWeight:'bold', backgroundColor:'#f0f0f0' };
      }
    """))
    grid_opts = gb.build()

    # 11) Auto-fit & Grand Total styling
    grid_opts["onFirstDataRendered"] = JsCode("""
    function(params) {
      params.api.sizeColumnsToFit();
    }
    """)
    grid_opts["getRowStyle"] = JsCode("""
    function(params) {
      if (params.data && params.data.Manager === 'Grand Total') {
        return { fontWeight:'bold', backgroundColor:'#f0f0f0' };
      }
    }
    """)

    # 12) Render at height=250
    AgGrid(
        report,
        gridOptions=grid_opts,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        height=250,
        theme="light"
    )
    
    #13 ─── Export to Excel button ────────────────────────────────────────
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
        report.to_excel(writer, index=False, sheet_name="Demand")
    towrite.seek(0)

    st.download_button(
        label="📥 Export to Excel",
        data=towrite,
        file_name="demand_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )