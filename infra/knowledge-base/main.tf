terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 6.67" } }
  backend "s3" {}
}
variable "region" { type = string }
variable "name" { type = string }
variable "documents_bucket" { type = string }
provider "aws" { region = var.region }
data "aws_caller_identity" "current" {}
locals { embedding_arn = "arn:aws:bedrock:${var.region}::foundation-model/amazon.titan-embed-text-v2:0" }
resource "aws_s3_bucket" "docs" { bucket = var.documents_bucket }
resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = aws_s3_bucket.docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "docs" {
  bucket = aws_s3_bucket.docs.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3vectors_vector_bucket" "this" { vector_bucket_name = "${var.name}-vectors" }
resource "aws_s3vectors_index" "this" {
  index_name         = "runbooks"
  vector_bucket_name = aws_s3vectors_vector_bucket.this.vector_bucket_name
  data_type          = "float32"
  dimension          = 1024
  distance_metric    = "cosine"
  metadata_configuration { non_filterable_metadata_keys = ["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA"] }
}
resource "aws_iam_role" "kb" {
  name               = "${var.name}-knowledge-base"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "bedrock.amazonaws.com" }, Action = "sts:AssumeRole", Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }, ArnLike = { "aws:SourceArn" = "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*" } } }] })
}
resource "aws_iam_role_policy" "kb" {
  role = aws_iam_role.kb.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = [local.embedding_arn] },
    { Effect = "Allow", Action = ["s3:ListBucket"], Resource = [aws_s3_bucket.docs.arn] },
    { Effect = "Allow", Action = ["s3:GetObject"], Resource = ["${aws_s3_bucket.docs.arn}/runbooks/*"] },
    { Effect = "Allow", Action = ["s3vectors:GetIndex", "s3vectors:QueryVectors", "s3vectors:PutVectors", "s3vectors:DeleteVectors", "s3vectors:GetVectors"], Resource = [aws_s3vectors_index.this.index_arn] }
  ] })
}
resource "aws_bedrockagent_knowledge_base" "this" {
  name     = var.name
  role_arn = aws_iam_role.kb.arn
  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_arn
      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = 1024
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }
  storage_configuration {
    type = "S3_VECTORS"
    s3_vectors_configuration { index_arn = aws_s3vectors_index.this.index_arn }
  }
  depends_on = [aws_iam_role_policy.kb]
}
resource "aws_bedrockagent_data_source" "runbooks" {
  knowledge_base_id    = aws_bedrockagent_knowledge_base.this.id
  name                 = "runbooks"
  data_deletion_policy = "DELETE"
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = aws_s3_bucket.docs.arn
      inclusion_prefixes = ["runbooks/"]
    }
  }
}
output "knowledge_base_id" { value = aws_bedrockagent_knowledge_base.this.id }
output "knowledge_base_arn" { value = aws_bedrockagent_knowledge_base.this.arn }
output "data_source_id" { value = aws_bedrockagent_data_source.runbooks.data_source_id }
output "documents_bucket" { value = aws_s3_bucket.docs.id }
