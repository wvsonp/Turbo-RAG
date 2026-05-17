Create new project in GCP

gcloud services enable \
  container.googleapis.com \
  sqladmin.googleapis.com \
  pubsub.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  --project=turbo-rag