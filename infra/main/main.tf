locals { prefix = "${var.name}-${var.environment}" }
module "network" {
  source             = "../modules/network"
  name               = local.prefix
  cidr               = var.vpc_cidr
  single_nat_gateway = var.single_nat_gateway
}
module "eks" {
  source              = "../modules/eks"
  name                = local.prefix
  cluster_version     = var.cluster_version
  subnet_ids          = module.network.private_subnet_ids
  allowed_api_cidrs   = var.allowed_api_cidrs
  admin_principal_arn = var.admin_principal_arn
  instance_type       = var.node_instance_type
  desired_size        = var.node_desired_size
  max_size            = var.node_max_size
}
resource "aws_ecr_repository" "services" {
  for_each             = toset(["productpage", "details", "ratings", "reviews"])
  name                 = "${local.prefix}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration { scan_on_push = true }
}
resource "aws_ecr_lifecycle_policy" "untagged" {
  for_each   = aws_ecr_repository.services
  repository = each.value.name
  policy     = jsonencode({ rules = [{ rulePriority = 1, description = "Remove untagged images after seven days", selection = { tagStatus = "untagged", countType = "sinceImagePushed", countUnit = "days", countNumber = 7 }, action = { type = "expire" } }] })
}
resource "aws_iam_role" "github_ci" {
  name               = "${local.prefix}-github-ci"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Federated = var.github_oidc_provider_arn }, Action = "sts:AssumeRoleWithWebIdentity", Condition = { StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com", "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:${var.environment}" } } }] })
}
resource "aws_iam_role_policy" "ecr_publish" {
  role = aws_iam_role.github_ci.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"], Resource = [for r in aws_ecr_repository.services : r.arn] }
  ] })
}
resource "aws_eks_addon" "pod_identity" {
  count        = (var.enable_agent_identity || var.enable_storage || var.enable_load_balancer_controller) ? 1 : 0
  cluster_name = module.eks.name
  addon_name   = "eks-pod-identity-agent"
}
resource "aws_iam_role" "agent" {
  count              = var.enable_agent_identity ? 1 : 0
  name               = "${local.prefix}-agent-readonly"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "pods.eks.amazonaws.com" }, Action = ["sts:AssumeRole", "sts:TagSession"] }] })
  lifecycle {
    precondition {
      condition     = length(var.bedrock_model_arns) > 0
      error_message = "Set exact bedrock_model_arns before enabling the agent."
    }
  }
}
resource "aws_iam_role_policy" "agent" {
  count = var.enable_agent_identity ? 1 : 0
  role  = aws_iam_role.agent[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat(
    [{ Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = var.bedrock_model_arns }],
    var.knowledge_base_arn == "" ? [] : [{ Effect = "Allow", Action = ["bedrock:Retrieve"], Resource = [var.knowledge_base_arn] }]
  ) })
}
resource "aws_eks_pod_identity_association" "agent" {
  count           = var.enable_agent_identity ? 1 : 0
  cluster_name    = module.eks.name
  namespace       = "bookinfo-${var.environment}"
  service_account = "incident-agent"
  role_arn        = aws_iam_role.agent[0].arn
  depends_on      = [aws_eks_addon.pod_identity]
}
