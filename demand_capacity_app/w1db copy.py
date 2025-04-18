# database located in working-ds-dev cloudsql.
# https://console.cloud.google.com/sql/instances/demand-capacity/overview?invt=AbuvkQ&project=amw-dna-coe-working-ds-dev
import os
import sqlalchemy

DB_USER = "postgres"
DB_PASS = "Wn8%21pL4%23tVx%403zQe"
DB_NAME = "demand_capacity"
DB_PORT = "5432"

ON_CLOUD_RUN = os.environ.get("K_SERVICE") is not None

if ON_CLOUD_RUN:
    DB_HOST = "/cloudsql/amw-dna-coe-working-ds-dev:us-central1:demand-capacity"
    DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?host={DB_HOST}"
else:
    DB_HOST = "130.211.120.38"
    DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_connection():
    engine = sqlalchemy.create_engine(DB_URI)
    return engine.connect()

