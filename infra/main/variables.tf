variable "region" { type = string }
variable "environment" {
  type = string
  validation {
    condition     = contains(["develop", "uat", "staging", "prod"], var.environment)
    error_message = "Choose develop, uat, staging or prod."
  }
}
variable "name" { type = string }
variable "cluster_version" {
  type    = string
  default = "1.35"
}
variable "admin_principal_arn" { type = string }
variable "allowed_api_cidrs" {
  type = list(string)
  validation {
    condition     = length(var.allowed_api_cidrs) > 0 && alltrue([for c in var.allowed_api_cidrs : can(cidrnetmask(c)) && c != "0.0.0.0/0"])
    error_message = "Provide restricted IPv4 CIDRs for the workstation/VPN, never 0.0.0.0/0."
  }
}
variable "vpc_cidr" { type = string }
variable "single_nat_gateway" {
  type    = bool
  default = true
}
variable "node_instance_type" {
  type    = string
  default = "t3.large"
}
variable "node_desired_size" {
  type    = number
  default = 2
}
variable "node_max_size" {
  type    = number
  default = 4
}
variable "github_repository" { type = string }
variable "github_oidc_provider_arn" {
  type        = string
  description = "Existing account-wide GitHub OIDC provider; created once by bootstrap."
}
variable "bedrock_model_arns" {
  type        = list(string)
  default     = []
  description = "Foundation-model and inference-profile ARNs allowed for optional agent."
}
variable "knowledge_base_arn" {
  type    = string
  default = ""
}
variable "enable_agent_identity" {
  type    = bool
  default = false
}
variable "enable_storage" {
  type    = bool
  default = false
}
variable "enable_load_balancer_controller" {
  type    = bool
  default = false
}
