# ⚠️ DeployFlow — Full AWS demo stack (EXPENSIVE, EPHEMERAL)

This Terraform provisions the **full** AWS architecture from PRD §6.3: VPC, EKS, RDS Postgres, ElastiCache Redis. It's for **a one-time demo / screenshots / a resume video**.

> **Per PRD §4 and §16, this stack MUST NOT be left running 24/7.**
> EKS control plane alone is $72/month. The whole stack lands around **$100–150/month** if you forget. Set budget alerts.

## The intended workflow

1. `terraform apply` (15–20 min for EKS to provision)
2. Apply your Kubernetes manifests (`kubectl apply -f ../../../k8s/`)
3. Open the app in a browser, take screenshots / record a video
4. **`terraform destroy`** (5–10 min)
5. Verify in AWS Cost Explorer that your bill stopped growing
6. Don't repeat for at least a week

## Cost breakdown (rough, us-east-1, single-AZ)

| Resource | Approx. monthly |
|---|---|
| EKS control plane | $72 |
| 2× t3.small EKS nodes (spot) | ~$15 |
| db.t4g.micro RDS (single-AZ) | ~$15 |
| cache.t4g.micro ElastiCache | ~$10 |
| Data transfer + EBS for nodes | $5–15 |
| **Hourly run rate** | **~$0.15/hour** |

A 2-hour demo costs maybe $0.30 — totally reasonable. Leaving it running for a week costs ~$25.

## Apply (after confirming budget alerts exist)

```sh
cd infra/terraform/aws-full-demo
terraform init
TF_VAR_db_password='choose-something-strong' terraform plan
TF_VAR_db_password='choose-something-strong' terraform apply
```

## Connect kubectl

```sh
$(terraform output -raw kubeconfig_command)
kubectl get nodes
```

## Destroy (do this!)

```sh
terraform destroy
```

If `destroy` fails because of dependencies (LBs created by Kubernetes services, ENIs still in use):

```sh
# Delete K8s LoadBalancer services first so AWS frees the ELBs:
kubectl delete svc --all -A
# Wait 30s, then:
terraform destroy
```

## What's deliberately NOT here

- **ALB / CloudFront** — would add another $20/month each. Use `kubectl port-forward` or a temporary LoadBalancer service instead for the demo.
- **NAT Gateway** — $32/month minimum. Public subnets are used instead. PRD §16 explicitly forbids NAT.
- **Multi-AZ** — doubles RDS+ElastiCache cost. Single-AZ is fine for a demo.
- **Long backup retention, deletion protection, snapshots** — all disabled. This is throwaway data.

## Don't be the person who forgot

Set up a CloudWatch billing alarm at $20. Set a calendar reminder for 24 hours after `apply`. Verify the destroy succeeded by checking that the Cost Explorer "this month" total stops increasing.
