import json
import pandas as pd
import sys
import os

# Add parent directory to Python path so that this script can find db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))
from db import get_connection

###############################################################################################
# Export the schema of each table in the demand-capacity postgres database
###############################################################################################

OUTPUT_FILE = 'RAG/01_schema_definition/schema_definition.json'

# === Extract table schemas ===
QUERY = """
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable,
            character_maximum_length
        FROM
            information_schema.columns
        WHERE
            table_schema = 'public'
        ORDER BY
            table_name, ordinal_position;
    """


def main():
    conn = get_connection()

    print(f"Running get_schema query")
    df = pd.read_sql_query(QUERY, conn)
    
    with open(OUTPUT_FILE,'w') as f:
        json.dump(json.loads(df.to_json(orient='records')),f,indent=2)
        
    print('Completed')

    conn.close()


if __name__ == "__main__":
    main()
