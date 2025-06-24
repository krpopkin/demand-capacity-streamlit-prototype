import os
import json
import pandas as pd
from google.cloud import aiplatform_v1
from google.protobuf.struct_pb2 import Struct
from dotenv import load_dotenv 

load_dotenv()

# === CONFIG ===
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
MODEL = os.getenv("MODEL")
INPUT_DIR = os.getenv("INPUT_DIR")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

client = aiplatform_v1.PredictionServiceClient()

def embed(text: str):
    instance = Struct()
    instance.update({
        "task_type": "RETRIEVAL_DOCUMENT",
        "title": "doc",
        "content": text
    })

    response = client.predict(
        endpoint=f"projects/{PROJECT_ID}/locations/{LOCATION}/{MODEL}",
        instances=[instance],
        parameters=Struct()
    )

    return list(response.predictions[0]['embeddings']['values'])

def process_file(file_path, output_path):
    print(f"📄 Processing: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = json.load(f)

    if not isinstance(lines, list):
        raise ValueError(f"File {file_path} must contain a list of strings")

    records = []
    for i, text in enumerate(lines):
        try:
            vec = embed(text)
            records.append({"text": text, "embedding": vec})
        except Exception as e:
            print(f"❌ Error embedding line {i}: {e}")

    df = pd.DataFrame(records)
    df.to_parquet(output_path, index=False)
    print(f"✅ Saved: {output_path} ({len(df)} rows)")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename in os.listdir(INPUT_DIR):
        if not filename.endswith(".json"):
            continue

        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename.replace(".json", ".parquet"))

        process_file(input_path, output_path)
