import json
import pandas as pd
import sys
import os

# Add parent directory to Python path so that this script can find db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))
from db import get_connection

###############################################################################################
# Export all the data in the Demand-Capacity postgres sql tables into json files.  The json
# files are then used as input to create a vector database. 
###############################################################################################

# === Output file names per table ===
OUTPUT_FILES = {
    'assignments': 'RAG/02_exported_postgres_data/assignments.json',
    'products': 'RAG/02_exported_postgres_data/products.json',
    'roles': 'RAG/02_exported_postgres_data/roles.json',
    'skills_matrix': 'RAG/02_exported_postgres_data/skills_matrix.json',
    'teammembers': 'RAG/02_exported_postgres_data/teammembers.json'
}

# === Embedding-friendly queries ===
QUERIES = {
    'assignments': """
        SELECT
          'Assignment: ' || tm.name || ' is assigned to product "' || p.name || '" as a "' || r.name ||
          '" with allocation ' || a.allocation || '.' AS embedding_text
        FROM assignments a
        JOIN products p ON a.product_id = p.id
        JOIN roles r ON a.role_id = r.id
        JOIN teammembers tm ON a.teammember_id = tm.id
        WHERE a.is_active = TRUE;
    """,

    'products': """
        SELECT
          'Product: "' || name || '" managed by ' || manager || ', tech exec: ' || technology_executive ||
          ', active: ' || is_active AS embedding_text
        FROM products
        WHERE is_active = TRUE;
    """,

    'roles': """
        SELECT
          'Role: "' || name || '" - ' || description || ', active: ' || is_active AS embedding_text
        FROM roles
        WHERE is_active = TRUE;
    """,

    'skills_matrix': """
        SELECT
          'Skill Matrix: ' || tm.name || ' is ' || sm.skill_level || ' in role "' || r.name || '".' AS embedding_text
        FROM skills_matrix sm
        JOIN teammembers tm ON sm.teammember_id = tm.id
        JOIN roles r ON sm.role_id = r.id
        WHERE sm.is_active = TRUE;
    """,

    'teammembers': """
        SELECT
          'Team Member: ' || name || ', manager: ' || manager || ', level: ' || level ||
          ', active: ' || is_active AS embedding_text
        FROM teammembers
        WHERE is_active = TRUE;
    """
}


def main():
    conn = get_connection()

    for name, query in QUERIES.items():
        print(f"Running query for '{name}'...")
        df = pd.read_sql_query(query, conn)
        records = df['embedding_text'].tolist()

        with open(OUTPUT_FILES[name], 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2)

        print(f"✅ Saved {len(records)} rows to {OUTPUT_FILES[name]}")

    conn.close()


if __name__ == "__main__":
    main()
