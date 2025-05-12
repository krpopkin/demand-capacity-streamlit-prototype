#To run this script:  
# 1. chmod +x deploy.sh in terminal
# 2. ./deploy.sh

#!/usr/bin/env bash
set -euo pipefail

# --- Step 1: Set GCP project ---
gcloud config set project amw-dna-coe-working-ds-dev

# --- Step 2: Change directory to where your Dockerfile is ---
cd "/c/Users/krpop/Documents/KenP/Applications-Python/demand_capacity_app"

# --- Step 3: Build Docker image ---
docker build -t us-central1-docker.pkg.dev/amw-dna-coe-working-ds-dev/demand-capacity-repo/demand-capacity-app .

# --- Step 4: Push Docker image to Artifact Registry ---
docker push us-central1-docker.pkg.dev/amw-dna-coe-working-ds-dev/demand-capacity-repo/demand-capacity-app

# --- Step 5: Deploy to Cloud Run ---
gcloud run deploy demand-capacity-app \
  --image us-central1-docker.pkg.dev/amw-dna-coe-working-ds-dev/demand-capacity-repo/demand-capacity-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8501 \
  --add-cloudsql-instances=amw-dna-coe-working-ds-dev:us-central1:demand-capacity
