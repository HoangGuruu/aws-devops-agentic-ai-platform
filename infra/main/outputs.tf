output "cluster_name" { value = module.eks.name }
output "vpc_id" { value = module.network.vpc_id }
output "private_subnet_ids" { value = module.network.private_subnet_ids }
output "github_ci_role_arn" { value = aws_iam_role.github_ci.arn }
output "ecr_urls" { value = { for k, v in aws_ecr_repository.services : k => v.repository_url } }
output "agent_role_arn" { value = try(aws_iam_role.agent[0].arn, null) }
