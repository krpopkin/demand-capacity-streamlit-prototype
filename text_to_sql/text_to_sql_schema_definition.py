import json
import pandas as pd
import sys
import os

###################################################################################
# Produce a detailed schema of the postgres db that will optimize results obtained
# when using text to sql. Output the detailed schema as a json file
###################################################################################

# Add parent directory to Python path so that this script can find db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db import get_connection

OUTPUT_FILE = 'text_to_sql/text_to_sql_schema_definition.json'


def fetch_schema_details(conn):
    # Fetch table/column info with descriptions
    column_query = """
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

    # Fetch primary key columns
    primary_key_query = """
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

    # Fetch foreign key relationships
    foreign_key_query = """
        SELECT
            tc.table_name AS source_table,
            kcu.column_name AS source_column,
            ccu.table_name AS target_table,
            ccu.column_name AS target_column
        FROM
            information_schema.table_constraints AS tc
        JOIN
            information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN
            information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE
            constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
    """

    # Fetch table-level descriptions
    table_description_query = """
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

    df_columns = pd.read_sql_query(column_query, conn)
    df_pks = pd.read_sql_query(primary_key_query, conn)
    df_fks = pd.read_sql_query(foreign_key_query, conn)
    df_table_desc = pd.read_sql_query(table_description_query, conn)

    return df_columns, df_pks, df_fks, df_table_desc


def get_sample_values(conn, table, column, limit=3):
    try:
        query = f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT {limit};'
        df = pd.read_sql_query(query, conn)
        return df[column].dropna().astype(str).tolist()
    except Exception:
        return []


def build_schema_json(df_columns, df_pks, df_fks, df_table_desc, conn):
    schema = {}

    for _, row in df_columns.iterrows():
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
    for _, row in df_table_desc.iterrows():
        if row['table_name'] in schema:
            schema[row['table_name']]['description'] = row['table_description']

    # Add primary keys
    for _, row in df_pks.iterrows():
        table = row['table_name']
        column = row['column_name']
        if table in schema:
            schema[table]['primary_keys'].append(column)

    # Add foreign keys
    for _, row in df_fks.iterrows():
        source = row['source_table']
        if source in schema:
            schema[source]['foreign_keys'].append({
                'column': row['source_column'],
                'references_table': row['target_table'],
                'references_column': row['target_column']
            })

    return schema


def main():
    conn = get_connection()
    print("Extracting schema…")

    df_columns, df_pks, df_fks, df_table_desc = fetch_schema_details(conn)
    enriched_schema = build_schema_json(df_columns, df_pks, df_fks, df_table_desc, conn)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(enriched_schema, f, indent=2)

    print(f"✅ Schema exported to {OUTPUT_FILE}")
    conn.close()


if __name__ == "__main__":
    main()
