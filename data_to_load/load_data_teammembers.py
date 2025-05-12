import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Database credentials ---
DB_USER = "postgres"
DB_PASS = "Wn8%21pL4%23tVx%403zQe"
DB_NAME = "demand_capacity"

def is_cloud_run():
    return "K_SERVICE" in os.environ

# --- Connection string setup ---
if is_cloud_run():
    DB_HOST = "/cloudsql/amw-dna-coe-working-ds-dev:us-central1:demand-capacity"
    conn_str = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?host={DB_HOST}"
else:
    DB_HOST = "130.211.120.38"
    DB_PORT = "5432"
    conn_str = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- CSV path ---
csv_path = r"C:\Users\krpop\Documents\KenP\Applications-Python\demand_capacity_app\data_to_load\teammembers.csv"

# --- Load CSV ---
df = pd.read_csv(csv_path)
df = df[["name", "manager", "level"]]

# --- SQLAlchemy engine ---
engine = create_engine(conn_str)

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
