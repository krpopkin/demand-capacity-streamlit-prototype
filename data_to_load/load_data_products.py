import pandas as pd
from sqlalchemy import create_engine, text
import os
from db import get_engine

# --- Path to excel file and create dataframe ---
excel_path = r"C:\Users\krpop\Documents\KenP\Applications-Python\demand-capacity2\data_to_load\products.xlsx"
df = pd.read_excel(excel_path, sheet_name=0)

# --- Connect to DB ---
engine = get_engine()

# --- Define insert statement explicitly ---
insert_sql = text("""
    INSERT INTO products (name, manager, technology_executive)
    VALUES (:name, :manager, :technology_executive)
""")

# --- Insert each row explicitly ---
with engine.begin() as conn:
    for row in df.itertuples(index=False, name=None):
        conn.execute(insert_sql, {
            "name": row[0],
            "manager": row[1],
            "technology_executive": row[2]
        })

print("✅ Data inserted successfully.")
