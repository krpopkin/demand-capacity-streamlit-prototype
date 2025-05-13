import pandas as pd
from sqlalchemy import create_engine, text
import os
from db import get_engine

# --- Path to excel file and create dataframe ---
excel_path = r"C:\Users\krpop\Documents\KenP\Applications-Python\demand-capacity2\data_to_load\teammembers.xlsx"
df = pd.read_excel(excel_path, sheet_name=0)

# --- Connect to DB ---
engine = get_engine()


# --- Insert SQL ---
insert_sql = text("""
    INSERT INTO teammembers (name, manager, level)
    VALUES (:name, :manager, :level)
""")

# --- Execute insert row-by-row ---
with engine.begin() as conn:
    for row in df.itertuples(index=False, name=None):
        conn.execute(insert_sql, {
            "name": row[0],
            "manager": row[1],
            "level": row[2]
        })

print("✅ Team members loaded successfully.")
