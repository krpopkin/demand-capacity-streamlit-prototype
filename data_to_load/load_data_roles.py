import pandas as pd
from sqlalchemy import create_engine, text
import os
from db import get_engine

# --- Path to excel file and create dataframe ---
excel_path = r"C:\Users\krpop\Documents\KenP\Applications-Python\demand-capacity2\data_to_load\roles.xlsx"
df = pd.read_excel(excel_path, sheet_name=0)

# --- Connect to DB ---
engine = get_engine()

# --- SQL insert statement ---
insert_sql = text("""
    INSERT INTO roles (name, description)
    VALUES (:name, :description)
""")

# --- Insert rows one by one ---
with engine.begin() as conn:
    for row in df.itertuples(index=False, name=None):
        conn.execute(insert_sql, {
            "name": row[0],
            "description": row[1]
        })

print("✅ Roles loaded successfully.")
