## [Phase 1] PSA apply — Service Networking API disabled
**Date:** 2026-05-19
**What happened:** `terraform apply -target=module.network` created VPC, subnet, NAT, and PSA global address but failed on `google_service_networking_connection` because `servicenetworking.googleapis.com` was not enabled on project `turbo-rag`.
**Symptoms:** `Error 403: Service Networking API has not been used in project ... or it is disabled`
**What was tried:** Targeted apply without pre-checking API enablement
**Fix:** `gcloud services enable servicenetworking.googleapis.com --project=turbo-rag`, then re-run `terraform apply -target=module.network`
**Rule added:** _(none)_
