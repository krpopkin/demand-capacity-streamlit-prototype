import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import io

def capacity_report(conn):
    # 1) Load raw tables
    assignments = pd.read_sql(
        "SELECT teammember_id, role_id, product_id, allocation "
        "FROM assignments WHERE is_active = TRUE",
        conn
    )
    teammembers = pd.read_sql(
        "SELECT id AS teammember_id, manager, name AS team_member, level "
        "FROM teammembers WHERE is_active = TRUE",
        conn
    )
    roles = pd.read_sql(
        "SELECT id AS role_id, name AS role "
        "FROM roles WHERE is_active = TRUE",
        conn
    )
    products = pd.read_sql(
        "SELECT id AS product_id, name AS product "
        "FROM products WHERE is_active = TRUE",
        conn
    )
    skills = pd.read_sql(
        "SELECT teammember_id, role_id, skill_level "
        "FROM skills_matrix WHERE is_active = TRUE",
        conn
    )

    # 2) Merge so df has manager, team_member, level, role, allocation, product, and skill_level
    df = (
        assignments
        .merge(teammembers, on="teammember_id", how="left")
        .merge(roles,       on="role_id",       how="left")
        .merge(products,    on="product_id",    how="left")
        .merge(skills,      on=["teammember_id","role_id"], how="left")
    )

    # 3) Build Notes text per team member
    def make_notes(group):
        parts = []
        for _, row in group.iterrows():
            pct = f"{row['allocation']*100:.0f}%"
            parts.append(f"{row['role']} for {row['product']}@{pct}")
        return "; ".join(parts)

    notes_df = (
        df
        .groupby(["manager","team_member","level"])
        .apply(make_notes)
        .reset_index(name="Notes")
    )

    # 4) Pivot allocations into role-columns
    pivot = df.pivot_table(
        index=["manager","team_member","level"],
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
        .rename(columns={
            "manager":     "Manager",
            "team_member": "Team Member",
            "level":       "Level"
        })
    )

    # 5) Pivot skill_level into hidden "<role>_skill" columns
    skill_pivot = df.pivot_table(
        index=["manager","team_member","level"],
        columns="role",
        values="skill_level",
        aggfunc="first",
        fill_value=None
    ).reindex(columns=all_roles)
    skill_pivot = skill_pivot.reset_index().rename(columns={
        "manager":     "Manager",
        "team_member": "Team Member",
        "level":       "Level"
    })
    skill_pivot = skill_pivot.rename(columns={r: f"{r}_skill" for r in all_roles})

    # 6) Blank out zeros → None for empty cells
    fixed_cols   = ["Team Member","Manager","Level"]
    dynamic_cols = [c for c in report.columns if c not in fixed_cols]
    report[dynamic_cols] = report[dynamic_cols].replace(0, None)

    # 7) Add per-row Remaining Capacity
    report["Rem Cap"] = 1 - report[all_roles].sum(axis=1, skipna=True)

    # 8) Merge in Notes & skill levels
    notes_df = notes_df.rename(columns={
        "manager":     "Manager",
        "team_member": "Team Member",
        "level":       "Level"
    })
    report = (
        report
        .merge(notes_df, on=fixed_cols, how="left")
        .merge(skill_pivot, on=fixed_cols, how="left")
    )

    # 9) Prepend Grand Total row
    grand = {col: report[col].sum(skipna=True) for col in all_roles}
    grand["Rem Cap"]       = report["Rem Cap"].sum(skipna=True)
    grand["Notes"]         = ""
    grand["Team Member"]   = "Grand Total"
    grand["Manager"]       = ""
    grand["Level"]         = ""
    for r in all_roles:
        grand[f"{r}_skill"] = None

    report = pd.concat(
        [pd.DataFrame([grand], columns=report.columns), report],
        ignore_index=True
    )

    # 10) Reorder so Rem Cap is the second, pinned column
    fixed   = ["Team Member","Manager","Level"]
    dynamic = [
        c for c in report.columns
        if c not in fixed + ["Notes","Rem Cap"]
        and not c.endswith("_skill")
    ]
    cols = (
        ["Team Member", "Rem Cap"]
        + fixed[1:]             # Manager, Level
        + dynamic               # all the role columns
        + ["Notes"]             # Notes after roles
        + [f"{r}_skill" for r in dynamic]
    )
    report = report[cols]

    # 11) Build AgGrid options
    gb = GridOptionsBuilder.from_dataframe(report)
    gb.configure_default_column(resizable=True, sortable=True, width=95, minWidth=95)

    # pin Team Member and Rem Cap
    gb.configure_column("Team Member", pinned="left", width=120, minWidth=120)
    gb.configure_column("Rem Cap", pinned="left", cellStyle=JsCode("""
        function(params) {
            // base styling: bold + grey
            var style = { fontWeight:'bold', backgroundColor:'#f0f0f0' };
            // if negative, make font red
            if (params.value < 0) { style.color = 'red'; }
            return style;
            }
    """))

    # configure Notes
    gb.configure_column(
        "Notes",
        wrapText=False,
        autoHeight=False,
        tooltipField="Notes",
        minWidth=200,
        flex=1,
    )

    # hide skill columns & style role cells
    for role in dynamic:
        gb.configure_column(f"{role}_skill", hide=True)
        gb.configure_column(role, cellStyle=JsCode(f"""
            function(params) {{
              var lvl = params.data['{role}_skill'];
              if (lvl==='qualified')      {{ return {{ backgroundColor:'#C6EFCE' }}; }}
              else if (lvl==='building')  {{ return {{ backgroundColor:'#FFEB9C' }}; }}
              else if (lvl==='under performing') {{ return {{ backgroundColor:'#FFC1C1' }}; }}
            }}
        """))

    grid_opts = gb.build()
    grid_opts["onFirstDataRendered"] = JsCode("function(params){params.api.sizeColumnsToFit();}")
    grid_opts["getRowStyle"] = JsCode("""
        function(params) {
          if (params.data && params.data['Team Member'] === 'Grand Total') {
            return { fontWeight:'bold', backgroundColor:'#f0f0f0' };
          }
        }
    """)

    # 12) Render the gridview
    AgGrid(
        report,
        gridOptions=grid_opts,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        height=250,
        theme="light"
    )

    # 13) Export to Excel button
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
        report.to_excel(writer, index=False, sheet_name="Capacity")
    towrite.seek(0)

    st.download_button(
        label="📥 Export to Excel",
        data=towrite,
        file_name="capacity_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )