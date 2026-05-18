# Network module

VPC, VPC-native GKE subnet, Private Service Access (PSA), Cloud NAT, and baseline firewall rules for the RAG platform.

## CIDR plan

Per-environment VPC `rag-platform-{environment}`. Ranges must not overlap.

| Range | Default CIDR | Use |
| ----- | -------------- | --- |
| Nodes (primary subnet) | `10.0.0.0/20` | GKE node IPs |
| Pods (secondary) | `10.4.0.0/14` | VPC-native pod alias IPs |
| Services (secondary) | `10.8.0.0/20` | VPC-native ClusterIP range |
| PSA (global peering) | `10.16.0.0/16` | Cloud SQL private IP via `servicenetworking` |
| Master (future) | `172.16.0.0/28` | Private GKE control plane (not created here) |

Override CIDRs via module variables if multiple VPCs must coexist without collision.

## Resources

- Custom-mode VPC (no auto subnets)
- Regional subnet with pod/service secondary ranges
- PSA global address + `google_service_networking_connection`
- Cloud Router + Cloud NAT (`ALL_SUBNETWORKS_ALL_IP_RANGES`)
- Firewalls: health checks, internal VPC traffic, deny broad ingress

## Dependencies

- APIs: `compute.googleapis.com`, `servicenetworking.googleapis.com`
- PSA connection can take several minutes on first apply
- Cloud SQL (1.5) must use this VPC and wait for PSA before instance create

## Destroy order

GKE cluster → Cloud SQL → PSA connection → NAT → router → firewalls → subnet → global address → VPC

Do not remove PSA while Cloud SQL still uses the peering range.

## Production notes

- Set `enable_flow_logs = true` in prod tfvars
- Private GKE control plane endpoint: configure in GKE module (not this module)
- Access private endpoints via IAP tunnel, bastion, or VPN
