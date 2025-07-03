import os
import sys

# === Setup paths ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # One level up from /pipeline
DATA_DIR = os.path.join(BASE_DIR, "data")
SCHEMA_DIR = os.path.join(DATA_DIR, "schema")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
EMBEDDING_DIR = os.path.join(DATA_DIR, "embeddings")

# Add pipeline/ modules to import path
sys.path.append(os.path.join(BASE_DIR, "pipeline"))

# Add root directory to find db.py
sys.path.append(BASE_DIR)

# === Import local modules ===
import schema_extractor
import export_data
import generate_embeddings
import load_to_qdrant

###############################################################################################
# Runs all the scripts under /pipeline to update the vector database with the most recent
# data from the Postgres database.
###############################################################################################

def main():
    print("🔍 Starting schema extraction...")
    schema_extractor.main()

    print("📤 Exporting Postgres data...")
    export_data.main()

    print("🔗 Generating embeddings...")
    generate_embeddings.main()

    print("📦 Uploading to Qdrant...")
    load_to_qdrant.main()

    print("✅ Completed refresh of vector database.")


if __name__ == "__main__":
    main()
