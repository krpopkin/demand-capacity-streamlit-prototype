import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Database credentials ---
DB_USER = "postgres"
DB_PASS = "Wn8%21pL4%23tVx%403zQe"
DB_NAME = "demand_capacity"

def is_cloud_run():
    return "K_SERVICE" in os.environ

# --- Connection string based on environment ---
if is_cloud_run():
    DB_HOST = "/cloudsql/amw-dna-coe-working-ds-dev:us-central1:demand-capacity"
    conn_str = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?host={DB_HOST}"
else:
    DB_HOST = "130.211.120.38"
    DB_PORT = "5432"
    conn_str = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- CSV path ---
csv_path = r"C:\Users\krpop\Documents\KenP\Applications-Python\demand_capacity_app\data_to_load\unit_test_data\unit_test_roles.csv"

# --- Load CSV ---
df = pd.read_csv(csv_path)
df = df[["name", "description"]]

# --- SQLAlchemy engine ---
engine = create_engine(conn_str)

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
