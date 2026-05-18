## Create new project in GCP

activate the apis

`
gcloud services enable \
  container.googleapis.com \
  sqladmin.googleapis.com \
  pubsub.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  --project=turbo-rag
  `


  in the local repo install terraform and gcloud

  cd /home/wvsonp/Turbo-RAG

mkdir -p infra/modules/{gke,cloudsql,artifact_registry,pubsub,secret_manager,iam}
mkdir -p infra/environments

gcloud storage ls gs://rag-platform-tf-state/


Commands after saving files
cd /home/wvsonp/Turbo-RAG/infra
terraform init
terraform validate
terraform plan -var-file=environments/dev.tfvars