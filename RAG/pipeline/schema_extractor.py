import json
import pandas as pd
import sys
import os

# Add parent directory to Python path so that this script can find db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from db import get_connection

###############################################################################################
# Export one enriched schema file per table (for RAG), including samples
###############################################################################################

OUTPUT_DIR = 'RAG/data/schema'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_schema_metadata(conn):
    # Column details + comments
    columns_query = """
        SELECT
            cols.table_name,
            cols.column_name,
            cols.data_type,
            cols.is_nullable,
            cols.character_maximum_length,
            pgd.description AS column_description
        FROM
            information_schema.columns cols
        LEFT JOIN
            pg_catalog.pg_statio_all_tables st ON st.relname = cols.table_name
        LEFT JOIN
            pg_catalog.pg_description pgd ON pgd.objoid = st.relid AND pgd.objsubid = cols.ordinal_position
        WHERE
            cols.table_schema = 'public'
        ORDER BY
            cols.table_name, cols.ordinal_position;
    """

    # Primary keys
    pk_query = """
        SELECT
            tc.table_name,
            kcu.column_name
        FROM
            information_schema.table_constraints tc
        JOIN
            information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE
            tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public';
    """

    # Foreign keys
    fk_query = """
        SELECT
            tc.table_name AS source_table,
            kcu.column_name AS source_column,
            ccu.table_name AS target_table,
            ccu.column_name AS target_column
        FROM
            information_schema.table_constraints tc
        JOIN
            information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN
            information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE
            tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
    """

    # Table descriptions
    table_desc_query = """
        SELECT
            c.relname AS table_name,
            obj_description(c.oid) AS table_description
        FROM
            pg_class c
        LEFT JOIN
            pg_namespace n ON n.oid = c.relnamespace
        WHERE
            c.relkind = 'r' AND n.nspname = 'public';
    """

    return {
        'columns': pd.read_sql_query(columns_query, conn),
        'primary_keys': pd.read_sql_query(pk_query, conn),
        'foreign_keys': pd.read_sql_query(fk_query, conn),
        'table_descriptions': pd.read_sql_query(table_desc_query, conn)
    }


def get_sample_values(conn, table, column, limit=3):
    try:
        query = f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT {limit};'
        df = pd.read_sql_query(query, conn)
        return df[column].dropna().astype(str).tolist()
    except Exception:
        return []


def write_table_jsons(metadata, conn):
    schema = {}

    for _, row in metadata['columns'].iterrows():
        table = row['table_name']
        column = row['column_name']

        if table not in schema:
            schema[table] = {
                'description': None,
                'columns': {},
                'primary_keys': [],
                'foreign_keys': []
            }

        sample_values = get_sample_values(conn, table, column)

        schema[table]['columns'][column] = {
            'data_type': row['data_type'],
            'is_nullable': row['is_nullable'],
            'max_length': row['character_maximum_length'],
            'description': row['column_description'],
            'sample_values': sample_values
        }

    # Add table descriptions
    for _, row in metadata['table_descriptions'].iterrows():
        if row['table_name'] in schema:
            schema[row['table_name']]['description'] = row['table_description']

    # Add primary keys
    for _, row in metadata['primary_keys'].iterrows():
        if row['table_name'] in schema:
            schema[row['table_name']]['primary_keys'].append(row['column_name'])

    # Add foreign keys
    for _, row in metadata['foreign_keys'].iterrows():
        if row['source_table'] in schema:
            schema[row['source_table']]['foreign_keys'].append({
                'column': row['source_column'],
                'references_table': row['target_table'],
                'references_column': row['target_column']
            })

    # Write each table to its own file
    for table_name, data in schema.items():
        if table_name != 'history_log':  #exclude history log from RAG
            with open(os.path.join(OUTPUT_DIR, f"{table_name}.json"), 'w') as f:
                json.dump(data, f, indent=2)


def main():
    conn = get_connection()
    print("🔍 Extracting schema per table…")

    metadata = fetch_schema_metadata(conn)
    write_table_jsons(metadata, conn)

    print(f"✅ Individual table schemas saved to: {OUTPUT_DIR}")
    conn.close()

if __name__ == "__main__":
    main()