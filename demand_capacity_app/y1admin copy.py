import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import sqlalchemy

# Load existing products from the database
def load_products(conn):
    return pd.read_sql("SELECT name, manager, technology_executive FROM products", conn)

# Save updated products into the database
def save_products(conn, df):
    try:
        # Delete existing rows
        conn.execute(sqlalchemy.text("DELETE FROM products"))
        conn.commit()

        # Insert updated rows
        for _, row in df.iterrows():
            if all(pd.notnull([row["name"], row["manager"], row["technology_executive"]])):
                conn.execute(
                    sqlalchemy.text("""
                        INSERT INTO products (name, manager, technology_executive)
                        VALUES (:name, :manager, :technology_executive)
                    """),
                    {
                        "name": row["name"],
                        "manager": row["manager"],
                        "technology_executive": row["technology_executive"]
                    }
                )

        conn.commit()
        st.success("✅ Saved successfully.")
    except Exception as e:
        st.error(f"❌ Failed to save products: {e}")

# Main admin page with tabs
def show(conn):
    st.title("Welcome to the Admin page")

    if not conn:
        st.warning("No database connection.")
        return

    tab1, tab2, tab3 = st.tabs(["Products", "Roles", "Team Members"])

    # --- PRODUCTS TAB ---
    with tab1:
        st.subheader("Products")

        try:
            df = load_products(conn)
        except Exception:
            df = pd.DataFrame(columns=["name", "manager", "technology_executive"])

        # Add a blank row for new data entry
        df = pd.concat([df, pd.DataFrame([{"name": "", "manager": "", "technology_executive": ""}])], ignore_index=True)

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(editable=True)
        gb.configure_grid_options(stopEditingWhenGridLosesFocus=True)
        grid_options = gb.build()

        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            height=400,
            fit_columns_on_grid_load=True,
            enable_enterprise_modules=False,
            allow_unsafe_jscode=True,
        )

        updated_df = grid_response["data"]
        updated_df = updated_df[updated_df["name"].str.strip() != ""]

        if st.button("💾 Save Products"):
            if updated_df.empty:
                st.warning("No valid products to save.")
            else:
                save_products(conn, updated_df)

    # --- ROLES TAB ---
    with tab2:
        st.subheader("Roles")
        st.write("🔧 Roles grid will go here.")

    # --- TEAM MEMBERS TAB ---
    with tab3:
        st.subheader("Team Members")
        st.write("👥 Team members grid will go here.")
