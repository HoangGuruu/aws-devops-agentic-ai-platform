# Official references

Checked 2026-10-02. Release tags were resolved from official GitHub/Helm metadata; a valid release tag is not proof of end-to-end compatibility. Recheck support matrices before a cloud run.

- Original repository: https://github.com/HoangGuruu/devops-on-aws-all-in-one
- Terraform S3 native locking: https://developer.hashicorp.com/terraform/language/backend/s3
- EKS version lifecycle: https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html
- EKS 1.35 availability: https://aws.amazon.com/about-aws/whats-new/2026/01/amazon-eks-distro-kubernetes-version-1-35/
- GitHub OIDC for AWS: https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
- Argo automated sync/rollback restriction: https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/
- Bedrock Converse: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- Bedrock tool-use example: https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_Scenario_ToolUse_section.html
- AgentCore framework entrypoint: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/using-any-agent-framework.html
- AgentCore deployment: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html
- Bedrock KB service role: https://docs.aws.amazon.com/bedrock/latest/userguide/kb-permissions.html
- S3 Vectors + KB: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-bedrock-kb.html
- Provider KB resource: https://github.com/hashicorp/terraform-provider-aws/blob/v6.67.0/website/docs/r/bedrockagent_knowledge_base.html.markdown
- Provider vector index: https://github.com/hashicorp/terraform-provider-aws/blob/v6.67.0/website/docs/r/s3vectors_index.html.markdown
- Gateway infrastructure annotations: https://gateway-api.sigs.k8s.io/guides/user-guides/infrastructure/
- Istio Gateway API: https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/
- AWS LB controller policy source (bundled): https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/install/iam_policy.json

Check versions and results in your own account. Rendering a file successfully does not prove a successful cloud deployment.

- Docker Ubuntu: https://docs.docker.com/engine/install/ubuntu/
- AWS CLI Linux: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
- EKS version query: https://docs.aws.amazon.com/cli/latest/reference/eks/describe-cluster-versions.html
- Bedrock model access: https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html
- Inference profiles: https://docs.aws.amazon.com/cli/latest/reference/bedrock/list-inference-profiles.html
- AgentCore runtime IAM: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html
- AgentCore create API: https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore-control/create-agent-runtime.html
- AgentCore invoke API: https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore/invoke-agent-runtime.html
